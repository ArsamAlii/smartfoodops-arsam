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
    status_code=status.HTTP_201_CREATED,
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
        # ---------------------------------------------------
        # Create order in PostgreSQL
        # ---------------------------------------------------

        order = create_order(
            db=db,
            customer_id=current_user.user_id,
            order_data=order_data,
            idempotency_key=idempotency_key,
        )

        # ---------------------------------------------------
        # Start Temporal workflow
        # ---------------------------------------------------
        #
        # start_order_workflow() creates its own Temporal
        # client internally.
        #
        # Workflow ID:
        # order-workflow-{order_id}
        #
        # ---------------------------------------------------

        await start_order_workflow(
            order_id=order.order_id,
        )

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
    # Restaurant Admin → only their restaurant's orders
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

    # -------------------------------------------------------
    # Unknown/unsupported role
    # -------------------------------------------------------

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
    # -------------------------------------------------------
    # Find order
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
            detail="Order not found.",
        )

    # -------------------------------------------------------
    # Admin → can view any order
    # -------------------------------------------------------

    if current_user.role == UserRole.ADMIN:
        return order

    # -------------------------------------------------------
    # Customer → only their own orders
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
    # Rider → only assigned orders
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
    # Restaurant Admin → only their restaurant's orders
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

    # -------------------------------------------------------
    # Unknown/unsupported role
    # -------------------------------------------------------

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
            detail="Order not found.",
        )

    # =======================================================
    # ROLE-BASED ACCESS
    # =======================================================

    if current_user.role == UserRole.ADMIN:
        # Admin can update any order.
        pass

    elif current_user.role == UserRole.RESTAURANT_ADMIN:

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

        # ---------------------------------------------------
        # Customer can ONLY cancel their own order.
        # ---------------------------------------------------

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

        # ---------------------------------------------------
        # Get allowed transitions for this role
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

        # ---------------------------------------------------
        # Send signal to Temporal
        # ---------------------------------------------------

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

        # ---------------------------------------------------
        # Wait for Temporal Activity to update PostgreSQL
        # ---------------------------------------------------
        #
        # The Temporal signal is asynchronous.
        #
        # The signal being accepted does NOT necessarily
        # mean that the Activity has already completed.
        #
        # We therefore check PostgreSQL until the expected
        # status appears.
        #
        # Maximum wait:
        # 20 attempts × 0.25 seconds = 5 seconds
        #
        # ---------------------------------------------------

        status_updated = False

        for _ in range(20):

            # Refresh the object from PostgreSQL
            db.refresh(order)

            if order.status == new_status:
                status_updated = True
                break

            await asyncio.sleep(0.25)

        # ---------------------------------------------------
        # Temporal accepted the signal but the Activity
        # did not update PostgreSQL within the timeout.
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
    # RIDER ASSIGNMENT
    # =======================================================

    if order_data.rider_id is not None:

        # ---------------------------------------------------
        # Only Admin / Restaurant Admin can assign riders
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
        # Restaurant Admin must belong to this restaurant
        # ---------------------------------------------------

        if current_user.role == UserRole.RESTAURANT_ADMIN:

            restaurant = (
                db.query(Restaurant)
                .filter(
                    Restaurant.user_id
                    == current_user.user_id,
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
        # Verify rider exists and lock rider row
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
        # Check rider availability
        # ---------------------------------------------------

        if not rider.is_available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected rider is not available.",
            )

        # ---------------------------------------------------
        # Assign rider
        # ---------------------------------------------------

        order.rider_id = rider.user_id
        rider.is_available = False

        # ---------------------------------------------------
        # Commit rider assignment
        # ---------------------------------------------------

        try:
            db.commit()

        except Exception:
            db.rollback()
            raise

        db.refresh(order)

    # =======================================================
    # Final Refresh
    # =======================================================

    db.refresh(order)

    return order