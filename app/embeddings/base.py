from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """
    Interface for generating vector embeddings.

    The rest of the application depends on this interface,
    not on a specific embedding provider.
    """

    @abstractmethod
    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """
        Generate one embedding vector per input text.
        """
        raise NotImplementedError

    @abstractmethod
    def embed_query(
        self,
        text: str,
    ) -> list[float]:
        """
        Generate an embedding for a search query.
        """
        raise NotImplementedError