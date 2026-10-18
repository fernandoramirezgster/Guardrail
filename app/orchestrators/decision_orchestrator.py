"""Punto único de integración entre hallazgos y motor de políticas."""
from app.policies.engine import PolicyEngine
from app.schemas.guardrail import Finding, GuardrailDecision


class DecisionOrchestrator:
    def __init__(self, policy_engine: PolicyEngine | None = None):
        self.policy_engine = policy_engine or PolicyEngine()

    def decide(
        self,
        findings: list[Finding],
        *,
        pii_detected: bool = False,
        default: GuardrailDecision = GuardrailDecision.ALLOW,
    ) -> GuardrailDecision:
        return self.policy_engine.decide(
            findings,
            pii_detected=pii_detected,
            default=default,
        )
