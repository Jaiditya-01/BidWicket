from typing import List
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status
from datetime import datetime, timezone

from app.api.deps import CurrentUser, OrganizerUser, TeamOwnerUser
from app.models.auction import Auction, AuctionItem, AuctionStatus, AuctionItemStatus, Bid
from app.schemas.auction import (
    AuctionCreate, AuctionUpdate, AuctionOut,
    AuctionItemCreate, AuctionItemOut,
    PlaceBidRequest, BidOut,
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
        status=i.status, bid_count=i.bid_count, sold_at=i.sold_at,
    )


# ── Auction CRUD ───────────────────────────────────────────────────────────────

@router.post("/", response_model=AuctionOut, status_code=status.HTTP_201_CREATED)
async def create_auction(body: AuctionCreate, current_user: OrganizerUser):
    auction = Auction(**body.model_dump())
    await auction.insert()
    return _auction_out(auction)


@router.get("/", response_model=List[AuctionOut])
async def list_auctions(current_user: CurrentUser):
    return [_auction_out(a) for a in await Auction.find_all().to_list()]


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
    await item.set({"status": AuctionItemStatus.active, "updated_at": datetime.now(timezone.utc)})
    a = await Auction.get(auction_id)
    await a.set({"current_item_id": item_id, "updated_at": datetime.now(timezone.utc)})
    await auction_manager.broadcast(auction_id, {"type": "item_activated", "item_id": item_id, "base_price": item.base_price, "player_id": item.player_id})
    return _item_out(item)


@router.post("/{auction_id}/items/{item_id}/sell")
async def sell_item(auction_id: str, item_id: str, current_user: OrganizerUser):
    result = await auction_service.sell_item(item_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


# ── Bidding ────────────────────────────────────────────────────────────────────

@router.post("/{auction_id}/items/{item_id}/bid")
async def place_bid(auction_id: str, item_id: str, body: PlaceBidRequest, current_user: TeamOwnerUser):
    result = await auction_service.place_bid(
        auction_item_id=item_id,
        user_id=str(current_user.id),
        team_id=body.team_id,
        amount=body.amount,
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
            await websocket.receive_text()  # keep-alive
    except WebSocketDisconnect:
        auction_manager.disconnect(auction_id, websocket)
