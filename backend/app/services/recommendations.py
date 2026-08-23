from pathlib import Path

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
# LOCAL AUDIO
# ============================================================

def get_local_audio_track_ids() -> set[str]:
    """
    Return Spotify track IDs for locally downloaded audio files.

    Files are expected to use the Spotify track ID as filename:

        audio_files/<spotify_track_id>.mp3
        audio_files/<spotify_track_id>.wav
        audio_files/<spotify_track_id>.flac
        audio_files/<spotify_track_id>.m4a

    These tracks are excluded from recommendations because they
    are locally owned/analyzed tracks, not discovery candidates.
    """

    audio_directory = Path("audio_files")

    if not audio_directory.exists():
        return set()

    supported_extensions = {
        ".mp3",
        ".wav",
        ".flac",
        ".m4a",
        ".ogg",
    }

    return {
        file_path.stem
        for file_path in audio_directory.iterdir()
        if (
            file_path.is_file()
            and file_path.suffix.lower()
            in supported_extensions
        )
    }


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
# LISTENED TRACKS
# ============================================================

async def get_listened_track_ids(
    db: AsyncSession,
    user_id,
) -> set:

    result = await db.execute(
        select(
            ListeningHistory.track_id
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
# LISTENED ARTISTS
# ============================================================

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
        .distinct()
    )

    return {
        row[0]
        for row in result.all()
    }


# ============================================================
# FEATURE SIMILARITY
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

            difference = abs(
                user_value - candidate_value
            ) / 200

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
        similarity,
    )


# ============================================================
# FINAL RECOMMENDATION SCORE
# ============================================================

def calculate_recommendation_score(
    similarity_score: float,
    context_score: float,
    novelty_score: float,
    discovery_score: float,
) -> float:
    """
    Combine recommendation signals into a final 0-100 score.
    """

    final_score = (
        similarity_score * 0.50
        + context_score * 0.25
        + novelty_score * 0.15
        + discovery_score * 0.10
    )

    return round(
        final_score,
        2,
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

    listened_ids = await get_listened_track_ids(
        db,
        user_id,
    )

    # IMPORTANT:
    # Never recommend locally downloaded/analyzed tracks.
    local_audio_ids = get_local_audio_track_ids()

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

    candidates = []

    for track, artist_name, features in result.all():

        spotify_track_id = track.spotify_track_id

        # ----------------------------------------------------
        # FILTER 1: already listened
        # ----------------------------------------------------

        if track.id in listened_ids:
            continue

        # ----------------------------------------------------
        # FILTER 2: locally downloaded/analyzed
        # ----------------------------------------------------

        if spotify_track_id in local_audio_ids:
            continue

        # ----------------------------------------------------
        # FEATURE SIMILARITY
        # ----------------------------------------------------

        similarity = calculate_feature_similarity(
            profile,
            features,
        )

        if similarity <= 0:
            continue

        # ----------------------------------------------------
        # NOVELTY
        #
        # Completely new track = high novelty.
        # Already excluded listened tracks, therefore 1.0.
        # ----------------------------------------------------

        novelty_score = 1.0

        # ----------------------------------------------------
        # DISCOVERY
        #
        # Slight boost for tracks whose artist has not been
        # listened to before.
        # ----------------------------------------------------

        artist_result = await db.execute(
            select(ListeningHistory.id)
            .join(
                Track,
                Track.id == ListeningHistory.track_id,
            )
            .where(
                ListeningHistory.user_id == user_id,
                Track.artist_id == track.artist_id,
            )
            .limit(1)
        )

        artist_already_listened = (
            artist_result.scalar_one_or_none()
            is not None
        )

        discovery_score = (
            0.0
            if artist_already_listened
            else 1.0
        )

        # ----------------------------------------------------
        # CONTEXT
        #
        # Base context score for now.
        # Mood-specific recommendations use their own score.
        # ----------------------------------------------------

        context_score = similarity

        final_score = calculate_recommendation_score(
            similarity_score=similarity,
            context_score=context_score,
            novelty_score=novelty_score,
            discovery_score=discovery_score,
        )

        candidates.append(
            {
                "track_id": str(track.id),
                "spotify_track_id": spotify_track_id,
                "track": track.name,
                "artist": artist_name,
                "score": round(
                    final_score * 100,
                    2,
                ),
                "similarity_score": round(
                    similarity * 100,
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
                "reason": (
                    "New song with an audio profile "
                    "similar to your listening taste."
                ),
            }
        )

    candidates.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return candidates[:limit]


# ============================================================
# ARTIST RECOMMENDATIONS
# ============================================================

async def get_artist_recommendations(
    db: AsyncSession,
    user_id,
    limit: int = 10,
) -> list[dict]:

    # ---------------------------------------------------------
    # Get artists already listened to by the user
    # ---------------------------------------------------------

    listened_artist_result = await db.execute(
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
        .distinct()
    )

    listened_artist_ids = {
        row[0]
        for row in listened_artist_result.all()
    }

    # ---------------------------------------------------------
    # Get all artists that have tracks
    # ---------------------------------------------------------

    result = await db.execute(
        select(
            Artist.id,
            Artist.name,
            func.count(Track.id).label("track_count"),
        )
        .join(
            Track,
            Track.artist_id == Artist.id,
        )
        .group_by(
            Artist.id,
            Artist.name,
        )
    )

    candidates = []

    for row in result.all():

        # -----------------------------------------------------
        # HARD FILTER:
        # Never recommend an artist already listened to
        # -----------------------------------------------------

        if row.id in listened_artist_ids:
            continue

        # -----------------------------------------------------
        # Basic discovery score
        #
        # Artists with more available tracks get a slightly
        # higher discovery score because they provide more
        # recommendation opportunities.
        # -----------------------------------------------------

        discovery_score = min(
            row.track_count * 10,
            100,
        )

        candidates.append(
            {
                "artist_id": str(row.id),
                "artist": row.name,
                "score": round(
                    discovery_score,
                    2,
                ),
                "reason": (
                    "New artist you haven't listened to "
                    "yet."
                ),
            }
        )

    # ---------------------------------------------------------
    # Sort only after filtering known artists
    # ---------------------------------------------------------

    candidates.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return candidates[:limit]

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
            "valence": 0.7,
            "energy": 0.6,
        },

        "sad": {
            "valence": 0.3,
            "energy": 0.4,
        },

        "energetic": {
            "energy": 0.8,
            "valence": 0.5,
        },

        "calm": {
            "energy": 0.3,
            "acousticness": 0.5,
        },
    }

    target = mood_ranges.get(
        mood.lower()
    )

    if not target:
        return []

    listened_ids = await get_listened_track_ids(
        db,
        user_id,
    )

    # IMPORTANT:
    # Never recommend the locally downloaded test track.
    local_audio_ids = get_local_audio_track_ids()

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

        # ----------------------------------------------------
        # FILTER 1: already listened
        # ----------------------------------------------------

        if track.id in listened_ids:
            continue

        # ----------------------------------------------------
        # FILTER 2: local audio
        # ----------------------------------------------------

        if track.spotify_track_id in local_audio_ids:
            continue

        differences = []

        for feature, target_value in target.items():

            value = getattr(
                features,
                feature,
                None,
            )

            if value is not None:

                if feature == "tempo":

                    difference = abs(
                        value - target_value
                    ) / 200

                else:

                    difference = abs(
                        value - target_value
                    )

                differences.append(
                    min(
                        difference,
                        1,
                    )
                )

        if not differences:
            continue

        mood_similarity = max(
            0.0,
            1 - (
                sum(differences)
                / len(differences)
            ),
        )

        # New track = maximum novelty.
        novelty_score = 1.0

        # ----------------------------------------------------
        # Check whether artist is new.
        # ----------------------------------------------------

        artist_result = await db.execute(
            select(ListeningHistory.id)
            .join(
                Track,
                Track.id == ListeningHistory.track_id,
            )
            .where(
                ListeningHistory.user_id == user_id,
                Track.artist_id == track.artist_id,
            )
            .limit(1)
        )

        artist_already_listened = (
            artist_result.scalar_one_or_none()
            is not None
        )

        discovery_score = (
            0.0
            if artist_already_listened
            else 1.0
        )

        final_score = calculate_recommendation_score(
            similarity_score=mood_similarity,
            context_score=mood_similarity,
            novelty_score=novelty_score,
            discovery_score=discovery_score,
        )

        recommendations.append(
            {
                "track_id": str(track.id),
                "spotify_track_id": track.spotify_track_id,
                "track": track.name,
                "artist": artist_name,
                "score": round(
                    final_score * 100,
                    2,
                ),
                "mood": mood,
                "similarity_score": round(
                    mood_similarity * 100,
                    2,
                ),
                "reason": (
                    f"New song matching your "
                    f"{mood} mood."
                ),
            }
        )

    recommendations.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return recommendations[:limit]