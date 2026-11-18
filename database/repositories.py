
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import (
    Appointment,
    AppointmentSlot,
    Conversation,
    ConversationMessage,
    Department,
    Doctor,
    Patient,
    PatientSummary,
    User,
)


# -------------------------
# USER OPERATIONS
# -------------------------

def create_user(
    db: Session,
    email: str,
    password_hash: str,
    role: str = "patient",
) -> User:
    user = User(
        email=email.strip().lower(),
        password_hash=password_hash,
        role=role,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def get_user_by_email(db: Session, email: str) -> User | None:
    statement = select(User).where(
        User.email == email.strip().lower()
    )
    return db.scalar(statement)


def get_user_by_id(db: Session, user_id: str) -> User | None:
    return db.get(User, user_id)


# -------------------------
# PATIENT OPERATIONS
# -------------------------

def create_patient(
    db: Session,
    user_id: str,
    full_name: str,
    phone: str | None = None,
) -> Patient:
    patient = Patient(
        user_id=user_id,
        full_name=full_name,
        phone=phone,
    )

    db.add(patient)
    db.commit()
    db.refresh(patient)

    return patient


def get_patient_by_id(db: Session, patient_id: str) -> Patient | None:
    return db.get(Patient, patient_id)


def get_patient_by_user_id(db: Session, user_id: str) -> Patient | None:
    statement = select(Patient).where(
        Patient.user_id == user_id
    )
    return db.scalar(statement)


# -------------------------
# DEPARTMENT OPERATIONS
# -------------------------

def create_department(
    db: Session,
    name: str,
    description: str | None = None,
) -> Department:
    department = Department(
        name=name.strip(),
        description=description,
    )

    db.add(department)
    db.commit()
    db.refresh(department)

    return department


def get_department_by_id(
    db: Session,
    department_id: str,
) -> Department | None:
    return db.get(Department, department_id)


def get_department_by_name(
    db: Session,
    name: str,
) -> Department | None:
    statement = select(Department).where(
        Department.name == name.strip()
    )
    return db.scalar(statement)


def get_active_departments(db: Session) -> list[Department]:
    statement = (
        select(Department)
        .where(Department.is_active.is_(True))
        .order_by(Department.name.asc())
    )

    return list(db.scalars(statement).all())


# -------------------------
# DOCTOR OPERATIONS
# -------------------------

def create_doctor(
    db: Session,
    department_id: str,
    full_name: str,
    specialization: str | None = None,
    qualification: str | None = None,
) -> Doctor:
    doctor = Doctor(
        department_id=department_id,
        full_name=full_name.strip(),
        specialization=specialization,
        qualification=qualification,
    )

    db.add(doctor)
    db.commit()
    db.refresh(doctor)

    return doctor


def get_doctor_by_id(
    db: Session,
    doctor_id: str,
) -> Doctor | None:
    return db.get(Doctor, doctor_id)


def get_doctors_by_department(
    db: Session,
    department_id: str,
) -> list[Doctor]:
    statement = (
        select(Doctor)
        .where(
            Doctor.department_id == department_id,
            Doctor.is_active.is_(True),
        )
        .order_by(Doctor.full_name.asc())
    )

    return list(db.scalars(statement).all())


def get_active_doctors(db: Session) -> list[Doctor]:
    statement = (
        select(Doctor)
        .where(Doctor.is_active.is_(True))
        .order_by(Doctor.full_name.asc())
    )

    return list(db.scalars(statement).all())


# -------------------------
# APPOINTMENT SLOT OPERATIONS
# -------------------------

def create_appointment_slot(
    db: Session,
    doctor_id: str,
    starts_at: datetime,
    ends_at: datetime,
) -> AppointmentSlot:
    if starts_at >= ends_at:
        raise ValueError("Slot end time must be after its start time.")

    slot = AppointmentSlot(
        doctor_id=doctor_id,
        starts_at=starts_at,
        ends_at=ends_at,
        status="available",
    )

    db.add(slot)
    db.commit()
    db.refresh(slot)

    return slot


def get_appointment_slot_by_id(
    db: Session,
    slot_id: str,
) -> AppointmentSlot | None:
    return db.get(AppointmentSlot, slot_id)


def get_available_slots(
    db: Session,
    doctor_id: str,
    start_time: datetime,
    end_time: datetime,
) -> list[AppointmentSlot]:
    statement = (
        select(AppointmentSlot)
        .where(
            AppointmentSlot.doctor_id == doctor_id,
            AppointmentSlot.status == "available",
            AppointmentSlot.starts_at >= start_time,
            AppointmentSlot.starts_at < end_time,
        )
        .order_by(AppointmentSlot.starts_at.asc())
    )

    return list(db.scalars(statement).all())


def get_doctor_slots(
    db: Session,
    doctor_id: str,
) -> list[AppointmentSlot]:
    statement = (
        select(AppointmentSlot)
        .where(AppointmentSlot.doctor_id == doctor_id)
        .order_by(AppointmentSlot.starts_at.asc())
    )

    return list(db.scalars(statement).all())


# -------------------------
# APPOINTMENT OPERATIONS
# -------------------------

def create_appointment(
    db: Session,
    patient_id: str,
    department: str,
    doctor_name: str,
    appointment_at: datetime,
    booking_reference: str,
    slot_id: str | None = None,
) -> Appointment:
    appointment = Appointment(
        patient_id=patient_id,
        slot_id=slot_id,
        department=department,
        doctor_name=doctor_name,
        appointment_at=appointment_at,
        booking_reference=booking_reference,
        status="pending_confirmation",
        patient_confirmed=False,
    )

    db.add(appointment)
    db.commit()
    db.refresh(appointment)

    return appointment


def get_patient_appointments(
    db: Session,
    patient_id: str,
) -> list[Appointment]:
    statement = (
        select(Appointment)
        .where(Appointment.patient_id == patient_id)
        .order_by(Appointment.appointment_at.desc())
    )

    return list(db.scalars(statement).all())


def get_appointment_by_id(
    db: Session,
    appointment_id: str,
) -> Appointment | None:
    return db.get(Appointment, appointment_id)


def get_appointment_by_reference(
    db: Session,
    booking_reference: str,
) -> Appointment | None:
    statement = select(Appointment).where(
        Appointment.booking_reference == booking_reference
    )
    return db.scalar(statement)


# -------------------------
# CONVERSATION OPERATIONS
# -------------------------

def create_conversation(
    db: Session,
    patient_id: str,
) -> Conversation:
    conversation = Conversation(patient_id=patient_id)

    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return conversation


def add_conversation_message(
    db: Session,
    conversation_id: str,
    role: str,
    content: str,
) -> ConversationMessage:
    message = ConversationMessage(
        conversation_id=conversation_id,
        role=role,
        content=content,
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    return message


def get_conversation(
    db: Session,
    conversation_id: str,
) -> Conversation | None:
    return db.get(Conversation, conversation_id)


def get_conversation_messages(
    db: Session,
    conversation_id: str,
) -> list[ConversationMessage]:
    statement = (
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conversation_id)
        .order_by(ConversationMessage.created_at.asc())
    )

    return list(db.scalars(statement).all())


# -------------------------
# PATIENT SUMMARY OPERATIONS
# -------------------------

def create_patient_summary(
    db: Session,
    patient_id: str,
    summary_text: str,
    conversation_id: str | None = None,
    chief_complaint: str | None = None,
    symptoms: str | None = None,
    recommended_department: str | None = None,
) -> PatientSummary:
    summary = PatientSummary(
        patient_id=patient_id,
        conversation_id=conversation_id,
        summary_text=summary_text,
        chief_complaint=chief_complaint,
        symptoms=symptoms,
        recommended_department=recommended_department,
    )

    db.add(summary)
    db.commit()
    db.refresh(summary)

    return summary


def get_patient_summary_by_id(
    db: Session,
    summary_id: str,
) -> PatientSummary | None:
    return db.get(PatientSummary, summary_id)


def get_patient_summaries(
    db: Session,
    patient_id: str,
) -> list[PatientSummary]:
    statement = (
        select(PatientSummary)
        .where(PatientSummary.patient_id == patient_id)
        .order_by(PatientSummary.created_at.desc())
    )

    return list(db.scalars(statement).all())


def link_summary_to_appointment(
    db: Session,
    summary_id: str,
    appointment_id: str,
    patient_id: str,
) -> PatientSummary:
    summary = db.get(PatientSummary, summary_id)
    appointment = db.get(Appointment, appointment_id)

    if summary is None:
        raise ValueError("Patient summary was not found.")

    if appointment is None:
        raise ValueError("Appointment was not found.")

    if summary.patient_id != patient_id:
        raise ValueError("Summary does not belong to this patient.")

    if appointment.patient_id != patient_id:
        raise ValueError("Appointment does not belong to this patient.")

    if summary.appointment_id is not None:
        raise ValueError("This summary is already linked to an appointment.")

    summary.appointment_id = appointment.id

    db.commit()
    db.refresh(summary)

    return summary


def get_summary_by_appointment(
    db: Session,
    appointment_id: str,
    patient_id: str,
) -> PatientSummary | None:
    statement = select(PatientSummary).where(
        PatientSummary.appointment_id == appointment_id,
        PatientSummary.patient_id == patient_id,
    )

    return db.scalar(statement)
