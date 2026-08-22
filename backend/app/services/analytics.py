from collections import Counter
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.artist import Artist
from app.db.models.listening_history import ListeningHistory
from app.db.models.track import Track


async def get_listening_behavior(
    db: AsyncSession,
    user_id,
) -> dict:
    result = await db.execute(
        select(
            func.count(ListeningHistory.id),
            func.count(func.distinct(ListeningHistory.track_id)),
            func.count(func.distinct(Track.artist_id)),
            func.sum(ListeningHistory.duration_ms),
        )
        .join(
            Track,
            Track.id == ListeningHistory.track_id,
        )
        .where(
            ListeningHistory.user_id == user_id
        )
    )

    (
        total_plays,
        unique_tracks,
        unique_artists,
        total_duration_ms,
    ) = result.one()

    total_plays = total_plays or 0
    unique_tracks = unique_tracks or 0
    unique_artists = unique_artists or 0
    total_duration_ms = total_duration_ms or 0

    return {
        "total_plays": total_plays,
        "unique_tracks": unique_tracks,
        "unique_artists": unique_artists,
        "total_listening_time_ms": total_duration_ms,
        "total_listening_time_minutes": round(
            total_duration_ms / 60000,
            2,
        ),
        "total_listening_time_hours": round(
            total_duration_ms / 3600000,
            2,
        ),
    }


async def get_top_artists(
    db: AsyncSession,
    user_id,
    limit: int = 10,
) -> list[dict]:
    result = await db.execute(
        select(
            Artist.name,
            func.count(ListeningHistory.id).label("play_count"),
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
            func.count(ListeningHistory.id).desc()
        )
        .limit(limit)
    )

    rows = result.all()

    total_result = await db.execute(
        select(
            func.count(ListeningHistory.id)
        ).where(
            ListeningHistory.user_id == user_id
        )
    )

    total_plays = total_result.scalar() or 0

    return [
        {
            "rank": index,
            "artist": row.name,
            "play_count": row.play_count,
            "share_of_listens": round(
                row.play_count / total_plays,
                4,
            ) if total_plays else 0,
        }
        for index, row in enumerate(rows, start=1)
    ]


async def get_top_tracks(
    db: AsyncSession,
    user_id,
    limit: int = 10,
) -> list[dict]:
    result = await db.execute(
        select(
            Track.name,
            Artist.name.label("artist"),
            func.count(ListeningHistory.id).label("play_count"),
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
        .group_by(
            Track.id,
            Track.name,
            Artist.name,
        )
        .order_by(
            func.count(ListeningHistory.id).desc()
        )
        .limit(limit)
    )

    return [
        {
            "rank": index,
            "track": row.name,
            "artist": row.artist,
            "play_count": row.play_count,
        }
        for index, row in enumerate(
            result.all(),
            start=1,
        )
    ]


async def get_listening_patterns(
    db: AsyncSession,
    user_id,
) -> dict:
    result = await db.execute(
        select(ListeningHistory.played_at)
        .where(
            ListeningHistory.user_id == user_id
        )
    )

    played_at_values = [
        row[0]
        for row in result.all()
    ]

    hour_counts = Counter()
    weekday_counts = Counter()

    for played_at in played_at_values:
        hour_counts[played_at.hour] += 1
        weekday_counts[played_at.strftime("%A")] += 1

    weekday_order = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]

    peak_hour = (
        hour_counts.most_common(1)[0][0]
        if hour_counts
        else None
    )

    peak_day = (
        weekday_counts.most_common(1)[0][0]
        if weekday_counts
        else None
    )

    return {
        "listens_by_hour": {
            str(hour): hour_counts.get(hour, 0)
            for hour in range(24)
        },
        "listens_by_weekday": {
            day: weekday_counts.get(day, 0)
            for day in weekday_order
        },
        "peak_listening_hour": peak_hour,
        "peak_listening_day": peak_day,
    }


async def get_audio_profile(
    db: AsyncSession,
    user_id,
) -> dict:
    result = await db.execute(
        select(
            func.count(ListeningHistory.id),
            func.count(func.distinct(ListeningHistory.track_id)),
            func.count(func.distinct(Track.artist_id)),
            func.sum(ListeningHistory.duration_ms),
            func.avg(ListeningHistory.duration_ms),
        )
        .join(
            Track,
            Track.id == ListeningHistory.track_id,
        )
        .where(
            ListeningHistory.user_id == user_id
        )
    )

    (
        total_plays,
        unique_tracks,
        unique_artists,
        total_duration_ms,
        average_duration_ms,
    ) = result.one()

    total_plays = total_plays or 0
    unique_tracks = unique_tracks or 0
    unique_artists = unique_artists or 0
    total_duration_ms = total_duration_ms or 0
    average_duration_ms = average_duration_ms or 0

    repeat_rate = (
        round(
            (total_plays - unique_tracks)
            / total_plays,
            4,
        )
        if total_plays
        else 0
    )

    average_plays_per_track = (
        round(
            total_plays / unique_tracks,
            2,
        )
        if unique_tracks
        else 0
    )

    artist_concentration = (
        round(
            unique_artists / total_plays,
            4,
        )
        if total_plays
        else 0
    )

    return {
        "tracks_analyzed": unique_tracks,
        "unique_artists": unique_artists,
        "total_plays": total_plays,
        "total_listening_time_ms": total_duration_ms,
        "total_listening_time_minutes": round(
            total_duration_ms / 60000,
            2,
        ),
        "total_listening_time_hours": round(
            total_duration_ms / 3600000,
            2,
        ),
        "average_track_duration_ms": round(
            average_duration_ms,
            2,
        ),
        "average_track_duration_minutes": round(
            average_duration_ms / 60000,
            2,
        ),
        "average_plays_per_track": average_plays_per_track,
        "repeat_rate": repeat_rate,
        "artist_diversity_ratio": artist_concentration,
        "audio_features_available": False,
    }


async def get_listening_trends(
    db: AsyncSession,
    user_id,
) -> dict:
    result = await db.execute(
        select(ListeningHistory.played_at)
        .where(
            ListeningHistory.user_id == user_id
        )
        .order_by(ListeningHistory.played_at)
    )

    played_at_values = [
        row[0]
        for row in result.all()
    ]

    daily_counts = Counter()
    weekly_counts = Counter()

    for played_at in played_at_values:
        daily_key = played_at.date().isoformat()

        week_start = (
            played_at.date()
            - timedelta(days=played_at.weekday())
        )

        weekly_key = week_start.isoformat()

        daily_counts[daily_key] += 1
        weekly_counts[weekly_key] += 1

    return {
        "daily_listens": dict(
            sorted(daily_counts.items())
        ),
        "weekly_listens": dict(
            sorted(weekly_counts.items())
        ),
        "days_with_listening_activity": len(
            daily_counts
        ),
    }


async def get_genre_analysis(
    db: AsyncSession,
    user_id,
) -> dict:
    """
    Analyze stored artist genres when available.

    Spotify may not provide genre metadata through the
    current API flow, so this endpoint safely returns
    an empty analysis when no genre metadata exists.
    """

    return {
        "genres_available": False,
        "genres": [],
        "message": (
            "Genre metadata is not currently available "
            "from the synchronized Spotify data."
        ),
    }


async def get_taste_profile(
    db: AsyncSession,
    user_id,
) -> dict:
    behavior = await get_listening_behavior(
        db,
        user_id,
    )

    patterns = await get_listening_patterns(
        db,
        user_id,
    )

    audio_profile = await get_audio_profile(
        db,
        user_id,
    )

    top_artists = await get_top_artists(
        db,
        user_id,
        limit=5,
    )

    top_tracks = await get_top_tracks(
        db,
        user_id,
        limit=5,
    )

    return {
        "summary": {
            "total_plays": behavior["total_plays"],
            "unique_tracks": behavior["unique_tracks"],
            "unique_artists": behavior["unique_artists"],
            "listening_hours": behavior[
                "total_listening_time_hours"
            ],
        },
        "preferences": {
            "top_artists": top_artists,
            "top_tracks": top_tracks,
        },
        "listening_patterns": {
            "peak_hour": patterns[
                "peak_listening_hour"
            ],
            "peak_day": patterns[
                "peak_listening_day"
            ],
        },
        "behavioral_metrics": {
            "repeat_rate": audio_profile[
                "repeat_rate"
            ],
            "average_plays_per_track": audio_profile[
                "average_plays_per_track"
            ],
            "artist_diversity_ratio": audio_profile[
                "artist_diversity_ratio"
            ],
        },
    }