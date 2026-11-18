
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Validation schema for new user registration."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    """Validation schema for user login."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    """Public user information returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    role: Literal["patient", "doctor", "admin"]
    is_active: bool
    created_at: datetime
