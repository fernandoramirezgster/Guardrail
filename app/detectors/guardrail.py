from typing import List
from .base import Detection
from .injection import InjectionDetector
from .pii import PIIDetector
from .secrets import SecretsDetector


class Guardrail:
    def __init__(self, detectors=None):
        self.detectors = detectors or [
            InjectionDetector(),
            PIIDetector(),
            SecretsDetector(),
        ]

    def detect(self, text: str) -> List[Detection]:
        if not isinstance(text, str):
            raise TypeError("Guardrail input must be a string")

        return [detector.detect(text) for detector in self.detectors]

    def is_safe(self, text: str) -> bool:
        return not any(result.detected for result in self.detect(text))

    def sanitize(self, text: str) -> str:
        result = text
        for detector in self.detectors:
            detection = detector.detect(result)
            if detection.detected:
                result = detection.sanitized
        return result
