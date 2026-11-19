
import json
import logging
from typing import Any

from tools.booking_tools import book_appointment_tool
from tools.appointment_details_tools import get_appointment_details


logger = logging.getLogger(__name__)


def _parse_tool_response(
    response: Any,
    tool_name: str,
) -> dict[str, Any]:
    """Convert a tool response into a Python dictionary."""

    if isinstance(response, str):
        try:
            response = json.loads(response)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"{tool_name} returned invalid JSON."
            ) from exc

    if not isinstance(response, dict):
        raise ValueError(
            f"{tool_name} returned an invalid response."
        )

    return response


def book_patient_appointment(
    slot_id: str,
    patient_id: str,
    patient_confirmed: bool,
) -> dict[str, Any]:
    """
    Book an appointment after explicit patient confirmation.

    Patient ID and confirmation must come from the trusted backend.
    The LLM must never decide or supply patient confirmation.
    """

    # 1. Validate inputs.
    if not isinstance(slot_id, str) or not slot_id.strip():
        raise ValueError("A valid appointment slot ID is required.")

    if not isinstance(patient_id, str) or not patient_id.strip():
        raise ValueError("A valid patient ID is required.")

    if not isinstance(patient_confirmed, bool):
        raise ValueError("Patient confirmation must be a boolean.")

    slot_id = slot_id.strip()
    patient_id = patient_id.strip()

    # 2. Require explicit patient confirmation.
    if patient_confirmed is not True:
        return {
            "success": False,
            "booking_status": "awaiting_confirmation",
            "message": (
                "Appointment not booked. "
                "Explicit patient confirmation is required."
            ),
        }

    try:
        # 3. Call the original booking function directly.
        raw_booking = book_appointment_tool.func(
            slot_id=slot_id,
            patient_id=patient_id,
            patient_confirmed=True,
        )

        booking_result = _parse_tool_response(
            raw_booking,
            "Appointment booking tool",
        )

        if not booking_result.get("success"):
            return {
                "success": False,
                "booking_status": "failed",
                "message": booking_result.get(
                    "error",
                    "Appointment booking failed.",
                ),
            }

        appointment = booking_result.get("appointment")

        if not isinstance(appointment, dict):
            raise ValueError(
                "Booking succeeded but appointment details are missing."
            )

        appointment_id = appointment.get("appointment_id")

        if not appointment_id:
            raise ValueError(
                "Booking succeeded but appointment ID is missing."
            )

        # 4. Retrieve the saved appointment using the same patient ID.
        raw_details = get_appointment_details.func(
            patient_id=patient_id,
            appointment_id=appointment_id,
        )

        details_result = _parse_tool_response(
            raw_details,
            "Appointment details tool",
        )

        if not details_result.get("success"):
            # Booking is already committed. Do not report it as failed.
            logger.error(
                "Appointment booked, but detail retrieval failed: %s",
                details_result.get("error"),
            )

            return {
                "success": True,
                "booking_status": "confirmed",
                "booking": appointment,
                "booking_details_retrieved": False,
                "message": (
                    "Your appointment has been booked successfully, "
                    "but detailed booking information could not be retrieved."
                ),
            }

        saved_appointment = details_result.get("appointment")

        if not isinstance(saved_appointment, dict):
            raise ValueError(
                "Appointment details response is missing the appointment."
            )

        # 5. Return the confirmed appointment.
        return {
            "success": True,
            "booking_status": "confirmed",
            "booking": saved_appointment,
            "booking_details_retrieved": True,
            "message": "Your appointment has been successfully booked.",
        }

    except Exception as exc:
        logger.exception("Appointment booking agent failed.")

        raise RuntimeError(
            "Appointment booking workflow encountered an unexpected error."
        ) from exc
