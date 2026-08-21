from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db
from app.services.analytics import (
    get_listening_summary,
    get_top_artists,
    get_top_tracks,
)


router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
)


@router.get("/{user_id}/summary")
async def listening_summary(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    return await get_listening_summary(
        db,
        user_id,
    )


@router.get("/{user_id}/top-artists")
async def top_artists(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    return await get_top_artists(
        db,
        user_id,
    )


@router.get("/{user_id}/top-tracks")
async def top_tracks(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    return await get_top_tracks(
        db,
        user_id,
    )