import json
from typing import List

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from datetime import datetime, timedelta, timezone
from starlette.concurrency import run_in_threadpool

from app.api.deps import CurrentUser, OrganizerUser, TeamOwnerUser
from app.core.config import settings
from app.core.mailer import send_email
from app.core.rate_limiter import rate_limit_or_429
from app.models.auction import Auction, AuctionItem, AuctionStatus, AuctionItemStatus, Bid
from app.models.player import Player
from app.models.team import Team
from app.models.user import User
from app.schemas.auction import (
    AuctionCreate, AuctionUpdate, AuctionOut,
    AuctionItemCreate, AuctionItemOut,
    BidOut,
    ForceSellRequest,
    PlaceBidRequest,
    ResetTimerRequest,
)
from app.services.auction_service import auction_service
from app.websockets.connection_manager import auction_manager

router = APIRouter(prefix="/auctions", tags=["Auctions"])


# ── Helpers ────────────────────────────────────────────────────────────────────

def _auction_out(a: Auction) -> AuctionOut:
    return AuctionOut(
        id=str(a.id), tournament_id=a.tournament_id, name=a.name,
        status=a.status, bid_timer_seconds=a.bid_timer_seconds,
        current_item_id=a.current_item_id, scheduled_at=a.scheduled_at,
        started_at=a.started_at, ended_at=a.ended_at, created_at=a.created_at,
    )


def _item_out(i: AuctionItem) -> AuctionItemOut:
    return AuctionItemOut(
        id=str(i.id), auction_id=i.auction_id, player_id=i.player_id,
        base_price=i.base_price, current_bid=i.current_bid,
        highest_bidder_id=i.highest_bidder_id, winning_team_id=i.winning_team_id,
        status=i.status, bid_count=i.bid_count,
        activated_at=i.activated_at, ends_at=i.ends_at,
        sold_at=i.sold_at, finalized_at=i.finalized_at,
    )


# ── Auction CRUD ───────────────────────────────────────────────────────────────

@router.post("/", response_model=AuctionOut, status_code=status.HTTP_201_CREATED)
async def create_auction(body: AuctionCreate, current_user: OrganizerUser):
    auction = Auction(**body.model_dump())
    await auction.insert()
    return _auction_out(auction)


@router.get("/", response_model=List[AuctionOut])
async def list_auctions(current_user: CurrentUser, page: int = 1, limit: int = 20):
    limit = max(1, min(100, limit))
    skip = (max(1, page) - 1) * limit
    return [_auction_out(a) for a in await Auction.find_all().skip(skip).limit(limit).to_list()]


@router.get("/{auction_id}", response_model=AuctionOut)
async def get_auction(auction_id: str, current_user: CurrentUser):
    a = await Auction.get(auction_id)
    if not a:
        raise HTTPException(status_code=404, detail="Auction not found")
    return _auction_out(a)


@router.patch("/{auction_id}", response_model=AuctionOut)
async def update_auction(auction_id: str, body: AuctionUpdate, current_user: OrganizerUser):
    a = await Auction.get(auction_id)
    if not a:
        raise HTTPException(status_code=404, detail="Auction not found")
    data = body.model_dump(exclude_none=True)
    data["updated_at"] = datetime.now(timezone.utc)
    if body.status == AuctionStatus.live and not a.started_at:
        data["started_at"] = datetime.now(timezone.utc)
    if body.status == AuctionStatus.completed and not a.ended_at:
        data["ended_at"] = datetime.now(timezone.utc)
    await a.set(data)
    await auction_manager.broadcast(auction_id, {"type": "auction_status", "status": a.status})
    return _auction_out(a)


@router.post("/{auction_id}/start", response_model=AuctionOut)
async def start_auction(auction_id: str, current_user: OrganizerUser):
    """Explicitly start an auction (set status to live)."""
    a = await Auction.get(auction_id)
    if not a:
        raise HTTPException(status_code=404, detail="Auction not found")
    if a.status == AuctionStatus.live:
        raise HTTPException(status_code=400, detail="Auction already live")
    now = datetime.now(timezone.utc)
    await a.set({"status": AuctionStatus.live, "started_at": now, "updated_at": now})
    await auction_manager.broadcast(auction_id, {"type": "auction_status", "status": "live"})
    return _auction_out(a)


@router.post("/{auction_id}/finalize", response_model=AuctionOut)
async def finalize_auction(auction_id: str, current_user: OrganizerUser):
    """Explicitly finalize (complete) an auction."""
    a = await Auction.get(auction_id)
    if not a:
        raise HTTPException(status_code=404, detail="Auction not found")
    if a.status == AuctionStatus.completed:
        raise HTTPException(status_code=400, detail="Auction already completed")
    now = datetime.now(timezone.utc)
    # Finalize any active items first
    if a.current_item_id:
        await auction_service.finalize_item(a.current_item_id, reason="auction_finalized")
    await a.set({"status": AuctionStatus.completed, "ended_at": now, "current_item_id": None, "updated_at": now})
    await auction_manager.broadcast(auction_id, {"type": "auction_finalized", "auction_id": auction_id})
    return _auction_out(a)


@router.post("/{auction_id}/reset", response_model=AuctionOut)
async def reset_auction(auction_id: str, current_user: OrganizerUser):
    """Reset all items in an auction back to pending so bidding can start fresh."""
    a = await Auction.get(auction_id)
    if not a:
        raise HTTPException(status_code=404, detail="Auction not found")

    now = datetime.now(timezone.utc)
    items = await AuctionItem.find(AuctionItem.auction_id == auction_id).to_list()

    for item in items:
        # Reverse sold items: restore budget and remove player from team
        if item.status == AuctionItemStatus.sold and item.winning_team_id:
            team = await Team.get(item.winning_team_id)
            if team:
                restored_budget = team.remaining_budget + item.current_bid
                new_players = [pid for pid in team.players if pid != item.player_id]
                await team.set({"remaining_budget": restored_budget, "players": new_players, "updated_at": now})
            # Also clear the player's team assignment so roster queries are correct
            reset_player = await Player.get(item.player_id)
            if reset_player:
                await reset_player.set({"team_id": None, "is_available": True, "updated_at": now})

        # Delete all bids for this item
        old_bids = await Bid.find(Bid.auction_item_id == str(item.id)).to_list()
        for b in old_bids:
            await b.delete()

        # Reset item to pending
        await item.set({
            "status": AuctionItemStatus.pending,
            "current_bid": 0.0,
            "highest_bidder_id": None,
            "winning_team_id": None,
            "bid_count": 0,
            "activated_at": None,
            "ends_at": None,
            "sold_at": None,
            "finalized_at": None,
            "updated_at": now,
        })

    # Reset auction state but keep it live
    await a.set({"current_item_id": None, "updated_at": now})
    await auction_manager.broadcast(auction_id, {"type": "auction_reset"})
    return _auction_out(a)


@router.delete("/{auction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_auction(auction_id: str, current_user: OrganizerUser):
    a = await Auction.get(auction_id)
    if not a:
        raise HTTPException(status_code=404, detail="Auction not found")

    # Use raw dict queries for reliable string-field matching across Beanie versions
    items = await AuctionItem.find({"auction_id": auction_id}).to_list()
    now = datetime.now(timezone.utc)
    for item in items:
        # Reverse item actions: refund budget and release player
        if item.status == AuctionItemStatus.sold and item.winning_team_id:
            team = await Team.get(item.winning_team_id)
            if team:
                restored_budget = team.remaining_budget + item.current_bid
                new_players = [pid for pid in team.players if pid != item.player_id]
                await team.set({"remaining_budget": restored_budget, "players": new_players, "updated_at": now})

        reset_player = await Player.get(item.player_id)
        if reset_player:
            await reset_player.set({"team_id": None, "is_available": True, "updated_at": now})

        # Delete each item's bids
        item_bids = await Bid.find({"auction_item_id": str(item.id)}).to_list()
        for bid in item_bids:
            await bid.delete()
            
        await item.delete()

    # Delete any remaining bids by auction_id
    bids = await Bid.find({"auction_id": auction_id}).to_list()
    for bid in bids:
        await bid.delete()

    await a.delete()


# ── Auction Items ──────────────────────────────────────────────────────────────

@router.post("/{auction_id}/items", response_model=AuctionItemOut, status_code=status.HTTP_201_CREATED)
async def add_auction_item(auction_id: str, body: AuctionItemCreate, current_user: OrganizerUser):
    a = await Auction.get(auction_id)
    if not a:
        raise HTTPException(status_code=404, detail="Auction not found")
    item = AuctionItem(auction_id=auction_id, player_id=body.player_id, base_price=body.base_price)
    await item.insert()
    return _item_out(item)


@router.get("/{auction_id}/items", response_model=List[AuctionItemOut])
async def list_auction_items(auction_id: str, current_user: CurrentUser):
    items = await AuctionItem.find(AuctionItem.auction_id == auction_id).to_list()
    return [_item_out(i) for i in items]


@router.post("/{auction_id}/items/{item_id}/activate", response_model=AuctionItemOut)
async def activate_item(auction_id: str, item_id: str, current_user: OrganizerUser):
    item = await AuctionItem.get(item_id)
    if not item or item.auction_id != auction_id:
        raise HTTPException(status_code=404, detail="Item not found")
    a = await Auction.get(auction_id)
    if not a:
        raise HTTPException(status_code=404, detail="Auction not found")
    if a.status != AuctionStatus.live:
        raise HTTPException(status_code=400, detail="Auction must be live to activate items")

    now = datetime.now(timezone.utc)
    ends_at = now + timedelta(seconds=a.bid_timer_seconds)

    # If this item was previously sold, reverse the sale (restore budget + remove player from team)
    if item.status == AuctionItemStatus.sold and item.winning_team_id:
        team = await Team.get(item.winning_team_id)
        if team:
            restored_budget = team.remaining_budget + item.current_bid
            new_players = [pid for pid in team.players if pid != item.player_id]
            await team.set({"remaining_budget": restored_budget, "players": new_players, "updated_at": now})
        # Clear the player's team assignment so roster queries are correct
        restart_player = await Player.get(item.player_id)
        if restart_player:
            await restart_player.set({"team_id": None, "is_available": True, "updated_at": now})

    # Delete all previous bids for this item so bidding starts fresh
    old_bids = await Bid.find(Bid.auction_item_id == item_id).to_list()
    for b in old_bids:
        await b.delete()

    # Reset the item completely and activate it
    await item.set(
        {
            "status": AuctionItemStatus.active,
            "current_bid": 0.0,
            "highest_bidder_id": None,
            "winning_team_id": None,
            "bid_count": 0,
            "sold_at": None,
            "finalized_at": None,
            "activated_at": now,
            "ends_at": ends_at,
            "updated_at": now,
        }
    )
    await a.set({"current_item_id": item_id, "updated_at": datetime.now(timezone.utc)})
    await auction_service.start_item_timer(auction_id=auction_id, auction_item_id=item_id)
    await auction_manager.broadcast(auction_id, {"type": "item_activated", "item_id": item_id, "base_price": item.base_price, "player_id": item.player_id})
    return _item_out(item)


@router.post("/{auction_id}/items/{item_id}/sell")
async def sell_item(auction_id: str, item_id: str, current_user: OrganizerUser):
    item = await AuctionItem.get(item_id)
    if not item or item.auction_id != auction_id:
        raise HTTPException(status_code=404, detail="Item not found")
    result = await auction_service.sell_item(item_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.post("/{auction_id}/items/{item_id}/force-sell")
async def force_sell_item(auction_id: str, item_id: str, body: ForceSellRequest, current_user: OrganizerUser):
    item = await AuctionItem.get(item_id)
    if not item or item.auction_id != auction_id:
        raise HTTPException(status_code=404, detail="Item not found")
    result = await auction_service.force_sell(item_id, team_id=body.team_id, amount=body.amount)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.post("/{auction_id}/items/{item_id}/unsold")
async def mark_item_unsold(auction_id: str, item_id: str, current_user: OrganizerUser):
    item = await AuctionItem.get(item_id)
    if not item or item.auction_id != auction_id:
        raise HTTPException(status_code=404, detail="Item not found")
    result = await auction_service.mark_unsold(item_id, reason="manual")
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.post("/{auction_id}/items/{item_id}/reset-timer")
async def reset_item_timer(auction_id: str, item_id: str, body: ResetTimerRequest, current_user: OrganizerUser):
    item = await AuctionItem.get(item_id)
    if not item or item.auction_id != auction_id:
        raise HTTPException(status_code=404, detail="Item not found")
    result = await auction_service.reset_timer(item_id, seconds=body.seconds)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


# ── Bidding ────────────────────────────────────────────────────────────────────

@router.post("/{auction_id}/items/{item_id}/bid")
async def place_bid(auction_id: str, item_id: str, body: PlaceBidRequest, current_user: TeamOwnerUser, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_or_429(f"bid:ip:{client_ip}", capacity=30, refill_per_sec=30 / 60)
    rate_limit_or_429(f"bid:user:{str(current_user.id)}", capacity=20, refill_per_sec=20 / 60)
    rate_limit_or_429(f"bid:team:{body.team_id}", capacity=30, refill_per_sec=30 / 60)
    result = await auction_service.place_bid(
        auction_item_id=item_id,
        user_id=str(current_user.id),
        team_id=body.team_id,
        amount=body.amount,
        user_roles=current_user.roles,
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.get("/{auction_id}/items/{item_id}/bids", response_model=List[BidOut])
async def list_bids(auction_id: str, item_id: str, current_user: CurrentUser):
    bids = await Bid.find(Bid.auction_item_id == item_id).to_list()
    return [
        BidOut(
            id=str(b.id), auction_item_id=b.auction_item_id, auction_id=b.auction_id,
            user_id=b.user_id, team_id=b.team_id, amount=b.amount,
            is_winning=b.is_winning, timestamp=b.timestamp,
        )
        for b in bids
    ]


# ── WebSocket: real-time auction room ─────────────────────────────────────────

@router.websocket("/{auction_id}/ws")
async def auction_websocket(websocket: WebSocket, auction_id: str):
    await auction_manager.connect(auction_id, websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except Exception:
                await auction_manager.send_personal(websocket, {"type": "error", "message": "Invalid JSON"})
                continue

            if not isinstance(msg, dict) or "type" not in msg:
                await auction_manager.send_personal(websocket, {"type": "error", "message": "Invalid message format"})
                continue

            mtype = msg.get("type")
            if mtype == "ping":
                await auction_manager.send_personal(websocket, {"type": "pong"})
                continue

            if mtype == "get_state":
                a = await Auction.get(auction_id)
                current_item = await AuctionItem.get(a.current_item_id) if a and a.current_item_id else None
                await auction_manager.send_personal(
                    websocket,
                    {
                        "type": "state",
                        "data": {
                            "auction": _auction_out(a).model_dump() if a else None,
                            "current_item": _item_out(current_item).model_dump() if current_item else None,
                        },
                    },
                )
                continue

            await auction_manager.send_personal(websocket, {"type": "error", "message": "Unknown message type"})
    except WebSocketDisconnect:
        auction_manager.disconnect(auction_id, websocket)
