import os
import time

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

        self.timeout = float(
            os.getenv("EMBEDDING_TIMEOUT", "60")
        )

        self.max_retries = int(
            os.getenv("EMBEDDING_MAX_RETRIES", "2")
        )

    def _embed(self, inputs):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                response = httpx.post(
                    self.url,
                    headers=headers,
                    json={
                        "inputs": inputs,
                    },
                    timeout=self.timeout,
                )

                response.raise_for_status()

                return response.json()

            except (
                httpx.ConnectError,
                httpx.ConnectTimeout,
                httpx.ReadTimeout,
                httpx.ReadError,
            ) as exc:
                last_error = exc

                if attempt < self.max_retries:
                    time.sleep(1 * (attempt + 1))
                    continue

                raise RuntimeError(
                    "Embedding service is temporarily unavailable. "
                    "Please try again."
                ) from exc

            except httpx.HTTPStatusError as exc:
                raise RuntimeError(
                    "Embedding service returned an error."
                ) from exc

        raise RuntimeError(
            "Embedding service is temporarily unavailable."
        ) from last_error

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