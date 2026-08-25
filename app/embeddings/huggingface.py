import os

from huggingface_hub import InferenceClient

from app.embeddings.base import EmbeddingProvider


class HuggingFaceEmbeddingProvider(EmbeddingProvider):
    """
    Hugging Face embedding provider.

    Uses the configured Hugging Face embedding model.
    """

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
    ):
        self.model = (
            model
            or os.getenv(
                "EMBEDDING_MODEL",
                "sentence-transformers/all-MiniLM-L6-v2",
            )
        )

        self.api_key = (
            api_key
            or os.getenv("EMBEDDING_API_KEY")
        )

        if not self.api_key:
            raise ValueError(
                "EMBEDDING_API_KEY is not configured"
            )

        self.client = InferenceClient(
            provider="hf-inference",
            api_key=self.api_key,
        )

    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        if not texts:
            return []

        embeddings = self.client.feature_extraction(
            texts,
            model=self.model,
        )

        return [
            list(map(float, embedding))
            for embedding in embeddings
        ]

    def embed_query(
        self,
        text: str,
    ) -> list[float]:

        embedding = self.client.feature_extraction(
            text,
            model=self.model,
        )

        return list(
            map(float, embedding)
        )