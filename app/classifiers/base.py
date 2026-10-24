"""Contrato común de los clasificadores de prompt injection (fase 2)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ClassificationResult:
    # Probabilidad de que el texto sea una inyección/jailbreak (máximo entre fragmentos).
    score_injection: float
    model_id: str
    chunk_count: int = 1
    latency_ms: float = 0.0


class BaseInjectionClassifier:
    model_id = "base"
    enabled = True

    def classify(self, text: str) -> ClassificationResult:
        raise NotImplementedError


class NullClassifier(BaseInjectionClassifier):
    """Clasificador desactivado: conserva el comportamiento de la fase 1."""

    model_id = "none"
    enabled = False

    def classify(self, text: str) -> ClassificationResult:
        return ClassificationResult(score_injection=0.0, model_id=self.model_id, chunk_count=0)
