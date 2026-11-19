
import json
import logging
from typing import Any

from tools.appointment_tools import check_available_slots
from tools.doctor_tools import find_departments_and_doctors


logger = logging.getLogger(__name__)


def _parse_tool_result(result: Any, tool_name: str) -> dict:
    """Convert a tool's JSON string response into a dictionary."""

    if isinstance(result, str):
        try:
            result = json.loads(result)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"{tool_name} returned invalid JSON."
            ) from exc

    if not isinstance(result, dict):
        raise ValueError(
            f"{tool_name} returned an unexpected response."
        )

    if result.get("success") is False:
        raise RuntimeError(
            result.get("error", f"{tool_name} failed.")
        )

    return result


def find_appointment_availability(
    department_name: str,
    appointment_date: str = "",
    doctor_name: str = "",
    max_results: int = 10,
) -> dict[str, Any]:
    """
    Find actual available doctors and appointment slots.

    This function only checks availability.
    It does not reserve or book appointments.
    """

    if not isinstance(department_name, str) or not department_name.strip():
        raise ValueError("Department name cannot be empty.")

    if not isinstance(appointment_date, str):
        raise ValueError("Appointment date must be a string.")

    if appointment_date:
        from datetime import date

        try:
            requested_date = date.fromisoformat(appointment_date)

            if requested_date.isoformat() != appointment_date:
                raise ValueError()

        except ValueError as exc:
            raise ValueError(
                "Appointment date must use YYYY-MM-DD format."
            ) from exc

    if not isinstance(doctor_name, str):
        raise ValueError("Doctor name must be a string.")

    if not isinstance(max_results, int) or isinstance(max_results, bool):
        raise ValueError("max_results must be an integer.")

    if not 1 <= max_results <= 50:
        raise ValueError("max_results must be between 1 and 50.")

    department_name = department_name.strip()
    doctor_name = doctor_name.strip()

    try:
        # Step 1: Find registered departments and doctors.
        raw_doctors = find_departments_and_doctors.invoke({
            "department_name": department_name,
            "doctor_name": doctor_name,
        })

        doctor_result = _parse_tool_result(
            raw_doctors,
            "Doctor directory tool",
        )

        # Step 2: Find actual available appointment slots.
        raw_slots = check_available_slots.invoke({
            "department_name": department_name,
            "doctor_name": doctor_name,
            "appointment_date": appointment_date,
            "max_results": max_results,
        })

        slot_result = _parse_tool_result(
            raw_slots,
            "Appointment availability tool",
        )

        # Step 3: Return structured results.
        available_slots = slot_result.get("slots", [])

        if not isinstance(available_slots, list):
            raise ValueError("Invalid appointment slot response.")

        return {
            "success": True,
            "department": department_name,
            "requested_date": appointment_date or None,
            "requested_doctor": doctor_name or None,
            "total_doctors": doctor_result.get("total_doctors", 0),
            "total_available_slots": len(available_slots),
            "doctors": doctor_result.get("departments", []),
            "slots": available_slots,
            "message": (
                "Available appointment slots were found."
                if available_slots
                else "No available appointment slots were found."
            ),
        }

    except Exception as exc:
        logger.exception("Appointment availability lookup failed.")

        raise RuntimeError(
            "Could not retrieve appointment availability. "
            "Check the database and appointment tools."
        ) from exc
