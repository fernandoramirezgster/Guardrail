"""Motor de políticas configurable para decisiones ALLOW/MASK/REVIEW/BLOCK."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable

from app.schemas.guardrail import Finding, GuardrailDecision


VALID_ACTIONS = {item.value for item in GuardrailDecision}


class PolicyConfigurationError(ValueError):
    """La configuración de políticas no cumple el contrato esperado."""


class PolicyEngine:
    def __init__(self, config: dict[str, Any] | None = None, config_path: str | None = None):
        if config is None:
            configured_path = config_path or os.getenv("GUARDRAIL_POLICY_PATH")
            path = Path(configured_path) if configured_path else Path(__file__).with_name("default_policy.json")
            try:
                config = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise PolicyConfigurationError("No fue posible cargar la configuración de políticas.") from exc
        self._validate(config)
        self.config = config
        self.priority = {action: len(config["priority"]) - index for index, action in enumerate(config["priority"])}

    @staticmethod
    def _validate(config: dict[str, Any]) -> None:
        if not isinstance(config, dict):
            raise PolicyConfigurationError("La configuración debe ser un objeto JSON.")
        priority = config.get("priority")
        if not isinstance(priority, list) or set(priority) != VALID_ACTIONS or len(priority) != len(VALID_ACTIONS):
            raise PolicyConfigurationError("priority debe ordenar exactamente ALLOW, MASK, REVIEW y BLOCK.")
        rules = config.get("rules")
        if not isinstance(rules, list):
            raise PolicyConfigurationError("rules debe ser una lista.")
        for rule in rules:
            if not isinstance(rule, dict) or not isinstance(rule.get("name"), str):
                raise PolicyConfigurationError("Cada regla debe tener nombre.")
            if rule.get("action") not in VALID_ACTIONS:
                raise PolicyConfigurationError(f"Acción inválida en regla {rule.get('name')}.")
            for key in ("categories", "category_prefixes", "exclude_categories", "severities"):
                if key in rule and not isinstance(rule[key], list):
                    raise PolicyConfigurationError(f"{key} debe ser una lista en la regla {rule['name']}.")

    def decide(
        self,
        findings: Iterable[Finding],
        *,
        pii_detected: bool = False,
        default: GuardrailDecision = GuardrailDecision.ALLOW,
    ) -> GuardrailDecision:
        findings = list(findings)
        matched_actions: list[GuardrailDecision] = []
        for rule in self.config["rules"]:
            if self._matches(rule, findings):
                matched_actions.append(GuardrailDecision(rule["action"]))
        if pii_detected:
            for rule in self.config["rules"]:
                if rule.get("name") == "enmascarar_datos_personales":
                    matched_actions.append(GuardrailDecision(rule["action"]))
        if not matched_actions:
            return default
        # Resolución explícita y determinista; la prioridad se configura en JSON.
        return max(matched_actions, key=lambda action: self.priority[action.value])

    @staticmethod
    def _matches(rule: dict[str, Any], findings: list[Finding]) -> bool:
        categories = rule.get("categories", [])
        prefixes = rule.get("category_prefixes", [])
        severities = rule.get("severities", [])
        excluded = rule.get("exclude_categories", [])
        for finding in findings:
            category = finding.category
            if category in excluded:
                continue
            has_condition = bool(categories or prefixes or severities)
            if not has_condition:
                continue
            category_match = (
                (not categories and not prefixes)
                or category in categories
                or any(category.startswith(prefix) for prefix in prefixes)
            )
            severity_match = not severities or finding.severity in severities
            if category_match and severity_match:
                return True
        return False
