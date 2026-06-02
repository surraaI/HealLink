"""add_provider_refresh_tokens

Revision ID: 20260602_prefresh
Revises: 20260602_pemail
Create Date: 2026-06-02 12:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260602_prefresh"
down_revision: Union[str, None] = "20260602_pemail"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("refresh_tokens", sa.Column("provider_id", sa.Integer(), nullable=True))
    op.alter_column(
        "refresh_tokens",
        "patient_id",
        existing_type=sa.INTEGER(),
        nullable=True,
    )
    op.create_index(op.f("ix_refresh_tokens_provider_id"), "refresh_tokens", ["provider_id"], unique=False)
    op.create_foreign_key(
        "fk_refresh_tokens_provider_id",
        "refresh_tokens",
        "providers",
        ["provider_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_refresh_tokens_provider_id", "refresh_tokens", type_="foreignkey")
    op.drop_index(op.f("ix_refresh_tokens_provider_id"), table_name="refresh_tokens")
    op.alter_column(
        "refresh_tokens",
        "patient_id",
        existing_type=sa.INTEGER(),
        nullable=False,
    )
    op.drop_column("refresh_tokens", "provider_id")
