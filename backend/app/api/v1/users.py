from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas import UserCreate, UserResponse
from app.db.dependencies import get_db
from app.db.models.user import User


router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.post(
    "/",
    response_model=UserResponse,
    status_code=201,
)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    existing_user = await db.scalar(
        select(User).where(User.email == user_data.email)
    )

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="User already exists",
        )

    user = User(
        email=user_data.email,
        display_name=user_data.display_name,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user