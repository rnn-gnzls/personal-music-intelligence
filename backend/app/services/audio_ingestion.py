from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.track import Track
from app.db.models.track_features import TrackFeatures

from app.services.audio_features import (
    extract_audio_features,
    find_audio_file,
)


DEFAULT_AUDIO_DIRECTORY = Path("audio_files")


async def ingest_track_audio_features(
    db: AsyncSession,
    track: Track,
    audio_directory: str | Path = DEFAULT_AUDIO_DIRECTORY,
) -> bool:
    """
    Analyze one track's audio and save the extracted
    features to TrackFeatures.
    """

    audio_path = find_audio_file(
        audio_directory,
        track.spotify_track_id,
    )

    if audio_path is None:
        print(
            f"AUDIO NOT FOUND: "
            f"{track.spotify_track_id}"
        )
        return False

    try:
        features = extract_audio_features(
            audio_path
        )

    except Exception as exc:
        print(
            f"AUDIO ANALYSIS ERROR "
            f"{track.spotify_track_id}: "
            f"{type(exc).__name__}: {exc}"
        )
        return False

    result = await db.execute(
        select(TrackFeatures).where(
            TrackFeatures.track_id == track.id
        )
    )

    track_features = (
        result.scalar_one_or_none()
    )

    if track_features is None:
        track_features = TrackFeatures(
            track_id=track.id
        )

        db.add(track_features)

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
        "\n========== AUDIO FEATURES =========="
    )

    print(
        f"Track: {track.name}"
    )

    print(
        f"Spotify ID: "
        f"{track.spotify_track_id}"
    )

    print(
        f"Audio: {audio_path}"
    )

    print(
        f"Energy: "
        f"{features.get('energy')}"
    )

    print(
        f"Danceability: "
        f"{features.get('danceability')}"
    )

    print(
        f"Valence: "
        f"{features.get('valence')}"
    )

    print(
        f"Acousticness: "
        f"{features.get('acousticness')}"
    )

    print(
        f"Instrumentalness: "
        f"{features.get('instrumentalness')}"
    )

    print(
        f"Speechiness: "
        f"{features.get('speechiness')}"
    )

    print(
        f"Tempo: "
        f"{features.get('tempo')}"
    )

    print(
        "====================================\n"
    )

    return True


async def ingest_all_available_audio(
    db: AsyncSession,
    audio_directory: str | Path = DEFAULT_AUDIO_DIRECTORY,
) -> dict:
    """
    Analyze every database track for which an audio
    file is available.
    """

    result = await db.execute(
        select(Track)
    )

    tracks = result.scalars().all()

    analyzed = 0
    missing = 0
    failed = 0

    for track in tracks:

        audio_path = find_audio_file(
            audio_directory,
            track.spotify_track_id,
        )

        if audio_path is None:
            missing += 1
            continue

        success = await ingest_track_audio_features(
            db,
            track,
            audio_directory,
        )

        if success:
            analyzed += 1
        else:
            failed += 1

    await db.commit()

    return {
        "total_tracks": len(tracks),
        "analyzed": analyzed,
        "missing_audio": missing,
        "failed": failed,
    }