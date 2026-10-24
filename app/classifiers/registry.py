"""Selección del clasificador de prompt injection según la configuración."""
from .base import BaseInjectionClassifier, NullClassifier

# Etiquetas maliciosas según las tarjetas de cada modelo en Hugging Face.
PRESETS = {
    "prompt_guard": {
        "model_id": "meta-llama/Llama-Prompt-Guard-2-86M",
        "default_path": "/models/prompt-guard-2-86m",
        "malicious_labels": ("LABEL_1", "malicious"),
        "trust_remote_code": False,
    },
    "piguard": {
        "model_id": "leolee99/PIGuard",
        "default_path": "/models/piguard",
        "malicious_labels": ("injection",),
        "trust_remote_code": True,
    },
}

SUPPORTED = ("none", *PRESETS)


def build_classifier(settings) -> BaseInjectionClassifier:
    name = settings.injection_classifier
    if name == "none":
        return NullClassifier()
    if name not in PRESETS:
        raise ValueError(f"INJECTION_CLASSIFIER no soportado: {name!r}. Opciones: {SUPPORTED}.")

    from .hf_classifier import HFSequenceClassifier

    preset = PRESETS[name]
    return HFSequenceClassifier(
        model_path=settings.injection_model_path or preset["default_path"],
        malicious_labels=preset["malicious_labels"],
        model_id=preset["model_id"],
        device=settings.injection_classifier_device,
        trust_remote_code=preset["trust_remote_code"],
    )
