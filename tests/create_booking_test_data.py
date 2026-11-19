
from datetime import datetime, timedelta

from database.connection import SessionLocal
from database import repositories


def create_booking_test_data():
    """Create temporary records for testing Agent 7."""

    db = SessionLocal()

    try:
        # 1. Create a test user.
        user = repositories.create_user(
            db=db,
            email="booking.test@example.com",
            password_hash="test-only-placeholder",
            role="patient",
        )

        # 2. Create the patient profile.
        patient = repositories.create_patient(
            db=db,
            user_id=user.id,
            full_name="Test Patient",
            phone="9999999999",
        )

        # 3. Create a department.
        department = repositories.create_department(
            db=db,
            name="General Medicine",
            description="General medical consultations",
        )

        # 4. Create an active doctor.
        doctor = repositories.create_doctor(
            db=db,
            department_id=department.id,
            full_name="Dr. Test Doctor",
            specialization="General Medicine",
            qualification="MBBS",
        )

        # 5. Create a future appointment slot.
        appointment_start = datetime.now() + timedelta(days=7)
        appointment_end = appointment_start + timedelta(minutes=30)

        slot = repositories.create_appointment_slot(
            db=db,
            doctor_id=doctor.id,
            starts_at=appointment_start,
            ends_at=appointment_end,
        )

        print("\nTEST DATA CREATED SUCCESSFULLY")
        print("-" * 45)
        print("User ID:", user.id)
        print("Patient ID:", patient.id)
        print("Department ID:", department.id)
        print("Doctor ID:", doctor.id)
        print("Slot ID:", slot.id)
        print("Appointment time:", slot.starts_at)
        print("-" * 45)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    create_booking_test_data()
