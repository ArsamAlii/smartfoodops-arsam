import os

import httpx

from app.embeddings.base import EmbeddingProvider


class HuggingFaceEmbeddingProvider(EmbeddingProvider):
    """
    Hugging Face embedding provider.

    Uses the Hugging Face Serverless Inference API directly.
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

        self.url = (
            "https://router.huggingface.co/"
            f"hf-inference/models/{self.model}"
            "/pipeline/feature-extraction"
        )

    def _embed(self, inputs):
        response = httpx.post(
            self.url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "inputs": inputs,
            },
            timeout=60,
        )

        response.raise_for_status()

        return response.json()

    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        if not texts:
            return []

        embeddings = self._embed(texts)

        return [
            list(map(float, embedding))
            for embedding in embeddings
        ]

    def embed_query(
        self,
        text: str,
    ) -> list[float]:
        embedding = self._embed(text)

        return list(
            map(float, embedding)
        )