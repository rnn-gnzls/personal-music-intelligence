from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.album import Album
from app.db.models.artist import Artist
from app.db.models.listening_history import ListeningHistory
from app.db.models.track import Track


async def validate_spotify_data(
    db: AsyncSession,
) -> dict:

    issues: list[str] = []

    # -----------------------------------------
    # Artists
    # -----------------------------------------

    artist_count = (
        await db.scalar(
            select(func.count()).select_from(Artist)
        )
    ) or 0

    artists_without_name = (
        await db.scalar(
            select(func.count())
            .select_from(Artist)
            .where(
                (Artist.name.is_(None))
                | (Artist.name == "")
            )
        )
    ) or 0

    if artists_without_name > 0:
        issues.append(
            f"{artists_without_name} artists have no name."
        )

    # -----------------------------------------
    # Albums
    # -----------------------------------------

    album_count = (
        await db.scalar(
            select(func.count()).select_from(Album)
        )
    ) or 0

    albums_without_name = (
        await db.scalar(
            select(func.count())
            .select_from(Album)
            .where(
                (Album.name.is_(None))
                | (Album.name == "")
            )
        )
    ) or 0

    if albums_without_name > 0:
        issues.append(
            f"{albums_without_name} albums have no name."
        )

    albums_without_artist = (
        await db.scalar(
            select(func.count())
            .select_from(Album)
            .where(
                Album.artist_id.is_(None)
            )
        )
    ) or 0

    if albums_without_artist > 0:
        issues.append(
            f"{albums_without_artist} albums have no artist."
        )

    # -----------------------------------------
    # Tracks
    # -----------------------------------------

    track_count = (
        await db.scalar(
            select(func.count()).select_from(Track)
        )
    ) or 0

    tracks_without_name = (
        await db.scalar(
            select(func.count())
            .select_from(Track)
            .where(
                (Track.name.is_(None))
                | (Track.name == "")
            )
        )
    ) or 0

    if tracks_without_name > 0:
        issues.append(
            f"{tracks_without_name} tracks have no name."
        )

    tracks_without_artist = (
        await db.scalar(
            select(func.count())
            .select_from(Track)
            .where(
                Track.artist_id.is_(None)
            )
        )
    ) or 0

    if tracks_without_artist > 0:
        issues.append(
            f"{tracks_without_artist} tracks have no artist."
        )

    tracks_with_invalid_duration = (
        await db.scalar(
            select(func.count())
            .select_from(Track)
            .where(
                (Track.duration_ms.is_not(None))
                & (Track.duration_ms <= 0)
            )
        )
    ) or 0

    if tracks_with_invalid_duration > 0:
        issues.append(
            f"{tracks_with_invalid_duration} tracks have invalid duration."
        )

    # -----------------------------------------
    # Listening history
    # -----------------------------------------

    history_count = (
        await db.scalar(
            select(func.count())
            .select_from(ListeningHistory)
        )
    ) or 0

    history_without_track = (
        await db.scalar(
            select(func.count())
            .select_from(ListeningHistory)
            .where(
                ListeningHistory.track_id.is_(None)
            )
        )
    ) or 0

    if history_without_track > 0:
        issues.append(
            f"{history_without_track} listening records have no track."
        )

    history_without_user = (
        await db.scalar(
            select(func.count())
            .select_from(ListeningHistory)
            .where(
                ListeningHistory.user_id.is_(None)
            )
        )
    ) or 0

    if history_without_user > 0:
        issues.append(
            f"{history_without_user} listening records have no user."
        )

    # -----------------------------------------
    # Final result
    # -----------------------------------------

    return {
        "status": (
            "passed"
            if not issues
            else "failed"
        ),
        "artists_checked": artist_count,
        "albums_checked": album_count,
        "tracks_checked": track_count,
        "listening_history_checked": history_count,
        "issues": issues,
    }