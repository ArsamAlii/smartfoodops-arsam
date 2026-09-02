import os
from collections.abc import AsyncIterator

from groq import AsyncGroq

from app.llm.base import LLMProvider, LLMResponse


class GroqLLMProvider(LLMProvider):
    """
    Hardened Groq implementation of the LLMProvider interface.

    Features:
    - Uses Groq's async client so FastAPI's event loop is not blocked.
    - Validates the API key during initialization.
    - Uses a configurable timeout.
    - Disables automatic retries so failures return promptly.
    - Converts provider/network failures into clear RuntimeErrors.
    - Handles empty/malformed provider responses safely.
    """

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
    ):
        self.api_key = (
            api_key
            or os.getenv("LLM_API_KEY")
            or ""
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

        timeout_raw = os.getenv(
            "LLM_TIMEOUT_SECONDS",
            "60",
        )

        try:
            timeout_seconds = float(timeout_raw)
        except ValueError as exc:
            raise ValueError(
                "LLM_TIMEOUT_SECONDS must be a valid number"
            ) from exc

        if timeout_seconds <= 0:
            raise ValueError(
                "LLM_TIMEOUT_SECONDS must be greater than 0"
            )

        self.client = AsyncGroq(
            api_key=self.api_key,
            timeout=timeout_seconds,
            max_retries=0,
        )

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> LLMResponse:
        """
        Generate a complete response from Groq.

        Provider failures are converted into a clear RuntimeError
        so the API layer can return a controlled error response.
        """

        try:
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

        except Exception as exc:
            raise RuntimeError(
                "AI provider is currently unavailable. "
                "Please try again later."
            ) from exc

        if not response.choices:
            raise RuntimeError(
                "AI provider returned an empty response."
            )

        choice = response.choices[0]

        text = choice.message.content or ""

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
            text=text,
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

        Provider failures are converted into a clear RuntimeError.
        """

        try:
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

        except Exception as exc:
            raise RuntimeError(
                "AI provider is currently unavailable. "
                "Please try again later."
            ) from exc