from typing import List
from fastapi import APIRouter, HTTPException, status, WebSocket, WebSocketDisconnect
from datetime import datetime, timezone

from app.api.deps import CurrentUser, OrganizerUser
from app.models.match import Match, Commentary
from app.schemas.match import MatchCreate, MatchUpdate, MatchOut, CommentaryCreate
from app.websockets.connection_manager import match_manager

router = APIRouter(prefix="/matches", tags=["Matches"])


def _out(m: Match) -> MatchOut:
    return MatchOut(
        id=str(m.id),
        tournament_id=m.tournament_id,
        team1_id=m.team1_id,
        team2_id=m.team2_id,
        venue=m.venue,
        match_date=m.match_date,
        status=m.status,
        toss_winner_id=m.toss_winner_id,
        toss_decision=m.toss_decision,
        innings1=m.innings1,
        innings2=m.innings2,
        winner_id=m.winner_id,
        result_description=m.result_description,
        commentary=m.commentary,
        created_at=m.created_at,
    )


@router.post("/", response_model=MatchOut, status_code=status.HTTP_201_CREATED)
async def create_match(body: MatchCreate, current_user: OrganizerUser):
    match = Match(**body.model_dump())
    await match.insert()
    return _out(match)


@router.get("/", response_model=List[MatchOut])
async def list_matches(current_user: CurrentUser, tournament_id: str | None = None):
    query = Match.find(Match.tournament_id == tournament_id) if tournament_id else Match.find_all()
    matches = await query.to_list()
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
    update_data = body.model_dump(exclude_none=True)
    update_data["updated_at"] = datetime.now(timezone.utc)
    await m.set(update_data)

    # Broadcast score update via WebSocket
    await match_manager.broadcast(match_id, {"type": "score_update", "data": _out(m).model_dump()})
    return _out(m)


@router.post("/{match_id}/commentary", response_model=MatchOut)
async def add_commentary(match_id: str, body: CommentaryCreate, current_user: OrganizerUser):
    m = await Match.get(match_id)
    if not m:
        raise HTTPException(status_code=404, detail="Match not found")

    entry = Commentary(**body.model_dump())
    m.commentary.append(entry)
    m.updated_at = datetime.now(timezone.utc)
    await m.save()

    payload = {"type": "commentary", "data": entry.model_dump()}
    await match_manager.broadcast(match_id, payload)
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
