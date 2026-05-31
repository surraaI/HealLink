"""Remove full_name from patients and add first_name/last_name

Revision ID: 20260531_007
Revises: 20260510_001
Create Date: 2026-05-31 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260531_007"
down_revision: Union[str, None] = "20260510_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # add new nullable columns
    op.add_column("patients", sa.Column("first_name", sa.String(length=128), nullable=True))
    op.add_column("patients", sa.Column("last_name", sa.String(length=128), nullable=True))

    # migrate existing full_name into first_name/last_name where possible
    # first_name := first token
    # last_name := rest of the string after first token (empty -> NULL)
    op.execute(
        """
        UPDATE patients
        SET first_name = split_part(full_name, ' ', 1),
            last_name = NULLIF(regexp_replace(full_name, '^[^ ]+\s*', ''), '')
        WHERE full_name IS NOT NULL
        """
    )

    # drop the old column
    op.drop_column("patients", "full_name")


def downgrade() -> None:
    # add full_name back
    op.add_column("patients", sa.Column("full_name", sa.String(length=255), nullable=True))

    # repopulate full_name
    op.execute(
        """
        UPDATE patients
        SET full_name = concat_ws(' ', first_name, last_name)
        WHERE first_name IS NOT NULL OR last_name IS NOT NULL
        """
    )

    # drop the split columns
    op.drop_column("patients", "last_name")
    op.drop_column("patients", "first_name")
