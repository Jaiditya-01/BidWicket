from __future__ import annotations

from typing import List

from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.models.auction import Auction
from app.models.match import Match
from app.models.player import Player
from app.models.team import Team
from app.models.tournament import Tournament
from app.schemas.search import SearchResponse, SearchResult

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("/", response_model=SearchResponse)
async def search(q: str, current_user: CurrentUser, limit: int = 20):
    query = q.strip()
    limit = max(1, min(50, limit))
    if not query:
        return SearchResponse(query=query, results=[])

    results: List[SearchResult] = []

    tournaments = await Tournament.find({"name": {"$regex": query, "$options": "i"}}).limit(limit).to_list()
    for t in tournaments:
        results.append(SearchResult(entity="tournament", id=str(t.id), title=t.name, subtitle=t.tournament_type))

    if len(results) < limit:
        teams = await Team.find({"name": {"$regex": query, "$options": "i"}}).limit(limit).to_list()
        for tm in teams:
            results.append(SearchResult(entity="team", id=str(tm.id), title=tm.name, subtitle=tm.short_name))

    if len(results) < limit:
        players = await Player.find({"name": {"$regex": query, "$options": "i"}}).limit(limit).to_list()
        for p in players:
            results.append(SearchResult(entity="player", id=str(p.id), title=p.name, subtitle=p.country))

    if len(results) < limit:
        auctions = await Auction.find({"name": {"$regex": query, "$options": "i"}}).limit(limit).to_list()
        for a in auctions:
            results.append(SearchResult(entity="auction", id=str(a.id), title=a.name, subtitle=a.status))

    if len(results) < limit:
        matches = (
            await Match.find(
                {
                    "$or": [
                        {"tournament_id": {"$regex": query, "$options": "i"}},
                        {"team1_id": {"$regex": query, "$options": "i"}},
                        {"team2_id": {"$regex": query, "$options": "i"}},
                    ]
                }
            )
            .limit(min(limit, 10))
            .to_list()
        )
        for m in matches:
            t1 = await Team.get(m.team1_id)
            t2 = await Team.get(m.team2_id)
            t1_name = t1.name if t1 else m.team1_id
            t2_name = t2.name if t2 else m.team2_id
            results.append(
                SearchResult(
                    entity="match",
                    id=str(m.id),
                    title=f"{t1_name} vs {t2_name}",
                    subtitle=m.status,
                )
            )

    return SearchResponse(query=query, results=results[:limit])
