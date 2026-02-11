from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.db.models import User
from src.api.db.session import get_db
from src.api.schemas import UserCreate, UserPublic, UserUpdate
from src.api.security.auth import get_current_user, hash_password

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
    description="Create a new user (signup). Email must be unique.",
    operation_id="create_user",
)
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db)) -> UserPublic:
    """Create a user account."""
    user = User(email=str(payload.email).lower(), full_name=payload.full_name, password_hash=hash_password(payload.password))
    db.add(user)
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Email already exists") from e

    await db.refresh(user)
    return UserPublic.model_validate(user, from_attributes=True)


@router.get(
    "/me",
    response_model=UserPublic,
    summary="Get current user",
    description="Returns the currently authenticated user.",
    operation_id="get_current_user",
)
async def me(current_user: User = Depends(get_current_user)) -> UserPublic:
    """Get the current authenticated user."""
    return UserPublic.model_validate(current_user, from_attributes=True)


@router.get(
    "",
    response_model=list[UserPublic],
    summary="List users",
    description="List users (requires auth). Supports simple search by email/full_name.",
    operation_id="list_users",
)
async def list_users(
    q: str | None = Query(None, description="Optional search query (email or full name)"),
    limit: int = Query(50, ge=1, le=200, description="Page size"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[UserPublic]:
    """List users with optional search."""
    stmt: Select[tuple[User]] = select(User)

    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(func.lower(User.email).like(like) | func.lower(User.full_name).like(like))

    stmt = stmt.order_by(User.created_at.desc()).limit(limit).offset(offset)
    res = await db.execute(stmt)
    users = res.scalars().all()
    return [UserPublic.model_validate(u, from_attributes=True) for u in users]


@router.patch(
    "/{user_id}",
    response_model=UserPublic,
    summary="Update user",
    description="Update user fields (requires auth). No role model here; any authenticated user can update any user.",
    operation_id="update_user",
)
async def update_user(
    user_id: str,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> UserPublic:
    """Update a user."""
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.is_active is not None:
        user.is_active = payload.is_active

    await db.commit()
    await db.refresh(user)
    return UserPublic.model_validate(user, from_attributes=True)
