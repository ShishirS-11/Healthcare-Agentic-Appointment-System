
import json
import secrets
from datetime import datetime
from typing import Annotated

from langchain_core.tools import InjectedToolArg, tool
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from database.connection import SessionLocal
from database.models import (
    Appointment,
    AppointmentSlot,
    Department,
    Doctor,
    Patient,
)


@tool
def book_appointment_tool(
    slot_id: str,
    patient_id: Annotated[str, InjectedToolArg],
    patient_confirmed: Annotated[bool, InjectedToolArg],
) -> str:
    """
    Book an available appointment slot for the authenticated patient.

    Requires a slot ID, authenticated patient ID, and explicit
    patient confirmation supplied by the trusted backend.

    Atomically reserves the slot and creates the appointment.
    Prevents duplicate bookings and bookings of unavailable or
    expired slots.

    The AI agent cannot provide its own patient confirmation.
    """

    slot_id = slot_id.strip()
    patient_id = patient_id.strip()

    if not slot_id or not patient_id:
        return json.dumps({
            "success": False,
            "error": "Patient ID and appointment slot ID are required.",
        })

    if patient_confirmed is not True:
        return json.dumps({
            "success": False,
            "error": "Patient confirmation is required before booking.",
        })

    try:
        with SessionLocal() as db:

            # Verify that the patient exists.
            patient = db.get(Patient, patient_id)

            if patient is None:
                return json.dumps({
                    "success": False,
                    "error": "Patient profile not found.",
                })

            # Atomically claim the slot only if it is still available.
            # The conditional UPDATE prevents two requests from
            # successfully reserving the same slot.
            reservation_result = db.execute(
                update(AppointmentSlot)
                .where(
                    AppointmentSlot.id == slot_id,
                    AppointmentSlot.status == "available",
                    AppointmentSlot.starts_at > datetime.now(),
                )
                .values(status="booked")
            )

            if reservation_result.rowcount != 1:
                db.rollback()

                return json.dumps({
                    "success": False,
                    "error": (
                        "This appointment slot is unavailable, "
                        "already booked, expired, or does not exist. "
                        "Please check availability again."
                    ),
                })

            # Retrieve the reserved slot and its active doctor
            # and department.
            slot_details = db.execute(
                select(
                    AppointmentSlot,
                    Doctor,
                    Department,
                )
                .join(
                    Doctor,
                    AppointmentSlot.doctor_id == Doctor.id,
                )
                .join(
                    Department,
                    Doctor.department_id == Department.id,
                )
                .where(
                    AppointmentSlot.id == slot_id,
                    Doctor.is_active.is_(True),
                    Department.is_active.is_(True),
                )
            ).first()

            if slot_details is None:
                db.rollback()

                return json.dumps({
                    "success": False,
                    "error": (
                        "The doctor or department is no longer active. "
                        "Please select another appointment slot."
                    ),
                })

            slot, doctor, department = slot_details

            # Generate a unique booking reference.
            booking_reference = (
                f"APT-{secrets.token_hex(6).upper()}"
            )

            # Create the confirmed appointment.
            appointment = Appointment(
                patient_id=patient_id,
                slot_id=slot.id,
                department=department.name,
                doctor_name=doctor.full_name,
                appointment_at=slot.starts_at,
                status="confirmed",
                patient_confirmed=True,
                booking_reference=booking_reference,
            )

            db.add(appointment)

            # Both the slot update and appointment creation
            # are committed together.
            db.commit()
            db.refresh(appointment)

            return json.dumps({
                "success": True,
                "message": "Appointment booked successfully.",
                "appointment": {
                    "appointment_id": appointment.id,
                    "booking_reference": appointment.booking_reference,
                    "patient_id": appointment.patient_id,
                    "department": appointment.department,
                    "doctor_name": appointment.doctor_name,
                    "appointment_at": (
                        appointment.appointment_at.isoformat()
                    ),
                    "status": appointment.status,
                    "patient_confirmed": appointment.patient_confirmed,
                    "slot_id": appointment.slot_id,
                },
            }, indent=2)

    except IntegrityError:
        return json.dumps({
            "success": False,
            "error": (
                "The booking could not be completed because "
                "the slot may already have been reserved. "
                "Please check availability again."
            ),
        })

    except SQLAlchemyError:
        return json.dumps({
            "success": False,
            "error": (
                "A database error prevented the appointment "
                "from being booked. Please try again."
            ),
        })
