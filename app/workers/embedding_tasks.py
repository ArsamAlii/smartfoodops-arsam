from app.workers.celery_app import celery_app
from app.db.database import SessionLocal
from app.models.content_chunk import ContentChunk
from app.services.embedding_service import (
    calculate_text_hash,
    get_embedding_provider,
    EMBEDDING_DIMENSIONS,
)


BATCH_SIZE = 32


@celery_app.task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    max_retries=3,
)
def embed_content_chunks_batch_task(
    self,
    content_chunk_ids: list[int],
):
    """
    Generate embeddings for multiple content chunks
    in one provider request.

    Unchanged chunks are skipped using their text hash.
    """

    db = SessionLocal()

    try:
        chunks = (
            db.query(ContentChunk)
            .filter(
                ContentChunk.content_chunk_id.in_(
                    content_chunk_ids
                )
            )
            .order_by(
                ContentChunk.content_chunk_id
            )
            .all()
        )

        if not chunks:
            return {
                "status": "not_found",
                "processed": 0,
                "skipped": 0,
            }

        chunks_needing_embedding = []

        for chunk in chunks:

            current_hash = calculate_text_hash(
                chunk.text
            )

            if (
                chunk.embedding is not None
                and chunk.text_hash == current_hash
            ):
                continue

            chunks_needing_embedding.append(chunk)

        if not chunks_needing_embedding:
            return {
                "status": "nothing_to_embed",
                "processed": 0,
                "skipped": len(chunks),
            }

        texts = [
            chunk.text
            for chunk in chunks_needing_embedding
        ]

        provider = get_embedding_provider()

        embeddings = provider.embed_documents(texts)

        if len(embeddings) != len(texts):
            raise ValueError(
                "Embedding provider returned an unexpected "
                "number of embeddings"
            )

        processed = 0

        for chunk, embedding in zip(
            chunks_needing_embedding,
            embeddings,
        ):

            if len(embedding) != EMBEDDING_DIMENSIONS:
                raise ValueError(
                    f"Invalid embedding dimensions: "
                    f"expected {EMBEDDING_DIMENSIONS}, "
                    f"got {len(embedding)}"
                )

            chunk.text_hash = calculate_text_hash(
                chunk.text
            )

            chunk.embedding = embedding

            processed += 1

        db.commit()

        return {
            "status": "embedded",
            "processed": processed,
            "skipped": len(chunks) - processed,
            "content_chunk_ids": [
                chunk.content_chunk_id
                for chunk in chunks_needing_embedding
            ],
        }

    finally:
        db.close()