# VigilAI — imagen CPU. Los modelos NO se incluyen: se montan en /models (solo lectura).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    HF_HOME=/tmp/hf

# Para GPU: docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu

WORKDIR /app
COPY requirements.txt ./
RUN pip install -r requirements.txt --extra-index-url ${TORCH_INDEX_URL}

COPY app ./app
COPY tests ./tests
COPY experiments ./experiments
COPY datasets ./datasets
COPY pytest.ini ./

RUN useradd --create-home --uid 1000 vigilai
USER vigilai

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
