
import json
from datetime import date, datetime
from typing import Annotated

from langchain_core.tools import InjectedToolArg, tool
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from database.connection import SessionLocal
from database.models import Patient, User


@tool
def get_patient_profile(
    user_id: Annotated[str, InjectedToolArg],
) -> str:
    """
    Retrieve the profile of the currently authenticated patient.

    The user_id must be injected by the trusted backend.
    The AI agent must not choose or modify this identifier.

    Returns basic patient profile information only.
    Does not expose passwords, authentication details, or
    other patients' records.
    """

    if not user_id or not user_id.strip():
        return json.dumps({
            "success": False,
            "error": "Authenticated user information is required.",
        })

    try:
        statement = (
            select(Patient)
            .join(User, Patient.user_id == User.id)
            .where(
                User.id == user_id.strip(),
                User.is_active.is_(True),
            )
        )

        with SessionLocal() as db:
            patient = db.scalar(statement)

            if patient is None:
                return json.dumps({
                    "success": False,
                    "error": "Patient profile was not found.",
                })

            profile = {
                "patient_id": patient.id,
                "full_name": patient.full_name,
                "date_of_birth": (
                    patient.date_of_birth.isoformat()
                    if isinstance(patient.date_of_birth, date)
                    else None
                ),
                "gender": patient.gender,
                "created_at": (
                    patient.created_at.isoformat()
                    if isinstance(patient.created_at, datetime)
                    else None
                ),
            }

            return json.dumps({
                "success": True,
                "patient": profile,
            }, indent=2)

    except SQLAlchemyError:
        return json.dumps({
            "success": False,
            "error": "Unable to retrieve the patient profile.",
        })
