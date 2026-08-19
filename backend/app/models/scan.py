from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
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
# SCAN MODEL
# =========================================================

class Scan(Base):

    __tablename__ = "scans"

    # =====================================================
    # PRIMARY KEY
    # =====================================================

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    # =====================================================
    # PATIENT
    # =====================================================

    patient_id: Mapped[int] = mapped_column(
        ForeignKey(
            "patients.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # =====================================================
    # UPLOADED BY USER
    # =====================================================

    uploaded_by: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
        ),
        nullable=False,
        index=True,
    )

    # =====================================================
    # IMAGE
    # =====================================================

    image_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # =====================================================
    # AI PREDICTION
    # =====================================================

    predicted_plane: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    # =====================================================
    # COMPLETE AI ANALYSIS
    # =====================================================

    analysis_result: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    # =====================================================
    # TIMESTAMP
    # =====================================================

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # =====================================================
    # RELATIONSHIPS
    # =====================================================

    patient = relationship(
        "Patient",
        back_populates="scans",
    )

    user = relationship(
        "User",
        back_populates="scans",
    )