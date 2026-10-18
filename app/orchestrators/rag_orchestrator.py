"""Fachada de orquestación para la protección del contexto recuperado."""
from app.schemas.rag import RAGChunk, RAGEvaluationResponse
from app.services.rag_context_service import RAGContextService


class RAGOrchestrator:
    def __init__(self, context_service: RAGContextService | None = None):
        self.context_service = context_service or RAGContextService()

    async def inspect(self, request_id: str, chunks: list[RAGChunk]) -> RAGEvaluationResponse:
        return await self.context_service.evaluate(request_id=request_id, chunks=chunks)
