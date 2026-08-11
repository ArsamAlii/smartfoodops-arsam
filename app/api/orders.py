from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.models.enums import UserRole
from app.db.database import get_db
from app.api.dependencies import get_current_user
from app.models.order import Order
from app.models.users import User
from app.schemas.order import OrderCreate, OrderResponse
from app.services.order_service import create_order
from app.models.restaurant import Restaurant

router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
)


@router.post(
    "/",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_new_order(
    order_data: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        order = create_order(
            db=db,
            customer_id=current_user.user_id,
            order_data=order_data,
        )

        return order

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get(
    "/",
    response_model=list[OrderResponse],
)
def get_my_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    orders = (
        db.query(Order)
        .filter(Order.customer_id == current_user.user_id)
        .order_by(Order.created_at.desc())
        .all()
    )

    return orders


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = (
        db.query(Order)
        .filter(Order.order_id == order_id)
        .first()
    )

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # Admin can view any order
    if current_user.role == UserRole.ADMIN:
        return order

    # Customer can only view their own orders
    if current_user.role == UserRole.CUSTOMER:
        if order.customer_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this order.",
            )
        return order

    # Rider can only view orders assigned to them
    if current_user.role == UserRole.RIDER:
        if order.rider_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this order.",
            )
        return order

    # Restaurant admin can only view orders belonging to their restaurant
    if current_user.role == UserRole.RESTAURANT_ADMIN:
        restaurant = (
            db.query(Restaurant)
            .filter(
                Restaurant.user_id == current_user.user_id,
                Restaurant.restaurant_id == order.restaurant_id,
            )
            .first()
        )

        if restaurant is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this order.",
            )

        return order

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to view this order.",
    )
