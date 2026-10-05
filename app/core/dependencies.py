from fastapi import Depends, HTTPException

from app.core.settings import Settings
from app.providers.llm_client import MockLLMClient, OpenAICompatibleClient
from app.services.input_guard_service import InputGuardService
from app.services.output_guard_service import OutputGuardService
from app.services.secure_chat_service import SecureChatService


def get_input_guard_service():
    return InputGuardService()


def get_output_guard_service():
    return OutputGuardService()


def get_llm_client():
    settings = Settings.from_env()
    if settings.llm_provider == "mock":
        return MockLLMClient()
    if settings.llm_provider == "openai_compatible":
        return OpenAICompatibleClient(settings)
    raise HTTPException(status_code=503, detail="Proveedor LLM no configurado correctamente.")


def get_secure_chat_service(
    input_guard=Depends(get_input_guard_service),
    output_guard=Depends(get_output_guard_service),
    llm_client=Depends(get_llm_client),
):
    return SecureChatService(input_guard, output_guard, llm_client)

