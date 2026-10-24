"""Cargadores de conjuntos de evaluación → lista de Sample(text, label, lang, source).

label: 1 = inyección/jailbreak, 0 = benigno. Los conjuntos de Hugging Face se
descargan con la librería `datasets` (requirements.txt). Verificar en cada
tarjeta del dataset que columnas y splits siguen siendo los indicados aquí.
"""
import csv
from dataclasses import dataclass
from pathlib import Path

# Solo datos: datasets/ no es un paquete para no ocultar la librería `datasets`.
DATA_DIR = Path(__file__).resolve().parents[1] / "datasets"


@dataclass(frozen=True)
class Sample:
    text: str
    label: int
    lang: str
    source: str


def load_es_custom(limit=None):
    with open(DATA_DIR / "es_custom.csv", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    return [Sample(r["text"], int(r["label"]), "es", f"es_custom:{r['category']}")
            for r in rows][:limit]


def _hf(name, split, config=None):
    from datasets import load_dataset
    return load_dataset(name, config, split=split)


def load_deepset(limit=None):
    # deepset/prompt-injections: columnas text, label (1 = inyección). Mezcla EN y algo de DE.
    ds = _hf("deepset/prompt-injections", "test")
    return [Sample(r["text"], int(r["label"]), "en", "deepset")
            for r in ds][:limit]


def load_notinject(limit=None):
    # NotInject (autores de PIGuard): textos benignos con palabras gatillo → mide sobre-defensa (FPR).
    samples = []
    for split in ("NotInject_one", "NotInject_two", "NotInject_three"):
        for r in _hf("leolee99/NotInject", split):
            samples.append(Sample(r["prompt"], 0, "en", f"notinject:{split}"))
    return samples[:limit]


def load_jailbreak(limit=None):
    # jackhhao/jailbreak-classification: columnas prompt, type ∈ {jailbreak, benign}.
    ds = _hf("jackhhao/jailbreak-classification", "test")
    return [Sample(r["prompt"], int(r["type"] == "jailbreak"), "en", "jailbreak_cls")
            for r in ds][:limit]


LOADERS = {
    "es_custom": load_es_custom,
    "deepset": load_deepset,
    "notinject": load_notinject,
    "jailbreak": load_jailbreak,
}
