import re
from .base import BaseDetector, Detection


class SecretsDetector(BaseDetector):
    name = "secrets"

    PATTERNS = [
        ("openai_key", r"\bsk-[A-Za-z0-9_-]{20,}\b"),
        ("github_token", r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
        ("aws_access_key", r"\bAKIA[0-9A-Z]{16}\b"),
        ("jwt", r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
        ("private_key", r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        ("password_assignment", r"(?i)\b(?:password|passwd|pwd|secret|api[_-]?key|token)\s*[:=]\s*['\"]?[^\s'\"]{8,}"),
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
        sanitized = text
        for item in reversed(matches):
            start, end = item["start"], item["end"]
            sanitized = sanitized[:start] + f"[REDACTED:{item['type']}]" + sanitized[end:]

        return Detection(
            detected=detected,
            detector=self.name,
            type="secret" if detected else "",
            confidence=0.95 if detected else 0.0,
            matches=matches,
            sanitized=sanitized,
        )
