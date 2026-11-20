"""Stored photos: report photos kept in PostgreSQL (STORAGE_BACKEND=database),
for free cloud hosting where the server disk is wiped on restart.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-19 15:37:26.370791+00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0004'
down_revision: str | None = '0003'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('stored_photos',
    sa.Column('key', sa.String(length=255), nullable=False),
    sa.Column('data', sa.LargeBinary(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('key', name=op.f('pk_stored_photos'))
    )


def downgrade() -> None:
    op.drop_table('stored_photos')
