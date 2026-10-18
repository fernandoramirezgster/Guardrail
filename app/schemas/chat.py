from pydantic import BaseModel, Field

from app.schemas.guardrail import GuardrailDecision, InputEvaluationRequest
from app.schemas.rag import RAGChunk


class SecureChatRequest(InputEvaluationRequest):
    context_chunks: list[RAGChunk] | None = Field(default=None, max_length=50)


class SecureChatResponse(BaseModel):
    request_id: str
    input_decision: GuardrailDecision
    output_decision: GuardrailDecision | None = None
    context_decision: GuardrailDecision | None = None
    model_called: bool
    provider: str
    answer: str | None = None
    reasons: list[str] = Field(default_factory=list)

