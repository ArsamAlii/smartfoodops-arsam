# FastAPI utilities
from fastapi import APIRouter, Depends, HTTPException
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

@router.post("/", response_model=RestaurantResponse)
def create_new_restaurant(
    restaurant_data: RestaurantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.RESTAURANT_ADMIN)
    ),
):
    restaurant = create_restaurant(
        db=db,
        restaurant_data=restaurant_data,
        owner=current_user,
    )

    return restaurant


# ==================================================================
# GET ALL RESTAURANTS
# ==================================================================
# Public endpoint.
# ==================================================================

@router.get("/", response_model=list[RestaurantResponse])
def get_all_restaurants(
    db: Session = Depends(get_db),
):

    restaurants = get_restaurants(db)

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

    if restaurant is None:
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

    return restaurant

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