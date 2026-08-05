# FastAPI utilities
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

# Database dependency
from app.db.database import get_db

# JWT dependency (returns the logged-in user)
from app.api.dependencies import get_current_user

# User model (used for authentication)
from app.models.users import User

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
# Only authenticated users with role "owner"
# are allowed to create restaurants.
# ==================================================================

@router.post("/", response_model=RestaurantResponse)
def create_new_restaurant(
    restaurant_data: RestaurantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Only owners can create restaurants
    if current_user.role != "owner":
        raise HTTPException(
            status_code=403,
            detail="Only restaurant owners can create restaurants",
        )

    # Call service layer
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
# Returns every restaurant in the database.
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
# Returns one restaurant by ID.
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
# Only the owner of the restaurant can update it.
# ==================================================================

@router.put("/{restaurant_id}", response_model=RestaurantResponse)
def update_single_restaurant(
    restaurant_id: int,
    restaurant_data: RestaurantUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    # Check if restaurant exists
    restaurant = get_restaurant(
        db,
        restaurant_id,
    )

    if restaurant is None:
        raise HTTPException(
            status_code=404,
            detail="Restaurant not found",
        )

    # Check ownership
    if restaurant.user_id != current_user.user_id:
        raise HTTPException(
            status_code=403,
            detail="You do not own this restaurant",
        )

    # Update restaurant
    restaurant = update_restaurant(
        db,
        restaurant,
        restaurant_data,
    )

    return restaurant


# ==================================================================
# DELETE RESTAURANT
# ==================================================================
# Only the owner of the restaurant can delete it.
# ==================================================================

@router.delete("/{restaurant_id}")
def delete_single_restaurant(
    restaurant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    # Check if restaurant exists
    restaurant = get_restaurant(
        db,
        restaurant_id,
    )

    if restaurant is None:
        raise HTTPException(
            status_code=404,
            detail="Restaurant not found",
        )

    # Check ownership
    if restaurant.user_id != current_user.user_id:
        raise HTTPException(
            status_code=403,
            detail="You do not own this restaurant",
        )

    # Delete restaurant
    delete_restaurant(
        db,
        restaurant,
    )

    return {
        "message": "Restaurant deleted successfully"
    }