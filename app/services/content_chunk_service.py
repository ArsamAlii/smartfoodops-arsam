from sqlalchemy.orm import Session, joinedload

from app.models.content_chunk import ContentChunk
from app.models.menu_category import MenuCategory
from app.models.restaurant import Restaurant


def rebuild_restaurant_chunks(db: Session, restaurant_id: int) -> int:
    """Replace deterministic, search-ready chunks when a menu is made live."""
    restaurant = db.get(Restaurant, restaurant_id)
    if restaurant is None:
        raise ValueError("Restaurant not found")

    db.query(ContentChunk).filter(ContentChunk.restaurant_id == restaurant_id).delete()
    entries = [(None, "restaurant", " ".join(
        part for part in [restaurant.name, restaurant.description, restaurant.cuisine] if part
    ))]
    categories = (
        db.query(MenuCategory)
        .options(joinedload(MenuCategory.menu_items))
        .filter(MenuCategory.restaurant_id == restaurant_id)
        .order_by(MenuCategory.order_index)
        .all()
    )
    for category in categories:
        for item in sorted(category.menu_items, key=lambda value: (value.order_index, value.menu_item_id)):
            if item.is_available:
                entries.append((item.menu_item_id, category.name, " ".join(
                    part for part in [item.name, item.description] if part
                )))
    for item_id, category, text in entries:
        db.add(ContentChunk(
            restaurant_id=restaurant_id, menu_item_id=item_id, category=category,
            chunk_index=0, text=text, token_count=len(text.split()),
        ))
    db.commit()
    return len(entries)
