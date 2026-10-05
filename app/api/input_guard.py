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
        print("====================================")
        print("ERROR EN GUARDRAIL:")
        print(type(e).__name__)
        print(str(e))
        print("====================================")

        raise HTTPException(
            status_code=503,
            detail=str(e)
        ) from None

