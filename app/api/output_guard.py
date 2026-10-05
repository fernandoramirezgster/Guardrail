from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_output_guard_service
from app.schemas.guardrail import GuardrailEvaluationResponse, OutputEvaluationRequest

router = APIRouter(prefix="/api/v1/guardrails/output", tags=["Salida"])


@router.post("/evaluate", response_model=GuardrailEvaluationResponse)
async def evaluate_output(request: OutputEvaluationRequest, service=Depends(get_output_guard_service)):
    try:
        return await service.evaluate(request_id=request.request_id, model_output=request.model_output)
    except Exception:
        raise HTTPException(status_code=503, detail="No fue posible evaluar la salida.") from None

