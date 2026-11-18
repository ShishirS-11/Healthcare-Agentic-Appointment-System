
import json
from datetime import date, datetime, time, timedelta

from langchain_core.tools import tool
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from database.connection import SessionLocal
from database.models import AppointmentSlot, Department, Doctor


@tool
def check_available_slots(
    department_name: str = "",
    doctor_name: str = "",
    appointment_date: str = "",
    max_results: int = 10,
) -> str:
    """
    Find available appointment slots in the hospital database.

    Optionally filter by department, doctor, and appointment date.

    appointment_date must use YYYY-MM-DD format.
    Returns doctor details, department, slot ID, start time,
    and end time.

    This tool only checks availability. It does not book appointments.
    """

    department_name = department_name.strip()
    doctor_name = doctor_name.strip()
    appointment_date = appointment_date.strip()

    if not 1 <= max_results <= 50:
        return json.dumps({
            "success": False,
            "error": "max_results must be between 1 and 50.",
        })

    selected_date = None

    if appointment_date:
        try:
            selected_date = date.fromisoformat(appointment_date)
        except ValueError:
            return json.dumps({
                "success": False,
                "error": "Invalid date. Use YYYY-MM-DD format.",
            })

    try:
        now = datetime.now()

        statement = (
            select(AppointmentSlot, Doctor, Department)
            .join(
                Doctor,
                AppointmentSlot.doctor_id == Doctor.id,
            )
            .join(
                Department,
                Doctor.department_id == Department.id,
            )
            .where(
                AppointmentSlot.status == "available",
                AppointmentSlot.starts_at >= now,
                Doctor.is_active.is_(True),
                Department.is_active.is_(True),
            )
            .order_by(AppointmentSlot.starts_at.asc())
            .limit(max_results)
        )

        if department_name:
            statement = statement.where(
                Department.name.ilike(
                    f"%{department_name}%"
                )
            )

        if doctor_name:
            statement = statement.where(
                Doctor.full_name.ilike(
                    f"%{doctor_name}%"
                )
            )

        if selected_date:
            start_of_day = datetime.combine(
                selected_date,
                time.min,
            )
            start_of_next_day = start_of_day + timedelta(days=1)

            statement = statement.where(
                AppointmentSlot.starts_at >= start_of_day,
                AppointmentSlot.starts_at < start_of_next_day,
            )

        with SessionLocal() as db:
            results = db.execute(statement).all()

            slots = []

            for slot, doctor, department in results:
                slots.append({
                    "slot_id": slot.id,
                    "department": department.name,
                    "doctor_id": doctor.id,
                    "doctor_name": doctor.full_name,
                    "specialization": doctor.specialization,
                    "qualification": doctor.qualification,
                    "starts_at": slot.starts_at.isoformat(),
                    "ends_at": slot.ends_at.isoformat(),
                    "status": slot.status,
                })

            return json.dumps({
                "success": True,
                "filters": {
                    "department_name": department_name or None,
                    "doctor_name": doctor_name or None,
                    "appointment_date": appointment_date or None,
                },
                "total_available_slots": len(slots),
                "slots": slots,
            }, indent=2)

    except SQLAlchemyError:
        return json.dumps({
            "success": False,
            "error": "Unable to retrieve available appointment slots.",
        })
