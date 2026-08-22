import base64
from urllib.parse import urlencode

import httpx

from app.core.config import settings
from datetime import datetime, timedelta, timezone

SPOTIFY_AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_URL = "https://api.spotify.com/v1"

SCOPES = [
    "user-read-email",
    "user-read-private",
    "user-read-recently-played",
    "user-top-read",
]

def get_authorization_url() -> str:
    params = {
        "client_id": settings.spotify_client_id,
        "response_type": "code",
        "redirect_uri": settings.spotify_redirect_uri,
        "scope": " ".join(SCOPES),
    }
    return f"{SPOTIFY_AUTHORIZE_URL}?{urlencode(params)}"


async def exchange_code_for_token(code: str) -> dict:
    credentials = (
        f"{settings.spotify_client_id}:{settings.spotify_client_secret}"
    )

    encoded_credentials = base64.b64encode(
        credentials.encode()
    ).decode()

    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.spotify_redirect_uri,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            SPOTIFY_TOKEN_URL,
            headers=headers,
            data=data,
        )

    response.raise_for_status()
    return response.json()

async def get_current_user(access_token: str) -> dict:
    return await spotify_get(
        access_token,
        "/me",
    )

async def spotify_get(
    access_token: str,
    endpoint: str,
    params: dict | None = None,
) -> dict:
    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{SPOTIFY_API_URL}{endpoint}",
            headers=headers,
            params=params,
        )

    response.raise_for_status()
    return response.json()

async def get_top_artists(
    access_token: str,
    time_range: str = "medium_term",
) -> dict:
    return await spotify_get(
        access_token,
        "/me/top/artists",
        {
            "time_range": time_range,
            "limit": 50,
        },
    )

async def get_top_tracks(
    access_token: str,
    time_range: str = "medium_term",
) -> dict:
    return await spotify_get(
        access_token,
        "/me/top/tracks",
        {
            "time_range": time_range,
            "limit": 50,
        },
    )

async def get_recently_played(
    access_token: str,
) -> dict:
    return await spotify_get(
        access_token,
        "/me/player/recently-played",
        {
            "limit": 50,
        },
    )

async def refresh_access_token(refresh_token: str) -> dict:
    credentials = (
        f"{settings.spotify_client_id}:{settings.spotify_client_secret}"
    )

    encoded_credentials = base64.b64encode(
        credentials.encode()
    ).decode()

    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            SPOTIFY_TOKEN_URL,
            headers=headers,
            data=data,
        )

    response.raise_for_status()

    return response.json()

def is_token_expired(
    token_expires_at: datetime,
) -> bool:
    return datetime.now(timezone.utc) >= token_expires_at

async def get_valid_access_token(
    account,
) -> str:
    if not is_token_expired(account.token_expires_at):
        return account.access_token

    token_data = await refresh_access_token(
        account.refresh_token
    )

    account.access_token = token_data["access_token"]

    expires_in = token_data.get(
        "expires_in",
        3600,
    )

    account.token_expires_at = (
        datetime.now(timezone.utc)
        + timedelta(seconds=expires_in)
    )

    # Spotify may return a new refresh token.
    if token_data.get("refresh_token"):
        account.refresh_token = token_data["refresh_token"]

    return account.access_token