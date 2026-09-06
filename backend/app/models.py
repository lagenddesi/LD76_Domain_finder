from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DomainResult(Base):
    __tablename__ = "domain_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    domain: Mapped[str] = mapped_column(
        String(253),
        unique=True,
        index=True,
        nullable=False,
    )

    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    last_scan: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        default="unknown",
        nullable=False,
    )

    python_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    gemini_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    gemini_analyzed: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
    )

    content_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )

    title: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )

    classification: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    evidence_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    signals_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )


class ScanHistory(Base):
    __tablename__ = "scan_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        default="started",
        nullable=False,
    )

    domains_discovered: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    domains_scanned: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    candidates_found: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
