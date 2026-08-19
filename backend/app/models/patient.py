from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Patient(Base):
    __tablename__ = "patients"

    # =====================================================
    # PRIMARY KEY
    # =====================================================

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    # =====================================================
    # PATIENT IDENTIFIER
    # =====================================================

    patient_id: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )

    # =====================================================
    # PATIENT INFORMATION
    # =====================================================

    full_name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    age: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    gestational_age: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    phone: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    # =====================================================
    # OWNER / CREATOR
    # =====================================================

    created_by: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    # =====================================================
    # TIMESTAMP
    # =====================================================

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # =====================================================
    # RELATIONSHIPS
    # =====================================================

    created_by_user = relationship(
        "User",
        back_populates="patients",
    )

    scans = relationship(
        "Scan",
        back_populates="patient",
        cascade="all, delete-orphan",
    )