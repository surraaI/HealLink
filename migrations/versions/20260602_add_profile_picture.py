"""add_profile_picture

Revision ID: 20260602_profile_pic
Revises: 20260602_prefresh
Create Date: 2026-06-02 21:22:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260602_profile_pic'
down_revision: Union[str, None] = '20260602_prefresh'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add profile_picture column to patients table
    op.add_column('patients', sa.Column('profile_picture', sa.String(length=500), nullable=True))
    
    # Add profile_picture column to providers table
    op.add_column('providers', sa.Column('profile_picture', sa.String(length=500), nullable=True))


def downgrade() -> None:
    # Remove profile_picture column from patients table
    op.drop_column('patients', 'profile_picture')
    
    # Remove profile_picture column from providers table
    op.drop_column('providers', 'profile_picture')
