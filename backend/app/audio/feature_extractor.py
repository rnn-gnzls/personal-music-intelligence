import librosa


def extract_audio_features(
    audio_path: str,
) -> dict:
    """
    Extract audio features from a local audio file.

    These are locally computed audio-analysis features.
    They are Spotify-style features/proxies, not Spotify's
    original proprietary feature values.
    """

    y, sr = librosa.load(
        audio_path,
        sr=22050,
        mono=True,
    )

    if len(y) == 0:
        raise ValueError(
            "Audio file contains no readable audio."
        )

    # ---------------------------------------------------------
    # TEMPO
    # ---------------------------------------------------------

    tempo, _ = librosa.beat.beat_track(
        y=y,
        sr=sr,
    )

    # librosa 1.x may return tempo as a 1-element ndarray.
    tempo = float(tempo[0]) if hasattr(
        tempo,
        "__len__",
    ) else float(tempo)

    # ---------------------------------------------------------
    # RMS ENERGY
    # ---------------------------------------------------------

    rms = librosa.feature.rms(
        y=y,
    )[0]

    rms_mean = float(
        rms.mean()
    )

    energy = min(
        max(
            rms_mean * 5.0,
            0.0,
        ),
        1.0,
    )

    # ---------------------------------------------------------
    # DANCEABILITY PROXY
    # ---------------------------------------------------------

    onset_strength = librosa.onset.onset_strength(
        y=y,
        sr=sr,
    )

    onset_mean = float(
        onset_strength.mean()
    )

    danceability = min(
        max(
            (
                onset_mean / 10.0
            ) * 0.7
            + energy * 0.3,
            0.0,
        ),
        1.0,
    )

    # ---------------------------------------------------------
    # VALENCE PROXY
    # ---------------------------------------------------------

    spectral_centroid = (
        librosa.feature.spectral_centroid(
            y=y,
            sr=sr,
        )[0]
    )

    centroid_mean = float(
        spectral_centroid.mean()
    )

    centroid_normalized = min(
        max(
            centroid_mean / 5000.0,
            0.0,
        ),
        1.0,
    )

    valence = min(
        max(
            centroid_normalized * 0.5
            + energy * 0.3
            + danceability * 0.2,
            0.0,
        ),
        1.0,
    )

    # ---------------------------------------------------------
    # ACOUSTICNESS PROXY
    # ---------------------------------------------------------

    spectral_bandwidth = (
        librosa.feature.spectral_bandwidth(
            y=y,
            sr=sr,
        )[0]
    )

    bandwidth_mean = float(
        spectral_bandwidth.mean()
    )

    acousticness = min(
        max(
            1.0 - (
                bandwidth_mean / 5000.0
            ),
            0.0,
        ),
        1.0,
    )

    # ---------------------------------------------------------
    # ZERO CROSSING RATE
    # ---------------------------------------------------------

    zcr = librosa.feature.zero_crossing_rate(
        y,
    )[0]

    zcr_mean = float(
        zcr.mean()
    )

    # ---------------------------------------------------------
    # INSTRUMENTALNESS PROXY
    # ---------------------------------------------------------

    instrumentalness = min(
        max(
            1.0 - (
                zcr_mean * 5.0
            ),
            0.0,
        ),
        1.0,
    )

    # ---------------------------------------------------------
    # SPEECHINESS PROXY
    # ---------------------------------------------------------

    speechiness = min(
        max(
            zcr_mean * 5.0,
            0.0,
        ),
        1.0,
    )

    # ---------------------------------------------------------
    # RESULT
    # ---------------------------------------------------------

    return {
        "energy": round(
            energy,
            4,
        ),
        "danceability": round(
            danceability,
            4,
        ),
        "valence": round(
            valence,
            4,
        ),
        "acousticness": round(
            acousticness,
            4,
        ),
        "instrumentalness": round(
            instrumentalness,
            4,
        ),
        "speechiness": round(
            speechiness,
            4,
        ),
        "tempo": round(
            tempo,
            2,
        ),
    }