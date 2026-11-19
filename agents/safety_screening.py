
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from pydantic import BaseModel, ConfigDict, Field

from config.settings import settings
from guardrails.emergency_screening import screen_emergency_symptoms


logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# 1. SAFETY SCREENING SYSTEM PROMPT
# ---------------------------------------------------------

SAFETY_SCREENING_PROMPT = """
You are a Safety Screening Agent in a healthcare appointment system.

Your responsibility is to review patient-reported symptoms and
identify whether further safety attention may be required.

IMPORTANT RULES:

1. Review the patient's reported symptoms and available context.
2. Do not diagnose medical conditions.
3. Do not prescribe medication or treatment.
4. Do not claim that a patient is medically safe.
5. Never dismiss a patient's concern.
6. Never override a deterministic emergency warning.
7. If emergency indicators are detected by the safety rules,
   preserve the emergency status.
8. Explain the screening result in clear, simple language.
9. Do not invent symptoms or medical history.
10. Do not use the current date or time.

Your output must distinguish between:
- Emergency indicators detected.
- No emergency indicators detected by the configured rules.

IMPORTANT:
A result with no detected emergency indicators does NOT prove
that the patient is safe or rule out a medical emergency.
"""


# ---------------------------------------------------------
# 2. STRUCTURED OUTPUT MODEL
# ---------------------------------------------------------

class SafetyScreeningResult(BaseModel):
    """Structured safety screening result."""

    model_config = ConfigDict(extra="forbid")

    emergency_detected: bool = Field(
        description="Whether emergency warning signs were detected."
    )

    severity: str = Field(
        description="Screening status: emergency or no_detected_emergency."
    )

    matched_categories: list[str] = Field(
        default_factory=list,
        description="Emergency warning categories detected by deterministic rules."
    )

    requires_immediate_action: bool = Field(
        description="Whether the emergency pathway must be activated."
    )

    explanation: str = Field(
        description="Brief explanation of the screening result."
    )


# ---------------------------------------------------------
# 3. SAFETY SCREENING AGENT
# ---------------------------------------------------------

def run_safety_screening(
    patient_message: str,
    patient_intake: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Screen patient-reported information for predefined emergency signs.

    Deterministic screening takes priority over LLM interpretation.

    Args:
        patient_message: Latest patient message.
        patient_intake: Previously collected patient information.

    Returns:
        Structured safety screening result.
    """

    if not isinstance(patient_message, str) or not patient_message.strip():
        raise ValueError("Patient message cannot be empty.")

    if patient_intake is None:
        patient_intake = {}

    if not isinstance(patient_intake, dict):
        raise ValueError("Patient intake must be a dictionary.")

    # -----------------------------------------------------
    # STEP 1: DETERMINISTIC EMERGENCY SCREENING
    # -----------------------------------------------------

    screening_text = patient_message

    # Include previously reported symptoms and context.
    for field in (
        "chief_complaint",
        "symptoms",
        "associated_symptoms",
        "relevant_context",
    ):
        value = patient_intake.get(field)

        if isinstance(value, str):
            screening_text += " " + value

        elif isinstance(value, list):
            screening_text += " " + " ".join(
                str(item) for item in value
            )

    rule_result = screen_emergency_symptoms(screening_text)

    # -----------------------------------------------------
    # STEP 2: EMERGENCY OVERRIDE
    # -----------------------------------------------------

    if rule_result.get("emergency_detected") is True:

        return {
            "emergency_detected": True,
            "severity": "emergency",
            "matched_categories": rule_result.get(
                "matched_categories", []
            ),
            "requires_immediate_action": True,
            "explanation": (
                "Potential emergency warning signs were detected. "
                "Stop routine appointment intake and direct the "
                "patient to immediate emergency medical assistance."
            ),
        }

    # -----------------------------------------------------
    # STEP 3: LLM SCREENING FOR ADDITIONAL CONTEXT
    # -----------------------------------------------------

    model = ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=0,
    )

    structured_model = model.with_structured_output(
        SafetyScreeningResult
    )

    context = f"""
    LATEST PATIENT MESSAGE:
    {patient_message}

    PREVIOUSLY COLLECTED PATIENT INFORMATION:
    {patient_intake}

    DETERMINISTIC SCREENING:
    No emergency indicators were detected by the configured rules.

    Review the information and explain the screening result.
    Do not override the deterministic screening.
    """

    messages = [
        SystemMessage(content=SAFETY_SCREENING_PROMPT),
        HumanMessage(content=context),
    ]

    try:
        result = structured_model.invoke(messages)

        if not isinstance(result, SafetyScreeningResult):
            result = SafetyScreeningResult.model_validate(result)

        # The LLM cannot independently declare an emergency
        # or claim that the patient is medically safe.
        return {
            "emergency_detected": False,
            "severity": "no_detected_emergency",
            "matched_categories": rule_result.get(
                "matched_categories", []
            ),
            "requires_immediate_action": False,
            "explanation": result.explanation,
        }

    except Exception as exc:
        logger.exception("Safety screening agent failed.")

        # Fail closed: do not continue normal intake when
        # screening cannot be completed.
        raise RuntimeError(
            "Safety screening failed. Routine appointment intake "
            "must not continue until screening succeeds."
        ) from exc
