"""add_officer_to_notificationchannel_enum

Revision ID: 830026e3dc7e
Revises: 965910d2d883
Create Date: 2026-06-03 06:59:08.301705
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '830026e3dc7e'
down_revision: Union[str, None] = '965910d2d883'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add OFFICER to the notificationchannel enum
    op.execute("ALTER TYPE notificationchannel ADD VALUE 'OFFICER'")


def downgrade() -> None:
    # PostgreSQL doesn't support removing enum values directly
    # To downgrade, you would need to recreate the enum without OFFICER
    # This is a destructive operation, so we'll skip it for now
    pass
