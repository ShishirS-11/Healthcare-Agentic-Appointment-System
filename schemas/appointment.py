
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


AppointmentStatus = Literal[
    "pending_confirmation",
    "confirmed",
    "cancelled",
    "completed",
]


class AppointmentCreate(BaseModel):
    """Validates a new appointment request."""

    department: str = Field(min_length=2, max_length=100)
    doctor_name: str = Field(min_length=2, max_length=150)
    appointment_at: datetime
    booking_reference: str = Field(min_length=5, max_length=50)


class AppointmentConfirmation(BaseModel):
    """Validates the patient's explicit booking confirmation."""

    confirmed: bool


class AppointmentResponse(BaseModel):
    """Defines appointment information returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    department: str
    doctor_name: str
    appointment_at: datetime
    status: AppointmentStatus
    patient_confirmed: bool
    booking_reference: str
    created_at: datetime
