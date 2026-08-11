from sqlalchemy.orm import Session

from app.models.restaurant import Restaurant
from app.models.users import User
from app.schemas.restaurant import (
    RestaurantCreate,
    RestaurantUpdate,
)


def create_restaurant(
    db: Session,
    restaurant_data: RestaurantCreate,
    owner: User,
) -> Restaurant:
    """
    Create a new restaurant for the authenticated user.
    """
    # -------------------------------------------------------
    # 1. Check for duplicate restaurant
    # -------------------------------------------------------
    existing_restaurant = (
        db.query(Restaurant)
        .filter(
            Restaurant.name == restaurant_data.name,
            Restaurant.address == restaurant_data.address,
        )
        .first()
    )

    if existing_restaurant:
        raise ValueError(
            "A restaurant with the same name and address already exists."
        )

    restaurant = Restaurant(
        user_id=owner.user_id,
        name=restaurant_data.name,
        cuisine=restaurant_data.cuisine,
        address=restaurant_data.address,
    )

    db.add(restaurant)
    db.commit()
    db.refresh(restaurant)

    return restaurant


def get_restaurants(
    db: Session,
):
    """
    Return all restaurants.
    """

    return db.query(Restaurant).all()


def get_restaurant(
    db: Session,
    restaurant_id: int,
):
    """
    Return a single restaurant by ID.
    """

    return (
        db.query(Restaurant)
        .filter(Restaurant.restaurant_id == restaurant_id)
        .first()
    )

def update_restaurant(
    db: Session,
    restaurant: Restaurant,
    restaurant_data: RestaurantUpdate,
) -> Restaurant:
    """
    Update an existing restaurant.
    """

    update_data = restaurant_data.model_dump(
        exclude_unset=True
    )

    # -------------------------------------------------------
    # Check duplicate name + address
    # -------------------------------------------------------
    new_name = update_data.get("name", restaurant.name)
    new_address = update_data.get("address", restaurant.address)

    existing_restaurant = (
        db.query(Restaurant)
        .filter(
            Restaurant.name == new_name,
            Restaurant.address == new_address,
            Restaurant.restaurant_id != restaurant.restaurant_id,
        )
        .first()
    )

    if existing_restaurant:
        raise ValueError(
            "A restaurant with the same name and address already exists."
        )

    # -------------------------------------------------------
    # Apply updates
    # -------------------------------------------------------
    for key, value in update_data.items():
        setattr(restaurant, key, value)

    db.commit()
    db.refresh(restaurant)

    return restaurant

def delete_restaurant(
    db: Session,
    restaurant: Restaurant,
):
    """
    Delete a restaurant.
    """

    db.delete(restaurant)
    db.commit()