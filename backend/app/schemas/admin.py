from pydantic import BaseModel


class AdminOverviewResponse(BaseModel):
    users: int
    tournaments: int
    teams: int
    players: int
    matches: int
    auctions: int
    auction_items: int
    bids: int
