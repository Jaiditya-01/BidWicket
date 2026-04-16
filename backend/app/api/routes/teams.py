from typing import List
from fastapi import APIRouter, HTTPException, status
from datetime import datetime, timezone

from app.api.deps import CurrentUser, OrganizerUser, TeamOwnerUser
from app.models.team import Team
from app.schemas.team import TeamCreate, TeamUpdate, TeamOut

router = APIRouter(prefix="/teams", tags=["Teams"])


def _out(t: Team) -> TeamOut:
    return TeamOut(
        id=str(t.id),
        name=t.name,
        short_name=t.short_name,
        owner_id=t.owner_id,
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
    return _out(team)


@router.get("/", response_model=List[TeamOut])
async def list_teams(current_user: CurrentUser, tournament_id: str | None = None):
    query = Team.find_all() if not tournament_id else Team.find(Team.tournament_id == tournament_id)
    teams = await query.to_list()
    return [_out(t) for t in teams]


@router.get("/{team_id}", response_model=TeamOut)
async def get_team(team_id: str, current_user: CurrentUser):
    t = await Team.get(team_id)
    if not t:
        raise HTTPException(status_code=404, detail="Team not found")
    return _out(t)


@router.patch("/{team_id}", response_model=TeamOut)
async def update_team(team_id: str, body: TeamUpdate, current_user: TeamOwnerUser):
    t = await Team.get(team_id)
    if not t:
        raise HTTPException(status_code=404, detail="Team not found")
    # Only the owner or admin/organizer can edit
    if t.owner_id != str(current_user.id) and not any(r in current_user.roles for r in ("admin", "organizer")):
        raise HTTPException(status_code=403, detail="Not your team")
    update_data = body.model_dump(exclude_none=True)
    update_data["updated_at"] = datetime.now(timezone.utc)
    await t.set(update_data)
    return _out(t)


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(team_id: str, current_user: OrganizerUser):
    t = await Team.get(team_id)
    if not t:
        raise HTTPException(status_code=404, detail="Team not found")
    await t.delete()
