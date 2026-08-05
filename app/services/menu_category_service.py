from sqlalchemy.orm import Session

from app.models.menu_category import MenuCategory
from app.models.restaurant import Restaurant


def create_category(db: Session, restaurant_id: int, name: str) -> MenuCategory:

    restaurant = (
        db.query(Restaurant)
        .filter(Restaurant.restaurant_id == restaurant_id)
        .first()
    )

    if restaurant is None:
        raise ValueError("Restaurant not found")

    category = MenuCategory(
        restaurant_id=restaurant_id,
        name=name,
    )

    db.add(category)
    db.commit()
    db.refresh(category)

    return category


def get_categories_by_restaurant(
    db: Session,
    restaurant_id: int,
):

    return (
        db.query(MenuCategory)
        .filter(MenuCategory.restaurant_id == restaurant_id)
        .all()
    )


def get_category(
    db: Session,
    category_id: int,
):

    category = (
        db.query(MenuCategory)
        .filter(MenuCategory.category_id == category_id)
        .first()
    )

    if category is None:
        raise ValueError("Category not found")

    return category


def update_category(
    db: Session,
    category: MenuCategory,
    name: str,
):

    category.name = name

    db.commit()
    db.refresh(category)

    return category


def delete_category(
    db: Session,
    category: MenuCategory,
):

    db.delete(category)
    db.commit()