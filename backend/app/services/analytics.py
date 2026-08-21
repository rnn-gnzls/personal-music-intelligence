from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.artist import Artist
from app.db.models.track import Track
from app.db.models.listening_history import ListeningHistory


async def get_listening_summary(
    db: AsyncSession,
    user_id,
):
    total_plays = await db.scalar(
        select(
            func.count(ListeningHistory.id)
        ).where(
            ListeningHistory.user_id == user_id
        )
    )

    unique_tracks = await db.scalar(
        select(
            func.count(
                func.distinct(
                    ListeningHistory.track_id
                )
            )
        ).where(
            ListeningHistory.user_id == user_id
        )
    )

    unique_artists = await db.scalar(
        select(
            func.count(
                func.distinct(
                    Track.artist_id
                )
            )
        )
        .join(
            ListeningHistory,
            ListeningHistory.track_id == Track.id,
        )
        .where(
            ListeningHistory.user_id == user_id
        )
    )

    return {
        "total_plays": total_plays or 0,
        "unique_tracks": unique_tracks or 0,
        "unique_artists": unique_artists or 0,
    }


async def get_top_artists(
    db: AsyncSession,
    user_id,
    limit: int = 10,
):
    query = (
        select(
            Artist.name,
            func.count(
                ListeningHistory.id
            ).label("play_count"),
        )
        .join(
            Track,
            Track.artist_id == Artist.id,
        )
        .join(
            ListeningHistory,
            ListeningHistory.track_id == Track.id,
        )
        .where(
            ListeningHistory.user_id == user_id
        )
        .group_by(
            Artist.id,
            Artist.name,
        )
        .order_by(
            func.count(
                ListeningHistory.id
            ).desc()
        )
        .limit(limit)
    )

    result = await db.execute(query)

    return [
        {
            "artist": row.name,
            "play_count": row.play_count,
        }
        for row in result
    ]


async def get_top_tracks(
    db: AsyncSession,
    user_id,
    limit: int = 10,
):
    query = (
        select(
            Track.name,
            func.count(
                ListeningHistory.id
            ).label("play_count"),
        )
        .join(
            ListeningHistory,
            ListeningHistory.track_id == Track.id,
        )
        .where(
            ListeningHistory.user_id == user_id
        )
        .group_by(
            Track.id,
            Track.name,
        )
        .order_by(
            func.count(
                ListeningHistory.id
            ).desc()
        )
        .limit(limit)
    )

    result = await db.execute(query)

    return [
        {
            "track": row.name,
            "play_count": row.play_count,
        }
        for row in result
    ]