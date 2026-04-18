from datetime import datetime, timedelta, timezone
import hashlib
import secrets

from fastapi import APIRouter, HTTPException, Request, status
from starlette.concurrency import run_in_threadpool

from app.core.rate_limiter import rate_limit_or_429
from app.core.config import settings
from app.core.mailer import send_email
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.activity_log import ActivityLog
from app.models.auth_tokens import EmailVerificationToken, PasswordResetToken
from app.models.user import User
from app.models.refresh_session import RefreshSession
from app.schemas.auth import PasswordResetConfirmRequest, PasswordResetRequest, VerifyEmailRequest
from app.schemas.user import UserRegister, UserLogin, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["Auth"])


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def _log(
    *,
    action: str,
    success: bool,
    request: Request | None,
    user_id: str | None = None,
    meta: dict | None = None,
):
    ip = None
    user_agent = None
    if request is not None:
        ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

    entry = ActivityLog(
        user_id=user_id,
        action=action,
        success=success,
        ip=ip,
        user_agent=user_agent,
        meta=meta or {},
    )
    await entry.insert()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(body: UserRegister, request: Request):
    existing = await User.find_one(User.email == body.email)
    if existing:
        await _log(action="auth_register", success=False, request=request, meta={"reason": "email_exists"})
        raise HTTPException(status_code=400, detail="Email already registered")

    # Restrict sensitive roles from self-assignment
    safe_roles = [r for r in body.roles if r not in ("admin",)]
    if not safe_roles:
        safe_roles = ["viewer"]

    # In development mode, auto-verify users so email setup is not required
    dev_mode = settings.ENVIRONMENT == "development"

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        roles=safe_roles,
        is_verified=dev_mode,
    )
    await user.insert()

    if not dev_mode:
        # Create email verification token and send email
        raw_token = secrets.token_urlsafe(32)
        token_doc = EmailVerificationToken(
            user_id=str(user.id),
            token_hash=_hash_token(raw_token),
            expires_at=datetime.now(timezone.utc)
            + timedelta(minutes=settings.EMAIL_VERIFY_TOKEN_EXPIRE_MINUTES),
        )
        await token_doc.insert()

        verify_link = f"{settings.FRONTEND_BASE_URL}/verify-email?token={raw_token}"
        html = (
            f"<p>Welcome to BidWicket.</p>"
            f"<p>Verify your email by clicking this link:</p>"
            f"<p><a href=\"{verify_link}\">Verify Email</a></p>"
        )
        try:
            await run_in_threadpool(
                send_email,
                to_email=user.email,
                subject="Verify your BidWicket email",
                html=html,
            )
        except Exception as exc:
            await _log(
                action="auth_register_email_send",
                success=False,
                request=request,
                user_id=str(user.id),
                meta={"error": str(exc)},
            )

    await _log(action="auth_register", success=True, request=request, user_id=str(user.id))

    return UserOut(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        roles=user.roles,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: UserLogin, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_or_429(f"login:ip:{client_ip}", capacity=10, refill_per_sec=10 / 60)
    rate_limit_or_429(f"login:email:{body.email.lower()}", capacity=5, refill_per_sec=5 / 60)

    user = await User.find_one(User.email == body.email)
    if not user or not verify_password(body.password, user.hashed_password):
        await _log(action="auth_login", success=False, request=request, meta={"reason": "invalid_credentials"})
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        await _log(action="auth_login", success=False, request=request, user_id=str(user.id), meta={"reason": "inactive"})
        raise HTTPException(status_code=403, detail="Account deactivated")
    if not user.is_verified:
        await _log(action="auth_login", success=False, request=request, user_id=str(user.id), meta={"reason": "unverified"})
        raise HTTPException(status_code=403, detail="Email not verified")

    refresh_jti = secrets.token_hex(16)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    session = RefreshSession(
        user_id=str(user.id),
        refresh_jti=refresh_jti,
        expires_at=expires_at,
    )
    await session.insert()

    await _log(action="auth_login", success=True, request=request, user_id=str(user.id))

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id), jti=refresh_jti),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_or_429(f"refresh:ip:{client_ip}", capacity=30, refill_per_sec=30 / 60)
    try:
        payload = decode_token(refresh_token)
    except ValueError:
        await _log(action="auth_refresh", success=False, request=request, meta={"reason": "invalid_token"})
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if payload.get("type") != "refresh":
        await _log(action="auth_refresh", success=False, request=request, meta={"reason": "wrong_type"})
        raise HTTPException(status_code=401, detail="Expected refresh token")

    refresh_jti = payload.get("jti")
    if not refresh_jti:
        await _log(action="auth_refresh", success=False, request=request, meta={"reason": "missing_jti"})
        raise HTTPException(status_code=401, detail="Refresh token missing jti")

    session = await RefreshSession.find_one(RefreshSession.refresh_jti == refresh_jti)
    if not session:
        await _log(action="auth_refresh", success=False, request=request, meta={"reason": "session_not_found"})
        raise HTTPException(status_code=401, detail="Refresh session revoked or expired")

    # Refresh reuse detection:
    # If a refresh token that was already rotated is used again, assume theft and revoke all sessions.
    if session.revoked_at and session.revoke_reason == "rotated":
        await RefreshSession.find(RefreshSession.user_id == session.user_id).update(
            {"$set": {"revoked_at": datetime.now(timezone.utc), "revoke_reason": "reuse_detected"}}
        )
        await _log(
            action="auth_refresh",
            success=False,
            request=request,
            user_id=session.user_id,
            meta={"reason": "reuse_detected"},
        )
        raise HTTPException(status_code=401, detail="Refresh token reuse detected. Please login again")

    if session.revoked_at or session.expires_at < datetime.now(timezone.utc):
        await _log(action="auth_refresh", success=False, request=request, meta={"reason": "revoked_or_expired"})
        raise HTTPException(status_code=401, detail="Refresh session revoked or expired")

    user = await User.get(payload["sub"])
    if not user or not user.is_active:
        await _log(action="auth_refresh", success=False, request=request, meta={"reason": "user_not_found"})
        raise HTTPException(status_code=401, detail="User not found")

    # Rotate refresh token
    new_jti = secrets.token_hex(16)
    await session.set({
        "revoked_at": datetime.now(timezone.utc),
        "revoke_reason": "rotated",
        "replaced_by_jti": new_jti,
    })

    new_session = RefreshSession(
        user_id=str(user.id),
        refresh_jti=new_jti,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    await new_session.insert()

    await _log(action="auth_refresh", success=True, request=request, user_id=str(user.id))

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id), jti=new_jti),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(refresh_token: str, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_or_429(f"logout:ip:{client_ip}", capacity=60, refill_per_sec=60 / 60)
    try:
        payload = decode_token(refresh_token)
    except ValueError:
        await _log(action="auth_logout", success=False, request=request, meta={"reason": "invalid_token"})
        return

    if payload.get("type") != "refresh":
        await _log(action="auth_logout", success=False, request=request, meta={"reason": "wrong_type"})
        return

    refresh_jti = payload.get("jti")
    if not refresh_jti:
        await _log(action="auth_logout", success=False, request=request, meta={"reason": "missing_jti"})
        return

    session = await RefreshSession.find_one(RefreshSession.refresh_jti == refresh_jti)
    if session and not session.revoked_at:
        await session.set({
            "revoked_at": datetime.now(timezone.utc),
            "revoke_reason": "logout",
        })

    await _log(action="auth_logout", success=True, request=request, user_id=payload.get("sub"))


@router.post("/verify-email", status_code=status.HTTP_204_NO_CONTENT)
async def verify_email(body: VerifyEmailRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_or_429(f"verify_email:ip:{client_ip}", capacity=30, refill_per_sec=30 / 60)
    token_hash = _hash_token(body.token)
    token_doc = await EmailVerificationToken.find_one(EmailVerificationToken.token_hash == token_hash)
    if not token_doc or token_doc.used_at or token_doc.expires_at < datetime.now(timezone.utc):
        await _log(action="auth_verify_email", success=False, request=request, meta={"reason": "invalid_or_expired"})
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user = await User.get(token_doc.user_id)
    if not user:
        await _log(action="auth_verify_email", success=False, request=request, meta={"reason": "user_not_found"})
        raise HTTPException(status_code=400, detail="Invalid token")

    await user.set({"is_verified": True, "updated_at": datetime.now(timezone.utc)})
    await token_doc.set({"used_at": datetime.now(timezone.utc)})

    await _log(action="auth_verify_email", success=True, request=request, user_id=str(user.id))


@router.post("/password-reset", status_code=status.HTTP_204_NO_CONTENT)
async def password_reset(body: PasswordResetRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_or_429(f"password_reset:ip:{client_ip}", capacity=10, refill_per_sec=10 / 60)
    rate_limit_or_429(f"password_reset:email:{body.email.lower()}", capacity=5, refill_per_sec=5 / 60)
    # Always return 204 to avoid email enumeration
    user = await User.find_one(User.email == body.email)
    if not user or not user.is_active:
        await _log(action="auth_password_reset_request", success=True, request=request, meta={"email": body.email})
        return

    raw_token = secrets.token_urlsafe(32)
    token_doc = PasswordResetToken(
        user_id=str(user.id),
        token_hash=_hash_token(raw_token),
        expires_at=datetime.now(timezone.utc)
        + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES),
    )
    await token_doc.insert()

    reset_link = f"{settings.FRONTEND_BASE_URL}/reset-password?token={raw_token}"
    html = (
        f"<p>You requested a password reset.</p>"
        f"<p>Reset your password using this link:</p>"
        f"<p><a href=\"{reset_link}\">Reset Password</a></p>"
    )
    try:
        await run_in_threadpool(
            send_email,
            to_email=user.email,
            subject="Reset your BidWicket password",
            html=html,
        )
    except Exception as exc:
        await _log(
            action="auth_password_reset_email_send",
            success=False,
            request=request,
            user_id=str(user.id),
            meta={"error": str(exc)},
        )

    await _log(action="auth_password_reset_request", success=True, request=request, user_id=str(user.id))


@router.post("/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def password_reset_confirm(body: PasswordResetConfirmRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_or_429(f"password_reset_confirm:ip:{client_ip}", capacity=20, refill_per_sec=20 / 60)
    token_hash = _hash_token(body.token)
    token_doc = await PasswordResetToken.find_one(PasswordResetToken.token_hash == token_hash)
    if not token_doc or token_doc.used_at or token_doc.expires_at < datetime.now(timezone.utc):
        await _log(action="auth_password_reset_confirm", success=False, request=request, meta={"reason": "invalid_or_expired"})
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user = await User.get(token_doc.user_id)
    if not user or not user.is_active:
        await _log(action="auth_password_reset_confirm", success=False, request=request, meta={"reason": "user_not_found"})
        raise HTTPException(status_code=400, detail="Invalid token")

    await user.set({
        "hashed_password": hash_password(body.new_password),
        "updated_at": datetime.now(timezone.utc),
    })
    await token_doc.set({"used_at": datetime.now(timezone.utc)})

    await _log(action="auth_password_reset_confirm", success=True, request=request, user_id=str(user.id))
