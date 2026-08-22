from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db
from app.services.spotify_ingestion import sync_spotify_data


router = APIRouter(
    prefix="/spotify",
    tags=["Spotify"],
)


@router.post("/sync/{user_id}")
async def sync_spotify(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await sync_spotify_data(
            db=db,
            user_id=user_id,
        )

        return {
            "message": "Spotify synchronized successfully",
            "data": result,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Spotify synchronization failed: {str(exc)}",
        )