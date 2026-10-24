"""Descarga los modelos del clasificador a ./models (se ejecuta una vez, fuera de Docker).

Uso (PowerShell):
    $env:HF_TOKEN = "<token de Hugging Face>"
    python scripts/download_models.py                 # ambos modelos
    python scripts/download_models.py --only piguard

Llama Prompt Guard 2 está restringido: antes hay que aceptar la licencia en
https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M con la misma cuenta
del token. El token solo se usa aquí; nunca entra en la imagen Docker.
"""
import argparse
import os
import sys
from pathlib import Path

MODELS = {
    "prompt_guard": ("meta-llama/Llama-Prompt-Guard-2-86M", "prompt-guard-2-86m"),
    "piguard": ("leolee99/PIGuard", "piguard"),
}
ALLOW_PATTERNS = ["*.json", "*.safetensors", "*.py", "*.model", "*.txt", "*.md", "LICENSE*"]


def main():
    parser = argparse.ArgumentParser(description="Descarga los modelos del clasificador.")
    parser.add_argument("--only", nargs="+", choices=list(MODELS), default=list(MODELS))
    parser.add_argument("--dest", default=str(Path(__file__).resolve().parents[1] / "models"))
    args = parser.parse_args()

    from huggingface_hub import snapshot_download
    from huggingface_hub.errors import GatedRepoError, RepositoryNotFoundError

    token = os.getenv("HF_TOKEN") or None
    failed = False
    for name in args.only:
        repo_id, folder = MODELS[name]
        target = Path(args.dest) / folder
        print(f"Descargando {repo_id} → {target}")
        try:
            snapshot_download(repo_id, local_dir=target, token=token,
                              allow_patterns=ALLOW_PATTERNS)
        except (GatedRepoError, RepositoryNotFoundError):
            failed = True
            print(
                f"  Acceso denegado a {repo_id}. Acepta la licencia en "
                f"https://huggingface.co/{repo_id} y define HF_TOKEN con esa cuenta.",
                file=sys.stderr,
            )
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
