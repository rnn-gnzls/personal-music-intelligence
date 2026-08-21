from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from app.services.spotify import (
    exchange_code_for_token,
    get_authorization_url,
    get_current_user,
)

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.db.dependencies import get_db
from app.db.models.spotify_account import SpotifyAccount
from app.db.models.user import User

from app.db.dependencies import get_db
from app.services.spotify_ingestion import sync_spotify_data
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from uuid import UUID

router = APIRouter(
    prefix="/spotify",
    tags=["Spotify"],
)


@router.get("/login")
async def spotify_login():
    authorization_url = get_authorization_url()

    return RedirectResponse(
        url=authorization_url
    )


@router.get("/callback")
async def spotify_callback(
    code: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        # TEMPORARY DEVELOPMENT USER
        development_user_id = UUID(
            "ba2c8c1d-4619-4e8f-977d-f4fb48e363ea"
        )

        user = await db.scalar(
            select(User).where(
                User.id == development_user_id
            )
        )

        if not user:
            raise HTTPException(
                status_code=404,
                detail="Development user not found.",
            )

        token_data = await exchange_code_for_token(code)

        access_token = token_data["access_token"]
        refresh_token = token_data["refresh_token"]
        expires_in = token_data["expires_in"]

        spotify_user = await get_current_user(
            access_token
        )

        spotify_user_id = spotify_user["id"]

        token_expires_at = (
            datetime.now(timezone.utc)
            + timedelta(seconds=expires_in)
        )

        existing_account = await db.scalar(
            select(SpotifyAccount).where(
                SpotifyAccount.user_id == user.id
            )
        )

        if existing_account:
            existing_account.spotify_user_id = spotify_user_id
            existing_account.access_token = access_token
            existing_account.refresh_token = refresh_token
            existing_account.token_expires_at = token_expires_at

        else:
            spotify_account = SpotifyAccount(
                user_id=user.id,
                spotify_user_id=spotify_user_id,
                access_token=access_token,
                refresh_token=refresh_token,
                token_expires_at=token_expires_at,
            )

            db.add(spotify_account)

        await db.commit()

        return {
            "message": "Spotify connected successfully",
            "spotify_user": {
                "id": spotify_user.get("id"),
                "display_name": spotify_user.get("display_name"),
                "email": spotify_user.get("email"),
            },
        }

    except HTTPException:
        raise

    except Exception as exc:
        await db.rollback()

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

@router.get("/test-data")
async def test_spotify_data():
    raise HTTPException(
        status_code=501,
        detail="This endpoint is not implemented yet.",
    )

@router.post("/sync/{user_id}")
async def sync_spotify(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    try:

        result = await sync_spotify_data(
            db,
            user_id,
        )

        return {
            "message": "Spotify data synchronized successfully.",
            "data": result,
        }

    except Exception as exc:

        await db.rollback()

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )