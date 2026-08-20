import uuid

from sqlalchemy import Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TrackFeatures(Base):
    __tablename__ = "track_features"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    track_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tracks.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    energy: Mapped[float | None] = mapped_column(Float)
    danceability: Mapped[float | None] = mapped_column(Float)
    valence: Mapped[float | None] = mapped_column(Float)
    acousticness: Mapped[float | None] = mapped_column(Float)
    instrumentalness: Mapped[float | None] = mapped_column(Float)
    speechiness: Mapped[float | None] = mapped_column(Float)
    tempo: Mapped[float | None] = mapped_column(Float)