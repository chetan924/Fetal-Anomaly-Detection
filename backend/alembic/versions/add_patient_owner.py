"""
add patient ownership

Revision ID: e7a4c91b2f10
Revises: c99fe740fe19
Create Date: 2026-08-19
"""

import os
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# =========================================================
# REVISION IDENTIFIERS
# =========================================================

revision: str = "e7a4c91b2f10"

down_revision: Union[
    str,
    Sequence[str],
    None,
] = "c99fe740fe19"

branch_labels = None

depends_on = None


# =========================================================
# UPGRADE
# =========================================================

def upgrade() -> None:
    """
    Add ownership information to patients.

    Existing patients are handled safely by first creating
    the column as nullable, assigning an existing user as
    owner, and then making the column NOT NULL.
    """

    # -----------------------------------------------------
    # ADD created_by COLUMN
    # -----------------------------------------------------

    op.add_column(
        "patients",
        sa.Column(
            "created_by",
            sa.Integer(),
            nullable=True,
        ),
    )


    # -----------------------------------------------------
    # FOREIGN KEY
    # -----------------------------------------------------

    op.create_foreign_key(
        "fk_patients_created_by_users",
        "patients",
        "users",
        ["created_by"],
        ["id"],
        ondelete="RESTRICT",
    )


    # -----------------------------------------------------
    # INDEX
    # -----------------------------------------------------

    op.create_index(
        "ix_patients_created_by",
        "patients",
        ["created_by"],
        unique=False,
    )


    # -----------------------------------------------------
    # EXISTING DATA OWNER
    # -----------------------------------------------------

    owner_id = os.getenv(
        "DEFAULT_PATIENT_OWNER_USER_ID"
    )


    if not owner_id:

        raise RuntimeError(
            "DEFAULT_PATIENT_OWNER_USER_ID is required. "
            "Set it to an existing users.id before "
            "running alembic upgrade head."
        )


    try:

        owner_id_int = int(
            owner_id
        )

    except ValueError as exc:

        raise RuntimeError(
            "DEFAULT_PATIENT_OWNER_USER_ID must be "
            "a valid integer."
        ) from exc


    if owner_id_int <= 0:

        raise RuntimeError(
            "DEFAULT_PATIENT_OWNER_USER_ID must be "
            "greater than 0."
        )


    # -----------------------------------------------------
    # VERIFY USER
    # -----------------------------------------------------

    connection = op.get_bind()


    user_exists = connection.execute(
        sa.text(
            """
            SELECT id
            FROM users
            WHERE id = :owner_id
            LIMIT 1
            """
        ),
        {
            "owner_id": owner_id_int,
        },
    ).scalar_one_or_none()


    if user_exists is None:

        raise RuntimeError(
            "The user specified by "
            "DEFAULT_PATIENT_OWNER_USER_ID "
            "does not exist."
        )


    # -----------------------------------------------------
    # ASSIGN EXISTING PATIENTS
    # -----------------------------------------------------

    connection.execute(
        sa.text(
            """
            UPDATE patients
            SET created_by = :owner_id
            WHERE created_by IS NULL
            """
        ),
        {
            "owner_id": owner_id_int,
        },
    )


    # -----------------------------------------------------
    # MAKE created_by REQUIRED
    # -----------------------------------------------------

    op.alter_column(
        "patients",
        "created_by",
        existing_type=sa.Integer(),
        nullable=False,
    )


# =========================================================
# DOWNGRADE
# =========================================================

def downgrade() -> None:
    """
    Remove patient ownership.
    """

    op.drop_index(
        "ix_patients_created_by",
        table_name="patients",
    )


    op.drop_constraint(
        "fk_patients_created_by_users",
        "patients",
        type_="foreignkey",
    )


    op.drop_column(
        "patients",
        "created_by",
    )