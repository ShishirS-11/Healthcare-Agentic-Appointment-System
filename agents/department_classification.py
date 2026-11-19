
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from pydantic import BaseModel, ConfigDict, Field

from config.settings import settings


logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# 1. DEPARTMENT CLASSIFICATION PROMPT
# ---------------------------------------------------------

DEPARTMENT_CLASSIFICATION_PROMPT = """
You are a Department Classification Agent in a healthcare
appointment system.

Your responsibility is to recommend an appropriate medical
department based on patient-reported symptoms.

POSSIBLE DEPARTMENTS:

- General Medicine
- Cardiology
- Neurology
- Orthopedics
- Dermatology
- ENT
- Ophthalmology
- Gastroenterology
- Pulmonology
- Gynecology
- Urology
- Psychiatry
- Pediatrics
- Dentistry

CLASSIFICATION RULES:

1. Analyze the chief complaint and reported symptoms.
2. Recommend the most relevant department.
3. Explain the reason for your recommendation.
4. Do not diagnose medical conditions.
5. Do not prescribe medication or treatment.
6. Do not invent symptoms or medical history.
7. Do not invent doctors or appointment availability.
8. If information is insufficient, use General Medicine
   or return an uncertain classification when appropriate.
9. Do not force a classification when symptoms are unclear.
10. Consider the patient's age only if it is provided.
11. Do not use the current date or time.

CONFIDENCE:

- high: Symptoms clearly indicate a relevant specialty.
- medium: A specialty is plausible but more information is needed.
- low: Information is insufficient for a reliable recommendation.

IMPORTANT:

This is department routing, not medical diagnosis.
A department recommendation must not be treated as
confirmation of a medical condition.
"""


# ---------------------------------------------------------
# 2. STRUCTURED OUTPUT MODEL
# ---------------------------------------------------------

class DepartmentClassificationResult(BaseModel):
    """Structured department classification result."""

    model_config = ConfigDict(extra="forbid")

    recommended_department: str = Field(
        description="Recommended medical department."
    )

    confidence: str = Field(
        description="Classification confidence: high, medium, or low."
    )

    reason: str = Field(
        description="Brief explanation for selecting this department."
    )

    alternative_departments: list[str] = Field(
        default_factory=list,
        description="Other potentially relevant departments."
    )

    requires_more_information: bool = Field(
        description="Whether additional patient information is needed."
    )

    clarification_question: str | None = Field(
        default=None,
        description="One question if clarification is required."
    )


# ---------------------------------------------------------
# 3. VALIDATION
# ---------------------------------------------------------

VALID_DEPARTMENTS = {
    "General Medicine",
    "Cardiology",
    "Neurology",
    "Orthopedics",
    "Dermatology",
    "ENT",
    "Ophthalmology",
    "Gastroenterology",
    "Pulmonology",
    "Gynecology",
    "Urology",
    "Psychiatry",
    "Pediatrics",
    "Dentistry",
}

VALID_CONFIDENCE_LEVELS = {"high", "medium", "low"}


# ---------------------------------------------------------
# 4. DEPARTMENT CLASSIFICATION AGENT
# ---------------------------------------------------------

def classify_department(
    patient_intake: dict[str, Any],
    safety_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Recommend a medical department based on patient information.

    Args:
        patient_intake: Structured patient intake information.
        safety_result: Output from the Safety Screening Agent.

    Returns:
        Structured department classification.
    """

    if not isinstance(patient_intake, dict) or not patient_intake:
        raise ValueError("Patient intake information cannot be empty.")

    if safety_result is not None and not isinstance(safety_result, dict):
        raise ValueError("Safety result must be a dictionary.")

    # Emergency cases must bypass routine classification.
    if safety_result and (
        safety_result.get("emergency_detected") is True
        or safety_result.get("requires_immediate_action") is True
    ):
        return {
            "classification_allowed": False,
            "recommended_department": None,
            "confidence": "not_assessed",
            "reason": (
                "Emergency warning signs were detected. "
                "Routine department classification has been stopped. "
                "The patient must be directed to immediate emergency "
                "medical assistance."
            ),
            "alternative_departments": [],
            "requires_more_information": False,
            "clarification_question": None,
        }

    chief_complaint = patient_intake.get("chief_complaint", "")

    if not isinstance(chief_complaint, str) or not chief_complaint.strip():
        raise ValueError("A valid chief complaint is required.")

    model = ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=0,
    )

    structured_model = model.with_structured_output(
        DepartmentClassificationResult
    )

    patient_context = f"""
    PATIENT INFORMATION:

    Chief complaint:
    {chief_complaint}

    Symptoms:
    {patient_intake.get("symptoms", [])}

    Duration:
    {patient_intake.get("duration", "Unknown")}

    Severity:
    {patient_intake.get("severity", "Unknown")}

    Associated symptoms:
    {patient_intake.get("associated_symptoms", [])}

    Relevant context:
    {patient_intake.get("relevant_context", [])}

    Missing information:
    {patient_intake.get("missing_information", [])}

    Recommend the most appropriate department based only
    on the information provided.
    """

    messages = [
        SystemMessage(content=DEPARTMENT_CLASSIFICATION_PROMPT),
        HumanMessage(content=patient_context),
    ]

    try:
        result = structured_model.invoke(messages)

        if not isinstance(result, DepartmentClassificationResult):
            result = DepartmentClassificationResult.model_validate(result)

        if result.recommended_department not in VALID_DEPARTMENTS:
            raise ValueError(
                f"Invalid department returned: "
                f"{result.recommended_department}"
            )

        if result.confidence not in VALID_CONFIDENCE_LEVELS:
            raise ValueError("Invalid classification confidence.")

        for department in result.alternative_departments:
            if department not in VALID_DEPARTMENTS:
                raise ValueError(
                    f"Invalid alternative department: {department}"
                )

        return {
            "classification_allowed": True,
            **result.model_dump(),
        }

    except Exception as exc:
        logger.exception("Department classification failed.")

        raise RuntimeError(
            "Department classification failed. "
            "Check Ollama and the configured model."
        ) from exc
