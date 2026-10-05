import re
from .base import BaseDetector, Detection


class InjectionDetector(BaseDetector):
    name = "injection"

    PATTERNS = [
         ( "sql_injection", r"(?i)(?:union\s+select|select\s+.+\s+from|insert\s+into|drop\s+table|delete\s+from|update\s+.+\s+set)", ),
         ( "sql_comment", r"(?i)(?:/\*|\*/|(?:^|\s)--(?:\s|$)|;\s*(?:drop|delete|insert|update|select)\b)",),
         ( "command_injection", r"(?i)(?:;|&&|\|\||\|)\s*(?:sh|bash|cmd|powershell|curl|wget|nc|rm|chmod|chown|python|python3|perl|ruby)\b",), 
         ( "prompt_injection", r"(?i)(?:ignore\s+(?:all|any|previous|prior)\s+instructions|system\s+prompt|reveal\s+(?:your|the)\s+(?:system\s+)?prompt|bypass\s+(?:the\s+)?guardrail)", ),
               ]

    def detect(self, text: str) -> Detection:
        matches = []
        for kind, pattern in self.PATTERNS:
            for match in re.finditer(pattern, text):
                matches.append({
                    "type": kind,
                    "value": match.group(0),
                    "start": match.start(),
                    "end": match.end(),
                })

        detected = bool(matches)
        confidence = min(1.0, 0.75 + 0.05 * len(matches)) if detected else 0.0

        return Detection(
            detected=detected,
            detector=self.name,
            type="injection" if detected else "",
            confidence=confidence,
            matches=matches,
            sanitized=text if not detected else "[BLOCKED]",
        )
