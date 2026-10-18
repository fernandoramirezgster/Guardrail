"""Inspección de fragmentos recuperados antes de incorporarlos al contexto del LLM."""
from time import perf_counter
import json

from app.schemas.guardrail import GuardrailDecision
from app.schemas.rag import RAGChunk, RAGChunkResult, RAGEvaluationResponse
from app.services.input_guard_service import InputGuardService


class RAGContextService:
    MAX_CONTEXT_LENGTH = 100_000

    def __init__(self, input_guard_service=None):
        self.input_guard_service = input_guard_service or InputGuardService()

    async def evaluate(self, request_id: str, chunks: list[RAGChunk]) -> RAGEvaluationResponse:
        start = perf_counter()
        results: list[RAGChunkResult] = []
        safe_context_parts: list[str] = []
        decisions: list[GuardrailDecision] = []

        for chunk in chunks:
            evaluation = await self.input_guard_service.evaluate(
                request_id=request_id,
                prompt=chunk.content,
            )
            decisions.append(evaluation.decision)
            result = RAGChunkResult(
                source_id=chunk.source_id,
                document_id=chunk.document_id,
                chunk_id=chunk.chunk_id,
                metadata=chunk.metadata,
                decision=evaluation.decision,
                processed_content=evaluation.processed_content,
                findings=evaluation.findings,
                reasons=evaluation.reasons,
            )
            results.append(result)

            if evaluation.decision in (GuardrailDecision.ALLOW, GuardrailDecision.MASK):
                content = evaluation.processed_content
                if content is None or not content.strip():
                    # Defensa adicional: nunca recuperar el contenido original.
                    result.decision = GuardrailDecision.BLOCK
                    result.processed_content = None
                    result.reasons = ["El fragmento procesado no contiene contenido válido."]
                    decisions[-1] = GuardrailDecision.BLOCK
                    continue
                # El contenido se delimita como dato no confiable y se acompaña
                # de procedencia para evitar mezclarlo con instrucciones del sistema.
                safe_context_parts.append({
                    "source_id": chunk.source_id,
                    "document_id": chunk.document_id,
                    "chunk_id": chunk.chunk_id,
                    "content": content,
                    "trust": "untrusted_retrieved_data",
                })

        # El contexto completo se retiene si cualquier fragmento requiere revisión
        # o bloqueo; no se envía un subconjunto silencioso al modelo.
        if GuardrailDecision.BLOCK in decisions:
            overall = GuardrailDecision.BLOCK
        elif GuardrailDecision.REVIEW in decisions:
            overall = GuardrailDecision.REVIEW
        elif GuardrailDecision.MASK in decisions:
            overall = GuardrailDecision.MASK
        else:
            overall = GuardrailDecision.ALLOW

        context = json.dumps(safe_context_parts, ensure_ascii=False) if overall in (
            GuardrailDecision.ALLOW, GuardrailDecision.MASK
        ) else None
        if context is not None and len(context) > self.MAX_CONTEXT_LENGTH:
            overall = GuardrailDecision.BLOCK
            context = None
            reasons = ["El contexto procesado supera la longitud máxima permitida."]
        else:
            reasons = [f"Fragmentos evaluados: {len(results)}."]
            if overall == GuardrailDecision.BLOCK:
                reasons.append("Al menos un fragmento fue bloqueado; se retuvo todo el contexto.")
            elif overall == GuardrailDecision.REVIEW:
                reasons.append("Al menos un fragmento requiere revisión; se retuvo todo el contexto.")
            elif overall == GuardrailDecision.MASK:
                reasons.append("Se enmascararon datos sensibles antes de construir el contexto.")
            else:
                reasons.append("Todos los fragmentos fueron autorizados.")

        return RAGEvaluationResponse(
            request_id=request_id,
            decision=overall,
            chunks=results,
            context_for_llm=context,
            reasons=reasons,
            processing_time_ms=(perf_counter() - start) * 1000,
        )

    @staticmethod
    def _escape(value: str) -> str:
        return value.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
