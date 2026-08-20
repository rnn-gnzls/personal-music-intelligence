from fastapi import FastAPI

from app.api.v1.spotify import router as spotify_router
from app.api.v1.users import router as users_router


app = FastAPI(
    title="Personal Music Intelligence API",
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


@app.get("/")
async def root():
    return {
        "message": "Personal Music Intelligence API",
        "status": "running",
    }