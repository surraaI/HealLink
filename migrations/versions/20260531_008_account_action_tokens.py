"""account_action_tokens

Revision ID: d9f7c1a8b3e4
Revises: 55a70221b26e
Create Date: 2026-05-31 23:59:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd9f7c1a8b3e4'
down_revision: Union[str, None] = '55a70221b26e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


account_action_purpose = sa.Enum(
    'email_verification',
    'password_reset',
    'email_change',
    name='accountactionpurpose',
)


def upgrade() -> None:
    account_action_purpose.create(op.get_bind(), checkfirst=True)
    op.create_table(
        'account_action_tokens',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('purpose', account_action_purpose, nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('new_email', sa.String(length=255), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id']),
        sa.UniqueConstraint('token_hash'),
    )
    op.create_index(op.f('ix_account_action_tokens_patient_id'), 'account_action_tokens', ['patient_id'], unique=False)
    op.create_index(op.f('ix_account_action_tokens_purpose'), 'account_action_tokens', ['purpose'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_account_action_tokens_purpose'), table_name='account_action_tokens')
    op.drop_index(op.f('ix_account_action_tokens_patient_id'), table_name='account_action_tokens')
    op.drop_table('account_action_tokens')
    account_action_purpose.drop(op.get_bind(), checkfirst=True)
