from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.chat import router as chat_router
from app.api.input_guard import router as input_router
from app.api.output_guard import router as output_router
from app.api.rag_guard import router as rag_router
from app.core.dependencies import load_injection_classifier


@asynccontextmanager
async def lifespan(app):
    # Falla cerrada: si el clasificador configurado no carga, la API no arranca.
    app.state.injection_classifier = load_injection_classifier()
    yield


app = FastAPI(title="GenAI Guardrail — Fases 1 a 4", version="0.4.0", lifespan=lifespan)
app.include_router(input_router)
app.include_router(output_router)
app.include_router(chat_router)
app.include_router(rag_router)


@app.exception_handler(RequestValidationError)
async def invalid_request(request, error):
    # No repetir el texto recibido en los errores de validación.
    return JSONResponse(status_code=422, content={
        "detail": [
            {"loc": list(item["loc"]), "msg": item["msg"], "type": item["type"]}
            for item in error.errors()
        ],
    })


@app.get("/health", tags=["Estado"])
async def health():
    return {
        "status": "healthy",
        "service": "genai-guardrail",
        "phase": 4,
        "injection_classifier": load_injection_classifier().model_id,
    }
