from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db
from app.services.analytics import (
    get_audio_profile,
    get_listening_behavior,
    get_listening_patterns,
    get_top_artists,
    get_top_tracks,
)

from uuid import UUID

from app.services.analytics import (
    get_audio_profile,
    get_listening_behavior,
    get_listening_patterns,
    get_top_artists,
    get_top_tracks,
)

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
)

@router.get("/{user_id}")
async def get_user_analytics(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    try:
        behavior = await get_listening_behavior(
            db,
            user_id,
        )

        artists = await get_top_artists(
            db,
            user_id,
        )

        tracks = await get_top_tracks(
            db,
            user_id,
        )

        patterns = await get_listening_patterns(
            db,
            user_id,
        )

        audio_profile = await get_audio_profile(
            db,
            user_id,
        )

        return {
            "listening_behavior": behavior,
            "top_artists": artists,
            "top_tracks": tracks,
            "listening_patterns": patterns,
            "audio_profile": audio_profile,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )