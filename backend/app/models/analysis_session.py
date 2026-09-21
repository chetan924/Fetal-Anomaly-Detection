from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.db.database import Base


class AnalysisSession(Base):
    """
    Tracks the complete lifecycle of a multi-model clinical analysis session.
    
    Lifecycle States:
    - draft: Initialized, awaiting uploads or model selection
    - ready: Scan inputs validated and ready for inference
    - processing: Workers actively executing inference
    - completed: All requested models evaluated successfully
    - partial: Some requested models succeeded, others encountered errors
    - failed: All requested models failed or fatal error occurred
    - interrupted: System shutdown or worker crash while in processing state
    - archived: Historical record archived
    """
    __tablename__ = "analysis_sessions"

    # Primary Key
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
    )

    # Unique Logical Session Identifier (e.g. an_a1b2c3d4e5f6)
    session_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )

    # Associated Patient / Reference Identifier
    patient_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        index=True,
        nullable=True,
    )

    # User who created / owns this analysis session
    created_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Idempotency token to prevent duplicate concurrent submissions
    idempotency_key: Mapped[Optional[str]] = mapped_column(
        String(128),
        unique=True,
        index=True,
        nullable=True,
    )

    # Current lifecycle state
    status: Mapped[str] = mapped_column(
        String(30),
        default="draft",
        nullable=False,
        index=True,
    )

    # List of requested model names (e.g. ["plane", "spine", "brain", "lung", "bone", "placenta", "face", "heart"])
    requested_models: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True,
    )

    # List of successfully completed model names
    completed_models: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True,
    )

    # List of failed model names
    failed_models: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True,
    )

    # High-level summary metrics snapshot
    summary_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )

    # Complete multi-model analysis findings payload
    result_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )

    # Top-level error message if session failed or was interrupted
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user = relationship("User", foreign_keys=[created_by])
