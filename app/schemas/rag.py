"""Contratos de entrada y salida para inspección de contexto RAG."""
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.guardrail import Finding, GuardrailDecision, RequestBase


class RAGChunk(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: str = Field(min_length=1, max_length=200)
    document_id: str = Field(min_length=1, max_length=200)
    chunk_id: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=20_000)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("source_id", "document_id", "chunk_id")
    @classmethod
    def nonblank_identifier(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Los identificadores de procedencia no pueden estar vacíos.")
        return value

    @field_validator("content")
    @classmethod
    def nonblank_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("El contenido del fragmento no puede estar vacío.")
        return value


class RAGEvaluationRequest(RequestBase):
    chunks: list[RAGChunk] = Field(min_length=1, max_length=50)


class RAGChunkResult(BaseModel):
    source_id: str
    document_id: str
    chunk_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    decision: GuardrailDecision
    processed_content: str | None = None
    findings: list[Finding] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class RAGEvaluationResponse(BaseModel):
    request_id: str
    decision: GuardrailDecision
    chunks: list[RAGChunkResult]
    # Solo se llena si todos los fragmentos pueden utilizarse de forma segura.
    context_for_llm: str | None = None
    reasons: list[str] = Field(default_factory=list)
    processing_time_ms: float = Field(ge=0)
