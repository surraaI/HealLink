"""Notifications, recheck statuses, and appointment follow-up links

Revision ID: 20260510_004
Revises: 20260510_003
Create Date: 2026-05-10 18:10:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260510_004"
down_revision: Union[str, None] = "20260510_003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM pg_catalog.pg_enum e
            JOIN pg_catalog.pg_type t ON e.enumtypid = t.oid
            WHERE t.typname = 'appointmentstatus'
              AND e.enumlabel = 'NEEDS_RECHECK'
          ) THEN
            ALTER TYPE appointmentstatus ADD VALUE 'NEEDS_RECHECK';
          END IF;
          IF NOT EXISTS (
            SELECT 1 FROM pg_catalog.pg_enum e
            JOIN pg_catalog.pg_type t ON e.enumtypid = t.oid
            WHERE t.typname = 'appointmentstatus'
              AND e.enumlabel = 'FOLLOW_UP_BOOKED'
          ) THEN
            ALTER TYPE appointmentstatus ADD VALUE 'FOLLOW_UP_BOOKED';
          END IF;
        END $$;
        """
    )

    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE notificationchannel AS ENUM ('IN_APP', 'EMAIL'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )

    notification_channel = postgresql.ENUM(
        "IN_APP",
        "EMAIL",
        name="notificationchannel",
        create_type=False,
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("channel", notification_channel, nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("appointment_id", sa.Integer(), nullable=True),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column("email_attempted_at", sa.DateTime(), nullable=True),
        sa.Column(
            "email_failed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notifications_id"), "notifications", ["id"], unique=False)
    op.create_index(op.f("ix_notifications_patient_id"), "notifications", ["patient_id"], unique=False)
    op.create_index(
        op.f("ix_notifications_appointment_id"),
        "notifications",
        ["appointment_id"],
        unique=False,
    )

    op.add_column("appointments", sa.Column("follow_up_of_id", sa.Integer(), nullable=True))
    op.add_column(
        "appointments", sa.Column("continuation_appointment_id", sa.Integer(), nullable=True)
    )
    op.add_column(
        "appointments", sa.Column("provider_recheck_reason", sa.Text(), nullable=True)
    )
    op.create_index(
        op.f("ix_appointments_follow_up_of_id"), "appointments", ["follow_up_of_id"], unique=False
    )
    op.create_index(
        op.f("ix_appointments_continuation_appointment_id"),
        "appointments",
        ["continuation_appointment_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_appointments_follow_up_of_id",
        "appointments",
        "appointments",
        ["follow_up_of_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_appointments_continuation_appointment_id",
        "appointments",
        "appointments",
        ["continuation_appointment_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_appointments_continuation_appointment_id", "appointments", type_="foreignkey")
    op.drop_constraint("fk_appointments_follow_up_of_id", "appointments", type_="foreignkey")
    op.drop_index(op.f("ix_appointments_continuation_appointment_id"), table_name="appointments")
    op.drop_index(op.f("ix_appointments_follow_up_of_id"), table_name="appointments")
    op.drop_column("appointments", "provider_recheck_reason")
    op.drop_column("appointments", "continuation_appointment_id")
    op.drop_column("appointments", "follow_up_of_id")

    op.drop_index(op.f("ix_notifications_appointment_id"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_patient_id"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_id"), table_name="notifications")
    op.drop_table("notifications")

    op.execute("DROP TYPE IF EXISTS notificationchannel")
    # Enum values NEEDS_RECHECK / FOLLOW_UP_BOOKED are not removed from appointmentstatus (Postgres limitation).
