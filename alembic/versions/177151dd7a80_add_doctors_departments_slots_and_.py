
"""add doctors departments slots and patient summaries

Revision ID: 177151dd7a80
Revises:
Create Date: 2026-11-18 16:16:15.007752
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Revision identifiers
revision: str = "177151dd7a80"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create new healthcare tables and update existing tables."""

    # 1. Create departments
    op.create_table(
        "departments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_departments_name",
        "departments",
        ["name"],
        unique=True,
    )

    # 2. Create doctors
    op.create_table(
        "doctors",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("department_id", sa.String(length=36), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("specialization", sa.String(length=150), nullable=True),
        sa.Column("qualification", sa.String(length=200), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["departments.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_doctors_department_id",
        "doctors",
        ["department_id"],
    )

    # 3. Create appointment slots
    op.create_table(
        "appointment_slots",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("doctor_id", sa.String(length=36), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["doctor_id"],
            ["doctors.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "doctor_id",
            "starts_at",
            name="uq_doctor_appointment_start",
        ),
    )

    op.create_index(
        "ix_appointment_slots_doctor_id",
        "appointment_slots",
        ["doctor_id"],
    )

    # 4. Create patient summaries
    op.create_table(
        "patient_summaries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("patient_id", sa.String(length=36), nullable=False),
        sa.Column("conversation_id", sa.String(length=36), nullable=True),
        sa.Column("appointment_id", sa.String(length=36), nullable=True),
        sa.Column("chief_complaint", sa.Text(), nullable=True),
        sa.Column("symptoms", sa.Text(), nullable=True),
        sa.Column(
            "recommended_department",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["appointment_id"],
            ["appointments.id"],
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("appointment_id"),
        sa.UniqueConstraint("conversation_id"),
    )

    op.create_index(
        "ix_patient_summaries_patient_id",
        "patient_summaries",
        ["patient_id"],
    )

    # 5. Add slot relationship to existing appointments table
    with op.batch_alter_table("appointments") as batch_op:
        batch_op.add_column(
            sa.Column("slot_id", sa.String(length=36), nullable=True)
        )

        batch_op.create_unique_constraint(
            "uq_appointments_slot_id",
            ["slot_id"],
        )

        batch_op.create_foreign_key(
            "fk_appointments_slot_id_appointment_slots",
            "appointment_slots",
            ["slot_id"],
            ["id"],
        )

    # 6. Correct patient date-of-birth column type
    with op.batch_alter_table("patients") as batch_op:
        batch_op.alter_column(
            "date_of_birth",
            existing_type=sa.DATETIME(),
            type_=sa.Date(),
            existing_nullable=True,
        )


def downgrade() -> None:
    """Reverse the healthcare database schema changes."""

    # Reverse patient date-of-birth type change
    with op.batch_alter_table("patients") as batch_op:
        batch_op.alter_column(
            "date_of_birth",
            existing_type=sa.Date(),
            type_=sa.DATETIME(),
            existing_nullable=True,
        )

    # Remove slot relationship from appointments
    with op.batch_alter_table("appointments") as batch_op:
        batch_op.drop_constraint(
            "fk_appointments_slot_id_appointment_slots",
            type_="foreignkey",
        )

        batch_op.drop_constraint(
            "uq_appointments_slot_id",
            type_="unique",
        )

        batch_op.drop_column("slot_id")

    # Remove patient summaries
    op.drop_index(
        "ix_patient_summaries_patient_id",
        table_name="patient_summaries",
    )
    op.drop_table("patient_summaries")

    # Remove appointment slots
    op.drop_index(
        "ix_appointment_slots_doctor_id",
        table_name="appointment_slots",
    )
    op.drop_table("appointment_slots")

    # Remove doctors
    op.drop_index(
        "ix_doctors_department_id",
        table_name="doctors",
    )
    op.drop_table("doctors")

    # Remove departments
    op.drop_index(
        "ix_departments_name",
        table_name="departments",
    )
    op.drop_table("departments")
