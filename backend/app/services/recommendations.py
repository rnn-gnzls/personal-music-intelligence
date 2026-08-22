from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.artist import Artist
from app.db.models.listening_history import ListeningHistory
from app.db.models.track import Track
from app.db.models.track_features import TrackFeatures


FEATURES = [
    "energy",
    "danceability",
    "valence",
    "acousticness",
    "instrumentalness",
    "speechiness",
    "tempo",
]


# ============================================================
# USER PROFILE
# ============================================================

async def get_user_profile(
    db: AsyncSession,
    user_id,
) -> dict:
    result = await db.execute(
        select(
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
            ListeningHistory,
            ListeningHistory.track_id == Track.id,
        )
        .where(
            ListeningHistory.user_id == user_id
        )
    )

    rows = result.all()

    if not rows:
        return {
            feature: None
            for feature in FEATURES
        }

    profile = {}

    for index, feature in enumerate(FEATURES):
        values = [
            row[index]
            for row in rows
            if row[index] is not None
        ]

        profile[feature] = (
            sum(values) / len(values)
            if values
            else None
        )

    return profile


# ============================================================
# LISTENING HISTORY
# ============================================================

async def get_listened_track_ids(
    db: AsyncSession,
    user_id,
) -> set:
    result = await db.execute(
        select(
            ListeningHistory.track_id
        ).where(
            ListeningHistory.user_id == user_id
        )
    )

    return {
        row[0]
        for row in result.all()
    }


async def get_listened_artist_ids(
    db: AsyncSession,
    user_id,
) -> set:
    result = await db.execute(
        select(
            Track.artist_id
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
        row[0]
        for row in result.all()
    }


# ============================================================
# SIMILARITY
# ============================================================

def calculate_feature_similarity(
    profile: dict,
    candidate,
) -> float:
    differences = []

    for feature in FEATURES:
        user_value = profile.get(feature)

        candidate_value = getattr(
            candidate,
            feature,
            None,
        )

        if (
            user_value is None
            or candidate_value is None
        ):
            continue

        if feature == "tempo":
            difference = (
                abs(
                    user_value - candidate_value
                )
                / 200
            )
        else:
            difference = abs(
                user_value - candidate_value
            )

        differences.append(
            min(difference, 1)
        )

    if not differences:
        return 0.0

    similarity = 1 - (
        sum(differences)
        / len(differences)
    )

    return max(
        0.0,
        min(similarity, 1.0),
    )


# ============================================================
# RECOMMENDATION SCORE
# ============================================================

def calculate_recommendation_score(
    similarity_score: float,
    context_score: float,
    novelty_score: float,
    discovery_score: float,
) -> float:
    final_score = (
        similarity_score * 0.50
        + context_score * 0.25
        + novelty_score * 0.15
        + discovery_score * 0.10
    )

    return round(
        final_score,
        4,
    )


# ============================================================
# SONG RECOMMENDATIONS
# ============================================================

async def get_song_recommendations(
    db: AsyncSession,
    user_id,
    limit: int = 10,
) -> list[dict]:

    profile = await get_user_profile(
        db,
        user_id,
    )

    listened_track_ids = (
        await get_listened_track_ids(
            db,
            user_id,
        )
    )

    listened_artist_ids = (
        await get_listened_artist_ids(
            db,
            user_id,
        )
    )

    # No listening profile yet.
    if not any(
        value is not None
        for value in profile.values()
    ):
        return []

    result = await db.execute(
        select(
            Track,
            Artist.name.label("artist_name"),
            TrackFeatures,
        )
        .join(
            Artist,
            Artist.id == Track.artist_id,
        )
        .join(
            TrackFeatures,
            TrackFeatures.track_id == Track.id,
        )
    )

    recommendations = []

    for track, artist_name, features in result.all():

        # Never recommend something the user
        # has already listened to.
        if track.id in listened_track_ids:
            continue

        similarity_score = (
            calculate_feature_similarity(
                profile,
                features,
            )
        )

        # Context score:
        # currently based on similarity to the
        # user's overall audio profile.
        context_score = similarity_score

        # Since this is a NEW track,
        # it receives a strong novelty score.
        novelty_score = 1.0

        # New artist = discovery opportunity.
        discovery_score = (
            1.0
            if track.artist_id
            not in listened_artist_ids
            else 0.0
        )

        final_score = calculate_recommendation_score(
            similarity_score,
            context_score,
            novelty_score,
            discovery_score,
        )

        recommendations.append(
            {
                "track_id": str(track.id),
                "track": track.name,
                "artist": artist_name,
                "similarity_score": round(
                    similarity_score * 100,
                    2,
                ),
                "context_score": round(
                    context_score * 100,
                    2,
                ),
                "novelty_score": round(
                    novelty_score * 100,
                    2,
                ),
                "discovery_score": round(
                    discovery_score * 100,
                    2,
                ),
                "score": round(
                    final_score * 100,
                    2,
                ),
                "reason": (
                    "Recommended because its audio profile "
                    "matches your listening taste."
                    if discovery_score == 0
                    else
                    "Recommended because it matches your "
                    "listening taste while introducing a "
                    "new artist."
                ),
            }
        )

    recommendations.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return recommendations[:limit]


# ============================================================
# ARTIST RECOMMENDATIONS
# ============================================================

async def get_artist_recommendations(
    db: AsyncSession,
    user_id,
    limit: int = 10,
) -> list[dict]:

    profile = await get_user_profile(
        db,
        user_id,
    )

    listened_artist_ids = (
        await get_listened_artist_ids(
            db,
            user_id,
        )
    )

    # Find artists that have tracks with
    # available audio features.
    result = await db.execute(
        select(
            Artist.id,
            Artist.name,
            TrackFeatures,
        )
        .join(
            Track,
            Track.artist_id == Artist.id,
        )
        .join(
            TrackFeatures,
            TrackFeatures.track_id == Track.id,
        )
    )

    artist_candidates = {}

    for artist_id, artist_name, features in result.all():

        # IMPORTANT:
        # Skip artists the user has already listened to.
        if artist_id in listened_artist_ids:
            continue

        similarity = calculate_feature_similarity(
            profile,
            features,
        )

        if artist_id not in artist_candidates:
            artist_candidates[artist_id] = {
                "artist_id": str(artist_id),
                "artist": artist_name,
                "similarities": [],
            }

        artist_candidates[
            artist_id
        ]["similarities"].append(
            similarity
        )

    recommendations = []

    for candidate in artist_candidates.values():

        similarities = candidate["similarities"]

        if not similarities:
            continue

        similarity_score = (
            sum(similarities)
            / len(similarities)
        )

        context_score = similarity_score

        # Every artist here is new to the user.
        novelty_score = 1.0

        # New artist = discovery.
        discovery_score = 1.0

        final_score = calculate_recommendation_score(
            similarity_score,
            context_score,
            novelty_score,
            discovery_score,
        )

        recommendations.append(
            {
                "artist_id": candidate["artist_id"],
                "artist": candidate["artist"],
                "similarity_score": round(
                    similarity_score * 100,
                    2,
                ),
                "context_score": round(
                    context_score * 100,
                    2,
                ),
                "novelty_score": 100.0,
                "discovery_score": 100.0,
                "score": round(
                    final_score * 100,
                    2,
                ),
                "reason": (
                    "New artist whose music matches "
                    "your listening profile."
                ),
            }
        )

    recommendations.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return recommendations[:limit]


# ============================================================
# MOOD RECOMMENDATIONS
# ============================================================

async def get_mood_recommendations(
    db: AsyncSession,
    user_id,
    mood: str,
    limit: int = 10,
) -> list[dict]:

    mood_ranges = {
        "happy": {
            "valence": 0.75,
            "energy": 0.65,
        },
        "sad": {
            "valence": 0.25,
            "energy": 0.40,
        },
        "energetic": {
            "energy": 0.85,
            "valence": 0.60,
        },
        "calm": {
            "energy": 0.30,
            "acousticness": 0.60,
        },
        "romantic": {
            "valence": 0.60,
            "energy": 0.40,
            "acousticness": 0.45,
        },
        "focus": {
            "energy": 0.40,
            "instrumentalness": 0.35,
            "speechiness": 0.10,
        },
    }

    target = mood_ranges.get(
        mood.lower()
    )

    if not target:
        return []

    listened_track_ids = (
        await get_listened_track_ids(
            db,
            user_id,
        )
    )

    listened_artist_ids = (
        await get_listened_artist_ids(
            db,
            user_id,
        )
    )

    result = await db.execute(
        select(
            Track,
            Artist.name.label("artist_name"),
            TrackFeatures,
        )
        .join(
            Artist,
            Artist.id == Track.artist_id,
        )
        .join(
            TrackFeatures,
            TrackFeatures.track_id == Track.id,
        )
    )

    recommendations = []

    for track, artist_name, features in result.all():

        # Only NEW songs.
        if track.id in listened_track_ids:
            continue

        differences = []

        for feature, target_value in target.items():

            value = getattr(
                features,
                feature,
                None,
            )

            if value is None:
                continue

            if feature == "tempo":
                difference = (
                    abs(value - target_value)
                    / 200
                )
            else:
                difference = abs(
                    value - target_value
                )

            differences.append(
                min(difference, 1)
            )

        if not differences:
            continue

        context_score = max(
            0.0,
            1 - (
                sum(differences)
                / len(differences)
            ),
        )

        # New track.
        novelty_score = 1.0

        # New artist gets discovery bonus.
        discovery_score = (
            1.0
            if track.artist_id
            not in listened_artist_ids
            else 0.0
        )

        # User profile similarity is still useful
        # so mood recommendations don't become
        # completely disconnected from the user's taste.
        profile = await get_user_profile(
            db,
            user_id,
        )

        similarity_score = (
            calculate_feature_similarity(
                profile,
                features,
            )
            if any(
                value is not None
                for value in profile.values()
            )
            else context_score
        )

        final_score = calculate_recommendation_score(
            similarity_score,
            context_score,
            novelty_score,
            discovery_score,
        )

        recommendations.append(
            {
                "track_id": str(track.id),
                "track": track.name,
                "artist": artist_name,
                "mood": mood,
                "similarity_score": round(
                    similarity_score * 100,
                    2,
                ),
                "context_score": round(
                    context_score * 100,
                    2,
                ),
                "novelty_score": 100.0,
                "discovery_score": round(
                    discovery_score * 100,
                    2,
                ),
                "score": round(
                    final_score * 100,
                    2,
                ),
                "reason": (
                    f"Matches a {mood.lower()} vibe "
                    "while giving you something new."
                ),
            }
        )

    recommendations.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return recommendations[:limit]