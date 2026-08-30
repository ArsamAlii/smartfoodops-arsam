from collections.abc import AsyncIterator

from app.llm.base import LLMProvider, LLMResponse


class FakeLLM(LLMProvider):
    """
    Deterministic fake LLM used by tests.

    It never calls a real external API.
    """

    def __init__(
        self,
        response: str = (
            "This is a fake grounded response "
            "for testing."
        ),
    ):
        self.response = response
        self.model = "fake-llm"

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> LLMResponse:

        return LLMResponse(
            text=self.response,
            model=self.model,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
        )

    async def stream(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> AsyncIterator[str]:
        """
        Stream the fake response word-by-word so
        SSE can be tested without a network connection.
        """

        words = self.response.split()

        for index, word in enumerate(words):
            if index == 0:
                yield word
            else:
                yield f" {word}"