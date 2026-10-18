import pytest

from app.policies.engine import PolicyEngine, PolicyConfigurationError
from app.schemas.guardrail import Finding, GuardrailDecision


def test_default_policy_blocks_injection_over_mask():
    engine = PolicyEngine()
    findings = [
        Finding(category="pii:email", severity="medium", description="PII"),
        Finding(category="injection", severity="high", description="Injection"),
    ]
    assert engine.decide(findings, pii_detected=True) == GuardrailDecision.BLOCK


def test_default_policy_masks_pii():
    engine = PolicyEngine()
    finding = Finding(category="pii:email", severity="medium", description="PII")
    assert engine.decide([finding], pii_detected=True) == GuardrailDecision.MASK


def test_policy_can_be_configured_to_review():
    engine = PolicyEngine(config={
        "version": 1,
        "priority": ["BLOCK", "REVIEW", "MASK", "ALLOW"],
        "rules": [
            {"name": "review_injection", "categories": ["injection"], "action": "REVIEW"}
        ],
    })
    assert engine.decide([
        Finding(category="injection", severity="high", description="test")
    ]) == GuardrailDecision.REVIEW


def test_invalid_policy_rejected():
    with pytest.raises(PolicyConfigurationError):
        PolicyEngine(config={"priority": ["ALLOW"], "rules": []})
