
from datetime import date, datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.connection import Base


def utc_now():
    """Return the current UTC datetime."""
    return datetime.now(timezone.utc)


class User(Base):
    """Stores application user accounts."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(30), default="patient", nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    patient: Mapped["Patient | None"] = relationship(
        back_populates="user", uselist=False
    )


class Patient(Base):
    """Stores patient profile information."""

    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id"), unique=True, nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(
        Date, nullable=True
    )
    gender: Mapped[str | None] = mapped_column(String(30), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="patient")
    appointments: Mapped[list["Appointment"]] = relationship(
        back_populates="patient"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="patient"
    )
    summaries: Mapped[list["PatientSummary"]] = relationship(
        back_populates="patient"
    )


class Department(Base):
    """Stores available hospital medical departments."""

    __tablename__ = "departments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    doctors: Mapped[list["Doctor"]] = relationship(
        back_populates="department"
    )


class Doctor(Base):
    """Stores registered doctors and their department assignments."""

    __tablename__ = "doctors"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    department_id: Mapped[str] = mapped_column(
        ForeignKey("departments.id"), nullable=False, index=True
    )
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    specialization: Mapped[str | None] = mapped_column(
        String(150), nullable=True
    )
    qualification: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    department: Mapped["Department"] = relationship(
        back_populates="doctors"
    )
    appointment_slots: Mapped[list["AppointmentSlot"]] = relationship(
        back_populates="doctor"
    )


class AppointmentSlot(Base):
    """Stores appointment slots offered by individual doctors."""

    __tablename__ = "appointment_slots"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    doctor_id: Mapped[str] = mapped_column(
        ForeignKey("doctors.id"), nullable=False, index=True
    )
    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ends_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(30), default="available", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    doctor: Mapped["Doctor"] = relationship(
        back_populates="appointment_slots"
    )
    appointment: Mapped["Appointment | None"] = relationship(
        back_populates="slot", uselist=False
    )

    __table_args__ = (
        UniqueConstraint(
            "doctor_id",
            "starts_at",
            name="uq_doctor_appointment_start",
        ),
    )


class Appointment(Base):
    """Stores patient appointment bookings."""

    __tablename__ = "appointments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    patient_id: Mapped[str] = mapped_column(
        ForeignKey("patients.id"), nullable=False, index=True
    )
    slot_id: Mapped[str | None] = mapped_column(
        ForeignKey("appointment_slots.id"),
        unique=True,
        nullable=True,
    )
    department: Mapped[str] = mapped_column(String(100), nullable=False)
    doctor_name: Mapped[str] = mapped_column(String(150), nullable=False)
    appointment_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(30), default="pending_confirmation", nullable=False
    )
    patient_confirmed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    booking_reference: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    patient: Mapped["Patient"] = relationship(
        back_populates="appointments"
    )
    slot: Mapped["AppointmentSlot | None"] = relationship(
        back_populates="appointment"
    )
    summary: Mapped["PatientSummary | None"] = relationship(
        back_populates="appointment", uselist=False
    )

    __table_args__ = (
        Index("ix_appointment_slot", "doctor_name", "appointment_at"),
        Index("ix_appointment_patient_status", "patient_id", "status"),
    )


class Conversation(Base):
    """Stores patient-agent conversation sessions."""

    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    patient_id: Mapped[str] = mapped_column(
        ForeignKey("patients.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(30), default="active", nullable=False
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    patient: Mapped["Patient"] = relationship(
        back_populates="conversations"
    )
    messages: Mapped[list["ConversationMessage"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ConversationMessage.created_at",
    )
    patient_summary: Mapped["PatientSummary | None"] = relationship(
        back_populates="conversation", uselist=False
    )


class ConversationMessage(Base):
    """Stores individual messages in a conversation."""

    __tablename__ = "conversation_messages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    conversation: Mapped["Conversation"] = relationship(
        back_populates="messages"
    )


class PatientSummary(Base):
    """Stores generated summaries of patient consultations."""

    __tablename__ = "patient_summaries"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    patient_id: Mapped[str] = mapped_column(
        ForeignKey("patients.id"), nullable=False, index=True
    )
    conversation_id: Mapped[str | None] = mapped_column(
        ForeignKey("conversations.id"), unique=True, nullable=True
    )
    appointment_id: Mapped[str | None] = mapped_column(
        ForeignKey("appointments.id"), unique=True, nullable=True
    )
    chief_complaint: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    symptoms: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_department: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    patient: Mapped["Patient"] = relationship(
        back_populates="summaries"
    )
    conversation: Mapped["Conversation | None"] = relationship(
        back_populates="patient_summary"
    )
    appointment: Mapped["Appointment | None"] = relationship(
        back_populates="summary"
    )
