from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
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
# OTP MODEL
# =========================================================

class OTP(Base):

    __tablename__ = "otps"

    # =====================================================
    # PRIMARY KEY
    # =====================================================

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    # =====================================================
    # USER
    # =====================================================

    user_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )

    # =====================================================
    # EMAIL
    # =====================================================

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    # =====================================================
    # OTP HASH
    # =====================================================

    otp_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # =====================================================
    # PURPOSE
    # =====================================================

    purpose: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    # Possible values:
    #
    # signup
    # login
    # forgot_password

    # =====================================================
    # EXPIRATION
    # =====================================================

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    # =====================================================
    # VERIFICATION
    # =====================================================

    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # =====================================================
    # ATTEMPTS
    # =====================================================

    attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # =====================================================
    # CREATED AT
    # =====================================================

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # =====================================================
    # RELATIONSHIP
    # =====================================================

    user = relationship(
        "User",
        back_populates="otps",
    )