from app.workers.celery_app import celery_app
from app.db.database import SessionLocal
from app.models.content_chunk import ContentChunk
from app.services.embedding_service import embed_content_chunk


@celery_app.task(
    bind=True,
    autoretry_for=(ConnectionError,),
    retry_backoff=True,
    max_retries=3,
)
def embed_content_chunk_task(self, content_chunk_id: int):
    """
    Generate an embedding for one content chunk.

    Celery handles the background execution while the
    actual embedding logic remains in embedding_service.py.
    """

    db = SessionLocal()

    try:
        chunk = (
            db.query(ContentChunk)
            .filter(
                ContentChunk.content_chunk_id
                == content_chunk_id
            )
            .first()
        )

        if chunk is None:
            return {
                "status": "not_found",
                "content_chunk_id": content_chunk_id,
            }

        embed_content_chunk(
            db,
            chunk,
        )

        return {
            "status": "embedded",
            "content_chunk_id": content_chunk_id,
        }

    finally:
        db.close()