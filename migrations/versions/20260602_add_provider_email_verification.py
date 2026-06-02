"""add_provider_email_verification

Revision ID: 20260602_add_provider_email_verification
Revises: 54ef7c32c10f
Create Date: 2026-06-02 11:35:00.000000
"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = '20260602_add_provider_email_verification'
down_revision: Union[str, None] = '54ef7c32c10f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Kept as a no-op compatibility revision. The same provider email
    # verification schema changes are applied by 54ef7c32c10f.
    pass


def downgrade() -> None:
    pass
