from openai import AsyncOpenAI

from app.ai_core.llm_provider import LLMProvider
from app.core.errors import ProviderError


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, timeout_seconds: float = 20.0) -> None:
        self.model = model
        self.client = AsyncOpenAI(api_key=api_key, timeout=timeout_seconds) if api_key else None

    async def generate_response(self, system_prompt: str, user_message: str) -> str:
        if self.client is None:
            raise ProviderError("OpenAI API key is not configured.")

        try:
            response = await self.client.responses.create(
                model=self.model,
                instructions=system_prompt,
                input=user_message,
            )
            return response.output_text
        except Exception as exc:
            raise ProviderError("OpenAI request failed.") from exc
