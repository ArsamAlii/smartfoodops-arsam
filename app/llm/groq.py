import os
from collections.abc import AsyncIterator

from groq import AsyncGroq

from app.llm.base import LLMProvider, LLMResponse


class GroqLLMProvider(LLMProvider):
    """
    Groq implementation of the LLMProvider interface.

    Uses Groq's async client so LLM calls do not block
    FastAPI's event loop.
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
                "openai/gpt-oss-20b",
            )
        )

        self.client = AsyncGroq(
            api_key=self.api_key,
            timeout=60.0,
            max_retries=0,
        )

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> LLMResponse:
        """
        Generate a complete response from Groq.
        """

        response = (
            await self.client.chat.completions.create(
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
                max_completion_tokens=500,
                reasoning_effort="low",
                include_reasoning=False,
            )
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
            model=response.model or self.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

    async def stream(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> AsyncIterator[str]:
        """
        Stream generated text progressively.

        Only actual response text is yielded.
        Reasoning output is disabled.
        """

        stream = (
            await self.client.chat.completions.create(
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
                max_completion_tokens=500,
                reasoning_effort="low",
                include_reasoning=False,
                stream=True,
            )
        )

        async for chunk in stream:

            if not chunk.choices:
                continue

            text = (
                chunk.choices[0]
                .delta
                .content
            )

            if text:
                yield text