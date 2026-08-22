from fastapi import FastAPI

from app.api.v1.spotify import router as spotify_router
from app.api.v1.users import router as users_router
from app.api.v1.analytics import router as analytics_v1_router
from app.api.routes.spotify_sync import router as spotify_sync_router
from app.api.routes.data_quality import router as data_quality_router

app = FastAPI(
    title="vibe.ai",
    version="0.1.0",
)

app.include_router(
    users_router,
    prefix="/api/v1",
)

app.include_router(
    spotify_router,
    prefix="/api/v1",
)

app.include_router(
    spotify_sync_router,
    prefix="/api/v1"
)

app.include_router(
    analytics_v1_router,
    prefix="/api/v1",
)

app.include_router(
    data_quality_router,
    prefix="/api/v1",
)

@app.get("/")
async def root():
    return {
        "message": "Personal Music Intelligence API",
        "status": "running",
    }