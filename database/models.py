from datetime import (
    datetime,
    timezone,
)

from sqlalchemy import (
    DateTime,
    Integer,
    String,
    Text,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from database.connection import Base


class ServiceStateRecord(Base):
    __tablename__ = "service_states"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    service_name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )

    operational_state: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="HEALTHY",
    )

    consecutive_failures: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    consecutive_successes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class IncidentRecord(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    incident_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
    )

    service_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class MonitoringEventRecord(Base):
    __tablename__ = "monitoring_events"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    service_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    previous_state: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    new_state: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
