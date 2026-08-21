# FastAPI utilities
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

# Database dependency
from app.db.database import get_db

# Authentication & Authorization dependencies
from app.api.dependencies import (
    get_current_user,
    require_role,
)

# User model
from app.models.users import User
from app.models.restaurant import Restaurant
from app.models.menu_category import MenuCategory

# User Roles
from app.models.enums import UserRole

# Restaurant schemas
from app.schemas.restaurant import (
    RestaurantCreate,
    RestaurantUpdate,
    RestaurantResponse,
)

# Business logic (service layer)
from app.services.restaurant_service import (
    create_restaurant,
    get_restaurants,
    get_restaurant,
    update_restaurant,
    delete_restaurant,
)
from app.services.content_chunk_service import rebuild_restaurant_chunks

# ------------------------------------------------------------------
# Router Configuration
# ------------------------------------------------------------------

router = APIRouter(
    prefix="/restaurants",
    tags=["Restaurants"],
)

# ==================================================================
# CREATE RESTAURANT
# ==================================================================
# Only Restaurant Admins can create restaurants.
# ==================================================================

@router.post(
    "/",
    response_model=RestaurantResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_new_restaurant(
    restaurant_data: RestaurantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.RESTAURANT_ADMIN)),
):
    try:
        restaurant = create_restaurant(
            db=db,
            restaurant_data=restaurant_data,
            owner=current_user,
        )

        return restaurant

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

# ==================================================================
# GET ALL RESTAURANTS
# ==================================================================
# Public endpoint.
# ==================================================================

@router.get("/", response_model=list[RestaurantResponse])
def get_all_restaurants(
    cuisine: str | None = None,
    search: str | None = None,
    open_now: bool = True,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):

    restaurants = get_restaurants(
        db, cuisine=cuisine, search=search, open_now=open_now,
        offset=offset, limit=limit,
    )

    return restaurants


# ==================================================================
# GET SINGLE RESTAURANT
# ==================================================================

@router.get("/{restaurant_id}", response_model=RestaurantResponse)
def get_single_restaurant(
    restaurant_id: int,
    db: Session = Depends(get_db),
):

    restaurant = get_restaurant(
        db,
        restaurant_id,
    )

    if restaurant is None or not restaurant.is_open:
        raise HTTPException(
            status_code=404,
            detail="Restaurant not found",
        )

    return restaurant


# ==================================================================
# UPDATE RESTAURANT
# ==================================================================
# Only the Restaurant Admin who owns the restaurant
# can update it.
# ==================================================================

@router.put("/{restaurant_id}", response_model=RestaurantResponse)
def update_single_restaurant(
    restaurant_id: int,
    restaurant_data: RestaurantUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.RESTAURANT_ADMIN)
    ),
):

    restaurant = get_restaurant(
        db,
        restaurant_id,
    )

    if restaurant is None:
        raise HTTPException(
            status_code=404,
            detail="Restaurant not found",
        )

    # Ownership check
    if restaurant.user_id != current_user.user_id:
        raise HTTPException(
            status_code=403,
            detail="You do not own this restaurant",
        )

    restaurant = update_restaurant(
        db,
        restaurant,
        restaurant_data,
    )

    if restaurant.is_open:
        rebuild_restaurant_chunks(db, restaurant.restaurant_id)

    return restaurant


@router.get("/{restaurant_id}/menu")
def get_public_menu(restaurant_id: int, db: Session = Depends(get_db)):
    """Only expose orderable items from an open restaurant to customers."""
    restaurant = (
        db.query(Restaurant)
        .filter(Restaurant.restaurant_id == restaurant_id, Restaurant.is_open.is_(True))
        .first()
    )
    if restaurant is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    categories = (
        db.query(MenuCategory)
        .filter(MenuCategory.restaurant_id == restaurant_id)
        .order_by(MenuCategory.order_index, MenuCategory.category_id)
        .all()
    )
    return {
        "restaurant_id": restaurant.restaurant_id,
        "categories": [
            {
                "category_id": category.category_id,
                "name": category.name,
                "items": [
                    {
                        "menu_item_id": item.menu_item_id,
                        "name": item.name,
                        "description": item.description,
                        "price": str(item.price),
                        "stock": item.stock,
                    }
                    for item in sorted(
                        (item for item in category.menu_items if item.is_available),
                        key=lambda item: (item.order_index, item.menu_item_id),
                    )
                ],
            }
            for category in categories
        ],
    }


@router.post("/{restaurant_id}/publish", status_code=status.HTTP_202_ACCEPTED)
def publish_menu(
    restaurant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.RESTAURANT_ADMIN)),
):
    restaurant = db.get(Restaurant, restaurant_id)
    if restaurant is None or restaurant.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="You do not own this restaurant")
    restaurant.is_open = True
    db.commit()
    return {"restaurant_id": restaurant_id, "chunks_created": rebuild_restaurant_chunks(db, restaurant_id)}

# ==================================================================
# DELETE RESTAURANT
# ==================================================================
# Only the Restaurant Admin who owns the restaurant
# can delete it.
# ==================================================================

@router.delete("/{restaurant_id}")
def delete_single_restaurant(
    restaurant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.RESTAURANT_ADMIN)
    ),
):

    restaurant = get_restaurant(
        db,
        restaurant_id,
    )

    if restaurant is None:
        raise HTTPException(
            status_code=404,
            detail="Restaurant not found",
        )

    # Ownership check
    if restaurant.user_id != current_user.user_id:
        raise HTTPException(
            status_code=403,
            detail="You do not own this restaurant",
        )

    delete_restaurant(
        db,
        restaurant,
    )

    return {
        "message": "Restaurant deleted successfully"
    }
