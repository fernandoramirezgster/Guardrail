"""Contratos comunes de la fase 1. No contienen el texto original evaluado."""
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GuardrailDecision(str, Enum):
    ALLOW = "ALLOW"
    MASK = "MASK"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"


class RequestBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=100)


class InputEvaluationRequest(RequestBase):
    prompt: str = Field(min_length=1, max_length=20_000)

    @field_validator("prompt")
    @classmethod
    def nonblank_prompt(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("El prompt no puede estar vacío.")
        return value


class OutputEvaluationRequest(RequestBase):
    model_output: str = Field(min_length=1, max_length=50_000)

    @field_validator("model_output")
    @classmethod
    def nonblank_output(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("La salida no puede estar vacía.")
        return value


class Finding(BaseModel):
    category: str
    severity: str
    description: str


class GuardrailEvaluationResponse(BaseModel):
    request_id: str
    decision: GuardrailDecision
    processed_content: str | None = None
    findings: list[Finding] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    processing_time_ms: float = Field(ge=0)

