
from sqlalchemy import select

from database.connection import SessionLocal, init_db
from database.models import (
    Appointment,
    Conversation,
    ConversationMessage,
    Patient,
    User,
)
from database.repositories import (
    create_user,
    create_patient,
    create_conversation,
    add_conversation_message,
    get_user_by_email,
    get_patient_by_user_id,
    get_conversation_messages,
)


TEST_EMAIL = "database_test@example.com"


def cleanup_test_data(db, user):
    """Delete test records in foreign-key dependency order."""

    if user is None:
        return

    patient = get_patient_by_user_id(db, user.id)

    if patient is not None:
        conversations = db.scalars(
            select(Conversation).where(
                Conversation.patient_id == patient.id
            )
        ).all()

        for conversation in conversations:
            db.query(ConversationMessage).filter(
                ConversationMessage.conversation_id == conversation.id
            ).delete(synchronize_session=False)

        db.query(Conversation).filter(
            Conversation.patient_id == patient.id
        ).delete(synchronize_session=False)

        db.query(Appointment).filter(
            Appointment.patient_id == patient.id
        ).delete(synchronize_session=False)

        db.delete(patient)

    db.delete(user)
    db.commit()


def test_database_operations():
    init_db()
    db = SessionLocal()

    try:
        # Clean up data from an earlier test run.
        existing_user = get_user_by_email(db, TEST_EMAIL)

        if existing_user:
            cleanup_test_data(db, existing_user)

        # 1. Create a synthetic user.
        user = create_user(
            db=db,
            email=TEST_EMAIL,
            password_hash="test_hash_not_a_real_password",
        )

        print("User created:", user.email)

        # 2. Create a patient profile.
        patient = create_patient(
            db=db,
            user_id=user.id,
            full_name="Test Patient",
            phone="9999999999",
        )

        print("Patient created:", patient.full_name)

        # 3. Retrieve the patient.
        retrieved_patient = get_patient_by_user_id(db, user.id)

        assert retrieved_patient is not None
        assert retrieved_patient.id == patient.id

        print("Patient retrieval: Successful")

        # 4. Create a conversation.
        conversation = create_conversation(
            db=db,
            patient_id=patient.id,
        )

        print("Conversation created:", conversation.id)

        # 5. Save a message.
        add_conversation_message(
            db=db,
            conversation_id=conversation.id,
            role="user",
            content="I have a mild headache.",
        )

        # 6. Retrieve messages.
        messages = get_conversation_messages(
            db=db,
            conversation_id=conversation.id,
        )

        assert len(messages) == 1
        assert messages[0].content == "I have a mild headache."

        print("Message storage and retrieval: Successful")

        print("\nAll database operations passed!")

        # 7. Clean up synthetic test records.
        cleanup_test_data(db, user)

        print("Test data cleaned up successfully.")

    finally:
        db.close()


if __name__ == "__main__":
    test_database_operations()
