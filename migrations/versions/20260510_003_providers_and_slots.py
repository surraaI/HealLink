"""Add providers, service slots, and provider ownership

Revision ID: 20260510_003
Revises: 20260510_002
Create Date: 2026-05-10 17:55:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260510_003"
down_revision: Union[str, None] = "20260510_002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE providertype AS ENUM ('DOCTOR', 'CLINIC', 'DIAGNOSTIC_CENTER'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )
    provider_type = postgresql.ENUM(
        "DOCTOR",
        "CLINIC",
        "DIAGNOSTIC_CENTER",
        name="providertype",
        create_type=False,
    )

    op.create_table(
        "providers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("provider_type", provider_type, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_providers_id"), "providers", ["id"], unique=False)
    op.create_index(op.f("ix_providers_email"), "providers", ["email"], unique=True)
    op.create_index(op.f("ix_providers_location"), "providers", ["location"], unique=False)
    op.create_index(op.f("ix_providers_provider_type"), "providers", ["provider_type"], unique=False)

    op.add_column("service_catalog", sa.Column("provider_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_service_catalog_provider_id"), "service_catalog", ["provider_id"], unique=False)
    op.create_foreign_key(
        "fk_service_catalog_provider_id_providers",
        "service_catalog",
        "providers",
        ["provider_id"],
        ["id"],
    )

    op.create_table(
        "service_slots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("service_id", sa.Integer(), nullable=False),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=False),
        sa.Column("is_booked", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["service_id"], ["service_catalog.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_service_slots_id"), "service_slots", ["id"], unique=False)
    op.create_index(op.f("ix_service_slots_service_id"), "service_slots", ["service_id"], unique=False)
    op.create_index(op.f("ix_service_slots_starts_at"), "service_slots", ["starts_at"], unique=False)
    op.create_index(op.f("ix_service_slots_is_booked"), "service_slots", ["is_booked"], unique=False)

    op.add_column("appointments", sa.Column("slot_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_appointments_slot_id"), "appointments", ["slot_id"], unique=False)
    op.create_foreign_key(
        "fk_appointments_slot_id_service_slots",
        "appointments",
        "service_slots",
        ["slot_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_appointments_slot_id_service_slots", "appointments", type_="foreignkey")
    op.drop_index(op.f("ix_appointments_slot_id"), table_name="appointments")
    op.drop_column("appointments", "slot_id")

    op.drop_index(op.f("ix_service_slots_is_booked"), table_name="service_slots")
    op.drop_index(op.f("ix_service_slots_starts_at"), table_name="service_slots")
    op.drop_index(op.f("ix_service_slots_service_id"), table_name="service_slots")
    op.drop_index(op.f("ix_service_slots_id"), table_name="service_slots")
    op.drop_table("service_slots")

    op.drop_constraint("fk_service_catalog_provider_id_providers", "service_catalog", type_="foreignkey")
    op.drop_index(op.f("ix_service_catalog_provider_id"), table_name="service_catalog")
    op.drop_column("service_catalog", "provider_id")

    op.drop_index(op.f("ix_providers_provider_type"), table_name="providers")
    op.drop_index(op.f("ix_providers_location"), table_name="providers")
    op.drop_index(op.f("ix_providers_email"), table_name="providers")
    op.drop_index(op.f("ix_providers_id"), table_name="providers")
    op.drop_table("providers")

    op.execute("DROP TYPE IF EXISTS providertype")
