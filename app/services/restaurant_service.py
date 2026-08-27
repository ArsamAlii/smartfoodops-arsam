from sqlalchemy.orm import Session

from app.models.restaurant import Restaurant
from app.models.users import User

from app.schemas.restaurant import (
    RestaurantCreate,
    RestaurantUpdate,
)

from app.services.content_chunk_service import (
    rebuild_restaurant_chunks,
)

from app.workers.embedding_tasks import (
    embed_content_chunk_task,
)


# -------------------------------------------------------
# Create Restaurant
# -------------------------------------------------------
def create_restaurant(
    db: Session,
    restaurant_data: RestaurantCreate,
    owner: User,
) -> Restaurant:
    """
    Create a new restaurant for the authenticated user.

    A newly created restaurant normally has no menu items,
    so there are no content chunks to embed yet.
    """

    # ---------------------------------------------------
    # Check for duplicate restaurant
    # ---------------------------------------------------

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

    # ---------------------------------------------------
    # Create restaurant
    # ---------------------------------------------------

    restaurant = Restaurant(
        user_id=owner.user_id,
        name=restaurant_data.name,
        cuisine=restaurant_data.cuisine,
        address=restaurant_data.address,
        description=restaurant_data.description,
        operating_hours=restaurant_data.operating_hours,
    )

    db.add(restaurant)
    db.commit()
    db.refresh(restaurant)

    return restaurant


# -------------------------------------------------------
# Get Restaurants
# -------------------------------------------------------
def get_restaurants(
    db: Session,
    *,
    cuisine: str | None = None,
    search: str | None = None,
    open_now: bool = True,
    offset: int = 0,
    limit: int = 20,
):
    """
    Return restaurants.
    """

    query = db.query(Restaurant)

    if open_now:
        query = query.filter(
            Restaurant.is_open.is_(True)
        )

    if cuisine:
        query = query.filter(
            Restaurant.cuisine.ilike(
                f"%{cuisine}%"
            )
        )

    if search:
        query = query.filter(
            Restaurant.name.ilike(
                f"%{search}%"
            )
        )

    return (
        query
        .order_by(Restaurant.name)
        .offset(offset)
        .limit(limit)
        .all()
    )


# -------------------------------------------------------
# Get Single Restaurant
# -------------------------------------------------------
def get_restaurant(
    db: Session,
    restaurant_id: int,
):
    """
    Return a single restaurant by ID.
    """

    return (
        db.query(Restaurant)
        .filter(
            Restaurant.restaurant_id == restaurant_id
        )
        .first()
    )


# -------------------------------------------------------
# Update Restaurant
# -------------------------------------------------------
def update_restaurant(
    db: Session,
    restaurant: Restaurant,
    restaurant_data: RestaurantUpdate,
) -> Restaurant:
    """
    Update an existing restaurant.

    If fields used by menu-item embeddings change,
    the restaurant's content chunks are rebuilt.

    The embedding text contains:

        Restaurant: <name>
        Cuisine: <cuisine>
        Category: <category>
        Menu item: <name>
        Description: <description>

    Therefore changing the restaurant name or cuisine
    invalidates the existing menu-item embeddings.
    """

    # ---------------------------------------------------
    # Extract only supplied fields
    # ---------------------------------------------------

    update_data = restaurant_data.model_dump(
        exclude_unset=True
    )

    # ---------------------------------------------------
    # Check duplicate name + address
    # ---------------------------------------------------

    new_name = update_data.get(
        "name",
        restaurant.name,
    )

    new_address = update_data.get(
        "address",
        restaurant.address,
    )

    existing_restaurant = (
        db.query(Restaurant)
        .filter(
            Restaurant.name == new_name,
            Restaurant.address == new_address,
            Restaurant.restaurant_id
            != restaurant.restaurant_id,
        )
        .first()
    )

    if existing_restaurant:
        raise ValueError(
            "A restaurant with the same name and address already exists."
        )

    # ---------------------------------------------------
    # Apply updates
    # ---------------------------------------------------

    for key, value in update_data.items():
        setattr(
            restaurant,
            key,
            value,
        )

    db.commit()
    db.refresh(restaurant)

    # ---------------------------------------------------
    # Synchronize ContentChunks
    # ---------------------------------------------------

    chunks_needing_embedding = (
        rebuild_restaurant_chunks(
            db,
            restaurant.restaurant_id,
        )
    )

    # ---------------------------------------------------
    # Queue changed embeddings
    # ---------------------------------------------------

    for content_chunk_id in chunks_needing_embedding:

        embed_content_chunk_task.delay(
            content_chunk_id
        )

    return restaurant


# -------------------------------------------------------
# Delete Restaurant
# -------------------------------------------------------
def delete_restaurant(
    db: Session,
    restaurant: Restaurant,
):
    """
    Delete a restaurant.

    Its associated menu/content data should be handled
    according to the database relationship configuration.
    """

    db.delete(restaurant)
    db.commit()