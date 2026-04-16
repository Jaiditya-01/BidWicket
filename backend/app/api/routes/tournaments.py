from typing import List
from fastapi import APIRouter, HTTPException, status
from datetime import datetime, timezone

from app.api.deps import CurrentUser, OrganizerUser
from app.models.tournament import Tournament
from app.schemas.tournament import TournamentCreate, TournamentUpdate, TournamentOut

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


@router.post("/", response_model=TournamentOut, status_code=status.HTTP_201_CREATED)
async def create_tournament(body: TournamentCreate, current_user: OrganizerUser):
    tournament = Tournament(
        **body.model_dump(),
        organizer_id=str(current_user.id),
    )
    await tournament.insert()
    return _out(tournament)


@router.get("/", response_model=List[TournamentOut])
async def list_tournaments(current_user: CurrentUser):
    tournaments = await Tournament.find_all().to_list()
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
