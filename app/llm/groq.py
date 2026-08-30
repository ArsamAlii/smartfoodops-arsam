import os
from collections.abc import AsyncIterator

from groq import AsyncGroq

from app.llm.base import LLMProvider, LLMResponse


class GroqLLMProvider(LLMProvider):
    """
    Groq implementation of the LLMProvider interface.
    """

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
    ):
        self.api_key = (
            api_key
            or os.getenv("LLM_API_KEY")
        )

        if not self.api_key:
            raise ValueError(
                "LLM_API_KEY is not configured"
            )

        self.model = (
            model
            or os.getenv(
                "LLM_MODEL",
                "llama-3.1-8b-instant",
            )
        )

        self.client = AsyncGroq(
            api_key=self.api_key
        )

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> LLMResponse:

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            temperature=0,
            max_tokens=500,
        )

        choice = response.choices[0]

        usage = response.usage

        prompt_tokens = (
            usage.prompt_tokens
            if usage
            else 0
        )

        completion_tokens = (
            usage.completion_tokens
            if usage
            else 0
        )

        total_tokens = (
            usage.total_tokens
            if usage
            else prompt_tokens + completion_tokens
        )

        return LLMResponse(
            text=choice.message.content or "",
            model=self.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

    async def stream(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> AsyncIterator[str]:

        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            temperature=0,
            max_tokens=500,
            stream=True,
        )

        async for chunk in stream:
            if not chunk.choices:
                continue

            text = (
                chunk.choices[0].delta.content
            )

            if text:
                yield text