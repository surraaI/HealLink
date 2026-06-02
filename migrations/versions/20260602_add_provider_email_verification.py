"""add_provider_email_verification

Revision ID: 20260602_add_provider_email_verification
Revises: 938504b901a6
Create Date: 2026-06-02 11:35:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260602_add_provider_email_verification'
down_revision: Union[str, None] = '938504b901a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add provider_id to account_action_tokens
    op.add_column('account_action_tokens', sa.Column('provider_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_account_action_tokens_provider_id', 'account_action_tokens', 'providers', ['provider_id'], ['id'])
    op.create_index('ix_account_action_tokens_provider_id', 'account_action_tokens', ['provider_id'])
    
    # Make patient_id nullable
    op.alter_column('account_action_tokens', 'patient_id', nullable=True)
    
    # Add is_verified to providers
    op.add_column('providers', sa.Column('is_verified', sa.Boolean(), server_default='false', nullable=False))


def downgrade() -> None:
    # Remove is_verified from providers
    op.drop_column('providers', 'is_verified')
    
    # Make patient_id not nullable
    op.alter_column('account_action_tokens', 'patient_id', nullable=False)
    
    # Remove provider_id from account_action_tokens
    op.drop_index('ix_account_action_tokens_provider_id', table_name='account_action_tokens')
    op.drop_constraint('fk_account_action_tokens_provider_id', 'account_action_tokens', type_='foreignkey')
    op.drop_column('account_action_tokens', 'provider_id')
