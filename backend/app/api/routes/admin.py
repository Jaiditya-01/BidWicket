from __future__ import annotations

import csv
import io
from typing import List, Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.deps import AdminUser
from app.models.auction import Auction, AuctionItem, Bid
from app.models.match import Match
from app.models.player import Player
from app.models.team import Team
from app.models.tournament import Tournament
from app.models.user import User
from app.schemas.admin import AdminOverviewResponse

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/overview", response_model=AdminOverviewResponse)
async def overview(current_user: AdminUser):
    users = await User.find_all().count()
    tournaments = await Tournament.find_all().count()
    teams = await Team.find_all().count()
    players = await Player.find_all().count()
    matches = await Match.find_all().count()
    auctions = await Auction.find_all().count()
    auction_items = await AuctionItem.find_all().count()
    bids = await Bid.find_all().count()
    return AdminOverviewResponse(
        users=users,
        tournaments=tournaments,
        teams=teams,
        players=players,
        matches=matches,
        auctions=auctions,
        auction_items=auction_items,
        bids=bids,
    )


# ── CSV Exports ────────────────────────────────────────────────────────────────

@router.get("/export/users.csv")
async def export_users_csv(current_user: AdminUser):
    users = await User.find_all().to_list()

    def _iter():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["id", "email", "full_name", "roles", "is_active", "is_verified", "created_at"])
        yield buf.getvalue(); buf.seek(0); buf.truncate(0)
        for u in users:
            writer.writerow([str(u.id), u.email, u.full_name, "|".join(u.roles), str(u.is_active), str(u.is_verified), u.created_at.isoformat()])
            yield buf.getvalue(); buf.seek(0); buf.truncate(0)

    return StreamingResponse(_iter(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=users.csv"})


@router.get("/export/bids.csv")
async def export_bids_csv(current_user: AdminUser, auction_id: str | None = None):
    query = Bid.find(Bid.auction_id == auction_id) if auction_id else Bid.find_all()
    bids = await query.sort(-Bid.timestamp).to_list()

    def _iter():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["id", "auction_id", "auction_item_id", "user_id", "team_id", "amount", "is_winning", "timestamp"])
        yield buf.getvalue(); buf.seek(0); buf.truncate(0)
        for b in bids:
            writer.writerow([str(b.id), b.auction_id, b.auction_item_id, b.user_id, b.team_id, b.amount, str(b.is_winning), b.timestamp.isoformat()])
            yield buf.getvalue(); buf.seek(0); buf.truncate(0)

    return StreamingResponse(_iter(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=bids.csv"})


@router.get("/export/tournaments.csv")
async def export_tournaments_csv(current_user: AdminUser):
    items = await Tournament.find_all().to_list()

    def _iter():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["id", "name", "tournament_type", "status", "organizer_id", "start_date", "end_date", "created_at"])
        yield buf.getvalue(); buf.seek(0); buf.truncate(0)
        for t in items:
            writer.writerow([str(t.id), t.name, t.tournament_type, t.status, t.organizer_id,
                             t.start_date.isoformat() if t.start_date else "", t.end_date.isoformat() if t.end_date else "", t.created_at.isoformat()])
            yield buf.getvalue(); buf.seek(0); buf.truncate(0)

    return StreamingResponse(_iter(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=tournaments.csv"})


@router.get("/export/players.csv")
async def export_players_csv(current_user: AdminUser):
    items = await Player.find_all().to_list()

    def _iter():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["id", "name", "country", "age", "role", "batting_style", "bowling_style", "base_price", "team_id", "is_available", "matches", "runs", "wickets", "created_at"])
        yield buf.getvalue(); buf.seek(0); buf.truncate(0)
        for p in items:
            writer.writerow([str(p.id), p.name, p.country, p.age, p.role, p.batting_style, p.bowling_style,
                             p.base_price, p.team_id or "", str(p.is_available),
                             p.stats.matches, p.stats.runs, p.stats.wickets, p.created_at.isoformat()])
            yield buf.getvalue(); buf.seek(0); buf.truncate(0)

    return StreamingResponse(_iter(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=players.csv"})


@router.get("/export/matches.csv")
async def export_matches_csv(current_user: AdminUser, tournament_id: Optional[str] = None):
    query = Match.find(Match.tournament_id == tournament_id) if tournament_id else Match.find_all()
    items = await query.to_list()

    def _iter():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["id", "tournament_id", "team1_id", "team2_id", "stage", "status", "winner_id", "venue", "match_date", "created_at"])
        yield buf.getvalue(); buf.seek(0); buf.truncate(0)
        for m in items:
            writer.writerow([str(m.id), m.tournament_id, m.team1_id, m.team2_id, m.stage, m.status, m.winner_id or "",
                             m.venue or "", m.match_date.isoformat() if m.match_date else "", m.created_at.isoformat()])
            yield buf.getvalue(); buf.seek(0); buf.truncate(0)

    return StreamingResponse(_iter(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=matches.csv"})
