import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.models.auction import Auction, AuctionItem, AuctionItemStatus, AuctionStatus, Bid
from app.models.notification import NotificationType
from app.models.player import Player
from app.models.team import Team
from app.models.user import User
from app.services.notification_service import notification_service
from app.websockets.connection_manager import auction_manager


class AuctionService:
    """Handles bid validation, race-condition-safe bid processing, and timer logic."""

    # In-memory locks per auction item to prevent race conditions
    _locks: dict = {}
    _timer_tasks: dict = {}

    def _get_lock(self, item_id: str) -> asyncio.Lock:
        if item_id not in self._locks:
            self._locks[item_id] = asyncio.Lock()
        return self._locks[item_id]

    async def _broadcast_timer(self, *, auction_id: str, auction_item_id: str):
        item = await AuctionItem.get(auction_item_id)
        if not item or not item.ends_at:
            return
        remaining = int(max(0.0, (item.ends_at - datetime.now(timezone.utc)).total_seconds()))
        await auction_manager.broadcast(
            auction_id,
            {
                "type": "timer_tick",
                "data": {"auction_item_id": auction_item_id, "remaining_seconds": remaining, "ends_at": item.ends_at},
            },
        )

    def _cancel_timer_task(self, auction_item_id: str):
        task = self._timer_tasks.get(auction_item_id)
        if task and not task.done():
            task.cancel()
        self._timer_tasks.pop(auction_item_id, None)

    async def start_item_timer(self, *, auction_id: str, auction_item_id: str):
        self._cancel_timer_task(auction_item_id)

        async def _runner():
            try:
                while True:
                    item = await AuctionItem.get(auction_item_id)
                    if not item or item.status != AuctionItemStatus.active or not item.ends_at:
                        return
                    remaining = (item.ends_at - datetime.now(timezone.utc)).total_seconds()
                    if remaining <= 0:
                        await self.finalize_item(auction_item_id, reason="timer")
                        return
                    await self._broadcast_timer(auction_id=auction_id, auction_item_id=auction_item_id)
                    await asyncio.sleep(min(1.0, max(0.1, remaining)))
            except asyncio.CancelledError:
                return

        self._timer_tasks[auction_item_id] = asyncio.create_task(_runner())

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

            if item.ends_at and datetime.now(timezone.utc) >= item.ends_at.replace(tzinfo=timezone.utc):
                return {"success": False, "message": "Bidding time has ended"}

            auction = await Auction.get(item.auction_id)
            if not auction:
                return {"success": False, "message": "Auction not found"}
            if auction.status != AuctionStatus.live:
                return {"success": False, "message": "Auction is not live"}
            if auction.current_item_id != auction_item_id:
                return {"success": False, "message": "This item is not the current auction item"}

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
            if team.owner_id != user_id:
                return {"success": False, "message": "You are not the owner of this team"}
            if team.remaining_budget < amount:
                return {"success": False, "message": "Insufficient budget"}

            # Mark previous winning bid as not winning
            prev_highest_bidder_id = item.highest_bidder_id
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
                "ends_at": datetime.now(timezone.utc) + timedelta(seconds=auction.bid_timer_seconds),
                "updated_at": datetime.now(timezone.utc),
            })

            await self.start_item_timer(auction_id=item.auction_id, auction_item_id=auction_item_id)

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

            await notification_service.create(
                user_id=user_id,
                notification_type=NotificationType.bid_placed,
                title="Bid placed",
                message=f"You placed a bid of {amount:,.0f}",
                related_id=auction_item_id,
            )

            if prev_highest_bidder_id and prev_highest_bidder_id != user_id:
                await notification_service.create(
                    user_id=prev_highest_bidder_id,
                    notification_type=NotificationType.outbid,
                    title="You were outbid",
                    message=f"A new bid of {amount:,.0f} was placed",
                    related_id=auction_item_id,
                )

            return {"success": True, "message": "Bid placed", "bid_id": str(bid.id)}

    async def finalize_item(self, auction_item_id: str, *, reason: str) -> dict:
        lock = self._get_lock(auction_item_id)
        async with lock:
            item = await AuctionItem.get(auction_item_id)
            if not item:
                return {"success": False, "message": "Item not found"}
            if item.status in (AuctionItemStatus.sold, AuctionItemStatus.unsold):
                return {"success": True, "message": "Item already finalized"}

            self._cancel_timer_task(auction_item_id)

            now = datetime.now(timezone.utc)
            await item.set({"finalized_at": now, "updated_at": now})

            auction = await Auction.get(item.auction_id)
            if auction and auction.current_item_id == auction_item_id:
                await auction.set({"current_item_id": None, "updated_at": now})

            if item.current_bid == 0 or not item.highest_bidder_id:
                await item.set({"status": AuctionItemStatus.unsold, "updated_at": now})
                payload = {
                    "type": "item_unsold",
                    "data": {"auction_item_id": auction_item_id, "reason": reason},
                }
                await auction_manager.broadcast(item.auction_id, payload)
                if item.highest_bidder_id:
                    await notification_service.create(
                        user_id=item.highest_bidder_id,
                        notification_type=NotificationType.system,
                        title="Auction item unsold",
                        message="The item was marked unsold",
                        related_id=auction_item_id,
                    )
                await auction_manager.broadcast(
                    item.auction_id,
                    {
                        "type": "state_update",
                        "data": {"auction_item_id": auction_item_id, "status": "unsold"},
                    },
                )
                return {"success": True, "message": "Item marked unsold"}

            winning_bid = await Bid.find_one(Bid.auction_item_id == auction_item_id, Bid.is_winning == True)
            if not winning_bid:
                await item.set({"status": AuctionItemStatus.unsold, "updated_at": now})
                payload = {
                    "type": "item_unsold",
                    "data": {"auction_item_id": auction_item_id, "reason": "no_winning_bid"},
                }
                await auction_manager.broadcast(item.auction_id, payload)
                await auction_manager.broadcast(
                    item.auction_id,
                    {
                        "type": "state_update",
                        "data": {"auction_item_id": auction_item_id, "status": "unsold"},
                    },
                )
                return {"success": True, "message": "Item marked unsold"}

            team = await Team.get(winning_bid.team_id)
            if not team:
                await item.set({"status": AuctionItemStatus.unsold, "updated_at": now})
                payload = {
                    "type": "item_unsold",
                    "data": {"auction_item_id": auction_item_id, "reason": "team_not_found"},
                }
                await auction_manager.broadcast(item.auction_id, payload)
                await auction_manager.broadcast(
                    item.auction_id,
                    {
                        "type": "state_update",
                        "data": {"auction_item_id": auction_item_id, "status": "unsold"},
                    },
                )
                return {"success": True, "message": "Item marked unsold"}

            if team.remaining_budget < item.current_bid:
                await item.set({"status": AuctionItemStatus.unsold, "updated_at": now})
                payload = {
                    "type": "item_unsold",
                    "data": {"auction_item_id": auction_item_id, "reason": "budget_changed"},
                }
                await auction_manager.broadcast(item.auction_id, payload)
                await auction_manager.broadcast(
                    item.auction_id,
                    {
                        "type": "state_update",
                        "data": {"auction_item_id": auction_item_id, "status": "unsold"},
                    },
                )
                return {"success": True, "message": "Item marked unsold"}

            await team.set(
                {
                    "remaining_budget": team.remaining_budget - item.current_bid,
                    "players": team.players + [item.player_id],
                    "updated_at": now,
                }
            )

            # Update the player document to record which team they belong to
            sold_player = await Player.get(item.player_id)
            if sold_player:
                await sold_player.set({
                    "team_id": winning_bid.team_id,
                    "is_available": False,
                    "updated_at": now,
                })

            await item.set(
                {
                    "status": AuctionItemStatus.sold,
                    "winning_team_id": winning_bid.team_id,
                    "sold_at": now,
                    "updated_at": now,
                }
            )

            payload = {
                "type": "item_sold",
                "data": {
                    "auction_item_id": auction_item_id,
                    "player_id": item.player_id,
                    "sold_price": item.current_bid,
                    "winning_team_id": winning_bid.team_id,
                    "reason": reason,
                },
            }
            await auction_manager.broadcast(item.auction_id, payload)
            await notification_service.create(
                user_id=winning_bid.user_id,
                notification_type=NotificationType.player_sold,
                title="Player sold",
                message=f"You won the player for {item.current_bid:,.0f}",
                related_id=item.player_id,
            )
            # Email notification on auction won
            try:
                from app.core.config import settings
                from app.core.mailer import send_email
                import asyncio
                if settings.SMTP_HOST:
                    winner_user = await User.get(winning_bid.user_id)
                    if winner_user:
                        player = await Player.get(item.player_id)
                        player_name = player.name if player else "Player"
                        from starlette.concurrency import run_in_threadpool
                        await run_in_threadpool(
                            send_email,
                            to_email=winner_user.email,
                            subject=f"🏏 You won {player_name}! — BidWicket Auction",
                            html=(
                                f"<p>Hi {winner_user.full_name},</p>"
                                f"<p>Congratulations! You won <b>{player_name}</b> "
                                f"for <b>₹{item.current_bid:,.0f}</b> in the BidWicket auction.</p>"
                            ),
                        )
            except Exception:
                pass
            await auction_manager.broadcast(
                item.auction_id,
                {
                    "type": "state_update",
                    "data": {"auction_item_id": auction_item_id, "status": "sold"},
                },
            )
            # Auto-complete auction if all items are now finalized
            await self._auto_complete_if_done(item.auction_id)
            return {"success": True, "message": "Item sold"}

    async def _auto_complete_if_done(self, auction_id: str) -> None:
        """If every item in the auction is sold or unsold, auto-complete the auction."""
        auction = await Auction.get(auction_id)
        if not auction or auction.status != AuctionStatus.live:
            return
        all_items = await AuctionItem.find(AuctionItem.auction_id == auction_id).to_list()
        if not all_items:
            return
        finalized_statuses = {AuctionItemStatus.sold, AuctionItemStatus.unsold}
        all_done = all(i.status in finalized_statuses for i in all_items)
        if all_done:
            now = datetime.now(timezone.utc)
            await auction.set({"status": AuctionStatus.completed, "ended_at": now, "updated_at": now})
            await auction_manager.broadcast(
                auction_id,
                {"type": "auction_finalized", "auction_id": auction_id, "reason": "all_players_finalized"},
            )

    async def sell_item(self, auction_item_id: str) -> dict:
        return await self.finalize_item(auction_item_id, reason="manual")

    async def mark_unsold(self, auction_item_id: str, *, reason: str) -> dict:
        lock = self._get_lock(auction_item_id)
        async with lock:
            item = await AuctionItem.get(auction_item_id)
            if not item:
                return {"success": False, "message": "Item not found"}
            if item.status in (AuctionItemStatus.sold, AuctionItemStatus.unsold):
                return {"success": True, "message": "Item already finalized"}

            self._cancel_timer_task(auction_item_id)
            now = datetime.now(timezone.utc)
            await item.set({"status": AuctionItemStatus.unsold, "finalized_at": now, "updated_at": now})

            auction = await Auction.get(item.auction_id)
            if auction and auction.current_item_id == auction_item_id:
                await auction.set({"current_item_id": None, "updated_at": now})

            await auction_manager.broadcast(
                item.auction_id,
                {"type": "item_unsold", "data": {"auction_item_id": auction_item_id, "reason": reason}},
            )
            await auction_manager.broadcast(
                item.auction_id,
                {
                    "type": "state_update",
                    "data": {"auction_item_id": auction_item_id, "status": "unsold"},
                },
            )
            # Auto-complete auction if all items are now finalized
            await self._auto_complete_if_done(item.auction_id)
            return {"success": True, "message": "Item marked unsold"}

    async def reset_timer(self, auction_item_id: str, *, seconds: int) -> dict:
        lock = self._get_lock(auction_item_id)
        async with lock:
            item = await AuctionItem.get(auction_item_id)
            if not item:
                return {"success": False, "message": "Item not found"}
            if item.status != AuctionItemStatus.active:
                return {"success": False, "message": "Item is not active"}
            now = datetime.now(timezone.utc)
            ends_at = now + timedelta(seconds=seconds)
            await item.set({"ends_at": ends_at, "updated_at": now})
            await self._broadcast_timer(auction_id=item.auction_id, auction_item_id=auction_item_id)
            await self.start_item_timer(auction_id=item.auction_id, auction_item_id=auction_item_id)
            return {"success": True, "message": "Timer reset", "ends_at": ends_at}

    async def force_sell(self, auction_item_id: str, *, team_id: str, amount: Optional[float]) -> dict:
        lock = self._get_lock(auction_item_id)
        async with lock:
            item = await AuctionItem.get(auction_item_id)
            if not item:
                return {"success": False, "message": "Item not found"}
            if item.status != AuctionItemStatus.active:
                return {"success": False, "message": "Item is not active"}

            team = await Team.get(team_id)
            if not team:
                return {"success": False, "message": "Team not found"}

            final_amount = float(amount) if amount is not None else float(max(item.base_price, item.current_bid))
            if team.remaining_budget < final_amount:
                return {"success": False, "message": "Insufficient budget"}

            now = datetime.now(timezone.utc)
            old_bids = await Bid.find(
                Bid.auction_item_id == auction_item_id,
                Bid.is_winning == True,
            ).to_list()
            for b in old_bids:
                await b.set({"is_winning": False})

            # Create a winning bid record (admin override)
            bid = Bid(
                auction_item_id=auction_item_id,
                auction_id=item.auction_id,
                user_id=team.owner_id,
                team_id=team_id,
                amount=final_amount,
                is_winning=True,
            )
            await bid.insert()
            await item.set(
                {
                    "current_bid": final_amount,
                    "highest_bidder_id": team.owner_id,
                    "bid_count": item.bid_count + 1,
                    "updated_at": now,
                }
            )

        # Finalize outside the inner lock path (finalize_item will take the lock again)
        return await self.finalize_item(auction_item_id, reason="force_sell")


auction_service = AuctionService()
