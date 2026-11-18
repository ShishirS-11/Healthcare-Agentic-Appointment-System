
from typing import Any

from pydantic import BaseModel, Field


class APIResponse(BaseModel):
    """Standard response format for successful API operations."""

    success: bool = True
    message: str
    data: Any | None = None


class ErrorResponse(BaseModel):
    """Standard response format for API errors."""

    success: bool = False
    message: str
    error_code: str | None = None
    details: Any | None = None


class HealthResponse(BaseModel):
    """Application health-check response."""

    status: str
    application: str
    version: str
    database: str
    llm: str


class AgentResponse(BaseModel):
    """Standardized response from an individual agent."""

    agent_name: str
    status: str
    message: str
    data: dict[str, Any] = Field(default_factory=dict)
