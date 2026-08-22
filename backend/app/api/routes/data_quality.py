from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db
from app.services.data_quality import validate_spotify_data


router = APIRouter(
    prefix="/data-quality",
    tags=["Data Quality"],
)


@router.get("/spotify")
async def spotify_data_quality(
    db: AsyncSession = Depends(get_db),
):
    return await validate_spotify_data(db)