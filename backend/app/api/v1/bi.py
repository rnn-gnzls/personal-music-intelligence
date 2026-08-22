from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db
from app.services.bi import (
    get_bi_audio_features,
    get_bi_listening_behavior,
    get_bi_overview,
)

router = APIRouter(
    prefix="/bi",
    tags=["Business Intelligence"],
)

@router.get("/{user_id}/overview")
async def bi_overview(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    return await get_bi_overview(
        db,
        user_id,
    )

@router.get("/{user_id}/listening")
async def bi_listening(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    return await get_bi_listening_behavior(
        db,
        user_id,
    )

@router.get("/{user_id}/audio-features")
async def bi_audio_features(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    return await get_bi_audio_features(
        db,
        user_id,
    )