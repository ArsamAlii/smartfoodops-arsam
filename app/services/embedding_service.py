import hashlib
import os

from sqlalchemy.orm import Session

from app.embeddings import (
    FakeEmbeddings,
    HuggingFaceEmbeddingProvider,
)
from app.models.content_chunk import ContentChunk


EMBEDDING_DIMENSIONS = int(
    os.getenv("EMBEDDING_DIMENSIONS", "384")
)


def get_embedding_provider():
    """
    Return the configured embedding provider.

    USE_FAKE_LLM=true is useful for tests because it avoids
    making requests to Hugging Face.
    """

    use_fake = os.getenv(
        "USE_FAKE_LLM",
        "false",
    ).lower() == "true"

    if use_fake:
        return FakeEmbeddings()

    return HuggingFaceEmbeddingProvider()


def calculate_text_hash(text: str) -> str:
    """Return a deterministic SHA-256 hash for embedding input."""

    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def generate_embedding(text: str) -> list[float]:
    """
    Generate one embedding vector for a text string.
    """

    provider = get_embedding_provider()

    embedding = provider.embed_query(text)

    if len(embedding) != EMBEDDING_DIMENSIONS:
        raise ValueError(
            f"Invalid embedding dimensions: "
            f"expected {EMBEDDING_DIMENSIONS}, "
            f"got {len(embedding)}"
        )

    return embedding


def embed_content_chunk(
    db: Session,
    chunk: ContentChunk,
) -> ContentChunk:
    """
    Generate and store an embedding for one content chunk.

    If the chunk already has an embedding and its text hash
    matches the current text, no new embedding request is made.
    """

    current_hash = calculate_text_hash(
        chunk.text
    )

    # Avoid unnecessary embedding requests.
    if (
        chunk.embedding is not None
        and chunk.text_hash == current_hash
    ):
        return chunk

    embedding = generate_embedding(
        chunk.text
    )

    chunk.text_hash = current_hash
    chunk.embedding = embedding

    db.commit()
    db.refresh(chunk)

    return chunk


def embed_all_content_chunks(
    db: Session,
) -> int:
    """
    Generate embeddings for all chunks that need them.

    Returns the number of chunks processed.
    """

    chunks = (
        db.query(ContentChunk)
        .order_by(ContentChunk.content_chunk_id)
        .all()
    )

    processed = 0

    for chunk in chunks:
        current_hash = calculate_text_hash(
            chunk.text
        )

        # Skip unchanged chunks that already have embeddings.
        if (
            chunk.embedding is not None
            and chunk.text_hash == current_hash
        ):
            continue

        embedding = generate_embedding(
            chunk.text
        )

        chunk.text_hash = current_hash
        chunk.embedding = embedding

        processed += 1

    db.commit()

    return processed