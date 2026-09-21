from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.db.database import Base


# =========================================================
# REPORT MODEL
# =========================================================

class Report(Base):
    """
    Persisted immutable clinical analysis report snapshot.
    """
    __tablename__ = "reports"

    # Primary Key
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
    )

    # Sequential Human-Friendly Report Number (e.g. FETAL-RPT-000001)
    report_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )

    # Logical Analysis Identifier
    analysis_id: Mapped[str] = mapped_column(
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

    # User who triggered analysis (nullable for anonymous / prototype runs)
    created_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Overall Status: completed | partial | failed | archived
    status: Mapped[str] = mapped_column(
        String(30),
        default="completed",
        nullable=False,
        index=True,
    )

    # Complete Analysis Result Snapshot (Findings 01-16)
    result_json: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )

    # Summary Metrics Snapshot
    summary_json: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )

    # Warnings & Errors List
    warnings_json: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True,
    )

    errors_json: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON,
        nullable=True,
    )

    # Archive flag
    is_archived: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    user = relationship("User", foreign_keys=[created_by])
