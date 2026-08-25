import hashlib
import math

from app.embeddings.base import EmbeddingProvider


class FakeEmbeddings(EmbeddingProvider):
    """
    Deterministic fake embedding provider.

    Used in tests so tests do not depend on an external
    embedding API.
    """

    DIMENSIONS = 384

    def _embed(self, text: str) -> list[float]:
        values = []

        counter = 0

        while len(values) < self.DIMENSIONS:

            digest = hashlib.sha256(
                f"{text}:{counter}".encode("utf-8")
            ).digest()

            for byte in digest:
                values.append(
                    (byte / 127.5) - 1.0
                )

                if len(values) >= self.DIMENSIONS:
                    break

            counter += 1

        # Normalize the vector.
        magnitude = math.sqrt(
            sum(value * value for value in values)
        )

        if magnitude == 0:
            return values

        return [
            value / magnitude
            for value in values
        ]

    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:

        return [
            self._embed(text)
            for text in texts
        ]

    def embed_query(
        self,
        text: str,
    ) -> list[float]:

        return self._embed(text)