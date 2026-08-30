from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """
    Standard response returned by an LLM provider.
    """

    text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class LLMProvider(ABC):
    """
    Interface for generating text with an LLM.

    The rest of the application depends on this interface,
    not on a specific provider such as Groq.
    """

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> LLMResponse:
        """
        Generate a complete LLM response.
        """
        raise NotImplementedError

    @abstractmethod
    async def stream(
        self,
        system_prompt: str,
        user_prompt: str,
    ):
        """
        Stream generated text progressively.

        Implementations should yield text chunks.
        """
        raise NotImplementedError