"""Benchmark de detección de prompt injection: reglas vs. modelos vs. híbrido.

Ejemplos:
    python -m experiments.run_benchmark --datasets es_custom
    python -m experiments.run_benchmark --models prompt_guard piguard \
        --datasets es_custom deepset notinject jailbreak --models-dir ./models

Cada muestra se evalúa una vez por sistema (reglas y cada modelo); los sistemas
híbridos (reglas OR modelo >= umbral) se derivan de esas mismas puntuaciones.
Resultados en experiments/results/<marca de tiempo>/:
    summary.csv   métricas por sistema y conjunto (umbral de bloqueo)
    sweep.csv     TPR/FPR por umbral, para elegir block/review
    samples.csv   puntuación por muestra, para análisis de errores
"""
import argparse
import asyncio
import csv
import json
import statistics
from datetime import datetime
from pathlib import Path

from app.classifiers.registry import PRESETS, build_classifier
from app.core.settings import Settings
from app.services.input_guard_service import InputGuardService
from experiments.loaders import LOADERS

RESULTS_DIR = Path(__file__).resolve().parent / "results"
MODEL_FOLDERS = {"prompt_guard": "prompt-guard-2-86m", "piguard": "piguard"}
RULE_INJECTION_CATEGORIES = {
    "instruction_override", "system_prompt_extraction", "sensitive_data_request", "jailbreak",
}


def rules_flag(service, text):
    """True si las reglas/detectores de fase 1 señalan inyección (no PII ni secretos)."""
    result = asyncio.run(service.evaluate("benchmark", text))
    return any(
        f.category in RULE_INJECTION_CATEGORIES or f.category.startswith("injection:")
        for f in result.findings
    )


def metrics(labels, preds):
    tp = sum(1 for y, p in zip(labels, preds) if y and p)
    fp = sum(1 for y, p in zip(labels, preds) if not y and p)
    fn = sum(1 for y, p in zip(labels, preds) if y and not p)
    tn = sum(1 for y, p in zip(labels, preds) if not y and not p)
    tpr = tp / (tp + fn) if tp + fn else None
    fpr = fp / (fp + tn) if fp + tn else None
    precision = tp / (tp + fp) if tp + fp else None
    f1 = (2 * precision * tpr / (precision + tpr)
          if precision and tpr else None)
    return {
        "n": len(labels), "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "tpr": tpr, "fpr": fpr, "precision": precision, "f1": f1,
        # ASR residual: fracción de ataques que el guardrail deja pasar.
        "asr": fn / (tp + fn) if tp + fn else None,
        "accuracy": (tp + tn) / len(labels) if labels else None,
    }


def roc_auc(labels, scores):
    """AUC por rangos (Mann-Whitney); None si falta una de las clases."""
    pos = [s for y, s in zip(labels, scores) if y]
    neg = [s for y, s in zip(labels, scores) if not y]
    if not pos or not neg:
        return None
    wins = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return wins / (len(pos) * len(neg))


def percentile(values, q):
    if not values:
        return None
    values = sorted(values)
    return values[min(len(values) - 1, int(round(q * (len(values) - 1))))]


def fmt(value):
    return "" if value is None else (f"{value:.4f}" if isinstance(value, float) else value)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--datasets", nargs="+", default=["es_custom"], choices=list(LOADERS))
    parser.add_argument("--models", nargs="*", default=[], choices=list(PRESETS))
    parser.add_argument("--models-dir", default="/models")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--threshold", type=float, default=0.90,
                        help="Umbral de bloqueo para las métricas de summary.csv.")
    parser.add_argument("--limit", type=int, default=None, help="Máximo de muestras por conjunto.")
    args = parser.parse_args()

    samples = [s for name in args.datasets for s in LOADERS[name](args.limit)]
    print(f"Muestras: {len(samples)} de {args.datasets}")

    rules_service = InputGuardService()
    rows = [{"source": s.source, "lang": s.lang, "label": s.label, "text": s.text,
             "rules": rules_flag(rules_service, s.text)} for s in samples]

    latencies = {}
    for name in args.models:
        settings = Settings("mock", "", "", "", injection_classifier=name,
                            injection_model_path=str(Path(args.models_dir) / MODEL_FOLDERS[name]),
                            injection_classifier_device=args.device)
        classifier = build_classifier(settings)
        latencies[name] = []
        for row in rows:
            result = classifier.classify(row["text"])
            row[name] = result.score_injection
            latencies[name].append(result.latency_ms)
        print(f"{name}: p50={percentile(latencies[name], 0.5):.1f} ms "
              f"p95={percentile(latencies[name], 0.95):.1f} ms")

    # Sistemas: reglas, cada modelo solo y cada híbrido.
    systems = {"rules": lambda r: r["rules"]}
    for name in args.models:
        systems[name] = lambda r, n=name: r[n] >= args.threshold
        systems[f"rules+{name}"] = lambda r, n=name: r["rules"] or r[n] >= args.threshold

    groups = {"ALL": rows}
    for key in ("lang", "source"):
        for value in sorted({r[key] for r in rows}):
            groups[f"{key}={value}"] = [r for r in rows if r[key] == value]
    for dataset in args.datasets:
        groups[f"dataset={dataset}"] = [r for r in rows if r["source"].split(":")[0] == dataset]

    summary = []
    for system, predict in systems.items():
        model = system.split("+")[-1] if system != "rules" else None
        for group, group_rows in groups.items():
            if not group_rows:
                continue
            labels = [r["label"] for r in group_rows]
            row = {"system": system, "group": group, "threshold": args.threshold if model else "",
                   **metrics(labels, [predict(r) for r in group_rows])}
            row["roc_auc"] = (roc_auc(labels, [r[model] for r in group_rows])
                              if model and system == model else None)
            if model and group == "ALL":
                row["latency_p50_ms"] = percentile(latencies[model], 0.5)
                row["latency_p95_ms"] = percentile(latencies[model], 0.95)
                row["latency_mean_ms"] = statistics.fmean(latencies[model])
            summary.append(row)

    sweep = []
    for name in args.models:
        labels = [r["label"] for r in rows]
        for step in range(1, 20):
            t = step / 20
            for system, flag in ((name, lambda r: r[name] >= t),
                                 (f"rules+{name}", lambda r: r["rules"] or r[name] >= t)):
                m = metrics(labels, [flag(r) for r in rows])
                sweep.append({"system": system, "threshold": t, "tpr": m["tpr"],
                              "fpr": m["fpr"], "f1": m["f1"]})

    out = RESULTS_DIR / datetime.now().strftime("%Y%m%d-%H%M%S")
    out.mkdir(parents=True)
    write_csv(out / "summary.csv", summary)
    write_csv(out / "sweep.csv", sweep)
    write_csv(out / "samples.csv", rows)
    (out / "config.json").write_text(json.dumps(vars(args), indent=2), encoding="utf-8")

    print(f"\n{'sistema':<22}{'TPR':>8}{'FPR':>8}{'F1':>8}{'AUC':>8}")
    for row in summary:
        if row["group"] == "ALL":
            print(f"{row['system']:<22}" + "".join(
                f"{fmt(row[k]) or '-':>8}" for k in ("tpr", "fpr", "f1", "roc_auc")))
    print(f"\nResultados: {out}")


def write_csv(path, rows):
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: fmt(row.get(k)) for k in fields})


if __name__ == "__main__":
    main()
