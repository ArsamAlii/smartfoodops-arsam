from sqlalchemy.orm import Session

from app.models.menu_item import MenuItem
from app.models.menu_category import MenuCategory


# -------------------------------------------------------
# Create Menu Item
# -------------------------------------------------------
def create_menu_item(
    db: Session,
    category_id: int,
    item_data,
) -> MenuItem:

    # Verify category exists
    category = (
        db.query(MenuCategory)
        .filter(MenuCategory.category_id == category_id)
        .first()
    )

    if category is None:
        raise ValueError("Category not found")

    menu_item = MenuItem(
        category_id=category_id,
        name=item_data.name,
        description=item_data.description,
        price=item_data.price,
        stock=item_data.stock,
        order_index=item_data.order_index,
        image_url=item_data.image_url,
        is_available=item_data.is_available,
    )

    db.add(menu_item)
    db.commit()
    db.refresh(menu_item)

    return menu_item


# -------------------------------------------------------
# Get All Menu Items of a Category
# -------------------------------------------------------
def get_menu_items_by_category(
    db: Session,
    category_id: int,
):

    return (
        db.query(MenuItem)
        .filter(MenuItem.category_id == category_id)
        .order_by(MenuItem.order_index, MenuItem.menu_item_id)
        .all()
    )


# -------------------------------------------------------
# Get Single Menu Item
# -------------------------------------------------------
def get_menu_item(
    db: Session,
    menu_item_id: int,
) -> MenuItem:

    menu_item = (
        db.query(MenuItem)
        .filter(MenuItem.menu_item_id == menu_item_id)
        .first()
    )

    if menu_item is None:
        raise ValueError("Menu item not found")

    return menu_item


# -------------------------------------------------------
# Update Menu Item
# -------------------------------------------------------
def update_menu_item(
    db: Session,
    menu_item: MenuItem,
    item_data,
) -> MenuItem:

    if item_data.name is not None:
        menu_item.name = item_data.name

    if item_data.description is not None:
        menu_item.description = item_data.description

    if item_data.price is not None:
        menu_item.price = item_data.price

    if item_data.stock is not None:
        menu_item.stock = item_data.stock

    if item_data.order_index is not None:
        menu_item.order_index = item_data.order_index

    if item_data.image_url is not None:
        menu_item.image_url = item_data.image_url

    if item_data.is_available is not None:
        menu_item.is_available = item_data.is_available

    db.commit()
    db.refresh(menu_item)

    return menu_item


# -------------------------------------------------------
# Delete Menu Item
# -------------------------------------------------------
def delete_menu_item(
    db: Session,
    menu_item: MenuItem,
):

    db.delete(menu_item)
    db.commit()
