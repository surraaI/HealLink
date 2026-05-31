"""add provider verification fields

Revision ID: 20260601_005_provider_verif
Revises: 29d3ecc2c067
Create Date: 2026-06-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260601_005_provider_verif'
down_revision = '29d3ecc2c067'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # create enum type
    verification_enum = sa.Enum('pending', 'approved', 'rejected', name='verificationstatus')
    verification_enum.create(op.get_bind(), checkfirst=True)

    op.add_column('providers', sa.Column('verification_status', verification_enum, nullable=False, server_default='pending'))
    op.add_column('providers', sa.Column('license_document_url', sa.String(length=500), nullable=True))
    op.add_column('providers', sa.Column('rejection_reason', sa.Text(), nullable=True))
    op.add_column('providers', sa.Column('verified_by', sa.Integer(), nullable=True))
    op.add_column('providers', sa.Column('verified_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('providers', 'verified_at')
    op.drop_column('providers', 'verified_by')
    op.drop_column('providers', 'rejection_reason')
    op.drop_column('providers', 'license_document_url')
    op.drop_column('providers', 'verification_status')
    # drop enum type
    verification_enum = sa.Enum('pending', 'approved', 'rejected', name='verificationstatus')
    verification_enum.drop(op.get_bind(), checkfirst=True)
