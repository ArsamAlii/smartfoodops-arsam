from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.api.dependencies import get_current_user

from app.models.users import User
from app.models.restaurant import Restaurant

from app.schemas.menu_category import (
    MenuCategoryCreate,
    MenuCategoryUpdate,
    MenuCategoryResponse,
)

from app.services.menu_category_service import (
    create_category,
    get_categories_by_restaurant,
    get_category,
    update_category,
    delete_category,
)

router = APIRouter(
    prefix="/categories",
    tags=["Menu Categories"],
)


# -----------------------------
# Create Category
# -----------------------------
@router.post("/", response_model=MenuCategoryResponse)
def create_new_category(
    restaurant_id: int,
    category: MenuCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    # Only owners can create categories
    if current_user.role != "owner":
        raise HTTPException(
            status_code=403,
            detail="Only restaurant owners can create categories",
        )

    # Verify the restaurant belongs to this owner
    restaurant = (
        db.query(Restaurant)
        .filter(
            Restaurant.restaurant_id == restaurant_id,
            Restaurant.user_id == current_user.user_id,
        )
        .first()
    )

    if restaurant is None:
        raise HTTPException(
            status_code=403,
            detail="You do not own this restaurant",
        )

    return create_category(
        db=db,
        restaurant_id=restaurant_id,
        name=category.name,
    )


# -----------------------------
# Get Categories of Restaurant
# -----------------------------
@router.get(
    "/restaurant/{restaurant_id}",
    response_model=list[MenuCategoryResponse],
)
def list_categories(
    restaurant_id: int,
    db: Session = Depends(get_db),
):

    return get_categories_by_restaurant(
        db,
        restaurant_id,
    )


# -----------------------------
# Get Single Category
# -----------------------------
@router.get(
    "/{category_id}",
    response_model=MenuCategoryResponse,
)
def get_single_category(
    category_id: int,
    db: Session = Depends(get_db),
):

    try:
        return get_category(db, category_id)

    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )


# -----------------------------
# Update Category
# -----------------------------
@router.put(
    "/{category_id}",
    response_model=MenuCategoryResponse,
)
def edit_category(
    category_id: int,
    category_data: MenuCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    try:
        category = get_category(db, category_id)

        # Verify ownership
        restaurant = (
            db.query(Restaurant)
            .filter(
                Restaurant.restaurant_id == category.restaurant_id,
                Restaurant.user_id == current_user.user_id,
            )
            .first()
        )

        if restaurant is None:
            raise HTTPException(
                status_code=403,
                detail="You do not own this restaurant",
            )

        return update_category(
            db,
            category,
            category_data.name,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )


# -----------------------------
# Delete Category
# -----------------------------
@router.delete("/{category_id}")
def remove_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    try:
        category = get_category(db, category_id)

        restaurant = (
            db.query(Restaurant)
            .filter(
                Restaurant.restaurant_id == category.restaurant_id,
                Restaurant.user_id == current_user.user_id,
            )
            .first()
        )

        if restaurant is None:
            raise HTTPException(
                status_code=403,
                detail="You do not own this restaurant",
            )

        delete_category(
            db,
            category,
        )

        return {
            "message": "Category deleted successfully"
        }

    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )