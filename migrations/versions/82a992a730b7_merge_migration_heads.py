"""merge migration heads

Revision ID: 82a992a730b7
Revises: 20260531_006_registration_fields, 20260531_007
Create Date: 2026-05-31 21:43:19.631853
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '82a992a730b7'
down_revision: Union[str, None] = ('20260531_006_registration_fields', '20260531_007')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
