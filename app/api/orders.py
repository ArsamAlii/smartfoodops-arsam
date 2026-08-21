import asyncio

from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.api.dependencies import get_current_user

from app.models.users import User
from app.models.enums import UserRole
from app.models.order import Order
from app.models.restaurant import Restaurant

from app.schemas.order import (
    OrderCreate,
    OrderResponse,
    OrderUpdate,
)

from app.services.order_service import create_order

from app.workflows.temporal_client import (
    start_order_workflow,
    signal_order_workflow,
)
from app.core.observability import ORDERS_PLACED


router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
)


# ===========================================================
# Allowed Order Status Transitions
# ===========================================================

ALLOWED_STATUS_TRANSITIONS = {
    "admin": {
        "placed": {"payment_confirmed", "cancelled"},
        "payment_confirmed": {"confirmed", "cancelled"},
        "confirmed": {"preparing", "cancelled"},
        "preparing": {"ready"},
        "ready": {"assigned"},
        "assigned": {"picked_up"},
        "picked_up": {"delivered"},
        "delivered": {"completed"},
    },

    "restaurant_admin": {
        "placed": {"payment_confirmed", "rejected"},
        "payment_confirmed": {"confirmed", "rejected"},
        "confirmed": {"preparing", "rejected"},
        "preparing": {"ready"},
        "ready": {"assigned"},
    },

    "rider": {
        "assigned": {"picked_up"},
        "picked_up": {"delivered"},
        "delivered": {"completed"},
    },

    "customer": {
        "placed": {"cancelled"},
        "payment_confirmed": {"cancelled"},
        "confirmed": {"cancelled"},
    },
}


# ===========================================================
# Create Order
# ===========================================================

@router.post(
    "/",
    response_model=OrderResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_new_order(
    order_data: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    idempotency_key: str = Header(
        ...,
        alias="Idempotency-Key",
    ),
):
    try:
        if current_user.role != UserRole.CUSTOMER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only customers can place orders.",
            )
        order = create_order(
            db=db,
            customer_id=current_user.user_id,
            order_data=order_data,
            idempotency_key=idempotency_key,
        )

        await start_order_workflow(
            order_id=order.order_id,
        )

        ORDERS_PLACED.inc()

        return order

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


# ===========================================================
# Get Orders
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
    # Rider → only orders assigned to them
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
                detail="Restaurant not found.",
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
            detail="Order not found.",
        )

    # -------------------------------------------------------
    # Admin
    # -------------------------------------------------------

    if current_user.role == UserRole.ADMIN:
        return order

    # -------------------------------------------------------
    # Customer
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
    # Rider
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
    # Restaurant Admin
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
async def update_order(
    order_id: int,
    order_data: OrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # =======================================================
    # Find Order
    # =======================================================

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
            detail="Order not found.",
        )

    # =======================================================
    # ROLE-BASED ACCESS
    # =======================================================

    if current_user.role == UserRole.ADMIN:
        pass

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

    elif current_user.role == UserRole.RIDER:

        if order.rider_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "You do not have permission "
                    "to update this order."
                ),
            )

    elif current_user.role == UserRole.CUSTOMER:

        if order.customer_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "You can only cancel your own orders."
                ),
            )

        if order_data.status is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Customers can only request "
                    "order cancellation."
                ),
            )

        if order_data.status.value != "cancelled":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Customers can only cancel orders."
                ),
            )

    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update orders.",
        )

    # =======================================================
    # RIDER ASSIGNMENT
    #
    # IMPORTANT:
    #
    # Rider assignment happens BEFORE the order is allowed
    # to move to "assigned".
    #
    # ready
    #   ↓
    # rider assigned
    #   ↓
    # assigned
    #
    # =======================================================

    if order_data.rider_id is not None:

        # ---------------------------------------------------
        # Only Admin / Restaurant Admin
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
        # Restaurant Admin ownership check
        # ---------------------------------------------------

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
                        "to assign a rider to this order."
                    ),
                )

        # ---------------------------------------------------
        # Cannot assign a rider to a completed/cancelled order
        # ---------------------------------------------------

        if order.status != "ready":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A rider can only be assigned while an order is READY.",
            )

        if order.status in {
            "cancelled",
            "rejected",
            "completed",
            "delivered",
            "picked_up",
        }:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Cannot assign a rider when order "
                    f"is '{order.status}'."
                ),
            )

        # ---------------------------------------------------
        # Find and lock rider
        # ---------------------------------------------------

        rider = (
            db.query(User)
            .filter(
                User.user_id == order_data.rider_id,
                User.role == UserRole.RIDER,
            )
            .with_for_update()
            .first()
        )

        if rider is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rider not found.",
            )

        # ---------------------------------------------------
        # Rider must be available
        # ---------------------------------------------------

        if not rider.is_available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected rider is not available.",
            )

        # ---------------------------------------------------
        # If another rider is already assigned
        # ---------------------------------------------------

        if (
            order.rider_id is not None
            and order.rider_id != rider.user_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "A different rider is already assigned "
                    "to this order."
                ),
            )

        # ---------------------------------------------------
        # Assign rider
        # ---------------------------------------------------

        order.rider_id = rider.user_id

        # Rider becomes unavailable while carrying order
        rider.is_available = False

        try:
            db.commit()

        except Exception:
            db.rollback()
            raise

        db.refresh(order)

    # =======================================================
    # STATUS UPDATE
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
                detail="Order is already in this status.",
            )

        # ===================================================
        # CRITICAL RIDER CHECK
        #
        # An order CANNOT become "assigned" unless it already
        # has a rider.
        # ===================================================

        if new_status == "assigned":

            if order.rider_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Cannot set order status to "
                        "'assigned' because no rider "
                        "has been assigned. "
                        "Assign a rider first."
                    ),
                )

        # ---------------------------------------------------
        # Rider cannot be removed while assigned
        # ---------------------------------------------------

        if (
            new_status in {
                "assigned",
                "picked_up",
                "delivered",
            }
            and order.rider_id is None
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Order cannot move to '{new_status}' "
                    "without an assigned rider."
                ),
            )

        # ---------------------------------------------------
        # Get allowed transitions
        # ---------------------------------------------------

        role_name = current_user.role.value

        allowed_transitions = (
            ALLOWED_STATUS_TRANSITIONS
            .get(role_name, {})
            .get(old_status, set())
        )

        # ---------------------------------------------------
        # Reject illegal transition
        # ---------------------------------------------------

        if new_status not in allowed_transitions:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Cannot change order status "
                    f"from '{old_status}' "
                    f"to '{new_status}'."
                ),
            )

        # ===================================================
        # SIGNAL TEMPORAL
        # ===================================================

        try:

            await signal_order_workflow(
                order_id=order.order_id,
                status=new_status,
            )

        except Exception as exc:

            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Unable to communicate with Temporal: "
                    f"{exc}"
                ),
            )

        # ===================================================
        # WAIT FOR TEMPORAL ACTIVITY
        # ===================================================

        status_updated = False

        for _ in range(20):

            db.refresh(order)

            # READY may immediately advance to ASSIGNED when dispatch finds an
            # available rider, so both states acknowledge a successful READY
            # signal.
            if order.status == new_status or (
                new_status == "ready" and order.status == "assigned"
            ):
                status_updated = True
                break

            await asyncio.sleep(0.25)

        # ---------------------------------------------------
        # Timeout
        # ---------------------------------------------------

        if not status_updated:

            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=(
                    "Temporal accepted the order status "
                    "update, but the database was not "
                    "updated within 5 seconds."
                ),
            )

    # =======================================================
    # FINAL VALIDATION
    # =======================================================

    db.refresh(order)

    # -------------------------------------------------------
    # Safety check:
    #
    # assigned/picked_up/delivered must ALWAYS have rider.
    # -------------------------------------------------------

    if order.status in {
        "assigned",
        "picked_up",
        "delivered",
    } and order.rider_id is None:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Data integrity error: order is in "
                f"'{order.status}' status but has no rider."
            ),
        )

    return order
