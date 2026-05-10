"""Add appointments and service catalog tables

Revision ID: 20260510_002
Revises: 20260510_001
Create Date: 2026-05-10 17:45:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260510_002"
down_revision: Union[str, None] = "20260510_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE appointmentstatus AS ENUM ('BOOKED', 'CANCELLED', 'COMPLETED'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )
    appointment_status = postgresql.ENUM(
        "BOOKED",
        "CANCELLED",
        "COMPLETED",
        name="appointmentstatus",
        create_type=False,
    )

    op.create_table(
        "service_catalog",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("service_type", sa.String(length=50), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_service_catalog_id"), "service_catalog", ["id"], unique=False)
    op.create_index(
        op.f("ix_service_catalog_service_type"), "service_catalog", ["service_type"], unique=False
    )
    op.create_index(op.f("ix_service_catalog_location"), "service_catalog", ["location"], unique=False)

    op.create_table(
        "appointments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("service_id", sa.Integer(), nullable=False),
        sa.Column("appointment_at", sa.DateTime(), nullable=False),
        sa.Column("status", appointment_status, nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["service_id"], ["service_catalog.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_appointments_id"), "appointments", ["id"], unique=False)
    op.create_index(op.f("ix_appointments_patient_id"), "appointments", ["patient_id"], unique=False)
    op.create_index(op.f("ix_appointments_service_id"), "appointments", ["service_id"], unique=False)
    op.create_index(
        op.f("ix_appointments_appointment_at"), "appointments", ["appointment_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_appointments_appointment_at"), table_name="appointments")
    op.drop_index(op.f("ix_appointments_service_id"), table_name="appointments")
    op.drop_index(op.f("ix_appointments_patient_id"), table_name="appointments")
    op.drop_index(op.f("ix_appointments_id"), table_name="appointments")
    op.drop_table("appointments")

    op.drop_index(op.f("ix_service_catalog_location"), table_name="service_catalog")
    op.drop_index(op.f("ix_service_catalog_service_type"), table_name="service_catalog")
    op.drop_index(op.f("ix_service_catalog_id"), table_name="service_catalog")
    op.drop_table("service_catalog")

    op.execute("DROP TYPE IF EXISTS appointmentstatus")
