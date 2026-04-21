from typing import List
from fastapi import APIRouter, HTTPException, status
from datetime import datetime, timezone

from app.api.deps import CurrentUser, OrganizerUser, TeamOwnerUser
from app.models.team import Team
from app.models.player import Player
from app.models.match import Match, MatchStatus
from app.models.user import User
from app.schemas.team import TeamCreate, TeamUpdate, TeamOut, TeamHistoryOut

router = APIRouter(prefix="/teams", tags=["Teams"])


async def _out(t: Team) -> TeamOut:
    owner_name = None
    if t.owner_id:
        try:
            u = await User.get(t.owner_id)
            if u:
                owner_name = u.full_name
        except Exception:
            # owner_id may not be a valid ObjectId in some edge cases
            owner_name = None

    return TeamOut(
        id=str(t.id),
        name=t.name,
        short_name=t.short_name,
        owner_id=t.owner_id,
        owner_name=owner_name,
        tournament_id=t.tournament_id,
        budget=t.budget,
        remaining_budget=t.remaining_budget,
        logo_url=t.logo_url,
        home_ground=t.home_ground,
        players=t.players,
        created_at=t.created_at,
    )


@router.post("/", response_model=TeamOut, status_code=status.HTTP_201_CREATED)
async def create_team(body: TeamCreate, current_user: TeamOwnerUser):
    team = Team(
        **body.model_dump(),
        owner_id=str(current_user.id),
        remaining_budget=body.budget,
    )
    await team.insert()
    return await _out(team)


@router.get("/", response_model=List[TeamOut])
async def list_teams(current_user: CurrentUser, tournament_id: str | None = None, page: int = 1, limit: int = 20):
    limit = max(1, min(100, limit))
    skip = (max(1, page) - 1) * limit
    query = Team.find_all() if not tournament_id else Team.find(Team.tournament_id == tournament_id)
    teams = await query.skip(skip).limit(limit).to_list()
    return [await _out(t) for t in teams]


@router.get("/{team_id}", response_model=TeamOut)
async def get_team(team_id: str, current_user: CurrentUser):
    t = await Team.get(team_id)
    if not t:
        raise HTTPException(status_code=404, detail="Team not found")
    return await _out(t)


@router.get("/{team_id}/history", response_model=TeamHistoryOut)
async def team_history(team_id: str, current_user: CurrentUser):
    """Returns win/loss/tie record for the team."""
    t = await Team.get(team_id)
    if not t:
        raise HTTPException(status_code=404, detail="Team not found")

    matches = await Match.find(
        {"$or": [{"team1_id": team_id}, {"team2_id": team_id}]},
        Match.status == MatchStatus.completed,
    ).to_list()

    won = sum(1 for m in matches if m.winner_id == team_id)
    lost = sum(1 for m in matches if m.winner_id and m.winner_id != team_id)
    tied = sum(1 for m in matches if not m.winner_id)
    played = len(matches)

    return TeamHistoryOut(
        team_id=team_id,
        played=played,
        won=won,
        lost=lost,
        tied=tied,
    )


@router.post("/{team_id}/players/{player_id}", response_model=TeamOut)
async def add_player_to_team(team_id: str, player_id: str, current_user: TeamOwnerUser):
    """Manually add a player to team roster (outside auction)."""
    t = await Team.get(team_id)
    if not t:
        raise HTTPException(status_code=404, detail="Team not found")
    if t.owner_id != str(current_user.id) and not any(r in current_user.roles for r in ("admin", "organizer")):
        raise HTTPException(status_code=403, detail="Not your team")
    p = await Player.get(player_id)
    if not p:
        raise HTTPException(status_code=404, detail="Player not found")
    if player_id in t.players:
        raise HTTPException(status_code=400, detail="Player already in team")
    await t.set({"players": t.players + [player_id], "updated_at": datetime.now(timezone.utc)})
    await p.set({"team_id": team_id, "is_available": False, "updated_at": datetime.now(timezone.utc)})
    return await _out(t)


@router.delete("/{team_id}/players/{player_id}", response_model=TeamOut)
async def remove_player_from_team(team_id: str, player_id: str, current_user: TeamOwnerUser):
    """Remove a player from team roster."""
    t = await Team.get(team_id)
    if not t:
        raise HTTPException(status_code=404, detail="Team not found")
    if t.owner_id != str(current_user.id) and not any(r in current_user.roles for r in ("admin", "organizer")):
        raise HTTPException(status_code=403, detail="Not your team")
    if player_id not in t.players:
        raise HTTPException(status_code=404, detail="Player not in team")
    new_roster = [pid for pid in t.players if pid != player_id]
    await t.set({"players": new_roster, "updated_at": datetime.now(timezone.utc)})
    p = await Player.get(player_id)
    if p:
        await p.set({"team_id": None, "is_available": True, "updated_at": datetime.now(timezone.utc)})
    return await _out(t)


@router.patch("/{team_id}", response_model=TeamOut)
async def update_team(team_id: str, body: TeamUpdate, current_user: TeamOwnerUser):
    t = await Team.get(team_id)
    if not t:
        raise HTTPException(status_code=404, detail="Team not found")
    if t.owner_id != str(current_user.id) and not any(r in current_user.roles for r in ("admin", "organizer")):
        raise HTTPException(status_code=403, detail="Not your team")
    update_data = body.model_dump(exclude_none=True)
    if "budget" in update_data and update_data["budget"] != t.budget:
        if not t.players:
            update_data["remaining_budget"] = update_data["budget"]
        else:
            diff = update_data["budget"] - t.budget
            update_data["remaining_budget"] = max(0.0, t.remaining_budget + diff)
    update_data["updated_at"] = datetime.now(timezone.utc)
    await t.set(update_data)
    return await _out(t)


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(team_id: str, current_user: TeamOwnerUser):
    t = await Team.get(team_id)
    if not t:
        raise HTTPException(status_code=404, detail="Team not found")
    if t.owner_id != str(current_user.id) and not any(r in current_user.roles for r in ("admin", "organizer")):
        raise HTTPException(status_code=403, detail="Not your team")
    await t.delete()
