from typing import Protocol

import httpx

from app.core.settings import Settings


class LLMClient(Protocol):
    name: str
    async def generate(self, prompt: str) -> str: ...


class MockLLMClient:
    """Simulador explícito de laboratorio; no es un modelo ni una defensa."""
    name = "mock"

    async def generate(self, prompt: str) -> str:
        return "Respuesta simulada: el flujo de la fase 1 se ejecutó correctamente."


class OpenAICompatibleClient:
    name = "openai_compatible"

    def __init__(self, settings: Settings):
        self.settings = settings

    async def generate(self, prompt: str) -> str:
        settings = self.settings
        if not settings.llm_base_url or not settings.llm_api_key or not settings.llm_model:
            raise RuntimeError("Configuración del proveedor incompleta.")
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=False) as client:
            response = await client.post(
                settings.llm_base_url.rstrip("/") + "/chat/completions",
                headers={"Authorization": "Bearer " + settings.llm_api_key},
                json={
                    "model": settings.llm_model,
                    "messages": [
                        {"role": "system", "content": "Responda únicamente la solicitud autorizada."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0,
                },
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

