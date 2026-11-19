
import json
import logging
from typing import Any

from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field

from config.settings import settings
from tools.summary_tools import manage_patient_summary


logger = logging.getLogger(__name__)


# =========================================================
# 1. STRUCTURED SUMMARY MODEL
# =========================================================

class PatientSummaryResult(BaseModel):
    """Structured summary of a patient consultation."""

    chief_complaint: str
    symptoms: list[str] = Field(default_factory=list)
    duration: str | None = None
    relevant_context: list[str] = Field(default_factory=list)
    safety_observations: list[str] = Field(default_factory=list)
    recommended_department: str | None = None
    appointment_status: str | None = None
    appointment_details: str | None = None
    summary_text: str
    missing_information: list[str] = Field(default_factory=list)


# =========================================================
# 2. LOCAL LLM CONFIGURATION
# =========================================================

llm = ChatOllama(
    model=settings.ollama_model,
    base_url=settings.ollama_base_url,
    temperature=0,
)

summary_llm = llm.with_structured_output(PatientSummaryResult)


# =========================================================
# 3. LLM PROMPT
# =========================================================

SUMMARY_PROMPT = """
You are a patient consultation summarization assistant.

Your task is to create a concise and accurate narrative
summary from the supplied patient information.

STRICT RULES:

1. Use only the supplied information.
2. Never invent symptoms or medical history.
3. Never create a medical diagnosis.
4. Never prescribe medicines or treatments.
5. Do not change the patient's reported symptoms.
6. Do not interpret a department recommendation as a diagnosis.
7. Preserve uncertainty and missing information.
8. Do not claim an appointment was booked unless the
   booking result explicitly confirms it.
9. Clearly distinguish patient-reported information
   from safety screening observations.
10. Do not include information that is absent from the input.

Return a concise narrative summary.

The structured factual fields will be populated separately
by the application. Focus on the narrative summary_text.
"""


# =========================================================
# 4. HELPER FUNCTIONS
# =========================================================

def _safe_dict(value: Any) -> dict[str, Any]:
    """Return a dictionary or an empty dictionary."""

    return value if isinstance(value, dict) else {}


def _string_list(value: Any) -> list[str]:
    """Normalize a list of non-empty strings."""

    if not isinstance(value, list):
        return []

    return [
        str(item).strip()
        for item in value
        if item is not None and str(item).strip()
    ]


def _extract_booking_details(
    appointment_result: dict[str, Any],
) -> str | None:
    """Extract confirmed appointment information."""

    if not appointment_result.get("success"):
        return None

    if appointment_result.get("booking_status") != "confirmed":
        return None

    booking = _safe_dict(
        appointment_result.get("booking")
    )

    if not booking:
        return None

    return json.dumps(
        {
            "booking_reference": booking.get("booking_reference"),
            "department": booking.get("department"),
            "doctor_name": booking.get("doctor_name"),
            "appointment_at": booking.get("appointment_at"),
            "status": booking.get("status"),
        },
        ensure_ascii=False,
    )


# =========================================================
# 5. GENERATE PATIENT SUMMARY
# =========================================================

def generate_patient_summary(
    patient_intake: dict[str, Any],
    safety_result: dict[str, Any] | None = None,
    classification_result: dict[str, Any] | None = None,
    appointment_result: dict[str, Any] | None = None,
    conversation_history: list[dict[str, str]] | None = None,
) -> PatientSummaryResult:
    """
    Generate a summary using verified agent results.

    Factual fields are populated directly from their source agents.
    The LLM generates only the narrative summary.
    """

    if not isinstance(patient_intake, dict):
        raise ValueError("Patient intake must be a dictionary.")

    safety = _safe_dict(safety_result)
    classification = _safe_dict(classification_result)
    appointment = _safe_dict(appointment_result)

    # -----------------------------------------------------
    # A. EXTRACT FACTUAL INFORMATION
    # -----------------------------------------------------

    chief_complaint = str(
        patient_intake.get("chief_complaint") or ""
    ).strip()

    if not chief_complaint:
        raise ValueError(
            "Patient intake does not contain a chief complaint."
        )

    symptoms = _string_list(
        patient_intake.get("symptoms")
    )

    duration = patient_intake.get("duration")

    if duration is not None:
        duration = str(duration).strip() or None

    relevant_context = _string_list(
        patient_intake.get("relevant_context")
    )

    missing_information = _string_list(
        patient_intake.get("missing_information")
    )

    # -----------------------------------------------------
    # B. EXTRACT SAFETY OBSERVATIONS
    # -----------------------------------------------------

    safety_observations = []

    if safety.get("emergency_detected") is True:
        safety_observations.append(
            "Emergency symptoms detected by the safety screening agent."
        )

    elif safety.get("emergency_detected") is False:
        safety_observations.append(
            "No emergency symptoms were detected by the screening agent. "
            "This is not medical clearance."
        )

    # -----------------------------------------------------
    # C. EXTRACT DEPARTMENT RECOMMENDATION
    # -----------------------------------------------------

    recommended_department = None

    if classification.get("classification_allowed") is not False:
        department = classification.get("department")

        if isinstance(department, str) and department.strip():
            recommended_department = department.strip()

    # -----------------------------------------------------
    # D. EXTRACT APPOINTMENT STATUS
    # -----------------------------------------------------

    appointment_status = None

    if appointment.get("success") is True:
        appointment_status = appointment.get("booking_status")

    appointment_details = _extract_booking_details(
        appointment
    )

    # -----------------------------------------------------
    # E. PREPARE LLM INPUT
    # -----------------------------------------------------

    input_data = {
        "patient_intake": patient_intake,
        "safety_result": safety,
        "classification_result": classification,
        "appointment_result": appointment,
        "conversation_history": conversation_history or [],
    }

    prompt = (
        SUMMARY_PROMPT
        + "\n\nPATIENT INFORMATION:\n"
        + json.dumps(
            input_data,
            indent=2,
            ensure_ascii=False,
        )
    )

    # -----------------------------------------------------
    # F. GENERATE NARRATIVE SUMMARY
    # -----------------------------------------------------

    try:
        llm_result = summary_llm.invoke(prompt)

        if isinstance(llm_result, BaseModel):
            narrative = llm_result.summary_text

        elif isinstance(llm_result, dict):
            narrative = llm_result.get("summary_text", "")

        else:
            raise ValueError(
                "Invalid LLM summary response."
            )

        narrative = str(narrative).strip()

        if not narrative:
            raise ValueError(
                "The generated narrative summary is empty."
            )

    except Exception as exc:
        logger.exception("Patient summary generation failed.")

        raise RuntimeError(
            "Unable to generate the patient summary."
        ) from exc

    # -----------------------------------------------------
    # G. BUILD FINAL STRUCTURED RESULT
    # -----------------------------------------------------

    return PatientSummaryResult(
        chief_complaint=chief_complaint,
        symptoms=symptoms,
        duration=duration,
        relevant_context=relevant_context,
        safety_observations=safety_observations,
        recommended_department=recommended_department,
        appointment_status=appointment_status,
        appointment_details=appointment_details,
        summary_text=narrative,
        missing_information=missing_information,
    )


# =========================================================
# 6. SAVE SUMMARY TO DATABASE
# =========================================================

def save_patient_summary(
    patient_id: str,
    summary: PatientSummaryResult,
    conversation_id: str = "",
    appointment_id: str = "",
) -> dict[str, Any]:
    """
    Save a generated summary for the authenticated patient.

    The summary can optionally be linked to a conversation
    and/or a confirmed appointment.
    """

    if not isinstance(patient_id, str) or not patient_id.strip():
        raise ValueError("Authenticated patient ID is required.")

    if not isinstance(summary, PatientSummaryResult):
        raise ValueError("A valid patient summary is required.")

    if not isinstance(conversation_id, str):
        raise ValueError("Conversation ID must be a string.")

    if not isinstance(appointment_id, str):
        raise ValueError("Appointment ID must be a string.")

    try:
        raw_result = manage_patient_summary.func(
            action="create",
            patient_id=patient_id.strip(),
            chief_complaint=summary.chief_complaint,
            symptoms=", ".join(summary.symptoms),
            recommended_department=(
                summary.recommended_department or ""
            ),
            summary_text=summary.summary_text,
            conversation_id=conversation_id.strip(),
            appointment_id=appointment_id.strip(),
        )

        if isinstance(raw_result, str):
            raw_result = json.loads(raw_result)

        if not isinstance(raw_result, dict):
            raise ValueError("Invalid database response.")

        return raw_result

    except Exception as exc:
        logger.exception("Saving patient summary failed.")

        raise RuntimeError(
            "Unable to save the patient summary."
        ) from exc


# =========================================================
# 7. RETRIEVE PATIENT SUMMARIES
# =========================================================

def get_patient_summaries(
    patient_id: str,
) -> dict[str, Any]:
    """Retrieve summaries belonging to the authenticated patient."""

    if not isinstance(patient_id, str) or not patient_id.strip():
        raise ValueError("Authenticated patient ID is required.")

    try:
        raw_result = manage_patient_summary.func(
            action="list",
            patient_id=patient_id.strip(),
        )

        if isinstance(raw_result, str):
            raw_result = json.loads(raw_result)

        if not isinstance(raw_result, dict):
            raise ValueError("Invalid database response.")

        return raw_result

    except Exception as exc:
        logger.exception("Retrieving patient summaries failed.")

        raise RuntimeError(
            "Unable to retrieve patient summaries."
        ) from exc
