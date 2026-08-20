from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.core.config import settings


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Backend API for a personalized music intelligence "
        "and discovery platform."
    ),
)


@app.get("/")
async def root():
    return {
        "message": "Welcome to the Personal Music Intelligence API",
        "version": settings.app_version,
        "environment": settings.environment,
    }


app.include_router(health_router)