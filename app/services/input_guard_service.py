"""Evaluación de entrada: reglas, detectores y clasificador de prompt injection."""
import html
import logging
import re
import unicodedata
from time import perf_counter

from starlette.concurrency import run_in_threadpool

from app.classifiers.base import NullClassifier
from app.detectors.injection import InjectionDetector
from app.detectors.pii import PIIDetector
from app.detectors.secrets import SecretsDetector
from app.schemas.guardrail import Finding, GuardrailDecision, GuardrailEvaluationResponse
from app.orchestrators.decision_orchestrator import DecisionOrchestrator

logger = logging.getLogger(__name__)

INJECTION_DESCRIPTION = (
    "Se detectó un posible intento de inyección o manipulación de instrucciones."
)


class InputGuardService:
    MAX_PROMPT_LENGTH = 20_000

    EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

    # Estas reglas existentes cubren intentos de prompt injection en español,
    # inglés y variantes Unicode/HTML. Los detectores especializados agregan
    # reglas reutilizables de la carpeta app/detectors.
    RULES = (
        (
            "instruction_override",
            re.compile(
                r"\b(?:ignora|ignore|ignorar|omite|omita|olvida|desobedece)\b.{0,80}\b"
                r"(?:instrucciones|reglas|restricciones|politicas)\b.{0,60}\b"
                r"(?:anteriores|previas|sistema|seguridad)\b"
                r"|\b(?:ignore|disregard|forget|override)\b.{0,60}\b"
                r"(?:previous|prior|system|security)\b.{0,60}\b"
                r"(?:instructions|rules|restrictions|policies)\b"
            ),
            "Posible intento de sustituir las instrucciones o reglas del sistema.",
        ),
        (
            "system_prompt_extraction",
            re.compile(
                r"\b(?:revela|revele|muestra|muestre|imprime|extrae|repite)\b.{0,80}\b"
                r"(?:prompt\s+(?:del\s+)?sistema|instrucciones\s+(?:del\s+)?sistema)\b"
                r"|\b(?:reveal|show|print|extract|repeat)\b.{0,80}\b"
                r"(?:system\s+prompt|system\s+instructions)\b"
            ),
            "Posible intento de obtener las instrucciones internas del sistema.",
        ),
        (
            "sensitive_data_request",
            re.compile(
                r"\b(?:revela|revele|muestra|muestre|extrae|lista|envia|exporta)\b.{0,80}\b"
                r"(?:contrasenas|credenciales|claves\s+secretas|datos\s+confidenciales)\b"
                r"|\b(?:reveal|show|extract|list|send|export)\b.{0,80}\b"
                r"(?:passwords|credentials|secret\s+keys|confidential\s+data)\b"
            ),
            "Posible solicitud de divulgación de credenciales o datos confidenciales.",
        ),
        (
            "jailbreak",
            re.compile(
                r"\b(?:actua|actue|opera|responde)\b.{0,60}\b"
                r"(?:sin\s+(?:restricciones|limites|filtros)|modo\s+(?:dan|sin\s+restricciones))\b"
                r"|\b(?:act|operate|respond)\b.{0,60}\b"
                r"(?:without\s+(?:restrictions|limits|filters)|unrestricted\s+mode)\b"
            ),
            "Posible intento de desactivar las restricciones del asistente.",
        ),
    )

    def __init__(self, detectors=None, policy_engine=None, classifier=None,
                 block_threshold=0.90, review_threshold=0.50):
        if not 0.0 <= review_threshold <= block_threshold <= 1.0:
            raise ValueError("Se requiere 0 <= review_threshold <= block_threshold <= 1.")
        self.policy_engine = policy_engine or DecisionOrchestrator()
        self.detectors = detectors or [
            InjectionDetector(),
            PIIDetector(),
            SecretsDetector(),
        ]
        self.classifier = classifier or NullClassifier()
        self.block_threshold = block_threshold
        self.review_threshold = review_threshold

    async def _classifier_finding(self, prompt: str):
        """Ejecuta el clasificador fuera del event loop y traduce su puntuación
        en un hallazgo; la acción la decide el motor de políticas."""
        if not self.classifier.enabled:
            return None
        # Los modelos se entrenaron con texto original, no con la versión normalizada.
        result = await run_in_threadpool(self.classifier.classify, prompt)
        score = result.score_injection
        logger.info(
            "classifier=%s score=%.4f chunks=%d latency_ms=%.1f",
            result.model_id, score, result.chunk_count, result.latency_ms,
        )
        if score >= self.block_threshold:
            return Finding(
                category="injection:classifier",
                severity="high",
                description=INJECTION_DESCRIPTION,
            )
        if score >= self.review_threshold:
            return Finding(
                # Sin prefijo "injection:" para que no se consolide ni lo capture
                # bloquear_inyeccion; la regla revisar_inyeccion_probable lo envía a REVIEW.
                category="injection_review",
                severity="medium",
                description=(
                    "El clasificador asignó una probabilidad intermedia de inyección; "
                    "la entrada requiere revisión."
                ),
            )
        return None

    @staticmethod
    def normalize_for_detection(content: str) -> str:
        normalized = unicodedata.normalize("NFKC", html.unescape(content)).casefold()
        normalized = "".join(
            char for char in normalized if unicodedata.category(char) != "Cf"
        )
        normalized = unicodedata.normalize("NFD", normalized)
        normalized = "".join(
            char for char in normalized if unicodedata.category(char) != "Mn"
        )
        return re.sub(r"\s+", " ", normalized).strip()

    @staticmethod
    def _finding_from_detector(detector_name, detection):
        severity = "high" if detector_name == "injection" else (
            "critical" if detector_name == "secrets" else "medium"
        )
        descriptions = {
            "injection": "Se detectó un posible intento de inyección o manipulación de instrucciones.",
            "pii": "Se detectaron posibles datos personales que deben ocultarse antes del LLM.",
            "secrets": "Se detectó una posible clave, credencial o secreto.",
        }
        return Finding(
            category=(
                "credential" if detector_name == "secrets"
                else f"{detector_name}:{detection.type or detector_name}"
            ),
            severity=severity,
            description=descriptions[detector_name],
        )

    async def evaluate(self, request_id: str, prompt: str) -> GuardrailEvaluationResponse:
        start = perf_counter()

        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("El prompt debe contener texto.")
        if len(prompt) > self.MAX_PROMPT_LENGTH:
            raise ValueError("El prompt supera la longitud permitida.")

        normalized = self.normalize_for_detection(prompt)
        findings = []

        # Compatibilidad con la regla de credenciales de fase 1: los valores
        # ficticios/cortos con prefijo sk- también deben detenerse.
        legacy_secret = re.search(
            r"\bsk-[a-z0-9_-]{10,}\b",
            normalized,
        )

        legacy_credential = re.search(
            r"\b(?:password|contrasena|api[_\-\s]?key|token)\s*[:=]\s*[^\s,;]+",
            normalized,
        )

        legacy_credential_detected = bool(
            legacy_secret or legacy_credential
        )

        # 1. Reglas de entrada existentes.
        for category, pattern, description in self.RULES:
            if pattern.search(normalized):
                logger.info("rule_match=%s", category)
                findings.append(Finding(
                    category=category,
                    severity="high",
                    description=description,
                ))

        # 2. Detectores especializados.
        detections = []
        for detector in self.detectors:
            detection = detector.detect(prompt)
            # No registrar los valores encontrados: pueden contener datos sensibles.
            logger.info(
                "detector=%s detected=%s match_types=%s",
                detector.name,
                detection.detected,
                sorted({m["type"] for m in detection.matches}),
            )
            detections.append(detection)
            if detection.detected:
                findings.append(self._finding_from_detector(detector.name, detection))

        # La detección especializada de secretos tiene prioridad.
        # La regla legacy solamente genera el finding si SecretsDetector
        # no detectó el secreto, evitando duplicar la misma alerta.
        secrets_detected = any(
            detection.detector == "secrets" and detection.detected
            for detection in detections
        )

        if legacy_credential_detected and not secrets_detected:
            findings.append(
                Finding(
                    category="credential",
                    severity="critical",
                    description=(
                        "La entrada contiene una posible clave secreta "
                        "o credencial asignada."
                    ),
                )
            )

        # 3. Clasificador de prompt injection (fase 2). Se agrega antes de
        # consolidar para que un bloqueo del modelo y de las reglas cuente
        # como un solo evento de inyección.
        classifier_finding = await self._classifier_finding(prompt)
        if classifier_finding:
            findings.append(classifier_finding)

        # 4. Consolidar señales de inyección.
        # Una misma entrada puede activar varias reglas (por ejemplo,
        # instruction_override + system_prompt_extraction + el detector
        # especializado). Todas describen el mismo evento de seguridad y no
        # deben aparecer como tres alertas independientes en la respuesta.
        injection_categories = {
            "instruction_override",
            "system_prompt_extraction",
            "sensitive_data_request",
            "jailbreak",
        }
        injection_findings = [
            finding
            for finding in findings
            if finding.category in injection_categories
            or finding.category.startswith("injection:")
        ]
        if injection_findings:
            # Consolidar en un solo hallazgo sin perder la categoría concreta
            # que esperan los consumidores y las pruebas existentes.
            preferred = next(
                (finding for finding in injection_findings
                 if finding.category in injection_categories),
                next(
                    (finding for finding in injection_findings
                     if finding.category.startswith("injection:")),
                    injection_findings[0],
                ),
            )
            findings = [
                finding for finding in findings
                if finding not in injection_findings
            ]
            findings.append(Finding(
                category=preferred.category,
                severity="high",
                description=(
                    "Se detectó un posible intento de inyección o manipulación "
                    "de instrucciones."
                ),
            ))

        pii_detected = any(
            detection.detector == "pii" and detection.detected
            for detection in detections
        )
        decision = self.policy_engine.decide(findings, pii_detected=pii_detected)

        # Solo se transforma contenido para MASK. REVIEW y BLOCK son fail-closed:
        # no se devuelve contenido para que un orquestador no pueda enviarlo al LLM.
        if decision == GuardrailDecision.MASK:
            safe_content = prompt
            for detection in detections:
                if detection.detector != "pii" or not detection.detected:
                    continue
                # Reemplazar de derecha a izquierda mantiene válidos los índices.
                for match in sorted(
                    detection.matches,
                    key=lambda m: m["start"],
                    reverse=True
                ):
                    start = match["start"]
                    end = match["end"]
                    replacement = "[EMAIL]" if match["type"] == "email" else f"[REDACTED:{match['type']}]"
                    safe_content = safe_content[:start] + replacement + safe_content[end:]
            content = safe_content
        elif decision == GuardrailDecision.ALLOW:
            content = prompt
        else:
            content = None
        return GuardrailEvaluationResponse(
            request_id=request_id,
            decision=decision,
            processed_content=content,
            findings=findings,
            reasons=[
                f.description for f in findings
            ] or ["Sin coincidencias con las reglas de entrada configuradas."],
            processing_time_ms=(perf_counter() - start) * 1000,
        )
