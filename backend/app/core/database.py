from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings


async def init_db():
    """Initialize Motor client and Beanie ODM with all document models."""
    # Import here to avoid circular imports
    from app.models.user import User
    from app.models.refresh_session import RefreshSession
    from app.models.auth_tokens import EmailVerificationToken, PasswordResetToken
    from app.models.activity_log import ActivityLog
    from app.models.tournament import Tournament
    from app.models.team import Team
    from app.models.player import Player
    from app.models.match import Match
    from app.models.auction import Auction, AuctionItem, Bid
    from app.models.notification import Notification

    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client.get_default_database()

    await init_beanie(
        database=db,
        document_models=[
            User,
            RefreshSession,
            EmailVerificationToken,
            PasswordResetToken,
            ActivityLog,
            Tournament,
            Team,
            Player,
            Match,
            Auction,
            AuctionItem,
            Bid,
            Notification,
        ],
    )
