from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from datetime import datetime, timezone

from app.api.deps import CurrentUser, AdminUser
from app.models.user import User
from app.schemas.user import UserOut, UserUpdate, UserSelfUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserOut)
async def get_me(current_user: CurrentUser):
    return UserOut(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        roles=current_user.roles,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
    )


@router.patch("/me", response_model=UserOut)
async def update_me(body: UserSelfUpdate, current_user: CurrentUser):
    update_data = body.model_dump(exclude_none=True)
    if update_data:
        update_data["updated_at"] = datetime.now(timezone.utc)
        await current_user.set(update_data)
    return UserOut(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        roles=current_user.roles,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
    )


@router.get("/", response_model=List[UserOut])
async def list_users(admin: AdminUser, page: int = 1, limit: int = 20, role: Optional[str] = None):
    limit = max(1, min(100, limit))
    skip = (max(1, page) - 1) * limit
    query = User.find_all()
    if role:
        query = User.find({"roles": role})
    users = await query.skip(skip).limit(limit).to_list()
    return [
        UserOut(
            id=str(u.id),
            email=u.email,
            full_name=u.full_name,
            roles=u.roles,
            is_active=u.is_active,
            is_verified=u.is_verified,
            created_at=u.created_at,
        )
        for u in users
    ]


@router.patch("/admin/{user_id}/roles", response_model=UserOut)
async def admin_update_roles(user_id: str, roles: List[str], admin: AdminUser):
    """Admin-only: set roles for any user."""
    user = await User.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    safe = [r for r in roles if r in ("admin", "organizer", "team_owner", "player", "viewer")]
    await user.set({"roles": safe, "updated_at": datetime.now(timezone.utc)})
    return UserOut(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        roles=user.roles,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
    )


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(user_id: str, body: UserUpdate, admin: AdminUser):
    user = await User.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = body.model_dump(exclude_none=True)
    update_data["updated_at"] = datetime.now(timezone.utc)
    await user.set(update_data)

    return UserOut(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        roles=user.roles,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: str, admin: AdminUser):
    user = await User.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await user.delete()
