
import json
from datetime import datetime
from typing import Annotated, Literal

from langchain_core.tools import InjectedToolArg, tool
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from database.connection import SessionLocal
from database.models import Conversation, ConversationMessage


@tool
def manage_conversation(
    action: Literal[
        "create",
        "get",
        "add_assistant_message",
    ],
    patient_id: Annotated[str, InjectedToolArg],
    conversation_id: str = "",
    content: str = "",
) -> str:
    """
    Manage conversations belonging to the authenticated patient.

    Supported actions:
    - create: Create a new conversation.
    - get: Retrieve a conversation and its message history.
    - add_assistant_message: Store an AI assistant response.

    The patient_id is injected by the trusted backend.
    The tool cannot access another patient's conversations.

    Patient messages must be stored by the backend, not by this tool.
    """

    patient_id = patient_id.strip()
    conversation_id = conversation_id.strip()
    content = content.strip()

    if not patient_id:
        return json.dumps({
            "success": False,
            "error": "Authenticated patient information is required.",
        })

    if action == "add_assistant_message" and not content:
        return json.dumps({
            "success": False,
            "error": "Assistant message content cannot be empty.",
        })

    if len(content) > 10000:
        return json.dumps({
            "success": False,
            "error": "Message content exceeds the 10000-character limit.",
        })

    try:
        with SessionLocal() as db:

            # ACTION 1: Create a new conversation.
            if action == "create":

                conversation = Conversation(
                    patient_id=patient_id,
                    status="active",
                )

                db.add(conversation)
                db.commit()
                db.refresh(conversation)

                return json.dumps({
                    "success": True,
                    "action": "create",
                    "conversation": {
                        "conversation_id": conversation.id,
                        "patient_id": conversation.patient_id,
                        "status": conversation.status,
                        "created_at": (
                            conversation.created_at.isoformat()
                            if conversation.created_at
                            else None
                        ),
                    },
                }, indent=2)

            # Other actions require a conversation ID.
            if not conversation_id:
                return json.dumps({
                    "success": False,
                    "error": "Conversation ID is required.",
                })

            # Verify that the conversation belongs to this patient.
            conversation = db.scalar(
                select(Conversation).where(
                    Conversation.id == conversation_id,
                    Conversation.patient_id == patient_id,
                )
            )

            if conversation is None:
                return json.dumps({
                    "success": False,
                    "error": "Conversation not found.",
                })

            # ACTION 2: Retrieve conversation history.
            if action == "get":

                messages = db.scalars(
                    select(ConversationMessage)
                    .where(
                        ConversationMessage.conversation_id
                        == conversation_id
                    )
                    .order_by(
                        ConversationMessage.created_at.asc()
                    )
                ).all()

                return json.dumps({
                    "success": True,
                    "action": "get",
                    "conversation": {
                        "conversation_id": conversation.id,
                        "patient_id": conversation.patient_id,
                        "status": conversation.status,
                        "summary": conversation.summary,
                        "created_at": (
                            conversation.created_at.isoformat()
                            if conversation.created_at
                            else None
                        ),
                        "updated_at": (
                            conversation.updated_at.isoformat()
                            if conversation.updated_at
                            else None
                        ),
                    },
                    "message_count": len(messages),
                    "messages": [
                        {
                            "message_id": message.id,
                            "role": message.role,
                            "content": message.content,
                            "created_at": (
                                message.created_at.isoformat()
                                if message.created_at
                                else None
                            ),
                        }
                        for message in messages
                    ],
                }, indent=2)

            # ACTION 3: Save an assistant response.
            if action == "add_assistant_message":

                if conversation.status != "active":
                    return json.dumps({
                        "success": False,
                        "error": "Cannot add messages to an inactive conversation.",
                    })

                message = ConversationMessage(
                    conversation_id=conversation.id,
                    role="assistant",
                    content=content,
                )

                conversation.updated_at = datetime.now()

                db.add(message)
                db.commit()
                db.refresh(message)

                return json.dumps({
                    "success": True,
                    "action": "add_assistant_message",
                    "message": {
                        "message_id": message.id,
                        "conversation_id": message.conversation_id,
                        "role": message.role,
                        "content": message.content,
                        "created_at": (
                            message.created_at.isoformat()
                            if message.created_at
                            else None
                        ),
                    },
                }, indent=2)

            return json.dumps({
                "success": False,
                "error": "Unsupported conversation action.",
            })

    except SQLAlchemyError:
        return json.dumps({
            "success": False,
            "error": "Unable to manage the patient conversation.",
        })
