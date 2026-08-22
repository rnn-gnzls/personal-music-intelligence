from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.artist import Artist
from app.db.models.listening_history import ListeningHistory
from app.db.models.track import Track
from app.db.models.track_features import TrackFeatures


async def get_bi_overview(
    db: AsyncSession,
    user_id,
) -> dict:

    result = await db.execute(
        select(
            func.count(
                ListeningHistory.id
            ),
            func.count(
                func.distinct(
                    ListeningHistory.track_id
                )
            ),
            func.sum(
                ListeningHistory.duration_ms
            ),
        )
        .where(
            ListeningHistory.user_id == user_id
        )
    )

    total_plays, unique_tracks, duration = (
        result.one()
    )

    return {
        "total_plays": total_plays or 0,
        "unique_tracks": unique_tracks or 0,
        "total_listening_hours": round(
            (duration or 0) / 3600000,
            2,
        ),
    }

async def get_bi_listening_behavior(
    db: AsyncSession,
    user_id,
) -> list[dict]:

    result = await db.execute(
        select(
            ListeningHistory.played_at,
            ListeningHistory.duration_ms,
            Track.name.label("track"),
            Artist.name.label("artist"),
        )
        .join(
            Track,
            Track.id == ListeningHistory.track_id,
        )
        .join(
            Artist,
            Artist.id == Track.artist_id,
        )
        .where(
            ListeningHistory.user_id == user_id
        )
        .order_by(
            ListeningHistory.played_at
        )
    )

    return [
        {
            "played_at": row.played_at,
            "duration_ms": row.duration_ms,
            "track": row.track,
            "artist": row.artist,
        }
        for row in result.all()
    ]

async def get_bi_audio_features(
    db: AsyncSession,
    user_id,
) -> list[dict]:

    result = await db.execute(
        select(
            Track.name.label("track"),
            Artist.name.label("artist"),
            TrackFeatures.energy,
            TrackFeatures.danceability,
            TrackFeatures.valence,
            TrackFeatures.acousticness,
            TrackFeatures.instrumentalness,
            TrackFeatures.speechiness,
            TrackFeatures.tempo,
        )
        .join(
            Track,
            Track.id == TrackFeatures.track_id,
        )
        .join(
            Artist,
            Artist.id == Track.artist_id,
        )
        .join(
            ListeningHistory,
            ListeningHistory.track_id == Track.id,
        )
        .where(
            ListeningHistory.user_id == user_id
        )
    )

    return [
        {
            "track": row.track,
            "artist": row.artist,
            "energy": row.energy,
            "danceability": row.danceability,
            "valence": row.valence,
            "acousticness": row.acousticness,
            "instrumentalness": row.instrumentalness,
            "speechiness": row.speechiness,
            "tempo": row.tempo,
        }
        for row in result.all()
    ]