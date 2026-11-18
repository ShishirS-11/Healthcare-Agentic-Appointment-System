
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select

from database.connection import SessionLocal
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
from database.repositories import (
    add_conversation_message,
    create_appointment,
    create_appointment_slot,
    create_conversation,
    create_department,
    create_doctor,
    create_patient,
    create_patient_summary,
    create_user,
    get_active_departments,
    get_available_slots,
    get_doctors_by_department,
    get_patient_summaries,
    link_summary_to_appointment,
)


def test_healthcare_database_workflow():
    db = SessionLocal()

    user = None
    patient = None
    department = None
    doctor = None
    slot = None
    conversation = None
    summary = None
    appointment = None

    test_email = f"test_{uuid4().hex[:12]}@example.com"

    try:
        # 1. Create a test user and patient
        user = create_user(
            db,
            email=test_email,
            password_hash="test_hash_only",
        )

        patient = create_patient(
            db,
            user_id=user.id,
            full_name="Test Patient",
            phone="9999999999",
        )

        # 2. Create a department
        department = create_department(
            db,
            name=f"Cardiology Test {uuid4().hex[:8]}",
            description="Test department",
        )

        assert department.id is not None

        # 3. Register a doctor
        doctor = create_doctor(
            db,
            department_id=department.id,
            full_name="Dr. Test Doctor",
            specialization="Cardiology",
            qualification="MBBS",
        )

        doctors = get_doctors_by_department(db, department.id)
        assert any(item.id == doctor.id for item in doctors)

        # 4. Create an appointment slot
        start_time = datetime.now(timezone.utc) + timedelta(days=2)
        end_time = start_time + timedelta(minutes=30)

        slot = create_appointment_slot(
            db,
            doctor_id=doctor.id,
            starts_at=start_time,
            ends_at=end_time,
        )

        available_slots = get_available_slots(
            db,
            doctor_id=doctor.id,
            start_time=start_time - timedelta(minutes=1),
            end_time=end_time + timedelta(minutes=1),
        )

        assert any(item.id == slot.id for item in available_slots)

        # 5. Create a conversation and message
        conversation = create_conversation(
            db,
            patient_id=patient.id,
        )

        add_conversation_message(
            db,
            conversation_id=conversation.id,
            role="user",
            content="This is a database integration test.",
        )

        # 6. Save a patient summary
        summary = create_patient_summary(
            db,
            patient_id=patient.id,
            conversation_id=conversation.id,
            chief_complaint="Test complaint",
            symptoms="Test symptoms",
            recommended_department="Cardiology",
            summary_text="Test patient consultation summary.",
        )

        summaries = get_patient_summaries(db, patient.id)
        assert any(item.id == summary.id for item in summaries)

        # 7. Create an appointment and link the summary
        appointment = create_appointment(
            db,
            patient_id=patient.id,
            department=department.name,
            doctor_name=doctor.full_name,
            appointment_at=start_time,
            booking_reference=f"TEST-{uuid4().hex[:10]}",
            slot_id=slot.id,
        )

        linked_summary = link_summary_to_appointment(
            db,
            summary_id=summary.id,
            appointment_id=appointment.id,
            patient_id=patient.id,
        )

        assert linked_summary.appointment_id == appointment.id

        # 8. Verify relationships
        db.refresh(appointment)
        db.refresh(slot)

        assert appointment.slot_id == slot.id
        assert appointment.patient_id == patient.id
        assert appointment.status == "pending_confirmation"
        assert appointment.patient_confirmed is False

        assert slot.doctor_id == doctor.id
        assert slot.status == "available"

        assert linked_summary.patient_id == patient.id
        assert linked_summary.appointment_id == appointment.id

        active_departments = get_active_departments(db)
        assert any(item.id == department.id for item in active_departments)

        print("User and patient creation: PASSED")
        print("Department creation: PASSED")
        print("Doctor registration: PASSED")
        print("Appointment slot creation: PASSED")
        print("Available slot retrieval: PASSED")
        print("Conversation and message storage: PASSED")
        print("Patient summary storage: PASSED")
        print("Appointment creation: PASSED")
        print("Summary-to-appointment linking: PASSED")
        print("Relationship verification: PASSED")

    finally:
        # Delete test records in foreign-key-safe order.
        if summary is not None:
            db.delete(summary)

        if appointment is not None:
            db.delete(appointment)

        if conversation is not None:
            db.execute(
                select(ConversationMessage).where(
                    ConversationMessage.conversation_id == conversation.id
                )
            )
            messages = db.scalars(
                select(ConversationMessage).where(
                    ConversationMessage.conversation_id == conversation.id
                )
            ).all()

            for message in messages:
                db.delete(message)

            db.delete(conversation)

        if slot is not None:
            db.delete(slot)

        if doctor is not None:
            db.delete(doctor)

        if department is not None:
            db.delete(department)

        if patient is not None:
            db.delete(patient)

        if user is not None:
            db.delete(user)

        db.commit()
        db.close()

        print("\nTest data cleanup: COMPLETED")


if __name__ == "__main__":
    test_healthcare_database_workflow()
    print("\nALL HEALTHCARE DATABASE TESTS PASSED!")
