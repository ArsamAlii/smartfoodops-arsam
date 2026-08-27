from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.database import get_db

from app.models.restaurant import Restaurant
from app.models.menu_item import MenuItem
from app.models.users import User
import os
from app.schemas.ai import (
    AIAskRequest,
    AIAskResponse,
    AISource,
)

from app.services.content_chunk_service import (
    search_content_chunks,
)

from app.services.llm_service import (
    generate_answer,
)


router = APIRouter(
    prefix="/ai",
    tags=["AI"],
)


@router.post(
    "/ask",
    response_model=AIAskResponse,
)
def ask_ai(
    request: AIAskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # ---------------------------------------------------------
    # 1. Semantic search
    # ---------------------------------------------------------

    retrieval_top_k = int(
        os.getenv("RETRIEVAL_TOP_K", "5")
    )

    retrieval_min_similarity = float(
        os.getenv("RETRIEVAL_MIN_SIMILARITY", "0.30")
    )

    results = search_content_chunks(
        db=db,
        query=request.question,
        limit=retrieval_top_k,
        similarity_threshold=retrieval_min_similarity,
    )

    # ---------------------------------------------------------
    # 2. Build context for the LLM
    # ---------------------------------------------------------

    context_parts = []

    sources = []

    for chunk, similarity in results:

        restaurant = db.get(
            Restaurant,
            chunk.restaurant_id,
        )

        menu_item = db.get(
            MenuItem,
            chunk.menu_item_id,
        )

        if restaurant is None or menu_item is None:
            continue

        context_parts.append(
            (
                f"Restaurant: {restaurant.name}\n"
                f"Cuisine: {chunk.cuisine}\n"
                f"Category: {chunk.category}\n"
                f"Menu item: {menu_item.name}\n"
                f"Description: {menu_item.description or 'N/A'}\n"
                f"Price: {menu_item.price}\n"
                f"Available: {menu_item.is_available}\n"
            )
        )

        sources.append(
            AISource(
                menu_item_id=chunk.menu_item_id,
                restaurant_id=chunk.restaurant_id,
                restaurant=restaurant.name,
                name=menu_item.name,
                category=chunk.category,
                price=str(chunk.price),
                is_available=chunk.is_available,
                similarity=float(similarity),
            )
        )

    # ---------------------------------------------------------
    # 3. No relevant results
    # ---------------------------------------------------------

    if not context_parts:
        return AIAskResponse(
            question=request.question,
            answer=(
                "I could not find relevant information "
                "in the available restaurant menus."
            ),
            sources=[],
        )

    # ---------------------------------------------------------
    # 4. Combine retrieved chunks
    # ---------------------------------------------------------

    context = "\n---\n".join(
        context_parts
    )

    # ---------------------------------------------------------
    # 5. Generate answer using Groq
    # ---------------------------------------------------------

    answer = generate_answer(
        question=request.question,
        context=context,
    )

    # ---------------------------------------------------------
    # 6. Return answer + sources
    # ---------------------------------------------------------

    return AIAskResponse(
        question=request.question,
        answer=answer,
        sources=sources,
    )