from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    async def generate_response(self, system_prompt: str, user_message: str) -> str:
        """Generate a draft response. The result must still pass AI Validator."""
