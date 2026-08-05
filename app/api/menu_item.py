from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_role
from app.db.database import get_db

from app.models.enums import UserRole
from app.models.users import User
from app.models.restaurant import Restaurant
from app.models.menu_category import MenuCategory

from app.schemas.menu_item import (
    MenuItemCreate,
    MenuItemUpdate,
    MenuItemResponse,
)

from app.services.menu_item_service import (
    create_menu_item,
    get_menu_items_by_category,
    get_menu_item,
    update_menu_item,
    delete_menu_item,
)

router = APIRouter(
    prefix="/menu-items",
    tags=["Menu Items"],
)


# ------------------------------------------------------------------
# Create Menu Item
# ------------------------------------------------------------------
@router.post("/", response_model=MenuItemResponse)
def create_new_menu_item(
    category_id: int,
    item_data: MenuItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.RESTAURANT_ADMIN)
    ),
):

    category = (
        db.query(MenuCategory)
        .filter(MenuCategory.category_id == category_id)
        .first()
    )

    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

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

    return create_menu_item(
        db,
        category_id,
        item_data,
    )


# ------------------------------------------------------------------
# Get All Menu Items of a Category
# ------------------------------------------------------------------
@router.get(
    "/category/{category_id}",
    response_model=list[MenuItemResponse],
)
def list_menu_items(
    category_id: int,
    db: Session = Depends(get_db),
):

    return get_menu_items_by_category(
        db,
        category_id,
    )


# ------------------------------------------------------------------
# Get Single Menu Item
# ------------------------------------------------------------------
@router.get(
    "/{menu_item_id}",
    response_model=MenuItemResponse,
)
def get_single_menu_item(
    menu_item_id: int,
    db: Session = Depends(get_db),
):

    try:
        return get_menu_item(
            db,
            menu_item_id,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


# ------------------------------------------------------------------
# Update Menu Item
# ------------------------------------------------------------------
@router.put(
    "/{menu_item_id}",
    response_model=MenuItemResponse,
)
def update_single_menu_item(
    menu_item_id: int,
    item_data: MenuItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.RESTAURANT_ADMIN)
    ),
):

    try:
        menu_item = get_menu_item(
            db,
            menu_item_id,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    category = (
        db.query(MenuCategory)
        .filter(MenuCategory.category_id == menu_item.category_id)
        .first()
    )

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

    return update_menu_item(
        db,
        menu_item,
        item_data,
    )


# ------------------------------------------------------------------
# Delete Menu Item
# ------------------------------------------------------------------
@router.delete("/{menu_item_id}")
def delete_single_menu_item(
    menu_item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.RESTAURANT_ADMIN)
    ),
):

    try:
        menu_item = get_menu_item(
            db,
            menu_item_id,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    category = (
        db.query(MenuCategory)
        .filter(MenuCategory.category_id == menu_item.category_id)
        .first()
    )

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

    delete_menu_item(
        db,
        menu_item,
    )

    return {
        "message": "Menu item deleted successfully"
    }