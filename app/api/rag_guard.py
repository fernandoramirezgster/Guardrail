from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_rag_orchestrator
from app.schemas.rag import RAGEvaluationRequest, RAGEvaluationResponse

router = APIRouter(prefix="/api/v1/guardrails/rag", tags=["Contexto RAG"])


@router.post("/evaluate", response_model=RAGEvaluationResponse)
async def evaluate_rag_context(
    request: RAGEvaluationRequest,
    orchestrator=Depends(get_rag_orchestrator),
):
    try:
        return await orchestrator.inspect(request_id=request.request_id, chunks=request.chunks)
    except Exception:
        # Falla cerrada y sin reflejar texto recuperado ni detalles internos.
        raise HTTPException(
            status_code=503,
            detail="No fue posible inspeccionar el contexto RAG.",
        ) from None
