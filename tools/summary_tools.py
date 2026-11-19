
import json
from typing import Annotated, Literal

from langchain_core.tools import InjectedToolArg, tool
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from database.connection import SessionLocal
from database.models import (
    Appointment,
    Conversation,
    Patient,
    PatientSummary,
)


@tool
def manage_patient_summary(
    action: Literal["create", "list", "get_by_appointment"],
    patient_id: Annotated[str, InjectedToolArg],
    chief_complaint: str = "",
    symptoms: str = "",
    recommended_department: str = "",
    summary_text: str = "",
    conversation_id: str = "",
    appointment_id: str = "",
) -> str:
    """
    Create and retrieve summaries for the authenticated patient.

    Supported actions:
    - create: Save a patient summary.
    - list: Retrieve all summaries belonging to the patient.
    - get_by_appointment: Retrieve a summary linked to an appointment.

    Patient ID is injected by the trusted backend.
    Appointment and conversation ownership are verified.
    """

    patient_id = patient_id.strip()
    conversation_id = conversation_id.strip()
    appointment_id = appointment_id.strip()

    if not patient_id:
        return json.dumps({
            "success": False,
            "error": "Authenticated patient information is required.",
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

            # -------------------------------------------------
            # ACTION 1: CREATE SUMMARY
            # -------------------------------------------------

            if action == "create":

                chief_complaint = chief_complaint.strip()
                symptoms = symptoms.strip()
                recommended_department = (
                    recommended_department.strip()
                )
                summary_text = summary_text.strip()

                if not chief_complaint or not summary_text:
                    return json.dumps({
                        "success": False,
                        "error": (
                            "Chief complaint and summary text are required."
                        ),
                    })

                if (
                    len(chief_complaint) > 1000
                    or len(symptoms) > 5000
                    or len(recommended_department) > 200
                    or len(summary_text) > 10000
                ):
                    return json.dumps({
                        "success": False,
                        "error": (
                            "One or more summary fields exceed "
                            "their character limits."
                        ),
                    })

                # Verify conversation ownership.
                if conversation_id:
                    conversation = db.scalar(
                        select(Conversation).where(
                            Conversation.id == conversation_id,
                            Conversation.patient_id == patient_id,
                        )
                    )

                    if conversation is None:
                        return json.dumps({
                            "success": False,
                            "error": (
                                "Conversation not found for this patient."
                            ),
                        })

                    existing_conversation_summary = db.scalar(
                        select(PatientSummary).where(
                            PatientSummary.conversation_id
                            == conversation_id
                        )
                    )

                    if existing_conversation_summary is not None:
                        return json.dumps({
                            "success": False,
                            "error": (
                                "A summary already exists "
                                "for this conversation."
                            ),
                        })

                # Verify appointment ownership.
                if appointment_id:
                    appointment = db.scalar(
                        select(Appointment).where(
                            Appointment.id == appointment_id,
                            Appointment.patient_id == patient_id,
                        )
                    )

                    if appointment is None:
                        return json.dumps({
                            "success": False,
                            "error": (
                                "Appointment not found for this patient."
                            ),
                        })

                    existing_appointment_summary = db.scalar(
                        select(PatientSummary).where(
                            PatientSummary.appointment_id
                            == appointment_id
                        )
                    )

                    if existing_appointment_summary is not None:
                        return json.dumps({
                            "success": False,
                            "error": (
                                "A summary already exists "
                                "for this appointment."
                            ),
                        })

                # Create and persist the summary.
                summary = PatientSummary(
                    patient_id=patient_id,
                    conversation_id=conversation_id or None,
                    appointment_id=appointment_id or None,
                    chief_complaint=chief_complaint,
                    symptoms=symptoms,
                    recommended_department=(
                        recommended_department or None
                    ),
                    summary_text=summary_text,
                )

                db.add(summary)
                db.commit()
                db.refresh(summary)

                return json.dumps({
                    "success": True,
                    "action": "create",
                    "summary": {
                        "summary_id": summary.id,
                        "patient_id": summary.patient_id,
                        "conversation_id": summary.conversation_id,
                        "appointment_id": summary.appointment_id,
                        "chief_complaint": summary.chief_complaint,
                        "symptoms": summary.symptoms,
                        "recommended_department": (
                            summary.recommended_department
                        ),
                        "summary_text": summary.summary_text,
                        "created_at": (
                            summary.created_at.isoformat()
                            if summary.created_at
                            else None
                        ),
                    },
                }, indent=2)

            # -------------------------------------------------
            # ACTION 2: LIST PATIENT SUMMARIES
            # -------------------------------------------------

            if action == "list":

                summaries = db.scalars(
                    select(PatientSummary)
                    .where(
                        PatientSummary.patient_id == patient_id
                    )
                    .order_by(
                        PatientSummary.created_at.desc()
                    )
                ).all()

                return json.dumps({
                    "success": True,
                    "action": "list",
                    "total_summaries": len(summaries),
                    "summaries": [
                        {
                            "summary_id": item.id,
                            "conversation_id": item.conversation_id,
                            "appointment_id": item.appointment_id,
                            "chief_complaint": item.chief_complaint,
                            "symptoms": item.symptoms,
                            "recommended_department": (
                                item.recommended_department
                            ),
                            "summary_text": item.summary_text,
                            "created_at": (
                                item.created_at.isoformat()
                                if item.created_at
                                else None
                            ),
                        }
                        for item in summaries
                    ],
                }, indent=2)

            # -------------------------------------------------
            # ACTION 3: GET SUMMARY BY APPOINTMENT
            # -------------------------------------------------

            if action == "get_by_appointment":

                if not appointment_id:
                    return json.dumps({
                        "success": False,
                        "error": "Appointment ID is required.",
                    })

                appointment = db.scalar(
                    select(Appointment).where(
                        Appointment.id == appointment_id,
                        Appointment.patient_id == patient_id,
                    )
                )

                if appointment is None:
                    return json.dumps({
                        "success": False,
                        "error": (
                            "Appointment not found for this patient."
                        ),
                    })

                summary = db.scalar(
                    select(PatientSummary).where(
                        PatientSummary.patient_id == patient_id,
                        PatientSummary.appointment_id == appointment_id,
                    )
                )

                if summary is None:
                    return json.dumps({
                        "success": False,
                        "error": (
                            "No summary is linked to this appointment."
                        ),
                    })

                return json.dumps({
                    "success": True,
                    "action": "get_by_appointment",
                    "summary": {
                        "summary_id": summary.id,
                        "appointment_id": summary.appointment_id,
                        "chief_complaint": summary.chief_complaint,
                        "symptoms": summary.symptoms,
                        "recommended_department": (
                            summary.recommended_department
                        ),
                        "summary_text": summary.summary_text,
                        "created_at": (
                            summary.created_at.isoformat()
                            if summary.created_at
                            else None
                        ),
                    },
                }, indent=2)

            return json.dumps({
                "success": False,
                "error": "Unsupported summary action.",
            })

    except IntegrityError:
        return json.dumps({
            "success": False,
            "error": (
                "A summary already exists for this conversation "
                "or appointment, or a database constraint was violated."
            ),
        })

    except SQLAlchemyError:
        return json.dumps({
            "success": False,
            "error": "Unable to manage the patient summary.",
        })
