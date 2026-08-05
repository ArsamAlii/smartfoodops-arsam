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

    for key, value in update_data.items():
        setattr(
            restaurant,
            key,
            value,
        )

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