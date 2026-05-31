"""add registration fields for patients and providers

Revision ID: 20260531_006_registration_fields
Revises: 20260601_005_provider_verif
Create Date: 2026-05-31 21:30:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260531_006_registration_fields"
down_revision = "20260601_005_provider_verif"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("patients", sa.Column("phone_number", sa.String(length=30), nullable=True))
    op.add_column("patients", sa.Column("date_of_birth", sa.Date(), nullable=True))
    op.add_column("patients", sa.Column("gender", sa.String(length=30), nullable=True))
    op.add_column(
        "patients",
        sa.Column("role", sa.String(length=50), nullable=False, server_default="patient"),
    )
    op.add_column(
        "patients",
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "patients",
        sa.Column("verification_status", sa.String(length=20), nullable=False, server_default="pending"),
    )
    op.add_column("patients", sa.Column("updated_at", sa.DateTime(), nullable=True))

    op.add_column("providers", sa.Column("specialization", sa.String(length=255), nullable=True))
    op.add_column("providers", sa.Column("license_number", sa.String(length=100), nullable=True))
    op.add_column("providers", sa.Column("tin_number", sa.String(length=100), nullable=True))
    op.add_column("providers", sa.Column("address", sa.String(length=255), nullable=True))
    op.create_index("ix_providers_license_number", "providers", ["license_number"], unique=False)
    op.create_index("ix_providers_tin_number", "providers", ["tin_number"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_providers_tin_number", table_name="providers")
    op.drop_index("ix_providers_license_number", table_name="providers")
    op.drop_column("providers", "address")
    op.drop_column("providers", "tin_number")
    op.drop_column("providers", "license_number")
    op.drop_column("providers", "specialization")

    op.drop_column("patients", "updated_at")
    op.drop_column("patients", "verification_status")
    op.drop_column("patients", "is_verified")
    op.drop_column("patients", "role")
    op.drop_column("patients", "gender")
    op.drop_column("patients", "date_of_birth")
    op.drop_column("patients", "phone_number")