from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, OrganizerUser
from app.models.match import Match, MatchStage, MatchStatus
from app.models.team import Team
from app.models.tournament import Tournament
from app.schemas.tournament import (
    FixtureGenerationResponse,
    PlayoffsGenerationResponse,
    PointsTableResponse,
    PointsTableRow,
    TournamentCreate,
    TournamentOut,
    TournamentUpdate,
)

router = APIRouter(prefix="/tournaments", tags=["Tournaments"])


def _out(t: Tournament) -> TournamentOut:
    return TournamentOut(
        id=str(t.id),
        name=t.name,
        description=t.description,
        tournament_type=t.tournament_type,
        status=t.status,
        start_date=t.start_date,
        end_date=t.end_date,
        organizer_id=t.organizer_id,
        max_teams=t.max_teams,
        logo_url=t.logo_url,
        created_at=t.created_at,
    )


async def _compute_points_table_rows(*, tournament_id: str, league_only: bool) -> List[PointsTableRow]:
    teams = await Team.find(Team.tournament_id == tournament_id).to_list()
    team_ids = {str(team.id) for team in teams}
    rows = {
        team_id: {
            "team_id": team_id,
            "played": 0,
            "won": 0,
            "lost": 0,
            "tied": 0,
            "no_result": 0,
            "points": 0,
            "runs_for": 0,
            "overs_for": 0.0,
            "runs_against": 0,
            "overs_against": 0.0,
        }
        for team_id in team_ids
    }

    query = Match.find(Match.tournament_id == tournament_id)
    if league_only:
        query = query.find(Match.stage == MatchStage.league)
    matches = await query.to_list()

    for m in matches:
        t1 = m.team1_id
        t2 = m.team2_id
        if t1 not in rows or t2 not in rows:
            continue

        if m.status == MatchStatus.completed:
            rows[t1]["played"] += 1
            rows[t2]["played"] += 1

            if m.winner_id and m.winner_id in rows:
                winner = m.winner_id
                loser = t1 if winner == t2 else t2
                rows[winner]["won"] += 1
                rows[winner]["points"] += 2
                rows[loser]["lost"] += 1
            else:
                rows[t1]["tied"] += 1
                rows[t2]["tied"] += 1
                rows[t1]["points"] += 1
                rows[t2]["points"] += 1

        elif m.status == MatchStatus.abandoned:
            rows[t1]["played"] += 1
            rows[t2]["played"] += 1
            rows[t1]["no_result"] += 1
            rows[t2]["no_result"] += 1
            rows[t1]["points"] += 1
            rows[t2]["points"] += 1

        if m.innings1 and m.innings2:
            i1 = m.innings1
            i2 = m.innings2
            if i1.team_id in rows and i2.team_id in rows:
                rows[i1.team_id]["runs_for"] += i1.runs
                rows[i1.team_id]["overs_for"] += float(i1.overs)
                rows[i1.team_id]["runs_against"] += i2.runs
                rows[i1.team_id]["overs_against"] += float(i2.overs)

                rows[i2.team_id]["runs_for"] += i2.runs
                rows[i2.team_id]["overs_for"] += float(i2.overs)
                rows[i2.team_id]["runs_against"] += i1.runs
                rows[i2.team_id]["overs_against"] += float(i1.overs)

    out_rows: List[PointsTableRow] = []
    for team_id, r in rows.items():
        rf = r["runs_for"]
        of = r["overs_for"]
        ra = r["runs_against"]
        oa = r["overs_against"]
        nrr = 0.0
        if of > 0 and oa > 0:
            nrr = (rf / of) - (ra / oa)

        out_rows.append(
            PointsTableRow(
                team_id=team_id,
                played=r["played"],
                won=r["won"],
                lost=r["lost"],
                tied=r["tied"],
                no_result=r["no_result"],
                points=r["points"],
                net_run_rate=round(nrr, 3),
            )
        )

    out_rows.sort(key=lambda x: (x.points, x.net_run_rate), reverse=True)
    return out_rows


@router.post("/", response_model=TournamentOut, status_code=status.HTTP_201_CREATED)
async def create_tournament(body: TournamentCreate, current_user: OrganizerUser):
    tournament = Tournament(
        **body.model_dump(),
        organizer_id=str(current_user.id),
    )
    await tournament.insert()
    return _out(tournament)


@router.get("/", response_model=List[TournamentOut])
async def list_tournaments(current_user: CurrentUser, page: int = 1, limit: int = 20):
    limit = max(1, min(100, limit))
    skip = (max(1, page) - 1) * limit
    tournaments = await Tournament.find_all().skip(skip).limit(limit).to_list()
    return [_out(t) for t in tournaments]


@router.get("/{tournament_id}", response_model=TournamentOut)
async def get_tournament(tournament_id: str, current_user: CurrentUser):
    t = await Tournament.get(tournament_id)
    if not t:
        raise HTTPException(status_code=404, detail="Tournament not found")
    return _out(t)


@router.patch("/{tournament_id}", response_model=TournamentOut)
async def update_tournament(tournament_id: str, body: TournamentUpdate, current_user: OrganizerUser):
    t = await Tournament.get(tournament_id)
    if not t:
        raise HTTPException(status_code=404, detail="Tournament not found")
    update_data = body.model_dump(exclude_none=True)
    update_data["updated_at"] = datetime.now(timezone.utc)
    await t.set(update_data)
    return _out(t)


@router.delete("/{tournament_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tournament(tournament_id: str, current_user: OrganizerUser):
    t = await Tournament.get(tournament_id)
    if not t:
        raise HTTPException(status_code=404, detail="Tournament not found")
    await t.delete()


@router.post("/{tournament_id}/generate-fixtures", response_model=FixtureGenerationResponse)
async def generate_fixtures(tournament_id: str, current_user: OrganizerUser):
    t = await Tournament.get(tournament_id)
    if not t:
        raise HTTPException(status_code=404, detail="Tournament not found")

    teams = await Team.find(Team.tournament_id == tournament_id).to_list()
    if len(teams) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 teams to generate fixtures")

    existing = await Match.find(Match.tournament_id == tournament_id).count()
    if existing > 0:
        raise HTTPException(status_code=400, detail="Fixtures already generated")

    # Scheduling: if start_date present, schedule 1 match per day.
    start = t.start_date or datetime.now(timezone.utc)
    match_ids: List[str] = []

    # League fixtures (round-robin)
    if t.tournament_type in ("league", "t20", "odi", "test"):
        day = 0
        for i in range(len(teams)):
            for j in range(i + 1, len(teams)):
                m = Match(
                    tournament_id=tournament_id,
                    team1_id=str(teams[i].id),
                    team2_id=str(teams[j].id),
                    match_date=start + timedelta(days=day),
                    stage=MatchStage.league,
                    status=MatchStatus.scheduled,
                )
                await m.insert()
                match_ids.append(str(m.id))
                day += 1

    # Knockout fixtures (single-elimination placeholders)
    elif t.tournament_type == "knockout":
        ordered = sorted(teams, key=lambda x: str(x.id))
        if len(ordered) % 2 != 0:
            raise HTTPException(status_code=400, detail="Knockout requires an even number of teams")

        day = 0
        if len(ordered) == 2:
            stage = MatchStage.final
        elif len(ordered) == 4:
            stage = MatchStage.semi_final
        else:
            stage = MatchStage.quarter_final
        for i in range(0, len(ordered), 2):
            m = Match(
                tournament_id=tournament_id,
                team1_id=str(ordered[i].id),
                team2_id=str(ordered[i + 1].id),
                match_date=start + timedelta(days=day),
                stage=stage,
                status=MatchStatus.scheduled,
            )
            await m.insert()
            match_ids.append(str(m.id))
            day += 1

    # Hybrid: round-robin league stage first (top-4 knockout is generated later after standings)
    else:
        day = 0
        for i in range(len(teams)):
            for j in range(i + 1, len(teams)):
                m = Match(
                    tournament_id=tournament_id,
                    team1_id=str(teams[i].id),
                    team2_id=str(teams[j].id),
                    match_date=start + timedelta(days=day),
                    stage=MatchStage.league,
                    status=MatchStatus.scheduled,
                )
                await m.insert()
                match_ids.append(str(m.id))
                day += 1

    return FixtureGenerationResponse(
        tournament_id=tournament_id,
        created_matches=len(match_ids),
        match_ids=match_ids,
    )


@router.get("/{tournament_id}/points-table", response_model=PointsTableResponse)
async def points_table(tournament_id: str, current_user: CurrentUser):
    t = await Tournament.get(tournament_id)
    if not t:
        raise HTTPException(status_code=404, detail="Tournament not found")

    league_only = t.tournament_type == "hybrid"
    out_rows = await _compute_points_table_rows(tournament_id=tournament_id, league_only=league_only)
    return PointsTableResponse(tournament_id=tournament_id, rows=out_rows)


@router.post(
    "/{tournament_id}/generate-playoffs/semi-finals",
    response_model=PlayoffsGenerationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_hybrid_semi_finals(tournament_id: str, current_user: OrganizerUser):
    t = await Tournament.get(tournament_id)
    if not t:
        raise HTTPException(status_code=404, detail="Tournament not found")
    if t.tournament_type != "hybrid":
        raise HTTPException(status_code=400, detail="Playoffs generation is only supported for hybrid tournaments")

    teams = await Team.find(Team.tournament_id == tournament_id).to_list()
    if len(teams) < 4:
        raise HTTPException(status_code=400, detail="Need at least 4 teams to generate semi-finals")

    existing_league = await Match.find(
        Match.tournament_id == tournament_id, Match.stage == MatchStage.league
    ).count()
    if existing_league == 0:
        raise HTTPException(status_code=400, detail="Generate league fixtures first")

    existing_playoffs = await Match.find(
        Match.tournament_id == tournament_id, Match.stage.in_([MatchStage.semi_final, MatchStage.final])
    ).count()
    if existing_playoffs > 0:
        raise HTTPException(status_code=400, detail="Playoff fixtures already generated")

    standings = await _compute_points_table_rows(tournament_id=tournament_id, league_only=True)
    if len(standings) < 4:
        raise HTTPException(status_code=400, detail="Not enough teams in points table")

    top4 = standings[:4]
    team1 = top4[0].team_id
    team2 = top4[1].team_id
    team3 = top4[2].team_id
    team4 = top4[3].team_id

    last_match = await Match.find(Match.tournament_id == tournament_id).sort(-Match.match_date).first_or_none()
    base_date = (last_match.match_date if last_match and last_match.match_date else datetime.now(timezone.utc))

    match_ids: List[str] = []
    for idx, (a, b) in enumerate([(team1, team4), (team2, team3)]):
        m = Match(
            tournament_id=tournament_id,
            team1_id=a,
            team2_id=b,
            match_date=base_date + timedelta(days=idx + 1),
            stage=MatchStage.semi_final,
            status=MatchStatus.scheduled,
        )
        await m.insert()
        match_ids.append(str(m.id))

    return PlayoffsGenerationResponse(
        tournament_id=tournament_id,
        stage="semi_final",
        created_matches=len(match_ids),
        match_ids=match_ids,
    )


@router.post(
    "/{tournament_id}/generate-playoffs/final",
    response_model=PlayoffsGenerationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_hybrid_final(tournament_id: str, current_user: OrganizerUser):
    t = await Tournament.get(tournament_id)
    if not t:
        raise HTTPException(status_code=404, detail="Tournament not found")
    if t.tournament_type != "hybrid":
        raise HTTPException(status_code=400, detail="Final generation is only supported for hybrid tournaments")

    existing_final = await Match.find(
        Match.tournament_id == tournament_id, Match.stage == MatchStage.final
    ).count()
    if existing_final > 0:
        raise HTTPException(status_code=400, detail="Final already generated")

    semis = await Match.find(
        Match.tournament_id == tournament_id, Match.stage == MatchStage.semi_final
    ).to_list()
    if len(semis) != 2:
        raise HTTPException(status_code=400, detail="Semi-finals not generated")

    winners: List[str] = []
    for m in semis:
        if m.status != MatchStatus.completed or not m.winner_id:
            raise HTTPException(status_code=400, detail="Semi-finals must be completed with winners before generating final")
        winners.append(m.winner_id)

    last_match = await Match.find(Match.tournament_id == tournament_id).sort(-Match.match_date).first_or_none()
    base_date = (last_match.match_date if last_match and last_match.match_date else datetime.now(timezone.utc))

    final_match = Match(
        tournament_id=tournament_id,
        team1_id=winners[0],
        team2_id=winners[1],
        match_date=base_date + timedelta(days=1),
        stage=MatchStage.final,
        status=MatchStatus.scheduled,
    )
    await final_match.insert()

    return PlayoffsGenerationResponse(
        tournament_id=tournament_id,
        stage="final",
        created_matches=1,
        match_ids=[str(final_match.id)],
    )
