from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
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
# USER MODEL
# =========================================================

class User(Base):

    __tablename__ = "users"


    # =====================================================
    # PRIMARY KEY
    # =====================================================

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )


    # =====================================================
    # BASIC INFORMATION
    # =====================================================

    full_name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )


    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )


    # =====================================================
    # AUTHENTICATION
    # =====================================================

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )


    # =====================================================
    # ROLE
    # =====================================================

    role: Mapped[str] = mapped_column(
        String(50),
        default="doctor",
        nullable=False,
    )


    # =====================================================
    # ACCOUNT STATUS
    # =====================================================

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )


    # =====================================================
    # PASSWORD RESET
    # =====================================================

    reset_token_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )


    reset_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


    # =====================================================
    # TIMESTAMPS
    # =====================================================

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


    # =====================================================
    # RELATIONSHIPS
    # =====================================================
    #
    # User
    #   ├── Patients created by this user
    #   └── Scans uploaded by this user
    #
    # These relationships require:
    #
    # Patient.created_by
    # Scan.uploaded_by
    #
    # =====================================================

    patients = relationship(
        "Patient",
        back_populates="created_by_user",
    )


    scans = relationship(
        "Scan",
        back_populates="user",
    )