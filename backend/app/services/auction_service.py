import asyncio
from datetime import datetime, timezone
from typing import Optional

from app.models.auction import Auction, AuctionItem, AuctionItemStatus, AuctionStatus, Bid
from app.models.team import Team
from app.websockets.connection_manager import auction_manager


class AuctionService:
    """Handles bid validation, race-condition-safe bid processing, and timer logic."""

    # In-memory locks per auction item to prevent race conditions
    _locks: dict = {}

    def _get_lock(self, item_id: str) -> asyncio.Lock:
        if item_id not in self._locks:
            self._locks[item_id] = asyncio.Lock()
        return self._locks[item_id]

    async def place_bid(
        self,
        auction_item_id: str,
        user_id: str,
        team_id: str,
        amount: float,
    ) -> dict:
        """
        Thread-safe bid placement.
        Returns {"success": bool, "message": str, "bid": BidOut | None}
        """
        lock = self._get_lock(auction_item_id)
        async with lock:
            item = await AuctionItem.get(auction_item_id)
            if not item:
                return {"success": False, "message": "Auction item not found"}
            if item.status != AuctionItemStatus.active:
                return {"success": False, "message": "Item is not currently active"}

            # Validate minimum bid increment (10% above current or base price)
            min_bid = max(item.base_price, item.current_bid) * 1.10
            if item.current_bid == 0:
                min_bid = item.base_price
            if amount < min_bid:
                return {
                    "success": False,
                    "message": f"Bid must be at least {min_bid:,.0f}",
                }

            # Check team budget
            team = await Team.get(team_id)
            if not team:
                return {"success": False, "message": "Team not found"}
            if team.remaining_budget < amount:
                return {"success": False, "message": "Insufficient budget"}

            # Mark previous winning bid as not winning
            if item.highest_bidder_id:
                old_bids = await Bid.find(
                    Bid.auction_item_id == auction_item_id,
                    Bid.is_winning == True,
                ).to_list()
                for b in old_bids:
                    await b.set({"is_winning": False})

            # Create new bid
            bid = Bid(
                auction_item_id=auction_item_id,
                auction_id=item.auction_id,
                user_id=user_id,
                team_id=team_id,
                amount=amount,
                is_winning=True,
            )
            await bid.insert()

            # Update auction item
            await item.set({
                "current_bid": amount,
                "highest_bidder_id": user_id,
                "bid_count": item.bid_count + 1,
                "updated_at": datetime.now(timezone.utc),
            })

            # Broadcast new bid to room
            payload = {
                "type": "new_bid",
                "data": {
                    "auction_item_id": auction_item_id,
                    "amount": amount,
                    "bidder_id": user_id,
                    "team_id": team_id,
                    "bid_count": item.bid_count + 1,
                },
            }
            await auction_manager.broadcast(item.auction_id, payload)
            return {"success": True, "message": "Bid placed", "bid_id": str(bid.id)}

    async def sell_item(self, auction_item_id: str) -> dict:
        """Finalise item — mark sold, deduct team budget, assign player to team."""
        item = await AuctionItem.get(auction_item_id)
        if not item:
            return {"success": False, "message": "Item not found"}

        if item.current_bid == 0 or not item.highest_bidder_id:
            await item.set({"status": AuctionItemStatus.unsold, "updated_at": datetime.now(timezone.utc)})
            payload = {"type": "item_unsold", "data": {"auction_item_id": auction_item_id}}
            await auction_manager.broadcast(item.auction_id, payload)
            return {"success": True, "message": "Item marked unsold"}

        # Deduct budget from winning team
        winning_bid = await Bid.find_one(
            Bid.auction_item_id == auction_item_id, Bid.is_winning == True
        )
        if winning_bid:
            team = await Team.get(winning_bid.team_id)
            if team:
                await team.set({
                    "remaining_budget": team.remaining_budget - item.current_bid,
                    "players": team.players + [item.player_id],
                    "updated_at": datetime.now(timezone.utc),
                })

        await item.set({
            "status": AuctionItemStatus.sold,
            "winning_team_id": winning_bid.team_id if winning_bid else None,
            "sold_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        })

        payload = {
            "type": "item_sold",
            "data": {
                "auction_item_id": auction_item_id,
                "player_id": item.player_id,
                "sold_price": item.current_bid,
                "winning_team_id": winning_bid.team_id if winning_bid else None,
            },
        }
        await auction_manager.broadcast(item.auction_id, payload)
        return {"success": True, "message": "Item sold"}


auction_service = AuctionService()
