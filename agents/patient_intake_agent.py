"""Patient intake agent powered by the locally hosted Ollama model."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from pydantic import BaseModel, ConfigDict, Field

from config.prompts import PATIENT_INTAKE_PROMPT
from config.settings import settings


class PatientIntakeResult(BaseModel):
    """Validated information extracted from a patient conversation."""

    model_config = ConfigDict(extra="forbid")

    chief_complaint: str = Field(
        description="The patient's main health concern, using their own wording."
    )
    symptoms: list[str] = Field(
        default_factory=list,
        description="Symptoms explicitly reported by the patient."
    )
    duration: str | None = Field(
        default=None,
        description="How long the symptoms have been present, if stated."
    )
    severity: str = Field(
        default="unknown",
        description="Patient-reported severity: mild, moderate, severe, or unknown."
    )
    associated_symptoms: list[str] = Field(
        default_factory=list,
        description="Other symptoms explicitly reported by the patient."
    )
    relevant_context: list[str] = Field(
        default_factory=list,
        description="Relevant context explicitly supplied by the patient."
    )
    missing_information: list[str] = Field(
        default_factory=list,
        description="Important intake details that remain unknown."
    )
    follow_up_question: str | None = Field(
        default=None,
        description="One concise question to clarify the most important missing detail."
    )


def _validate_history(conversation_history: list[dict[str, Any]]) -> list:
    """Convert supported history entries into LangChain messages."""

    converted = []

    for index, item in enumerate(conversation_history):
        if not isinstance(item, dict):
            raise ValueError(f"Conversation history item {index} must be a dictionary.")

        role = item.get("role")
        content = item.get("content")

        if not isinstance(content, str) or not content.strip():
            raise ValueError(
                f"Conversation history item {index} must contain non-empty text."
            )

        if role in {"user", "human"}:
            converted.append(HumanMessage(content=content))
        elif role in {"assistant", "ai"}:
            converted.append(AIMessage(content=content))
        else:
            raise ValueError(
                f"Unsupported role in conversation history item {index}: {role!r}"
            )

    # Bound the context so old conversations cannot grow the prompt indefinitely.
    return converted[-20:]


def run_patient_intake(
    patient_message: str,
    conversation_history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Extract structured intake information from the latest patient message.

    This function does not diagnose, prescribe, classify a department,
    or perform emergency screening. Those responsibilities belong to
    separate workflow components.
    """

    if not isinstance(patient_message, str) or not patient_message.strip():
        raise ValueError("A non-empty patient message is required.")

    if conversation_history is None:
        conversation_history = []

    if not isinstance(conversation_history, list):
        raise ValueError("Conversation history must be a list.")

    history_messages = _validate_history(conversation_history)

    model = ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=settings.ollama_temperature,
    )

    structured_model = model.with_structured_output(PatientIntakeResult)

    messages = [
        SystemMessage(
            content=(
                PATIENT_INTAKE_PROMPT
                + "\n\n"
                + "Return only fields supported by the conversation. "
                + "Use null or empty lists for unknown information. "
                + "Ask at most one follow-up question. "
                + "Do not diagnose or recommend treatment."
            )
        ),
        *history_messages,
        HumanMessage(content=patient_message.strip()),
    ]

    try:
        result = structured_model.invoke(messages)
        validated = (
            result
            if isinstance(result, PatientIntakeResult)
            else PatientIntakeResult.model_validate(result)
        )
        return validated.model_dump()
    except Exception as exc:
        raise RuntimeError(
            "Patient intake processing failed. Verify that Ollama is running, "
            "the configured model is installed, and the model supports "
            "structured output."
        ) from exc
