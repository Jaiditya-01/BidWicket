from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, WebSocket, WebSocketDisconnect
from datetime import datetime, timezone

from app.api.deps import CurrentUser, OrganizerUser
from app.models.match import Match, MatchStatus, Commentary
from app.models.notification import NotificationType
from app.models.team import Team
from app.schemas.match import MatchCreate, MatchUpdate, MatchOut, CommentaryCreate
from app.services.notification_service import notification_service
from app.websockets.connection_manager import match_manager
from starlette.concurrency import run_in_threadpool
from app.core.mailer import send_email
from app.core.config import settings

router = APIRouter(prefix="/matches", tags=["Matches"])


def _out(m: Match) -> MatchOut:
    return MatchOut(
        id=str(m.id),
        tournament_id=m.tournament_id,
        team1_id=m.team1_id,
        team2_id=m.team2_id,
        venue=m.venue,
        match_date=m.match_date,
        stage=m.stage,
        status=m.status,
        toss_winner_id=m.toss_winner_id,
        toss_decision=m.toss_decision,
        current_innings=m.current_innings,
        innings1=m.innings1,
        innings2=m.innings2,
        winner_id=m.winner_id,
        result_description=m.result_description,
        highlights_url=m.highlights_url,
        commentary=m.commentary,
        created_at=m.created_at,
    )


@router.post("/", response_model=MatchOut, status_code=status.HTTP_201_CREATED)
async def create_match(body: MatchCreate, current_user: OrganizerUser):
    match = Match(**body.model_dump())
    await match.insert()
    return _out(match)


@router.get("/", response_model=List[MatchOut])
async def list_matches(
    current_user: CurrentUser,
    tournament_id: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
):
    limit = max(1, min(100, limit))
    skip = (max(1, page) - 1) * limit
    query = Match.find(Match.tournament_id == tournament_id) if tournament_id else Match.find_all()
    matches = await query.skip(skip).limit(limit).to_list()
    return [_out(m) for m in matches]


@router.get("/{match_id}", response_model=MatchOut)
async def get_match(match_id: str, current_user: CurrentUser):
    m = await Match.get(match_id)
    if not m:
        raise HTTPException(status_code=404, detail="Match not found")
    return _out(m)


@router.patch("/{match_id}", response_model=MatchOut)
async def update_match(match_id: str, body: MatchUpdate, current_user: OrganizerUser):
    m = await Match.get(match_id)
    if not m:
        raise HTTPException(status_code=404, detail="Match not found")
    old_status = m.status
    old_winner_id = m.winner_id
    update_data = body.model_dump(exclude_none=True)
    update_data["updated_at"] = datetime.now(timezone.utc)
    await m.set(update_data)

    m = await Match.get(match_id)
    if m:
        if old_status != m.status and m.status == MatchStatus.live:
            t1 = await Team.get(m.team1_id)
            t2 = await Team.get(m.team2_id)
            owner_ids = [t.owner_id for t in (t1, t2) if t]
            for owner_id in owner_ids:
                await notification_service.create(
                    user_id=owner_id,
                    notification_type=NotificationType.match_start,
                    title="Match started",
                    message="Your match is now live",
                    related_id=match_id,
                )
            # Email: match start
            if settings.SMTP_HOST:
                for owner_id in owner_ids:
                    from app.models.user import User
                    u = await User.get(owner_id)
                    if u:
                        try:
                            await run_in_threadpool(
                                send_email,
                                to_email=u.email,
                                subject="Your match is now LIVE — BidWicket",
                                html=f"<p>Hi {u.full_name},</p><p>Your match has started! Watch it live on BidWicket.</p>",
                            )
                        except Exception:
                            pass

        if (
            old_status != m.status
            and m.status == MatchStatus.completed
            and m.winner_id
            and m.winner_id != old_winner_id
        ):
            t1 = await Team.get(m.team1_id)
            t2 = await Team.get(m.team2_id)
            owner_ids = [t.owner_id for t in (t1, t2) if t]
            winner_team = await Team.get(m.winner_id)
            for owner_id in owner_ids:
                await notification_service.create(
                    user_id=owner_id,
                    notification_type=NotificationType.match_result,
                    title="Match result",
                    message=f"Winner: {winner_team.name if winner_team else m.winner_id}",
                    related_id=match_id,
                )
            # Email: match result
            if settings.SMTP_HOST:
                for owner_id in owner_ids:
                    from app.models.user import User
                    u = await User.get(owner_id)
                    if u:
                        try:
                            await run_in_threadpool(
                                send_email,
                                to_email=u.email,
                                subject="Match Result — BidWicket",
                                html=f"<p>Hi {u.full_name},</p><p>Match completed. Winner: <b>{winner_team.name if winner_team else 'N/A'}</b>.</p>",
                            )
                        except Exception:
                            pass

    await match_manager.broadcast(match_id, {"type": "score_update", "data": _out(m).model_dump()})
    return _out(m)


@router.post("/{match_id}/commentary", response_model=MatchOut)
async def add_commentary(match_id: str, body: CommentaryCreate, current_user: OrganizerUser):
    m = await Match.get(match_id)
    if not m:
        raise HTTPException(status_code=404, detail="Match not found")

    entry = Commentary(**body.model_dump())
    m.commentary.append(entry)

    # Determine which innings to update
    from app.models.match import InningsScore, BatterScore, BowlerScore
    
    if m.current_innings == 1:
        if m.innings1 is None:
            # Figure out who the default batting and bowling teams are.
            # If toss decision is bat, toss winner bats first.
            if m.toss_decision == "bat" and m.toss_winner_id == m.team1_id:
                batting_team = m.team1_id
                bowling_team = m.team2_id
            elif m.toss_decision == "bowl" and m.toss_winner_id == m.team1_id:
                batting_team = m.team2_id
                bowling_team = m.team1_id
            elif m.toss_decision == "bat" and m.toss_winner_id == m.team2_id:
                batting_team = m.team2_id
                bowling_team = m.team1_id
            elif m.toss_decision == "bowl" and m.toss_winner_id == m.team2_id:
                batting_team = m.team1_id
                bowling_team = m.team2_id
            else:
                # Fallback if toss isn't recorded
                batting_team = m.team1_id
                bowling_team = m.team2_id
                
            m.innings1 = InningsScore(batting_team_id=batting_team, bowling_team_id=bowling_team)
        else:
            if not m.innings1.batting_team_id and m.innings1.team_id:
                m.innings1.batting_team_id = m.innings1.team_id
                m.innings1.bowling_team_id = m.team2_id if m.innings1.team_id == m.team1_id else m.team1_id
        current_inning = m.innings1
    else:
        if m.innings2 is None:
            prev_batting = m.innings1.batting_team_id or m.innings1.team_id
            batting_team = m.team2_id if prev_batting == m.team1_id else m.team1_id
            bowling_team = prev_batting
            m.innings2 = InningsScore(batting_team_id=batting_team, bowling_team_id=bowling_team)
        current_inning = m.innings2

    # Update Team Score
    current_inning.runs += body.runs_scored
    if body.wicket:
        current_inning.wickets += 1
    current_inning.overs = body.over

    # Update Batter Stats
    if body.batter_id:
        batter = next((b for b in current_inning.batters if b.player_id == body.batter_id), None)
        if not batter:
            batter = BatterScore(player_id=body.batter_id)
            current_inning.batters.append(batter)
        
        batter.runs += body.runs_scored
        batter.balls_faced += 1
        if body.runs_scored == 4:
            batter.fours += 1
        elif body.runs_scored == 6:
            batter.sixes += 1
        if body.wicket:
            batter.is_out = True

    # Update Bowler Stats
    if body.bowler_id:
        bowler = next((b for b in current_inning.bowlers if b.player_id == body.bowler_id), None)
        if not bowler:
            bowler = BowlerScore(player_id=body.bowler_id)
            current_inning.bowlers.append(bowler)
        
        bowler.overs = body.over
        bowler.runs_conceded += body.runs_scored
        if body.wicket:
            bowler.wickets += 1

    m.updated_at = datetime.now(timezone.utc)
    await m.save()

    # Broadcast commentary to all viewers
    payload = {"type": "commentary_update", "data": entry.model_dump()}
    await match_manager.broadcast(match_id, payload)

    # Broadcast updated scoreboard to all viewers
    await match_manager.broadcast(match_id, {"type": "score_update", "data": _out(m).model_dump()})

    # Emit dedicated wicket_update event
    if body.wicket:
        wicket_payload = {
            "type": "wicket_update",
            "data": {
                "match_id": match_id,
                "over": body.over,
                "description": body.ball_description,
            },
        }
        await match_manager.broadcast(match_id, wicket_payload)

    return _out(m)


@router.delete("/{match_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_match(match_id: str, current_user: OrganizerUser):
    m = await Match.get(match_id)
    if not m:
        raise HTTPException(status_code=404, detail="Match not found")
    await m.delete()


# ── WebSocket: live match updates ─────────────────────────────────────────────
@router.websocket("/{match_id}/ws")
async def match_websocket(websocket: WebSocket, match_id: str):
    await match_manager.connect(match_id, websocket)
    try:
        while True:
            await websocket.receive_text()  # keep-alive ping
    except WebSocketDisconnect:
        match_manager.disconnect(match_id, websocket)
