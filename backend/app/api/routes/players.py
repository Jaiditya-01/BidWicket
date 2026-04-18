from typing import List
from fastapi import APIRouter, HTTPException, status
from datetime import datetime, timezone

from app.api.deps import CurrentUser, OrganizerUser, TeamOwnerUser
from app.models.player import Player, PlayerStats
from app.schemas.player import PlayerCreate, PlayerUpdate, PlayerOut, PlayerStatsOut

router = APIRouter(prefix="/players", tags=["Players"])


def _out(p: Player) -> PlayerOut:
    return PlayerOut(
        id=str(p.id),
        name=p.name,
        country=p.country,
        age=p.age,
        role=p.role,
        batting_style=p.batting_style,
        bowling_style=p.bowling_style,
        bio=p.bio,
        photo_url=p.photo_url,
        base_price=p.base_price,
        stats=p.stats,
        team_id=p.team_id,
        is_available=p.is_available,
        created_at=p.created_at,
    )


@router.post("/", response_model=PlayerOut, status_code=status.HTTP_201_CREATED)
async def create_player(body: PlayerCreate, current_user: TeamOwnerUser):
    player = Player(
        **body.model_dump(exclude={"stats"}),
        stats=body.stats or PlayerStats(),
    )
    await player.insert()
    return _out(player)


@router.get("/rankings", response_model=List[PlayerOut])
async def player_rankings(current_user: CurrentUser, by: str = "runs", limit: int = 20):
    """Rank players by a stat field: runs, wickets, average, strike_rate, economy_rate."""
    limit = max(1, min(100, limit))
    valid_fields = {"runs", "wickets", "average", "strike_rate", "economy_rate", "matches", "centuries"}
    sort_field = by if by in valid_fields else "runs"
    players = (
        await Player.find_all()
        .sort(f"-stats.{sort_field}")
        .limit(limit)
        .to_list()
    )
    return [_out(p) for p in players]


@router.get("/", response_model=List[PlayerOut])
async def list_players(
    current_user: CurrentUser,
    role: str | None = None,
    is_available: bool | None = None,
    country: str | None = None,
    team_id: str | None = None,
    page: int = 1,
    limit: int = 20,
):
    limit = max(1, min(100, limit))
    skip = (max(1, page) - 1) * limit
    query: dict = {}
    if role:
        query["role"] = role
    if is_available is not None:
        query["is_available"] = is_available
    if country:
        query["country"] = country
    if team_id:
        query["team_id"] = team_id

    players = await Player.find(query).skip(skip).limit(limit).to_list()
    return [_out(p) for p in players]


@router.get("/{player_id}/stats", response_model=PlayerStatsOut)
async def get_player_stats(player_id: str, current_user: CurrentUser):
    p = await Player.get(player_id)
    if not p:
        raise HTTPException(status_code=404, detail="Player not found")
    return PlayerStatsOut(
        player_id=player_id,
        name=p.name,
        **p.stats.model_dump(),
    )


@router.get("/{player_id}", response_model=PlayerOut)
async def get_player(player_id: str, current_user: CurrentUser):
    p = await Player.get(player_id)
    if not p:
        raise HTTPException(status_code=404, detail="Player not found")
    return _out(p)


@router.patch("/{player_id}", response_model=PlayerOut)
async def update_player(player_id: str, body: PlayerUpdate, current_user: TeamOwnerUser):
    p = await Player.get(player_id)
    if not p:
        raise HTTPException(status_code=404, detail="Player not found")
    update_data = body.model_dump(exclude_none=True)
    update_data["updated_at"] = datetime.now(timezone.utc)
    await p.set(update_data)
    return _out(p)


@router.delete("/{player_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_player(player_id: str, current_user: TeamOwnerUser):
    p = await Player.get(player_id)
    if not p:
        raise HTTPException(status_code=404, detail="Player not found")
    await p.delete()
