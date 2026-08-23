from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audio.feature_extractor import extract_audio_features
from app.db.models.track import Track
from app.db.models.track_features import TrackFeatures


AUDIO_DIRECTORY = Path("audio_files")


async def ingest_local_audio_features(
    db: AsyncSession,
) -> dict:
    """
    Analyze local audio files and store their extracted
    features in the track_features table.

    Audio files must be named:

        <spotify_track_id>.mp3

    Example:

        4GgwuDH7G6WxsAw2wWDsaz.mp3
    """

    if not AUDIO_DIRECTORY.exists():
        return {
            "audio_files_found": 0,
            "tracks_matched": 0,
            "features_created": 0,
            "features_updated": 0,
            "skipped": 0,
        }

    audio_files = list(
        AUDIO_DIRECTORY.glob("*.mp3")
    )

    features_created = 0
    features_updated = 0
    tracks_matched = 0
    skipped = 0

    for audio_file in audio_files:

        spotify_track_id = audio_file.stem

        # -----------------------------------------------------
        # FIND TRACK
        # -----------------------------------------------------

        result = await db.execute(
            select(Track).where(
                Track.spotify_track_id
                == spotify_track_id
            )
        )

        track = result.scalar_one_or_none()

        if not track:
            print(
                f"SKIPPED: No database track found for "
                f"{audio_file.name}"
            )

            skipped += 1
            continue

        tracks_matched += 1

        print(
            f"ANALYZING: {track.name} "
            f"({spotify_track_id})"
        )

        # -----------------------------------------------------
        # EXTRACT FEATURES
        # -----------------------------------------------------

        try:
            features = extract_audio_features(
                str(audio_file)
            )

        except Exception as exc:
            print(
                f"FEATURE EXTRACTION ERROR "
                f"{audio_file.name}: {exc}"
            )

            skipped += 1
            continue

        # -----------------------------------------------------
        # FIND EXISTING FEATURES
        # -----------------------------------------------------

        result = await db.execute(
            select(TrackFeatures).where(
                TrackFeatures.track_id
                == track.id
            )
        )

        track_features = (
            result.scalar_one_or_none()
        )

        # -----------------------------------------------------
        # CREATE OR UPDATE
        # -----------------------------------------------------

        if not track_features:

            track_features = TrackFeatures(
                track_id=track.id,
            )

            db.add(track_features)

            features_created += 1

        else:
            features_updated += 1

        track_features.energy = features.get(
            "energy"
        )

        track_features.danceability = features.get(
            "danceability"
        )

        track_features.valence = features.get(
            "valence"
        )

        track_features.acousticness = features.get(
            "acousticness"
        )

        track_features.instrumentalness = (
            features.get(
                "instrumentalness"
            )
        )

        track_features.speechiness = features.get(
            "speechiness"
        )

        track_features.tempo = features.get(
            "tempo"
        )

        print(
            f"FEATURES SAVED: {features}"
        )

    await db.commit()

    return {
        "audio_files_found": len(audio_files),
        "tracks_matched": tracks_matched,
        "features_created": features_created,
        "features_updated": features_updated,
        "skipped": skipped,
    }