from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_secure_chat_service
from app.schemas.chat import SecureChatRequest, SecureChatResponse

router = APIRouter(prefix="/api/v1/chat", tags=["Chat protegido"])


@router.post("", response_model=SecureChatResponse)
async def chat(request: SecureChatRequest, service=Depends(get_secure_chat_service)):
    try:
        return await service.execute(request_id=request.request_id, prompt=request.prompt)
    except Exception:
        # Falla cerrada: no entregar prompt, salida original ni error del proveedor.
        raise HTTPException(status_code=503, detail="El flujo protegido no pudo completarse.") from None

