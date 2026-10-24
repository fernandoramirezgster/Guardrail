"""Clasificador genérico basado en un modelo de Hugging Face (secuencia → etiqueta).

torch y transformers se importan al construir el clasificador, de modo que la
API y las pruebas unitarias funcionan sin esas dependencias cuando el
clasificador está desactivado.
"""
from time import perf_counter

from .base import BaseInjectionClassifier, ClassificationResult


def split_into_windows(token_ids, window: int, stride: int):
    """Divide una lista de tokens en ventanas solapadas que cubren todo el texto.

    Un texto largo no se trunca: una inyección al final del prompt queda dentro
    de la última ventana.
    """
    if window <= 0:
        raise ValueError("window debe ser positivo.")
    if not 0 <= stride < window:
        raise ValueError("stride debe estar entre 0 y window - 1.")
    if len(token_ids) <= window:
        return [list(token_ids)]

    step = window - stride
    windows = []
    start = 0
    while True:
        windows.append(list(token_ids[start:start + window]))
        if start + window >= len(token_ids):
            break
        start += step
    return windows


class HFSequenceClassifier(BaseInjectionClassifier):
    def __init__(
        self,
        model_path: str,
        malicious_labels: tuple,
        model_id: str,
        device: str = "cpu",
        trust_remote_code: bool = False,
        max_length: int = 512,
        stride: int = 64,
        batch_size: int = 8,
    ):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self._torch = torch
        self.model_id = model_id
        self.device = device
        self.stride = stride
        self.batch_size = batch_size
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_path, trust_remote_code=trust_remote_code,
        )
        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_path, trust_remote_code=trust_remote_code,
        ).to(device).eval()

        # Ventana de contenido = longitud máxima menos los tokens especiales [CLS]/[SEP].
        special = self.tokenizer.num_special_tokens_to_add(pair=False)
        self.window = max_length - special

        id2label = {int(k): str(v).lower() for k, v in self.model.config.id2label.items()}
        wanted = {label.lower() for label in malicious_labels}
        self.malicious_ids = [idx for idx, label in id2label.items() if label in wanted]
        if not self.malicious_ids:
            raise ValueError(
                f"El modelo {model_id} no tiene ninguna etiqueta maliciosa esperada "
                f"{sorted(wanted)}; etiquetas disponibles: {sorted(id2label.values())}."
            )

    def classify(self, text: str) -> ClassificationResult:
        start = perf_counter()
        token_ids = self.tokenizer(text, add_special_tokens=False)["input_ids"]
        windows = split_into_windows(token_ids, self.window, self.stride)

        best = 0.0
        torch = self._torch
        with torch.inference_mode():
            for i in range(0, len(windows), self.batch_size):
                batch = [
                    self.tokenizer.build_inputs_with_special_tokens(ids)
                    for ids in windows[i:i + self.batch_size]
                ]
                encoded = self.tokenizer.pad(
                    {"input_ids": batch}, padding=True, return_tensors="pt",
                ).to(self.device)
                probs = torch.softmax(self.model(**encoded).logits, dim=-1)
                scores = probs[:, self.malicious_ids].sum(dim=-1)
                best = max(best, float(scores.max()))

        return ClassificationResult(
            score_injection=best,
            model_id=self.model_id,
            chunk_count=len(windows),
            latency_ms=(perf_counter() - start) * 1000,
        )
