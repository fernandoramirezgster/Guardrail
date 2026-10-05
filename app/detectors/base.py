from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Detection:
    detected: bool
    detector: str
    type: str
    confidence: float = 0.0
    matches: List[Dict[str, Any]] = field(default_factory=list)
    sanitized: str = ""


class BaseDetector:
    name = "base"

    def detect(self, text: str) -> Detection:
        raise NotImplementedError
