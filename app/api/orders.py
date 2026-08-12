from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.api.dependencies import get_current_user

from app.models.users import User
from app.models.enums import UserRole
from app.models.order import Order
from app.models.order_status_history import OrderStatusHistory
from app.models.restaurant import Restaurant

from app.schemas.order import (
    OrderCreate,
    OrderResponse,
    OrderUpdate,
)

from app.services.order_service import create_order


router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
)

from fastapi import Header
# ===========================================================
# Allowed Order Status Transitions
# ===========================================================

ALLOWED_STATUS_TRANSITIONS = {
    "restaurant_admin": {
        "placed": {"confirmed", "rejected", "cancelled"},
        "confirmed": {"preparing", "cancelled"},
        "preparing": {"ready"},
        "ready": {"assigned"},
    },
    "rider": {
        "assigned": {"picked_up"},
        "picked_up": {"delivered"},
        "delivered": {"completed"},
    },

    "admin": {
        "placed": {"payment_confirmed", "confirmed", "rejected", "cancelled"},
        "payment_confirmed": {"confirmed", "rejected", "cancelled"},
        "confirmed": {"preparing", "cancelled"},
        "preparing": {"ready", "cancelled"},
        "ready": {"assigned"},
        "assigned": {"picked_up"},
        "picked_up": {"delivered"},
        "delivered": {"completed"},
    },
}

# ===========================================================
# Create Order
# ===========================================================
@router.post(
    "/",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_new_order(
    order_data: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    idempotency_key: str = Header(
        ...,
        alias="Idempotency-Key",
    ),
):
    try:
        order = create_order(
            db=db,
            customer_id=current_user.user_id,
            order_data=order_data,
            idempotency_key=idempotency_key,
        )

        return order

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
# ===========================================================
# Get My / Accessible Orders
# ===========================================================

@router.get(
    "/",
    response_model=list[OrderResponse],
)
def get_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Order)

    # -------------------------------------------------------
    # Admin → all orders
    # -------------------------------------------------------

    if current_user.role == UserRole.ADMIN:
        return (
            query
            .order_by(Order.created_at.desc())
            .all()
        )

    # -------------------------------------------------------
    # Customer → only their orders
    # -------------------------------------------------------

    if current_user.role == UserRole.CUSTOMER:
        return (
            query
            .filter(
                Order.customer_id == current_user.user_id
            )
            .order_by(Order.created_at.desc())
            .all()
        )

    # -------------------------------------------------------
    # Rider → only assigned orders
    # -------------------------------------------------------

    if current_user.role == UserRole.RIDER:
        return (
            query
            .filter(
                Order.rider_id == current_user.user_id
            )
            .order_by(Order.created_at.desc())
            .all()
        )

    # -------------------------------------------------------
    # Restaurant Admin → restaurant orders
    # -------------------------------------------------------

    if current_user.role == UserRole.RESTAURANT_ADMIN:

        restaurant = (
            db.query(Restaurant)
            .filter(
                Restaurant.user_id == current_user.user_id
            )
            .first()
        )

        if restaurant is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Restaurant not found",
            )

        return (
            query
            .filter(
                Order.restaurant_id
                == restaurant.restaurant_id
            )
            .order_by(Order.created_at.desc())
            .all()
        )

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to view orders.",
    )


# ===========================================================
# Get Single Order
# ===========================================================

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
        .filter(
            Order.order_id == order_id
        )
        .first()
    )

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # -------------------------------------------------------
    # Admin → can view any order
    # -------------------------------------------------------

    if current_user.role == UserRole.ADMIN:
        return order

    # -------------------------------------------------------
    # Customer → own orders only
    # -------------------------------------------------------

    if current_user.role == UserRole.CUSTOMER:

        if order.customer_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "You do not have permission "
                    "to view this order."
                ),
            )

        return order

    # -------------------------------------------------------
    # Rider → assigned orders only
    # -------------------------------------------------------

    if current_user.role == UserRole.RIDER:

        if order.rider_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "You do not have permission "
                    "to view this order."
                ),
            )

        return order

    # -------------------------------------------------------
    # Restaurant Admin → restaurant orders only
    # -------------------------------------------------------

    if current_user.role == UserRole.RESTAURANT_ADMIN:

        restaurant = (
            db.query(Restaurant)
            .filter(
                Restaurant.user_id == current_user.user_id,
                Restaurant.restaurant_id
                == order.restaurant_id,
            )
            .first()
        )

        if restaurant is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "You do not have permission "
                    "to view this order."
                ),
            )

        return order

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=(
            "You do not have permission "
            "to view this order."
        ),
    )


# ===========================================================
# Update Order
# ===========================================================

@router.patch(
    "/{order_id}",
    response_model=OrderResponse,
)
def update_order(
    order_id: int,
    order_data: OrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # -------------------------------------------------------
    # Find Order
    # -------------------------------------------------------

    order = (
        db.query(Order)
        .filter(
            Order.order_id == order_id
        )
        .first()
    )

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # -------------------------------------------------------
    # Check Role-Based Access
    # -------------------------------------------------------

    # Admin can update any order
    if current_user.role == UserRole.ADMIN:
        pass

    # Restaurant Admin can update orders
    # belonging to their restaurant
    elif current_user.role == UserRole.RESTAURANT_ADMIN:

        restaurant = (
            db.query(Restaurant)
            .filter(
                Restaurant.user_id == current_user.user_id,
                Restaurant.restaurant_id
                == order.restaurant_id,
            )
            .first()
        )

        if restaurant is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "You do not have permission "
                    "to update this order."
                ),
            )

    # Rider can update only orders assigned to them
    elif current_user.role == UserRole.RIDER:

        if order.rider_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "You do not have permission "
                    "to update this order."
                ),
            )

    # Customers cannot update orders
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You do not have permission "
                "to update orders."
            ),
        )

    # =======================================================
    # Update Status
    # =======================================================

    if order_data.status is not None:

        old_status = order.status
        new_status = order_data.status.value

        # ---------------------------------------------------
        # Same status
        # ---------------------------------------------------

        if old_status == new_status:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Order is already in this status."
                ),
            )

        # ---------------------------------------------------
        # Get allowed transitions for role
        # ---------------------------------------------------

        role_name = current_user.role.value

        allowed_transitions = (
            ALLOWED_STATUS_TRANSITIONS
            .get(role_name, {})
            .get(old_status, set())
        )

        # ---------------------------------------------------
        # Validate transition
        # ---------------------------------------------------

        if new_status not in allowed_transitions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Cannot change order status "
                    f"from '{old_status}' "
                    f"to '{new_status}'."
                ),
            )

        # ---------------------------------------------------
        # Update Order
        # ---------------------------------------------------

        order.status = new_status

        # ---------------------------------------------------
        # Create Status History
        # ---------------------------------------------------

        status_history = OrderStatusHistory(
            order_id=order.order_id,
            from_status=old_status,
            to_status=new_status,
        )

        db.add(status_history)

    # =======================================================
    # Update Rider
    # =======================================================

    if order_data.rider_id is not None:

        # ---------------------------------------------------
        # Only admin or restaurant admin can assign riders
        # ---------------------------------------------------

        if current_user.role not in (
            UserRole.ADMIN,
            UserRole.RESTAURANT_ADMIN,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Only admin or restaurant admin "
                    "can assign riders."
                ),
            )

        # ---------------------------------------------------
        # Verify rider exists
        # ---------------------------------------------------

        rider = (
            db.query(User)
            .filter(
                User.user_id == order_data.rider_id
            )
            .first()
        )

        if rider is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rider not found.",
            )

        # ---------------------------------------------------
        # Verify user is actually a rider
        # ---------------------------------------------------

        if rider.role != UserRole.RIDER:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected user is not a rider.",
            )

        # ---------------------------------------------------
        # Assign rider
        # ---------------------------------------------------

        order.rider_id = rider.user_id


    # =======================================================
    # Commit
    # =======================================================

    db.commit()


    # =======================================================
    # Refresh
    # =======================================================

    db.refresh(order)

    return order