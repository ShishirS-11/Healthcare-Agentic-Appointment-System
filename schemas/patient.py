
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class PatientCreate(BaseModel):
    """Validation schema for creating a patient profile."""

    full_name: str = Field(min_length=2, max_length=150)
    date_of_birth: date | None = None
    gender: str | None = Field(default=None, max_length=30)
    phone: str | None = Field(default=None, min_length=10, max_length=20)


class PatientUpdate(BaseModel):
    """Validation schema for updating patient profile information."""

    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    date_of_birth: date | None = None
    gender: str | None = Field(default=None, max_length=30)
    phone: str | None = Field(default=None, min_length=10, max_length=20)


class PatientResponse(BaseModel):
    """Patient information returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    full_name: str
    date_of_birth: date | None
    gender: str | None
    phone: str | None
    created_at: datetime
