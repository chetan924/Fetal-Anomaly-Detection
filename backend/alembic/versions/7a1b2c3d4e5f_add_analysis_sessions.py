"""add analysis sessions table

Revision ID: 7a1b2c3d4e5f
Revises: 5fc8f8eba256
Create Date: 2026-09-05 03:02:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7a1b2c3d4e5f'
down_revision: Union[str, None] = '5fc8f8eba256'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'analysis_sessions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.String(length=64), nullable=False),
        sa.Column('patient_id', sa.String(length=50), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('idempotency_key', sa.String(length=128), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='draft'),
        sa.Column('requested_models', sa.JSON(), nullable=True),
        sa.Column('completed_models', sa.JSON(), nullable=True),
        sa.Column('failed_models', sa.JSON(), nullable=True),
        sa.Column('summary_json', sa.JSON(), nullable=True),
        sa.Column('result_json', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_analysis_sessions_id'), 'analysis_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_analysis_sessions_session_id'), 'analysis_sessions', ['session_id'], unique=True)
    op.create_index(op.f('ix_analysis_sessions_patient_id'), 'analysis_sessions', ['patient_id'], unique=False)
    op.create_index(op.f('ix_analysis_sessions_created_by'), 'analysis_sessions', ['created_by'], unique=False)
    op.create_index(op.f('ix_analysis_sessions_idempotency_key'), 'analysis_sessions', ['idempotency_key'], unique=True)
    op.create_index(op.f('ix_analysis_sessions_status'), 'analysis_sessions', ['status'], unique=False)
    op.create_index(op.f('ix_analysis_sessions_created_at'), 'analysis_sessions', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_analysis_sessions_created_at'), table_name='analysis_sessions')
    op.drop_index(op.f('ix_analysis_sessions_status'), table_name='analysis_sessions')
    op.drop_index(op.f('ix_analysis_sessions_idempotency_key'), table_name='analysis_sessions')
    op.drop_index(op.f('ix_analysis_sessions_created_by'), table_name='analysis_sessions')
    op.drop_index(op.f('ix_analysis_sessions_patient_id'), table_name='analysis_sessions')
    op.drop_index(op.f('ix_analysis_sessions_session_id'), table_name='analysis_sessions')
    op.drop_index(op.f('ix_analysis_sessions_id'), table_name='analysis_sessions')
    op.drop_table('analysis_sessions')
