from pydantic import BaseModel, Field

from app.schemas.guardrail import GuardrailDecision, InputEvaluationRequest


class SecureChatRequest(InputEvaluationRequest):
    pass


class SecureChatResponse(BaseModel):
    request_id: str
    input_decision: GuardrailDecision
    output_decision: GuardrailDecision | None = None
    model_called: bool
    provider: str
    answer: str | None = None
    reasons: list[str] = Field(default_factory=list)

