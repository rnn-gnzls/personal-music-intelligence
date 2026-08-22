from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.db.dependencies import get_db
from app.services.recommendations import (
    get_artist_recommendations,
    get_mood_recommendations,
    get_song_recommendations,
)

router = APIRouter(
    prefix="/recommendations",
    tags=["Recommendations"],
)

@router.get("/{user_id}/songs")
async def song_recommendations(
    user_id: UUID,
    limit: int = Query(
        default=10,
        ge=1,
        le=50,
    ),
    db: AsyncSession = Depends(get_db),
):
    return await get_song_recommendations(
        db,
        user_id,
        limit,
    )

@router.get("/{user_id}/artists")
async def artist_recommendations(
    user_id: UUID,
    limit: int = Query(
        default=10,
        ge=1,
        le=50,
    ),
    db: AsyncSession = Depends(get_db),
):
    return await get_artist_recommendations(
        db,
        user_id,
        limit,
    )

@router.get("/{user_id}/mood/{mood}")
async def mood_recommendations(
    user_id: UUID,
    mood: str,
    limit: int = Query(
        default=10,
        ge=1,
        le=50,
    ),
    db: AsyncSession = Depends(get_db),
):
    return await get_mood_recommendations(
        db,
        user_id,
        mood,
        limit,
    )

def get_context(
    hour: int,
) -> str:
    if 5 <= hour < 12:
        return "morning"

    if 12 <= hour < 18:
        return "afternoon"

    if 18 <= hour < 23:
        return "evening"

    return "night"