import asyncio
import os
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from passlib.context import CryptContext

from app.core.config import settings
from app.models.user import User
from app.models.tournament import Tournament, TournamentType, TournamentStatus
from app.models.team import Team
from app.models.player import Player, PlayerRole, BattingStyle, BowlingStyle
from app.models.auction import Auction, AuctionItem, AuctionStatus, AuctionItemStatus

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

players_data = [
    {"name": "Virat Kohli", "role": PlayerRole.batsman, "base": 20000000},
    {"name": "MS Dhoni", "role": PlayerRole.wicket_keeper, "base": 15000000},
    {"name": "Rohit Sharma", "role": PlayerRole.batsman, "base": 20000000},
    {"name": "Jasprit Bumrah", "role": PlayerRole.bowler, "base": 20000000},
    {"name": "Hardik Pandya", "role": PlayerRole.all_rounder, "base": 15000000},
    {"name": "Ravindra Jadeja", "role": PlayerRole.all_rounder, "base": 16000000},
    {"name": "Suryakumar Yadav", "role": PlayerRole.batsman, "base": 15000000},
    {"name": "Rishabh Pant", "role": PlayerRole.wicket_keeper, "base": 16000000},
    {"name": "KL Rahul", "role": PlayerRole.batsman, "base": 14000000},
    {"name": "Mohammed Shami", "role": PlayerRole.bowler, "base": 10000000},
    {"name": "Shubman Gill", "role": PlayerRole.batsman, "base": 8000000},
    {"name": "Yashasvi Jaiswal", "role": PlayerRole.batsman, "base": 4000000},
    {"name": "Kuldeep Yadav", "role": PlayerRole.bowler, "base": 5000000},
    {"name": "Yuzvendra Chahal", "role": PlayerRole.bowler, "base": 5000000},
    {"name": "Rinku Singh", "role": PlayerRole.batsman, "base": 5000000},
]

async def seed():
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client.get_default_database()
    await init_beanie(
        database=db,
        document_models=[User, Tournament, Team, Player, Auction, AuctionItem]
    )

    print("Cleaning database...")
    await User.find_all().delete()
    await Tournament.find_all().delete()
    await Team.find_all().delete()
    await Player.find_all().delete()
    await Auction.find_all().delete()
    await AuctionItem.find_all().delete()

    print("Seeding Users...")
    admin = User(email="admin@bidwicket.com", hashed_password=pwd_context.hash("password"), full_name="Admin User", roles=["admin", "organizer", "team_owner"], is_active=True, is_verified=True)
    await admin.insert()
    
    owner1 = User(email="csk@bidwicket.com", hashed_password=pwd_context.hash("password"), full_name="CSK Owner", roles=["team_owner"], is_active=True, is_verified=True)
    owner2 = User(email="mi@bidwicket.com", hashed_password=pwd_context.hash("password"), full_name="MI Owner", roles=["team_owner"], is_active=True, is_verified=True)
    await owner1.insert()
    await owner2.insert()

    print("Seeding Tournament...")
    tournament = Tournament(name="IPL 2025 Mega Auction", description="The biggest auction of the decade", tournament_type=TournamentType.t20, status=TournamentStatus.upcoming, organizer_id=str(admin.id), max_teams=10)
    await tournament.insert()

    print("Seeding Teams...")
    csk = Team(name="Chennai Super Kings", short_name="CSK", owner_id=str(owner1.id), tournament_id=str(tournament.id), budget=1000000000, remaining_budget=1000000000, home_ground="MA Chidambaram Stadium")
    mi = Team(name="Mumbai Indians", short_name="MI", owner_id=str(owner2.id), tournament_id=str(tournament.id), budget=1000000000, remaining_budget=1000000000, home_ground="Wankhede Stadium")
    await csk.insert()
    await mi.insert()

    print("Seeding Players...")
    player_docs = []
    for p in players_data:
        doc = Player(name=p["name"], country="India", role=p["role"], base_price=p["base"], is_available=True)
        player_docs.append(doc)
    await Player.insert_many(player_docs)

    print("Seeding Auction...")
    auction = Auction(tournament_id=str(tournament.id), name="Main Event IPL Auction", status=AuctionStatus.upcoming, bid_timer_seconds=30)
    await auction.insert()
    
    print("Adding Players to Auction...")
    items = []
    for p in player_docs:
        items.append(AuctionItem(auction_id=str(auction.id), player_id=str(p.id), base_price=p.base_price, status=AuctionItemStatus.pending))
    await AuctionItem.insert_many(items)

    print("Seed complete! 🎉")
    print(f"Login with: admin@bidwicket.com / password")

if __name__ == "__main__":
    asyncio.run(seed())
