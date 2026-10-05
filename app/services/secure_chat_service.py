from app.schemas.chat import SecureChatResponse
from app.schemas.guardrail import GuardrailDecision


class SecureChatService:
    def __init__(self, input_guard_service, output_guard_service, llm_client):
        self.input_guard_service = input_guard_service
        self.output_guard_service = output_guard_service
        self.llm_client = llm_client

    async def execute(self, request_id: str, prompt: str) -> SecureChatResponse:
        input_result = await self.input_guard_service.evaluate(request_id=request_id, prompt=prompt)
        response = SecureChatResponse(
            request_id=request_id, input_decision=input_result.decision,
            model_called=False, provider=self.llm_client.name,
        )
        if input_result.decision not in (GuardrailDecision.ALLOW, GuardrailDecision.MASK):
            response.reasons = input_result.reasons
            return response
        safe_prompt = input_result.processed_content
        if safe_prompt is None or not safe_prompt.strip():
            response.input_decision = GuardrailDecision.BLOCK
            response.reasons = ["La entrada procesada no contiene texto válido."]
            return response

        model_output = await self.llm_client.generate(safe_prompt)
        response.model_called = True
        if not isinstance(model_output, str) or not model_output.strip() or len(model_output) > 50_000:
            raise ValueError("El proveedor no devolvió una salida válida.")
        output_result = await self.output_guard_service.evaluate(
            request_id=request_id, model_output=model_output,
        )
        response.output_decision = output_result.decision
        response.reasons = output_result.reasons
        if output_result.decision not in (GuardrailDecision.ALLOW, GuardrailDecision.MASK):
            return response
        safe_answer = output_result.processed_content
        if safe_answer is None or not safe_answer.strip():
            response.output_decision = GuardrailDecision.BLOCK
            response.reasons = ["La salida procesada no contiene texto válido."]
            return response
        response.answer = safe_answer
        return response

