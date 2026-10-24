from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_input_guard_service
from app.schemas.guardrail import GuardrailEvaluationResponse, InputEvaluationRequest
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/guardrails/input", tags=["Entrada"])



@router.post("/evaluate", response_model=GuardrailEvaluationResponse)
async def evaluate_input(request: InputEvaluationRequest, service=Depends(get_input_guard_service)):
    try:
        return await service.evaluate(
            request_id=request.request_id,
            prompt=request.prompt
        )

    except Exception as e:
        # Falla cerrada sin exponer detalles internos (modelo, rutas, texto).
        logger.error("Error en el guardrail de entrada: %s", type(e).__name__)
        raise HTTPException(
            status_code=503,
            detail="La evaluación de entrada no pudo completarse.",
        ) from None

