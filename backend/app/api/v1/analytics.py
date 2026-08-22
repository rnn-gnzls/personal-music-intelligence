from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db
from app.services.analytics import (
    get_audio_profile,
    get_genre_analysis,
    get_listening_behavior,
    get_listening_patterns,
    get_listening_trends,
    get_taste_profile,
    get_top_artists,
    get_top_tracks,
)

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
)

@router.get("/{user_id}/summary")
async def listening_behavior(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    return await get_listening_behavior(
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

@router.get("/{user_id}/listening-patterns")
async def listening_patterns(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    return await get_listening_patterns(
        db,
        user_id,
    )

@router.get("/{user_id}/audio-profile")
async def audio_profile(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    return await get_audio_profile(
        db,
        user_id,
    )

@router.get("/{user_id}/trends")
async def listening_trends(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    return await get_listening_trends(
        db,
        user_id,
    )

@router.get("/{user_id}/genres")
async def genre_analysis(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    return await get_genre_analysis(
        db,
        user_id,
    )

@router.get("/{user_id}/taste-profile")
async def taste_profile(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    return await get_taste_profile(
        db,
        user_id,
    )