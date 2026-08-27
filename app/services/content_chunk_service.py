import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.content_chunk import ContentChunk
from app.models.menu_category import MenuCategory
from app.models.restaurant import Restaurant

from app.services.embedding_service import generate_embedding

from app.models.enums import UserRole
from app.models.users import User
# ---------------------------------------------------------
# Build Menu Item Text
# ---------------------------------------------------------
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


# ---------------------------------------------------------
# Calculate Text Hash
# ---------------------------------------------------------
def calculate_text_hash(text: str) -> str:
    """
    SHA-256 hash of the embedding input text.

    Used to determine whether an existing embedding
    is still valid.
    """

    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


# ---------------------------------------------------------
# Estimate Token Count
# ---------------------------------------------------------
def estimate_token_count(text: str) -> int:
    """
    Lightweight token estimate.

    The actual embedding provider is responsible
    for generating the embedding.
    """

    return len(text.split())

def rebuild_restaurant_chunks(
    db: Session,
    restaurant_id: int,
) -> list[int]:
    """
    Synchronize content_chunks with the restaurant's
    current menu.

    Returns:
        List of content_chunk_id values that require
        a new embedding.

    A chunk requires embedding when:

        - it is newly created
        - its embedding input text changed

    If only metadata such as price or availability changes,
    the existing embedding is preserved.
    """

    # ---------------------------------------------------------
    # Find restaurant
    # ---------------------------------------------------------

    restaurant = db.get(
        Restaurant,
        restaurant_id,
    )

    if restaurant is None:
        raise ValueError("Restaurant not found")

    # ---------------------------------------------------------
    # Load categories and menu items
    # ---------------------------------------------------------

    categories = (
        db.query(MenuCategory)
        .options(
            joinedload(MenuCategory.menu_items)
        )
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
    # Existing chunks
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

    chunks_needing_embedding: list[int] = []

    # ---------------------------------------------------------
    # Process menu items
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

            # -------------------------------------------------
            # Build enriched embedding text
            # -------------------------------------------------

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

                # ---------------------------------------------
                # Text did NOT change
                # ---------------------------------------------

                if existing.text_hash == text_hash:

                    existing.category = category.name

                    existing.cuisine = (
                        restaurant.cuisine
                    )

                    existing.price = (
                        menu_item.price
                    )

                    existing.is_available = (
                        menu_item.is_available
                    )

                    existing.token_count = (
                        estimate_token_count(text)
                    )

                # ---------------------------------------------
                # Text changed
                # ---------------------------------------------

                else:

                    existing.category = category.name

                    existing.cuisine = (
                        restaurant.cuisine
                    )

                    existing.price = (
                        menu_item.price
                    )

                    existing.is_available = (
                        menu_item.is_available
                    )

                    existing.text = text

                    existing.token_count = (
                        estimate_token_count(text)
                    )

                    existing.text_hash = text_hash

                    # Old embedding is no longer valid.
                    existing.embedding = None

                    chunks_needing_embedding.append(
                        existing.content_chunk_id
                    )

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

            # Force SQLAlchemy to obtain the generated ID.
            db.flush()

            chunks_needing_embedding.append(
                chunk.content_chunk_id
            )

    # ---------------------------------------------------------
    # Remove stale chunks
    # ---------------------------------------------------------

    for chunk in existing_chunks:

        if (
            chunk.menu_item_id
            not in current_menu_item_ids
        ):
            db.delete(chunk)

    # ---------------------------------------------------------
    # Save all database changes
    # ---------------------------------------------------------

    db.commit()

    return chunks_needing_embedding


# ---------------------------------------------------------
# Semantic Search
# ---------------------------------------------------------
def search_content_chunks(
    db: Session,
    query: str,
    current_user: User,
    limit: int = 5,
    similarity_threshold: float = 0.30,
) -> list[tuple[ContentChunk, float]]:
    """
    Search menu content using semantic similarity.

    Customer:
        - only available items
        - only open restaurants

    Restaurant admin:
        - only their own restaurant
        - may see unavailable items
        - may see items even when their restaurant is closed

    All filtering is performed in the database query.
    """

    # -----------------------------------------------------
    # Generate query embedding
    # -----------------------------------------------------

    query_embedding = generate_embedding(query)

    # -----------------------------------------------------
    # Calculate cosine similarity
    # -----------------------------------------------------

    distance = ContentChunk.embedding.cosine_distance(
        query_embedding
    )

    similarity = 1 - distance

    # -----------------------------------------------------
    # Base query
    # -----------------------------------------------------

    statement = (
        select(
            ContentChunk,
            similarity.label("similarity"),
        )
        .join(
            Restaurant,
            Restaurant.restaurant_id
            == ContentChunk.restaurant_id,
        )
        .where(
            ContentChunk.embedding.is_not(None),
            similarity >= similarity_threshold,
        )
    )

    # -----------------------------------------------------
    # Customer access rules
    # -----------------------------------------------------

    if current_user.role == UserRole.CUSTOMER:

        statement = statement.where(
            ContentChunk.is_available.is_(True),
            Restaurant.is_open.is_(True),
        )

    # -----------------------------------------------------
    # Restaurant admin access rules
    # -----------------------------------------------------

    elif current_user.role == UserRole.RESTAURANT_ADMIN:

        statement = statement.where(
            Restaurant.user_id == current_user.user_id,
        )

    # -----------------------------------------------------
    # Other roles
    # -----------------------------------------------------

    else:

        statement = statement.where(
            False,
        )

    # -----------------------------------------------------
    # Ranking
    # -----------------------------------------------------

    statement = (
        statement
        .order_by(distance)
        .limit(limit)
    )

    return list(
        db.execute(statement).all()
    )