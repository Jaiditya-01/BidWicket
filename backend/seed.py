# ═══════════════════════════════════════════════════════════════════════════════
# HOW TO RUN:
#
#   Safe mode  (only adds MISSING data, never wipes existing records):
#     cd backend
#     python seed.py
#
#   Force mode (wipes ALL existing data first, then re-seeds from scratch):
#     cd backend
#     python seed.py --force
#
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
import sys
import os
from datetime import datetime, timezone, timedelta

# Force UTF-8 output on Windows (avoids cp1252 UnicodeEncodeError with emoji)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
import bcrypt as _bcrypt

from app.core.config import settings
from app.models.user       import User
from app.models.tournament import Tournament, TournamentType, TournamentStatus
from app.models.team       import Team
from app.models.player     import Player, PlayerRole, BattingStyle, BowlingStyle, PlayerStats
from app.models.auction    import Auction, AuctionItem, AuctionStatus, AuctionItemStatus
from app.models.match      import Match, MatchStatus, MatchStage

def _hash_password(plain: str) -> str:
    """Hash using bcrypt directly — avoids passlib 1.7 / bcrypt 4.x incompatibility."""
    return _bcrypt.hashpw(plain.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")

FORCE = "--force" in sys.argv

# ── Player catalogue ────────────────────────────────────────────────────────────
# (name, role, batting_style, bowling_style, country, age, base_price_INR, stats_dict)

PLAYERS = [
    # ── Batsmen ────────────────────────────────────────────────────────────────
    ("Virat Kohli",       PlayerRole.batsman,       BattingStyle.right_hand, BowlingStyle.right_arm_medium, "India",     35, 20_000_000, {"matches":250,"runs":8500,"average":57.3,"strike_rate":138.5,"centuries":2,"half_centuries":65}),
    ("Rohit Sharma",      PlayerRole.batsman,       BattingStyle.right_hand, BowlingStyle.right_arm_medium, "India",     37, 20_000_000, {"matches":235,"runs":6200,"average":30.2,"strike_rate":130.0,"centuries":1,"half_centuries":40}),
    ("Shubman Gill",      PlayerRole.batsman,       BattingStyle.right_hand, BowlingStyle.right_arm_medium, "India",     24, 12_500_000, {"matches":90,"runs":3000,"average":40.0,"strike_rate":141.0,"half_centuries":25}),
    ("Yashasvi Jaiswal",  PlayerRole.batsman,       BattingStyle.left_hand,  BowlingStyle.left_arm_spin,    "India",     22,  7_500_000, {"matches":50,"runs":1900,"average":43.0,"strike_rate":165.0,"half_centuries":16}),
    ("KL Rahul",          PlayerRole.batsman,       BattingStyle.right_hand, BowlingStyle.none,             "India",     32, 15_000_000, {"matches":180,"runs":5200,"average":47.0,"strike_rate":134.5,"centuries":1,"half_centuries":42}),
    ("Shreyas Iyer",      PlayerRole.batsman,       BattingStyle.right_hand, BowlingStyle.none,             "India",     29, 12_500_000, {"matches":120,"runs":3800,"average":35.0,"strike_rate":127.0,"half_centuries":28}),
    ("Ruturaj Gaikwad",   PlayerRole.batsman,       BattingStyle.right_hand, BowlingStyle.none,             "India",     27,  7_500_000, {"matches":80,"runs":2700,"average":38.5,"strike_rate":140.0,"half_centuries":20}),
    ("Tilak Varma",       PlayerRole.batsman,       BattingStyle.left_hand,  BowlingStyle.left_arm_spin,    "India",     22,  5_000_000, {"matches":45,"runs":1400,"average":37.0,"strike_rate":145.0,"half_centuries":10}),
    ("Rinku Singh",       PlayerRole.batsman,       BattingStyle.left_hand,  BowlingStyle.none,             "India",     26,  5_000_000, {"matches":40,"runs":1100,"average":55.0,"strike_rate":162.0,"half_centuries":8}),
    ("Devdutt Padikkal",  PlayerRole.batsman,       BattingStyle.left_hand,  BowlingStyle.none,             "India",     24,  4_000_000, {"matches":55,"runs":1600,"average":32.0,"strike_rate":129.0,"half_centuries":12}),
    ("Suryakumar Yadav",  PlayerRole.batsman,       BattingStyle.right_hand, BowlingStyle.none,             "India",     33, 15_000_000, {"matches":160,"runs":4800,"average":44.0,"strike_rate":170.0,"centuries":1,"half_centuries":35}),
    ("Ishan Kishan",      PlayerRole.batsman,       BattingStyle.left_hand,  BowlingStyle.none,             "India",     25,  7_500_000, {"matches":90,"runs":2400,"average":30.0,"strike_rate":135.5,"half_centuries":18}),

    # ── Wicket-Keepers ─────────────────────────────────────────────────────────
    ("MS Dhoni",          PlayerRole.wicket_keeper, BattingStyle.right_hand, BowlingStyle.none,             "India",     42, 12_500_000, {"matches":250,"runs":5000,"average":38.5,"strike_rate":142.0,"half_centuries":24}),
    ("Rishabh Pant",      PlayerRole.wicket_keeper, BattingStyle.left_hand,  BowlingStyle.none,             "India",     26, 16_000_000, {"matches":110,"runs":3400,"average":35.0,"strike_rate":148.0,"half_centuries":22}),
    ("Sanju Samson",      PlayerRole.wicket_keeper, BattingStyle.right_hand, BowlingStyle.none,             "India",     29, 14_000_000, {"matches":140,"runs":4100,"average":36.0,"strike_rate":145.0,"centuries":1,"half_centuries":28}),
    ("Dinesh Karthik",    PlayerRole.wicket_keeper, BattingStyle.right_hand, BowlingStyle.none,             "India",     39,  4_000_000, {"matches":230,"runs":4800,"average":26.0,"strike_rate":140.0,"half_centuries":15}),

    # ── All-Rounders ────────────────────────────────────────────────────────────
    ("Hardik Pandya",     PlayerRole.all_rounder,   BattingStyle.right_hand, BowlingStyle.right_arm_medium, "India",     30, 15_000_000, {"matches":170,"runs":3000,"wickets":130,"average":28.0,"strike_rate":145.0,"economy_rate":8.9,"half_centuries":15}),
    ("Ravindra Jadeja",   PlayerRole.all_rounder,   BattingStyle.left_hand,  BowlingStyle.left_arm_spin,    "India",     35, 16_000_000, {"matches":210,"runs":2800,"wickets":170,"average":27.0,"strike_rate":133.0,"economy_rate":7.6,"half_centuries":12}),
    ("Axar Patel",        PlayerRole.all_rounder,   BattingStyle.left_hand,  BowlingStyle.left_arm_spin,    "India",     30,  7_500_000, {"matches":130,"runs":1600,"wickets":110,"average":22.0,"strike_rate":130.0,"economy_rate":7.4}),
    ("Washington Sundar", PlayerRole.all_rounder,   BattingStyle.right_hand, BowlingStyle.right_arm_spin,   "India",     25,  5_000_000, {"matches":80,"runs":900,"wickets":72,"average":19.0,"strike_rate":128.0,"economy_rate":7.8}),
    ("Shardul Thakur",    PlayerRole.all_rounder,   BattingStyle.right_hand, BowlingStyle.right_arm_medium, "India",     32,  5_000_000, {"matches":120,"runs":1000,"wickets":95,"average":20.0,"strike_rate":141.0,"economy_rate":9.1}),
    ("Venkatesh Iyer",    PlayerRole.all_rounder,   BattingStyle.left_hand,  BowlingStyle.right_arm_medium, "India",     29,  8_500_000, {"matches":75,"runs":1800,"wickets":42,"average":30.0,"strike_rate":148.0,"economy_rate":9.4,"half_centuries":12}),
    ("Krunal Pandya",     PlayerRole.all_rounder,   BattingStyle.left_hand,  BowlingStyle.left_arm_spin,    "India",     33,  5_000_000, {"matches":100,"runs":1200,"wickets":80,"average":22.0,"strike_rate":135.0,"economy_rate":8.2}),
    ("Deepak Hooda",      PlayerRole.all_rounder,   BattingStyle.right_hand, BowlingStyle.right_arm_spin,   "India",     29,  4_000_000, {"matches":85,"runs":1500,"wickets":45,"average":28.0,"strike_rate":147.0,"economy_rate":8.5}),

    # ── Fast Bowlers ────────────────────────────────────────────────────────────
    ("Jasprit Bumrah",    PlayerRole.bowler,        BattingStyle.right_hand, BowlingStyle.right_arm_fast,   "India",     30, 20_000_000, {"matches":130,"wickets":160,"economy_rate":6.8,"five_wicket_hauls":2}),
    ("Mohammed Shami",    PlayerRole.bowler,        BattingStyle.right_hand, BowlingStyle.right_arm_fast,   "India",     33, 10_000_000, {"matches":100,"wickets":130,"economy_rate":8.0}),
    ("Mohammed Siraj",    PlayerRole.bowler,        BattingStyle.right_hand, BowlingStyle.right_arm_fast,   "India",     30,  8_000_000, {"matches":90,"wickets":100,"economy_rate":8.3}),
    ("Umesh Yadav",       PlayerRole.bowler,        BattingStyle.right_hand, BowlingStyle.right_arm_fast,   "India",     36,  3_500_000, {"matches":150,"wickets":170,"economy_rate":8.9}),
    ("Arshdeep Singh",    PlayerRole.bowler,        BattingStyle.left_hand,  BowlingStyle.left_arm_fast,    "India",     25,  5_000_000, {"matches":70,"wickets":88,"economy_rate":8.4}),
    ("T Natarajan",       PlayerRole.bowler,        BattingStyle.left_hand,  BowlingStyle.left_arm_fast,    "India",     33,  4_000_000, {"matches":80,"wickets":85,"economy_rate":8.5}),
    ("Prasidh Krishna",   PlayerRole.bowler,        BattingStyle.right_hand, BowlingStyle.right_arm_fast,   "India",     28,  4_000_000, {"matches":60,"wickets":72,"economy_rate":8.7}),
    ("Avesh Khan",        PlayerRole.bowler,        BattingStyle.right_hand, BowlingStyle.right_arm_fast,   "India",     28,  4_000_000, {"matches":65,"wickets":78,"economy_rate":9.0}),
    ("Deepak Chahar",     PlayerRole.bowler,        BattingStyle.right_hand, BowlingStyle.right_arm_medium, "India",     32,  5_000_000, {"matches":100,"wickets":95,"economy_rate":8.1}),
    ("Bhuvneshwar Kumar", PlayerRole.bowler,        BattingStyle.right_hand, BowlingStyle.right_arm_medium, "India",     34,  5_000_000, {"matches":150,"wickets":145,"economy_rate":7.6}),
    ("Harshal Patel",     PlayerRole.bowler,        BattingStyle.right_hand, BowlingStyle.right_arm_medium, "India",     33,  5_500_000, {"matches":95,"wickets":120,"economy_rate":8.5}),

    # ── Spin Bowlers ────────────────────────────────────────────────────────────
    ("Yuzvendra Chahal",  PlayerRole.bowler,        BattingStyle.right_hand, BowlingStyle.right_arm_spin,   "India",     34,  6_500_000, {"matches":165,"wickets":187,"economy_rate":8.0}),
    ("Kuldeep Yadav",     PlayerRole.bowler,        BattingStyle.left_hand,  BowlingStyle.left_arm_spin,    "India",     30,  6_500_000, {"matches":100,"wickets":125,"economy_rate":7.9}),
    ("R Ashwin",          PlayerRole.bowler,        BattingStyle.right_hand, BowlingStyle.right_arm_spin,   "India",     37,  8_000_000, {"matches":180,"wickets":175,"economy_rate":6.9,"five_wicket_hauls":1}),
    ("Varun Chakravarthy",PlayerRole.bowler,        BattingStyle.right_hand, BowlingStyle.right_arm_spin,   "India",     33,  5_000_000, {"matches":65,"wickets":80,"economy_rate":7.8}),
    ("Ravi Bishnoi",      PlayerRole.bowler,        BattingStyle.right_hand, BowlingStyle.right_arm_spin,   "India",     24,  4_000_000, {"matches":55,"wickets":68,"economy_rate":7.5}),
    ("Piyush Chawla",     PlayerRole.bowler,        BattingStyle.right_hand, BowlingStyle.right_arm_spin,   "India",     35,  2_500_000, {"matches":170,"wickets":156,"economy_rate":8.1}),

    # ── Overseas stars ─────────────────────────────────────────────────────────
    ("Pat Cummins",       PlayerRole.all_rounder,   BattingStyle.right_hand, BowlingStyle.right_arm_fast,   "Australia", 31, 20_300_000, {"matches":80,"runs":800,"wickets":100,"economy_rate":8.5}),
    ("Mitchell Marsh",    PlayerRole.all_rounder,   BattingStyle.right_hand, BowlingStyle.right_arm_fast,   "Australia", 32, 10_000_000, {"matches":65,"runs":1400,"wickets":62,"economy_rate":9.1,"half_centuries":8}),
    ("Nicholas Pooran",   PlayerRole.wicket_keeper, BattingStyle.left_hand,  BowlingStyle.none,             "WestIndies",28,  9_750_000, {"matches":85,"runs":2100,"average":32.0,"strike_rate":157.0,"half_centuries":14}),
    ("Trent Boult",       PlayerRole.bowler,        BattingStyle.right_hand, BowlingStyle.left_arm_fast,    "NewZealand",35,  8_000_000, {"matches":100,"wickets":120,"economy_rate":8.0}),
    ("Kagiso Rabada",     PlayerRole.bowler,        BattingStyle.left_hand,  BowlingStyle.right_arm_fast,   "SouthAfrica",29, 14_000_000, {"matches":75,"wickets":108,"economy_rate":8.4}),
    ("Gerald Coetzee",    PlayerRole.bowler,        BattingStyle.right_hand, BowlingStyle.right_arm_fast,   "SouthAfrica",25,  5_000_000, {"matches":30,"wickets":42,"economy_rate":9.0}),
    ("Noor Ahmad",        PlayerRole.bowler,        BattingStyle.left_hand,  BowlingStyle.left_arm_spin,    "Afghanistan",20,  2_000_000, {"matches":20,"wickets":30,"economy_rate":7.4}),
]

# ── Teams + owner seed data ─────────────────────────────────────────────────────
TEAM_OWNERS = [
    ("csk@bidwicket.com",  "CSK Owner",    "Chennai Super Kings",        "CSK", "MA Chidambaram Stadium"),
    ("mi@bidwicket.com",   "MI Owner",     "Mumbai Indians",             "MI",  "Wankhede Stadium"),
    ("rcb@bidwicket.com",  "RCB Owner",    "Royal Challengers Bangalore","RCB", "M. Chinnaswamy Stadium"),
    ("kkr@bidwicket.com",  "KKR Owner",    "Kolkata Knight Riders",      "KKR", "Eden Gardens"),
    ("srh@bidwicket.com",  "SRH Owner",    "Sunrisers Hyderabad",        "SRH", "Rajiv Gandhi International Stadium"),
    ("rr@bidwicket.com",   "RR Owner",     "Rajasthan Royals",           "RR",  "Sawai Mansingh Stadium"),
]

BUDGET = 1_000_000_000  # ₹100 Cr


# ── Helpers ─────────────────────────────────────────────────────────────────────

async def upsert_user(email: str, full_name: str, roles: list[str]) -> User:
    """Return existing user or create a new one. Never overwrites existing records."""
    existing = await User.find_one(User.email == email)
    if existing:
        print(f"  ↩  User already exists: {email}")
        return existing
    user = User(
        email=email,
        hashed_password=_hash_password("password"),
        full_name=full_name,
        roles=roles,
        is_active=True,
        is_verified=True,
    )
    await user.insert()
    print(f"  ✔  Created user: {email}")
    return user


async def upsert_tournament(name: str, admin: User) -> Tournament:
    existing = await Tournament.find_one(Tournament.name == name)
    if existing:
        print(f"  ↩  Tournament already exists: {name}")
        return existing
    t = Tournament(
        name=name,
        description="The biggest T20 auction of the decade",
        tournament_type=TournamentType.t20,
        status=TournamentStatus.upcoming,
        organizer_id=str(admin.id),
        max_teams=10,
        start_date=datetime.now(timezone.utc) + timedelta(days=30),
        end_date=datetime.now(timezone.utc) + timedelta(days=90),
    )
    await t.insert()
    print(f"  ✔  Created tournament: {name}")
    return t


async def upsert_team(name: str, short_name: str, owner: User, tournament: Tournament, home_ground: str) -> Team:
    existing = await Team.find_one(Team.name == name)
    if existing:
        print(f"  ↩  Team already exists: {name}")
        return existing
    team = Team(
        name=name,
        short_name=short_name,
        owner_id=str(owner.id),
        tournament_id=str(tournament.id),
        budget=BUDGET,
        remaining_budget=BUDGET,
        home_ground=home_ground,
    )
    await team.insert()
    print(f"  ✔  Created team: {name}")
    return team


async def upsert_player(row: tuple) -> Player:
    name, role, bat, bowl, country, age, base, stats_d = row
    existing = await Player.find_one(Player.name == name)
    if existing:
        print(f"  ↩  Player already exists: {name}")
        return existing
    stats = PlayerStats(
        matches=stats_d.get("matches", 0),
        runs=stats_d.get("runs", 0),
        wickets=stats_d.get("wickets", 0),
        average=stats_d.get("average", 0.0),
        strike_rate=stats_d.get("strike_rate", 0.0),
        economy_rate=stats_d.get("economy_rate", 0.0),
        centuries=stats_d.get("centuries", 0),
        half_centuries=stats_d.get("half_centuries", 0),
        five_wicket_hauls=stats_d.get("five_wicket_hauls", 0),
    )
    player = Player(
        name=name,
        country=country,
        age=age,
        role=role,
        batting_style=bat,
        bowling_style=bowl,
        base_price=float(base),
        stats=stats,
        is_available=True,
    )
    await player.insert()
    print(f"  ✔  Created player: {name}  [{role.value}]  ₹{base:,.0f}")
    return player


# ── Main seed function ──────────────────────────────────────────────────────────

async def seed():
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client.get_default_database()
    await init_beanie(
        database=db,
        document_models=[User, Tournament, Team, Player, Auction, AuctionItem, Match],
    )

    if FORCE:
        print("\n⚠️  --force flag detected. Wiping all existing data...\n")
        await User.find_all().delete()
        await Tournament.find_all().delete()
        await Team.find_all().delete()
        await Player.find_all().delete()
        await Auction.find_all().delete()
        await AuctionItem.find_all().delete()
        await Match.find_all().delete()
        print("  ✔  Database cleared.\n")
    else:
        print("\n🔒  Safe mode — only inserting MISSING records (run with --force to reset).\n")

    # ── Users ──────────────────────────────────────────────────────────────────
    print("📋  Seeding Users...")
    admin = await upsert_user("admin@bidwicket.com", "Admin User", ["admin", "organizer", "team_owner"])

    owner_users: list[User] = []
    for email, full_name, _, _, _ in TEAM_OWNERS:
        u = await upsert_user(email, full_name, ["team_owner"])
        owner_users.append(u)

    # ── Tournament ─────────────────────────────────────────────────────────────
    print("\n🏆  Seeding Tournament...")
    tournament = await upsert_tournament("BidWicket IPL 2025 Mega Auction", admin)

    # ── Teams ──────────────────────────────────────────────────────────────────
    print("\n👕  Seeding Teams...")
    teams: list[Team] = []
    for (_, _, team_name, short_name, ground), owner in zip(TEAM_OWNERS, owner_users):
        t = await upsert_team(team_name, short_name, owner, tournament, ground)
        teams.append(t)

    # ── Players ────────────────────────────────────────────────────────────────
    print(f"\n🏏  Seeding Players ({len(PLAYERS)} total)...")
    player_docs: list[Player] = []
    for row in PLAYERS:
        p = await upsert_player(row)
        player_docs.append(p)

    # ── Auction ────────────────────────────────────────────────────────────────
    print("\n🔨  Seeding Auction...")
    auction = await Auction.find_one(Auction.name == "Main Event IPL 2025 Auction")
    if auction:
        print("  ↩  Auction already exists.")
    else:
        auction = Auction(
            tournament_id=str(tournament.id),
            name="Main Event IPL 2025 Auction",
            status=AuctionStatus.upcoming,
            bid_timer_seconds=30,
            scheduled_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        await auction.insert()
        print("  ✔  Created auction.")

    # ── Auction Items (one per player) ─────────────────────────────────────────
    print(f"\n📦  Seeding Auction Items...")
    existing_item_player_ids = {
        item.player_id
        for item in await AuctionItem.find({"auction_id": str(auction.id)}).to_list()
    }
    new_items: list[AuctionItem] = []
    for p in player_docs:
        pid = str(p.id)
        if pid not in existing_item_player_ids:
            new_items.append(AuctionItem(
                auction_id=str(auction.id),
                player_id=pid,
                base_price=p.base_price,
                status=AuctionItemStatus.pending,
            ))
    if new_items:
        await AuctionItem.insert_many(new_items)
        print(f"  ✔  Added {len(new_items)} new auction items.")
    else:
        print(f"  ↩  All auction items already exist.")

    # ── Sample Match (only if at least 2 teams exist) ──────────────────────────
    if len(teams) >= 2:
        print("\n🏟️  Seeding Sample Match...")
        existing_match = await Match.find_one({
            "team1_id": str(teams[0].id),
            "team2_id": str(teams[1].id),
        })
        if existing_match:
            print("  ↩  Sample match already exists.")
        else:
            match = Match(
                tournament_id=str(tournament.id),
                team1_id=str(teams[0].id),
                team2_id=str(teams[1].id),
                venue=teams[0].home_ground or "TBD",
                match_date=datetime.now(timezone.utc) + timedelta(days=35),
                stage=MatchStage.league,
                status=MatchStatus.scheduled,
            )
            await match.insert()
            print("  ✔  Created sample match: CSK vs MI")

    # ── Summary ────────────────────────────────────────────────────────────────
    print("""
╔══════════════════════════════════════════════════╗
║               ✅  SEED COMPLETE                  ║
╠══════════════════════════════════════════════════╣
║  Login credentials (all accounts):              ║
║    Password  : password                         ║
║    Admin     : admin@bidwicket.com              ║
║    CSK Owner : csk@bidwicket.com                ║
║    MI Owner  : mi@bidwicket.com                 ║
║    RCB Owner : rcb@bidwicket.com                ║
║    KKR Owner : kkr@bidwicket.com                ║
║    SRH Owner : srh@bidwicket.com                ║
║    RR Owner  : rr@bidwicket.com                 ║
╚══════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    asyncio.run(seed())
