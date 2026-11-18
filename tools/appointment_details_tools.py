
import json
from typing import Annotated

from langchain_core.tools import InjectedToolArg, tool
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from database.connection import SessionLocal
from database.models import Appointment


@tool
def get_appointment_details(
    patient_id: Annotated[str, InjectedToolArg],
    appointment_id: str = "",
    booking_reference: str = "",
) -> str:
    """
    Retrieve appointment details for the authenticated patient.

    Search using either an appointment ID or booking reference.

    Returns the department, doctor, appointment date and time,
    booking reference, appointment status, and confirmation status.

    The patient ID is injected by the trusted backend.
    The tool cannot access another patient's appointments.
    """

    patient_id = patient_id.strip()
    appointment_id = appointment_id.strip()
    booking_reference = booking_reference.strip()

    if not patient_id:
        return json.dumps({
            "success": False,
            "error": "Authenticated patient information is required.",
        })

    if not appointment_id and not booking_reference:
        return json.dumps({
            "success": False,
            "error": (
                "Provide either an appointment ID "
                "or a booking reference."
            ),
        })

    if appointment_id and booking_reference:
        return json.dumps({
            "success": False,
            "error": (
                "Provide only one search identifier: "
                "appointment ID or booking reference."
            ),
        })

    try:
        with SessionLocal() as db:

            statement = select(Appointment).where(
                Appointment.patient_id == patient_id
            )

            if appointment_id:
                statement = statement.where(
                    Appointment.id == appointment_id
                )
            else:
                statement = statement.where(
                    Appointment.booking_reference
                    == booking_reference
                )

            appointment = db.scalar(statement)

            if appointment is None:
                return json.dumps({
                    "success": False,
                    "error": "Appointment not found for this patient.",
                })

            return json.dumps({
                "success": True,
                "appointment": {
                    "appointment_id": appointment.id,
                    "booking_reference": appointment.booking_reference,
                    "patient_id": appointment.patient_id,
                    "department": appointment.department,
                    "doctor_name": appointment.doctor_name,
                    "appointment_at": (
                        appointment.appointment_at.isoformat()
                        if appointment.appointment_at
                        else None
                    ),
                    "status": appointment.status,
                    "patient_confirmed": appointment.patient_confirmed,
                    "slot_id": appointment.slot_id,
                    "created_at": (
                        appointment.created_at.isoformat()
                        if appointment.created_at
                        else None
                    ),
                },
            }, indent=2)

    except SQLAlchemyError:
        return json.dumps({
            "success": False,
            "error": "Unable to retrieve appointment details.",
        })
