from functools import lru_cache

from fastapi import Depends, HTTPException

from app.classifiers import build_classifier
from app.core.settings import Settings
from app.providers.llm_client import MockLLMClient, OpenAICompatibleClient
from app.services.input_guard_service import InputGuardService
from app.services.output_guard_service import OutputGuardService
from app.services.secure_chat_service import SecureChatService
from app.services.rag_context_service import RAGContextService
from app.orchestrators.rag_orchestrator import RAGOrchestrator


@lru_cache(maxsize=1)
def load_injection_classifier():
    # El modelo se carga una sola vez por proceso (se precarga en el arranque de la API).
    return build_classifier(Settings.from_env())


def get_injection_classifier():
    return load_injection_classifier()


def get_input_guard_service(classifier=Depends(get_injection_classifier)):
    settings = Settings.from_env()
    return InputGuardService(
        classifier=classifier,
        block_threshold=settings.injection_block_threshold,
        review_threshold=settings.injection_review_threshold,
    )


def get_output_guard_service():
    return OutputGuardService()


def get_llm_client():
    settings = Settings.from_env()
    if settings.llm_provider == "mock":
        return MockLLMClient()
    if settings.llm_provider == "openai_compatible":
        return OpenAICompatibleClient(settings)
    raise HTTPException(status_code=503, detail="Proveedor LLM no configurado correctamente.")


def get_rag_orchestrator(input_guard=Depends(get_input_guard_service)):
    # Los fragmentos RAG pasan por el mismo guard de entrada (reglas + clasificador).
    return RAGOrchestrator(RAGContextService(input_guard))


def get_secure_chat_service(
    input_guard=Depends(get_input_guard_service),
    output_guard=Depends(get_output_guard_service),
    llm_client=Depends(get_llm_client),
):
    return SecureChatService(input_guard, output_guard, llm_client)

