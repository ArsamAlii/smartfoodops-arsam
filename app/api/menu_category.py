from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_role
from app.db.database import get_db
from app.models.enums import UserRole
from app.models.restaurant import Restaurant
from app.models.users import User
from app.schemas.menu_category import (
    MenuCategoryCreate,
    MenuCategoryResponse,
    MenuCategoryUpdate,
)
from app.services.menu_category_service import (
    create_category,
    delete_category,
    get_categories_by_restaurant,
    get_category,
    update_category,
)

router = APIRouter(
    prefix="/categories",
    tags=["Menu Categories"],
)


# -------------------------------------------------
# Create Category
# -------------------------------------------------
@router.post("/", response_model=MenuCategoryResponse)
def create_new_category(
    restaurant_id: int,
    category: MenuCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.RESTAURANT_ADMIN)
    ),
):
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
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this restaurant",
        )

    return create_category(
        db=db,
        restaurant_id=restaurant_id,
        name=category.name,
    )


# -------------------------------------------------
# Get Categories of Restaurant
# -------------------------------------------------
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


# -------------------------------------------------
# Get Single Category
# -------------------------------------------------
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


# -------------------------------------------------
# Update Category
# -------------------------------------------------
@router.put(
    "/{category_id}",
    response_model=MenuCategoryResponse,
)
def edit_category(
    category_id: int,
    category_data: MenuCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.RESTAURANT_ADMIN)
    ),
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
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not own this restaurant",
            )

        return update_category(
            db,
            category,
            category_data.name,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


# -------------------------------------------------
# Delete Category
# -------------------------------------------------
@router.delete("/{category_id}")
def remove_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.RESTAURANT_ADMIN)
    ),
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
                status_code=status.HTTP_403_FORBIDDEN,
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )