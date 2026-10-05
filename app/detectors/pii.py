import re
from .base import BaseDetector, Detection


class PIIDetector(BaseDetector):
    name = "pii"

    # Mobile numbers in Colombia are 10 digits and start with 3.
    # Keep the phone rule more specific than the generic ID rule so a
    # mobile number is never classified as a Colombian ID.
    PATTERNS = [
        (
            "email",
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        ),
        (
            "phone",
            r"(?<!\d)(?:\+?57[\s-]?)?3\d{2}(?:[\s-]?\d{3})(?:[\s-]?\d{4})(?!\d)",
        ),
        (
            "colombian_id",
            r"(?i)(?:c[ée]dula(?:\s+de\s+ciudadan[ií]a)?\s*[:#-]?\s*)\d{7,10}\b|(?<![\d])\d{7,9}\b|(?<![\d3])\d{10}\b",
        ),
    ]

    def detect(self, text: str) -> Detection:
        matches = []
        for priority, (kind, pattern) in enumerate(self.PATTERNS):
            for match in re.finditer(pattern, text):
                matches.append({
                    "type": kind,
                    "value": match.group(0),
                    "start": match.start(),
                    "end": match.end(),
                    "priority": priority,
                })

        # Avoid overlapping classifications. More specific patterns (email/phone)
        # win over the generic ID rule.
        accepted = []
        for item in sorted(matches, key=lambda m: (m["start"], m["priority"], -(m["end"] - m["start"]))):
            overlaps = any(
                item["start"] < existing["end"] and item["end"] > existing["start"]
                for existing in accepted
            )
            if not overlaps:
                accepted.append(item)

        accepted.sort(key=lambda m: m["start"])
        for item in accepted:
            item.pop("priority", None)

        detected = bool(accepted)
        sanitized = text
        for item in reversed(accepted):
            start, end = item["start"], item["end"]
            sanitized = sanitized[:start] + f"[REDACTED:{item['type']}]" + sanitized[end:]

        return Detection(
            detected=detected,
            detector=self.name,
            type="pii" if detected else "",
            confidence=0.90 if detected else 0.0,
            matches=accepted,
            sanitized=sanitized,
        )
