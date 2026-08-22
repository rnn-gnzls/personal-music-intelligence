from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.album import Album
from app.db.models.artist import Artist
from app.db.models.track import Track
from app.db.models.listening_history import ListeningHistory
from app.db.models.spotify_account import SpotifyAccount
from app.db.models.spotify_sync_log import SpotifySyncLog

from app.services.spotify import (
    get_recently_played,
    get_top_artists,
    get_top_tracks,
    get_valid_access_token,
)

async def get_spotify_account(
    db: AsyncSession,
    user_id,
) -> SpotifyAccount:

    result = await db.execute(
        select(SpotifyAccount).where(
            SpotifyAccount.user_id == user_id
        )
    )
    account = result.scalar_one_or_none()

    if not account:
        raise ValueError(
            "Spotify account is not connected."
        )
    return account

async def sync_artists(
    db: AsyncSession,
    access_token: str,
    artists: list[dict],
):
    synced = 0

    for spotify_artist in artists:

        spotify_artist_id = spotify_artist["id"]

        result = await db.execute(
            select(Artist).where(
                Artist.spotify_artist_id
                == spotify_artist_id
            )
        )

        artist = result.scalar_one_or_none()

        if artist:
            artist.name = spotify_artist["name"]
        else:
            artist = Artist(
                spotify_artist_id=spotify_artist_id,
                name=spotify_artist["name"],
            )

            db.add(artist)

        synced += 1

    await db.flush()
    return synced

async def sync_tracks(
    db: AsyncSession,
    tracks: list[dict],
):
    synced = 0

    for spotify_track in tracks:

        spotify_track_id = spotify_track["id"]

        # Find/create artists
        for spotify_artist in spotify_track["artists"]:
            result = await db.execute(
                select(Artist).where(
                    Artist.spotify_artist_id
                    == spotify_artist["id"]
                )
            )
            artist = result.scalar_one_or_none()

            if not artist:
                artist = Artist(
                    spotify_artist_id=spotify_artist["id"],
                    name=spotify_artist["name"],
                )

                db.add(artist)
                await db.flush()

        # Get primary artist
        result = await db.execute(
            select(Artist).where(
                Artist.spotify_artist_id
                == spotify_track["artists"][0]["id"]
            )
        )
        artist = result.scalar_one()

        # Album
        spotify_album = spotify_track["album"]

        result = await db.execute(
            select(Album).where(
                Album.spotify_album_id == spotify_album["id"]
            )
        )

        album = result.scalar_one_or_none()

        release_date = None
        raw_release_date = spotify_album.get("release_date")

        if raw_release_date:
            try:
                if len(raw_release_date) == 10:
                    release_date = datetime.strptime(
                        raw_release_date,
                        "%Y-%m-%d",
                    ).date()

                elif len(raw_release_date) == 7:
                    release_date = datetime.strptime(
                        raw_release_date,
                        "%Y-%m",
                    ).date()

                elif len(raw_release_date) == 4:
                    release_date = datetime.strptime(
                        raw_release_date,
                        "%Y",
                    ).date()

            except ValueError:
                release_date = None

        if not album:
            album = Album(
                spotify_album_id=spotify_album["id"],
                name=spotify_album["name"],
                release_date=release_date,
                artist_id=artist.id,
            )

            db.add(album)
            await db.flush()

        else:
            album.name = spotify_album["name"]
            album.release_date = release_date

        # Track
        result = await db.execute(
            select(Track).where(
                Track.spotify_track_id
                == spotify_track_id
            )
        )

        track = result.scalar_one_or_none()

        if not track:

            track = Track(
                spotify_track_id=spotify_track_id,
                name=spotify_track["name"],
                artist_id=artist.id,
                album_id=album.id,
                duration_ms=spotify_track["duration_ms"],
            )

            db.add(track)

        else:

            track.name = spotify_track["name"]
            track.duration_ms = spotify_track["duration_ms"]

        synced += 1

    await db.flush()
    return synced

async def sync_recently_played(
    db: AsyncSession,
    user_id,
    recently_played: list[dict],
):
    synced = 0

    for item in recently_played:

        spotify_track = item["track"]

        result = await db.execute(
            select(Track).where(
                Track.spotify_track_id
                == spotify_track["id"]
            )
        )

        track = result.scalar_one_or_none()

        if not track:
            continue

        played_at = datetime.fromisoformat(
            item["played_at"].replace(
                "Z",
                "+00:00",
            )
        )

        # Prevent duplicate listening records
        result = await db.execute(
            select(ListeningHistory).where(
                ListeningHistory.user_id == user_id,
                ListeningHistory.track_id == track.id,
                ListeningHistory.played_at == played_at,
            )
        )

        existing = result.scalar_one_or_none()

        if existing:
            continue

        history = ListeningHistory(
            user_id=user_id,
            track_id=track.id,
            played_at=played_at,
            duration_ms=track.duration_ms,
        )

        db.add(history)

        synced += 1

    await db.flush()
    return synced

async def sync_spotify_data(
    db: AsyncSession,
    user_id,
):
    started_at = datetime.now(timezone.utc)

    sync_log = SpotifySyncLog(
        user_id=user_id,
        started_at=started_at,
        status="running",
    )

    db.add(sync_log)
    await db.flush()

    try:
        account = await get_spotify_account(
            db,
            user_id,
        )

        access_token = await get_valid_access_token(
            account
        )

        top_artists_data = await get_top_artists(
            access_token
        )

        top_tracks_data = await get_top_tracks(
            access_token
        )

        recently_played_data = await get_recently_played(
            access_token
        )

        artist_count = await sync_artists(
            db,
            access_token,
            top_artists_data["items"],
        )

        await sync_tracks(
            db,
            top_tracks_data["items"],
        )

        await sync_tracks(
            db,
            [
                item["track"]
                for item in recently_played_data["items"]
            ],
        )

        recent_count = await sync_recently_played(
            db,
            user_id,
            recently_played_data["items"],
        )

        sync_log.completed_at = datetime.now(
            timezone.utc
        )

        sync_log.status = "success"

        sync_log.artists_synced = artist_count

        sync_log.tracks_synced = (
            len(top_tracks_data["items"])
            + len(recently_played_data["items"])
        )

        sync_log.history_synced = recent_count

        await db.commit()

        return {
            "artists": artist_count,
            "top_tracks": len(
                top_tracks_data["items"]
            ),
            "recently_played": recent_count,
            "status": "success",
        }

    except Exception as exc:
        sync_log.completed_at = datetime.now(
            timezone.utc
        )

        sync_log.status = "failed"

        sync_log.error_message = str(exc)

        await db.commit()

        raise