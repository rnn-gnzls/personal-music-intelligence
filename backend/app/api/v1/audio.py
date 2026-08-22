from fastapi import APIRouter, Depends

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db

from app.services.audio_ingestion import (
    ingest_all_available_audio,
)


router = APIRouter(
    prefix="/audio",
    tags=["Audio Analysis"],
)


@router.post("/analyze")
async def analyze_available_audio(
    db: AsyncSession = Depends(get_db),
):
    return await ingest_all_available_audio(
        db
    )