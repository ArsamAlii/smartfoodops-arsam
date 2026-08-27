import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.content_chunk import ContentChunk
from app.models.menu_category import MenuCategory
from app.models.restaurant import Restaurant
from app.services.embedding_service import generate_embedding

def build_menu_item_text(
    restaurant: Restaurant,
    category: MenuCategory,
    menu_item,
) -> str:
    """
    Build the enriched text that will later be embedded.

    Each chunk contains enough context to be meaningful on its own.
    """

    parts = [
        f"Restaurant: {restaurant.name}",
        f"Cuisine: {restaurant.cuisine}",
        f"Category: {category.name}",
        f"Menu item: {menu_item.name}",
    ]

    if menu_item.description:
        parts.append(
            f"Description: {menu_item.description}"
        )

    return ". ".join(parts)


def calculate_text_hash(text: str) -> str:
    """
    SHA-256 hash of the embedding input text.

    Used later to skip re-embedding unchanged menu items.
    """

    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def estimate_token_count(text: str) -> int:
    """
    Lightweight token estimate.

    This is intentionally simple because the actual embedding
    provider will be responsible for generating embeddings.
    """

    return len(text.split())


def rebuild_restaurant_chunks(
    db: Session,
    restaurant_id: int,
) -> int:
    """
    Synchronize content_chunks with the restaurant's current menu.

    Behaviour:

    1. Creates one enriched chunk per menu item.
    2. Stores restaurant/menu metadata.
    3. Preserves existing chunks when their text is unchanged.
    4. Updates metadata when price/availability changes.
    5. Removes chunks for deleted menu items.
    6. Never creates duplicate chunks for the same menu item.
    """

    restaurant = db.get(
        Restaurant,
        restaurant_id,
    )

    if restaurant is None:
        raise ValueError("Restaurant not found")

    categories = (
        db.query(MenuCategory)
        .options(joinedload(MenuCategory.menu_items))
        .filter(
            MenuCategory.restaurant_id == restaurant_id
        )
        .order_by(
            MenuCategory.order_index,
            MenuCategory.category_id,
        )
        .all()
    )

    # ---------------------------------------------------------
    # Existing chunks indexed by menu_item_id
    # ---------------------------------------------------------

    existing_chunks = (
        db.query(ContentChunk)
        .filter(
            ContentChunk.restaurant_id == restaurant_id
        )
        .all()
    )

    existing_by_item = {
        chunk.menu_item_id: chunk
        for chunk in existing_chunks
    }

    current_menu_item_ids: set[int] = set()

    chunks_created = 0
    chunks_updated = 0
    chunks_unchanged = 0

    # ---------------------------------------------------------
    # Build/update one chunk per menu item
    # ---------------------------------------------------------

    for category in categories:

        menu_items = sorted(
            category.menu_items,
            key=lambda item: (
                item.order_index,
                item.menu_item_id,
            ),
        )

        for menu_item in menu_items:

            current_menu_item_ids.add(
                menu_item.menu_item_id
            )

            text = build_menu_item_text(
                restaurant=restaurant,
                category=category,
                menu_item=menu_item,
            )

            text_hash = calculate_text_hash(text)

            existing = existing_by_item.get(
                menu_item.menu_item_id
            )

            # -------------------------------------------------
            # Existing chunk
            # -------------------------------------------------

            if existing is not None:

                # The embedding input hasn't changed.
                # Keep the existing vector.
                if existing.text_hash == text_hash:
                    existing.category = category.name
                    existing.cuisine = restaurant.cuisine
                    existing.price = menu_item.price
                    existing.is_available = (
                        menu_item.is_available
                    )
                    existing.token_count = (
                        estimate_token_count(text)
                    )

                    chunks_unchanged += 1

                # The actual text changed.
                # Clear the old embedding so the Celery
                # embedding task knows it needs re-embedding.
                else:
                    existing.category = category.name
                    existing.cuisine = restaurant.cuisine
                    existing.price = menu_item.price
                    existing.is_available = (
                        menu_item.is_available
                    )
                    existing.text = text
                    existing.token_count = (
                        estimate_token_count(text)
                    )
                    existing.text_hash = text_hash
                    existing.embedding = None

                    chunks_updated += 1

                continue

            # -------------------------------------------------
            # New chunk
            # -------------------------------------------------

            chunk = ContentChunk(
                restaurant_id=restaurant_id,
                menu_item_id=menu_item.menu_item_id,
                category=category.name,
                cuisine=restaurant.cuisine,
                price=menu_item.price,
                is_available=menu_item.is_available,
                chunk_index=0,
                text=text,
                token_count=estimate_token_count(text),
                text_hash=text_hash,
                embedding=None,
            )

            db.add(chunk)

            chunks_created += 1

    # ---------------------------------------------------------
    # Remove stale chunks
    #
    # These correspond to menu items that no longer exist.
    # ---------------------------------------------------------

    for chunk in existing_chunks:

        if chunk.menu_item_id not in current_menu_item_ids:
            db.delete(chunk)

    db.commit()

    return (
        chunks_created
        + chunks_updated
        + chunks_unchanged
    )

def search_content_chunks(
    db: Session,
    query: str,
    restaurant_id: int | None = None,
    limit: int = 5,
) -> list[ContentChunk]:
    """
    Search menu content using semantic similarity.

    The user query is converted into a 384-dimensional
    embedding and compared against stored pgvector embeddings.
    """

    query_embedding = generate_embedding(query)

    similarity = ContentChunk.embedding.cosine_distance(
        query_embedding
    )

    statement = (
        select(ContentChunk)
        .where(
            ContentChunk.embedding.is_not(None),
            ContentChunk.is_available.is_(True),
        )
        .order_by(similarity)
        .limit(limit)
    )

    if restaurant_id is not None:
        statement = statement.where(
            ContentChunk.restaurant_id == restaurant_id
        )

    return list(
        db.scalars(statement).all()
    )