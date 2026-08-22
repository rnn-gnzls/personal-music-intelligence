from pathlib import Path

import librosa
import numpy as np


# Audio files are expected to be stored using their
# Spotify track ID as the filename.
#
# Example:
#
# audio_files/
#     4GgwuDH7G6WxsAw2wWDsaz.mp3
#
# Supported extensions are checked by find_audio_file().


SUPPORTED_EXTENSIONS = (
    ".mp3",
    ".wav",
    ".flac",
    ".ogg",
    ".m4a",
)


def find_audio_file(
    audio_directory: str | Path,
    spotify_track_id: str,
) -> Path | None:
    """
    Find an audio file associated with a Spotify track ID.
    """

    directory = Path(audio_directory)

    for extension in SUPPORTED_EXTENSIONS:
        path = directory / f"{spotify_track_id}{extension}"

        if path.exists():
            return path

    return None


def normalize_value(
    value: float,
    minimum: float,
    maximum: float,
) -> float:
    """
    Normalize a value into the 0-1 range.
    """

    if maximum <= minimum:
        return 0.0

    normalized = (
        value - minimum
    ) / (
        maximum - minimum
    )

    return float(
        np.clip(normalized, 0.0, 1.0)
    )


def extract_audio_features(
    audio_path: str | Path,
) -> dict:
    """
    Extract audio-derived features from an audio file.

    The output is intentionally compatible with the existing
    TrackFeatures database model:

        energy
        danceability
        valence
        acousticness
        instrumentalness
        speechiness
        tempo

    Some features are estimated from measurable audio
    characteristics rather than Spotify's proprietary
    audio-feature calculations.
    """

    audio_path = Path(audio_path)

    if not audio_path.exists():
        raise FileNotFoundError(
            f"Audio file not found: {audio_path}"
        )

    # Load audio.
    #
    # sr=22050 provides a good balance between processing
    # speed and audio analysis quality.
    y, sr = librosa.load(
        audio_path,
        sr=22050,
        mono=True,
    )

    if y.size == 0:
        raise ValueError(
            f"Audio file contains no audio data: {audio_path}"
        )

    # ---------------------------------------------------------
    # 1. TEMPO
    # ---------------------------------------------------------

    tempo, _ = librosa.beat.beat_track(
        y=y,
        sr=sr,
    )

    tempo_value = float(
        np.asarray(tempo).reshape(-1)[0]
    )

    # ---------------------------------------------------------
    # 2. RMS ENERGY
    # ---------------------------------------------------------

    rms = librosa.feature.rms(
        y=y
    )

    average_rms = float(
        np.mean(rms)
    )

    # Convert RMS into a practical 0-1 range.
    energy = float(
        np.clip(
            average_rms * 8.0,
            0.0,
            1.0,
        )
    )

    # ---------------------------------------------------------
    # 3. ZERO CROSSING RATE
    # ---------------------------------------------------------

    zero_crossing_rate = librosa.feature.zero_crossing_rate(
        y
    )

    average_zcr = float(
        np.mean(zero_crossing_rate)
    )

    # ---------------------------------------------------------
    # 4. SPECTRAL FEATURES
    # ---------------------------------------------------------

    spectral_centroid = librosa.feature.spectral_centroid(
        y=y,
        sr=sr,
    )

    average_centroid = float(
        np.mean(spectral_centroid)
    )

    spectral_bandwidth = librosa.feature.spectral_bandwidth(
        y=y,
        sr=sr,
    )

    average_bandwidth = float(
        np.mean(spectral_bandwidth)
    )

    # ---------------------------------------------------------
    # 5. CHROMA
    # ---------------------------------------------------------

    chroma = librosa.feature.chroma_stft(
        y=y,
        sr=sr,
    )

    average_chroma = float(
        np.mean(chroma)
    )

    # ---------------------------------------------------------
    # 6. MFCC
    # ---------------------------------------------------------

    mfcc = librosa.feature.mfcc(
        y=y,
        sr=sr,
        n_mfcc=13,
    )

    mfcc_mean = np.mean(
        mfcc,
        axis=1,
    )

    # ---------------------------------------------------------
    # 7. ACOUSTICNESS PROXY
    # ---------------------------------------------------------
    #
    # Acoustic recordings generally have lower spectral
    # centroid and lower high-frequency activity.
    #
    # This is an audio-derived proxy, NOT Spotify's
    # proprietary acousticness calculation.

    acousticness = 1.0 - normalize_value(
        average_centroid,
        500.0,
        5000.0,
    )

    acousticness = float(
        np.clip(
            acousticness,
            0.0,
            1.0,
        )
    )

    # ---------------------------------------------------------
    # 8. INSTRUMENTALNESS PROXY
    # ---------------------------------------------------------
    #
    # Speech/vocal-heavy material tends to have stronger
    # zero-crossing and spectral variation.
    #
    # This is intentionally treated as an approximate
    # audio-analysis feature.

    vocal_activity = (
        average_zcr * 4.0
    )

    instrumentalness = 1.0 - float(
        np.clip(
            vocal_activity,
            0.0,
            1.0,
        )
    )

    # ---------------------------------------------------------
    # 9. SPEECHINESS PROXY
    # ---------------------------------------------------------

    speechiness = float(
        np.clip(
            (
                average_zcr * 3.0
                + normalize_value(
                    average_centroid,
                    500.0,
                    5000.0,
                )
            )
            / 2.0,
            0.0,
            1.0,
        )
    )

    # ---------------------------------------------------------
    # 10. DANCEABILITY PROXY
    # ---------------------------------------------------------
    #
    # Danceability is estimated using tempo, energy,
    # rhythmic regularity, and spectral characteristics.

    tempo_score = 1.0 - min(
        abs(tempo_value - 120.0) / 120.0,
        1.0,
    )

    danceability = (
        tempo_score * 0.40
        + energy * 0.35
        + (1.0 - min(average_zcr * 3.0, 1.0))
        * 0.25
    )

    danceability = float(
        np.clip(
            danceability,
            0.0,
            1.0,
        )
    )

    # ---------------------------------------------------------
    # 11. VALENCE PROXY
    # ---------------------------------------------------------
    #
    # This is a rough musical-positivity estimate based on
    # energy, spectral brightness, and tempo.
    #
    # It should be treated as a project-specific proxy.

    brightness = normalize_value(
        average_centroid,
        500.0,
        5000.0,
    )

    tempo_positive = normalize_value(
        tempo_value,
        60.0,
        180.0,
    )

    valence = (
        energy * 0.40
        + brightness * 0.30
        + tempo_positive * 0.30
    )

    valence = float(
        np.clip(
            valence,
            0.0,
            1.0,
        )
    )

    # ---------------------------------------------------------
    # 12. FINAL RESULT
    # ---------------------------------------------------------

    return {
        "energy": round(energy, 6),
        "danceability": round(danceability, 6),
        "valence": round(valence, 6),
        "acousticness": round(acousticness, 6),
        "instrumentalness": round(instrumentalness, 6),
        "speechiness": round(speechiness, 6),
        "tempo": round(tempo_value, 4),

        # Additional diagnostic features.
        "spectral_centroid": round(
            average_centroid,
            4,
        ),
        "spectral_bandwidth": round(
            average_bandwidth,
            4,
        ),
        "zero_crossing_rate": round(
            average_zcr,
            6,
        ),
        "average_chroma": round(
            average_chroma,
            6,
        ),
        "mfcc_mean": [
            round(float(value), 4)
            for value in mfcc_mean
        ],
    }