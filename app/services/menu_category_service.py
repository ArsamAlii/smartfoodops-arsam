from sqlalchemy.orm import Session

from app.models.menu_category import MenuCategory
from app.models.restaurant import Restaurant

from app.services.content_chunk_service import (
    rebuild_restaurant_chunks,
)

from app.workers.embedding_tasks import (
    embed_content_chunk_task,
)


# -------------------------------------------------------
# Create Category
# -------------------------------------------------------
def create_category(
    db: Session,
    restaurant_id: int,
    name: str,
) -> MenuCategory:

    # ---------------------------------------------------
    # Verify restaurant exists
    # ---------------------------------------------------

    restaurant = (
        db.query(Restaurant)
        .filter(
            Restaurant.restaurant_id == restaurant_id
        )
        .first()
    )

    if restaurant is None:
        raise ValueError("Restaurant not found")

    # ---------------------------------------------------
    # Create category
    # ---------------------------------------------------

    category = MenuCategory(
        restaurant_id=restaurant_id,
        name=name,
    )

    db.add(category)
    db.commit()
    db.refresh(category)

    # ---------------------------------------------------
    # Synchronize ContentChunks
    #
    # A new category does not necessarily have menu items,
    # but rebuilding keeps the restaurant index consistent.
    # ---------------------------------------------------

    chunks_needing_embedding = (
        rebuild_restaurant_chunks(
            db,
            restaurant_id,
        )
    )

    # ---------------------------------------------------
    # Queue required embedding jobs
    # ---------------------------------------------------

    for content_chunk_id in chunks_needing_embedding:

        embed_content_chunk_task.delay(
            content_chunk_id
        )

    return category


# -------------------------------------------------------
# Get Categories by Restaurant
# -------------------------------------------------------
def get_categories_by_restaurant(
    db: Session,
    restaurant_id: int,
):

    return (
        db.query(MenuCategory)
        .filter(
            MenuCategory.restaurant_id == restaurant_id
        )
        .order_by(
            MenuCategory.order_index,
            MenuCategory.category_id,
        )
        .all()
    )


# -------------------------------------------------------
# Get Single Category
# -------------------------------------------------------
def get_category(
    db: Session,
    category_id: int,
):

    category = (
        db.query(MenuCategory)
        .filter(
            MenuCategory.category_id == category_id
        )
        .first()
    )

    if category is None:
        raise ValueError(
            "Category not found"
        )

    return category


# -------------------------------------------------------
# Update Category
# -------------------------------------------------------
def update_category(
    db: Session,
    category: MenuCategory,
    name: str,
):

    # ---------------------------------------------------
    # Update category name
    # ---------------------------------------------------

    category.name = name

    db.commit()
    db.refresh(category)

    # ---------------------------------------------------
    # Rebuild restaurant content chunks
    #
    # Category name is part of the embedding text:
    #
    # Category: Main Course
    #
    # Therefore changing the category name makes the
    # existing menu-item embedding stale.
    # ---------------------------------------------------

    chunks_needing_embedding = (
        rebuild_restaurant_chunks(
            db,
            category.restaurant_id,
        )
    )

    # ---------------------------------------------------
    # Queue only chunks whose embedding text changed
    # ---------------------------------------------------

    for content_chunk_id in chunks_needing_embedding:

        embed_content_chunk_task.delay(
            content_chunk_id
        )

    return category


# -------------------------------------------------------
# Delete Category
# -------------------------------------------------------
def delete_category(
    db: Session,
    category: MenuCategory,
):

    # ---------------------------------------------------
    # Save restaurant ID before deletion
    # ---------------------------------------------------

    restaurant_id = category.restaurant_id

    # ---------------------------------------------------
    # Delete category
    #
    # Depending on your SQLAlchemy relationship/cascade
    # configuration, its menu items may also be deleted.
    # ---------------------------------------------------

    db.delete(category)
    db.commit()

    # ---------------------------------------------------
    # Remove stale ContentChunks
    # ---------------------------------------------------

    rebuild_restaurant_chunks(
        db,
        restaurant_id,
    )