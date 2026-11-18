
import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from pydantic import BaseModel, ConfigDict, Field

from config.settings import settings


logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# 1. PATIENT INTAKE SYSTEM PROMPT
# ---------------------------------------------------------

PATIENT_INTAKE_PROMPT = """
You are a professional Patient Intake Agent in a healthcare
appointment system.

Your responsibility is to collect and organize information
provided by the patient.

IMPORTANT EXTRACTION RULES:

1. CHIEF COMPLAINT
   - Identify the patient's main health concern.
   - Keep it short and clear.
   - Example: "headache", not "mild headache for two days".

2. SYMPTOMS
   - Extract every symptom explicitly reported by the patient.
   - Use a list of simple symptom names.
   - Example: "I have a headache and fever."
     symptoms = ["headache", "fever"]

3. DURATION
   - Extract how long the symptoms have been present.
   - Preserve the patient's stated duration.
   - Example: "for two days" -> "two days".
   - If not mentioned, use null.

4. SEVERITY
   - Extract the severity explicitly reported by the patient.
   - Allowed values: mild, moderate, severe, unknown.
   - Example: "mild headache" -> "mild".
   - Do not guess severity.

5. ASSOCIATED SYMPTOMS
   - Record additional symptoms separately when appropriate.
   - Do not invent symptoms.
   - Use an empty list when none are reported.

6. RELEVANT CONTEXT
   - Include relevant information explicitly provided by
     the patient, such as medical history or medication.
   - Do not invent information.

7. MISSING INFORMATION
   - Identify important information not yet collected.
   - Consider duration, severity, associated symptoms and
     relevant medical context.
   - Do not include information already provided.

8. FOLLOW-UP QUESTION
   - Ask only ONE relevant question at a time.
   - Prefer asking about important missing information.
   - Do not ask questions that have already been answered.
   - If sufficient information is collected, use null.

GENERAL RULES:
- Consider the complete conversation history.
- Never invent patient information.
- Do not provide a medical diagnosis.
- Do not prescribe medication or treatment.
- Do not independently decide whether an emergency exists.
- Do not mention the current date or time.
- Keep the output accurate and concise.
"""


# ---------------------------------------------------------
# 2. STRUCTURED OUTPUT MODEL
# ---------------------------------------------------------

class PatientIntakeResult(BaseModel):
    """Structured information extracted from patient messages."""

    model_config = ConfigDict(extra="forbid")

    chief_complaint: str = Field(
        description="The patient's main health concern."
    )

    symptoms: list[str] = Field(
        default_factory=list,
        description="All symptoms explicitly reported by the patient."
    )

    duration: str | None = Field(
        default=None,
        description="How long the symptoms have been present."
    )

    severity: str = Field(
        default="unknown",
        description="One of: mild, moderate, severe, unknown."
    )

    associated_symptoms: list[str] = Field(
        default_factory=list,
        description="Additional symptoms reported by the patient."
    )

    relevant_context: list[str] = Field(
        default_factory=list,
        description="Relevant medical history or context provided."
    )

    missing_information: list[str] = Field(
        default_factory=list,
        description="Important information not yet collected."
    )

    follow_up_question: str | None = Field(
        default=None,
        description="One relevant follow-up question for the patient."
    )


# ---------------------------------------------------------
# 3. PATIENT INTAKE AGENT
# ---------------------------------------------------------

def run_patient_intake(
    patient_message: str,
    conversation_history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Extract structured patient information using local Ollama.

    Args:
        patient_message: Latest message from the patient.
        conversation_history: Previous user and assistant messages.

    Returns:
        Dictionary containing structured patient information.
    """

    if not isinstance(patient_message, str) or not patient_message.strip():
        raise ValueError("Patient message cannot be empty.")

    if conversation_history is None:
        conversation_history = []

    if not isinstance(conversation_history, list):
        raise ValueError("Conversation history must be a list.")

    history_messages = []

    for item in conversation_history[-20:]:

        if not isinstance(item, dict):
            raise ValueError("Each history item must be a dictionary.")

        role = item.get("role")
        content = item.get("content")

        if not isinstance(content, str) or not content.strip():
            raise ValueError("History content must be non-empty text.")

        if role in ("user", "human"):
            history_messages.append(HumanMessage(content=content))

        elif role in ("assistant", "ai"):
            history_messages.append(AIMessage(content=content))

        else:
            raise ValueError(f"Unsupported conversation role: {role}")

    # Initialize local Ollama model.
    model = ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=0,
    )

    # Require structured Pydantic output.
    structured_model = model.with_structured_output(
        PatientIntakeResult
    )

    messages = [
        SystemMessage(content=PATIENT_INTAKE_PROMPT),
        *history_messages,
        HumanMessage(content=patient_message.strip()),
    ]

    try:
        result = structured_model.invoke(messages)

        if not isinstance(result, PatientIntakeResult):
            result = PatientIntakeResult.model_validate(result)

        # Validate severity before returning.
        if result.severity not in {
            "mild",
            "moderate",
            "severe",
            "unknown",
        }:
            result.severity = "unknown"

        return result.model_dump()

    except Exception as exc:
        logger.exception("Patient intake agent execution failed.")

        raise RuntimeError(
            "Patient intake failed. Check Ollama and the configured model."
        ) from exc
