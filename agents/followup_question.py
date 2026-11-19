
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from pydantic import BaseModel, ConfigDict, Field

from config.settings import settings


# ---------------------------------------------------------
# 1. FOLLOW-UP QUESTION SYSTEM PROMPT
# ---------------------------------------------------------

FOLLOWUP_QUESTION_PROMPT = """
You are a Follow-up Question Agent in a healthcare
appointment system.

Your responsibility is to identify missing patient information
and ask the most relevant next question.

RULES:

1. Review the complete patient intake information.
2. Identify which important details are still missing.
3. Ask only ONE question at a time.
4. Never repeat a question that has already been answered.
5. Consider previous questions and patient responses.
6. Prioritize information relevant to understanding the complaint.
7. Do not assume or invent patient information.
8. If the patient has already provided sufficient information,
   do not ask unnecessary questions.
9. Do not diagnose medical conditions.
10. Do not prescribe medication or treatment.
11. Do not independently determine whether the patient has
    an emergency. Emergency screening is handled separately.
12. Do not ask about information that is already known.

QUESTION PRIORITY:

- Missing symptom duration.
- Missing symptom severity.
- Missing associated symptoms.
- Relevant medical history, if necessary.
- Other relevant context, if necessary.

IMPORTANT:
- Ask one clear, simple question.
- Do not combine multiple unrelated questions.
- If no further information is required, set should_ask_question
  to false and question to null.
- Explain briefly why the question is useful.
"""


# ---------------------------------------------------------
# 2. STRUCTURED OUTPUT MODEL
# ---------------------------------------------------------

class FollowUpResult(BaseModel):
    """Structured result produced by the follow-up agent."""

    model_config = ConfigDict(extra="forbid")

    should_ask_question: bool = Field(
        description="Whether another patient question is needed."
    )

    question: str | None = Field(
        default=None,
        description="The single next question for the patient."
    )

    missing_information: list[str] = Field(
        default_factory=list,
        description="Important information that remains unknown."
    )

    reason: str = Field(
        description="Brief explanation of why this question is useful."
    )


# ---------------------------------------------------------
# 3. FOLLOW-UP QUESTION AGENT
# ---------------------------------------------------------

def generate_followup_question(
    patient_intake: dict[str, Any],
    conversation_history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Generate the next relevant question for a patient.

    Args:
        patient_intake: Structured information from Patient Intake Agent.
        conversation_history: Previous patient and assistant messages.

    Returns:
        Structured follow-up decision.
    """

    if not isinstance(patient_intake, dict) or not patient_intake:
        raise ValueError("Patient intake information cannot be empty.")

    if conversation_history is None:
        conversation_history = []

    if not isinstance(conversation_history, list):
        raise ValueError("Conversation history must be a list.")

    # Validate conversation history.
    history_text = []

    for item in conversation_history[-20:]:

        if not isinstance(item, dict):
            raise ValueError("Each history item must be a dictionary.")

        role = item.get("role")
        content = item.get("content")

        if role not in ("user", "human", "assistant", "ai"):
            raise ValueError(f"Unsupported conversation role: {role}")

        if not isinstance(content, str) or not content.strip():
            raise ValueError("History content must be non-empty text.")

        history_text.append(
            f"{role.upper()}: {content.strip()}"
        )

    # Initialize local Ollama model.
    model = ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=0,
    )

    structured_model = model.with_structured_output(
        FollowUpResult
    )

    # Provide patient intake and conversation history.
    patient_context = f"""
    PATIENT INTAKE INFORMATION:

    {patient_intake}

    PREVIOUS CONVERSATION:

    {chr(10).join(history_text) if history_text else "No previous conversation."}

    Based on this information, decide whether another question
    is necessary.

    Return exactly one question if required.
    """

    messages = [
        SystemMessage(content=FOLLOWUP_QUESTION_PROMPT),
        HumanMessage(content=patient_context),
    ]

    try:
        result = structured_model.invoke(messages)

        if not isinstance(result, FollowUpResult):
            result = FollowUpResult.model_validate(result)

        # Prevent an empty question from being returned.
        if result.should_ask_question:
            if not result.question or not result.question.strip():
                raise ValueError(
                    "The agent decided to ask a question but returned none."
                )
        else:
            result.question = None

        return result.model_dump()

    except Exception as exc:
        raise RuntimeError(
            "Follow-up question generation failed. "
            "Check Ollama and the configured model."
        ) from exc
