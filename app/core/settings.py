import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)


@dataclass(frozen=True)
class Settings:
    llm_provider: str
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    injection_classifier: str = "none"
    injection_model_path: str = ""
    injection_block_threshold: float = 0.90
    injection_review_threshold: float = 0.50
    injection_classifier_device: str = "cpu"

    def __post_init__(self):
        for name in ("injection_block_threshold", "injection_review_threshold"):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name.upper()} debe estar entre 0 y 1.")
        if self.injection_review_threshold > self.injection_block_threshold:
            raise ValueError(
                "INJECTION_REVIEW_THRESHOLD no puede superar INJECTION_BLOCK_THRESHOLD."
            )

    @classmethod
    def from_env(cls):
        return cls(
            llm_provider=os.getenv("LLM_PROVIDER", "mock").strip().lower(),
            llm_base_url=os.getenv("LLM_BASE_URL", "").strip(),
            llm_api_key=os.getenv("LLM_API_KEY", ""),
            llm_model=os.getenv("LLM_MODEL", "").strip(),
            injection_classifier=os.getenv("INJECTION_CLASSIFIER", "none").strip().lower(),
            injection_model_path=os.getenv("INJECTION_MODEL_PATH", "").strip(),
            injection_block_threshold=float(os.getenv("INJECTION_BLOCK_THRESHOLD", "0.90")),
            injection_review_threshold=float(os.getenv("INJECTION_REVIEW_THRESHOLD", "0.50")),
            injection_classifier_device=os.getenv("INJECTION_CLASSIFIER_DEVICE", "cpu").strip().lower(),
        )
