"""Controles mínimos de salida para cerrar la fase 1; no evalúa RAG."""
import re
from time import perf_counter

from app.schemas.guardrail import Finding, GuardrailDecision, GuardrailEvaluationResponse
from app.orchestrators.decision_orchestrator import DecisionOrchestrator


class OutputGuardService:
    EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
    SECRET = re.compile(r"\bsk-[A-Za-z0-9_-]{10,}\b", re.IGNORECASE)
    CREDENTIAL = re.compile(r"\b(?:password|contraseña|api[_\-\s]?key|token)\s*[:=]\s*[^\s,;]+", re.IGNORECASE)

    def __init__(self, policy_engine=None):
        self.policy_engine = policy_engine or DecisionOrchestrator()

    async def evaluate(self, request_id: str, model_output: str) -> GuardrailEvaluationResponse:
        start = perf_counter()
        findings = []
        secret = bool(self.SECRET.search(model_output) or self.CREDENTIAL.search(model_output))
        email = bool(self.EMAIL.search(model_output))
        if secret:
            findings.append(Finding(
                category="credential", severity="critical",
                description="Se detectó un posible secreto o una credencial.",
            ))
        if email:
            findings.append(Finding(
                category="email", severity="medium",
                description="Se detectó una dirección de correo electrónico.",
            ))
        decision = self.policy_engine.decide(findings)
        if decision in (GuardrailDecision.BLOCK, GuardrailDecision.REVIEW):
            content = None
        elif decision == GuardrailDecision.MASK:
            content = self.EMAIL.sub("[EMAIL]", model_output)
        else:
            content = model_output
        return GuardrailEvaluationResponse(
            request_id=request_id, decision=decision, processed_content=content,
            findings=findings,
            reasons=[f.description for f in findings] or ["Sin coincidencias con las reglas básicas de salida."],
            processing_time_ms=(perf_counter() - start) * 1000,
        )

