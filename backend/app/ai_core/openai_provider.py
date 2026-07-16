from openai import AsyncOpenAI

from app.ai_core.llm_provider import LLMProvider


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self.model = model
        self.client = AsyncOpenAI(api_key=api_key) if api_key else None

    async def generate_response(self, system_prompt: str, user_message: str) -> str:
        if self.client is None:
            return "OpenAI API key is not configured."

        response = await self.client.responses.create(
            model=self.model,
            instructions=system_prompt,
            input=user_message,
        )
        return response.output_text
