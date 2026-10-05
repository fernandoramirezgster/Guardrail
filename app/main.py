from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.chat import router as chat_router
from app.api.input_guard import router as input_router
from app.api.output_guard import router as output_router

app = FastAPI(title="GenAI Guardrail — Fase 1", version="0.1.0")
app.include_router(input_router)
app.include_router(output_router)
app.include_router(chat_router)


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
    return {"status": "healthy", "service": "genai-guardrail", "phase": 1}
