from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.database import get_db

from app.models.enums import UserRole
from app.models.payment import Payment
from app.models.users import User

from app.schemas.payment import (
    PaymentResponse,
    PaymentStatusUpdate,
)


router = APIRouter(
    prefix="/payments",
    tags=["Payments"],
)


# ===========================================================
# Allowed Payment Status Transitions
# ===========================================================

ALLOWED_PAYMENT_TRANSITIONS = {
    "authorized": {
        "captured",
        "failed",
    },
    "captured": {
        "refunded",
    },
}


# ===========================================================
# Update Payment Status
# ===========================================================

@router.patch(
    "/{payment_id}",
    response_model=PaymentResponse,
)
def update_payment_status(
    payment_id: int,
    payment_data: PaymentStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # -------------------------------------------------------
    # Find payment
    # -------------------------------------------------------

    payment = (
        db.query(Payment)
        .filter(
            Payment.payment_id == payment_id
        )
        .first()
    )

    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found.",
        )

    # -------------------------------------------------------
    # Authorization
    # -------------------------------------------------------

    if current_user.role not in (
        UserRole.ADMIN,
        UserRole.RESTAURANT_ADMIN,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Only admin or restaurant admin "
                "can update payment status."
            ),
        )

    # -------------------------------------------------------
    # Validate new status
    # -------------------------------------------------------

    new_status = payment_data.payment_status.lower()

    allowed_statuses = {
        "authorized",
        "captured",
        "failed",
        "refunded",
    }

    if new_status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid payment status: "
                f"'{payment_data.payment_status}'."
            ),
        )

    # -------------------------------------------------------
    # Same status
    # -------------------------------------------------------

    if payment.payment_status == new_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Payment is already in this status."
            ),
        )

    # -------------------------------------------------------
    # Validate transition
    # -------------------------------------------------------

    allowed_transitions = (
        ALLOWED_PAYMENT_TRANSITIONS
        .get(payment.payment_status, set())
    )

    if new_status not in allowed_transitions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot change payment status "
                f"from '{payment.payment_status}' "
                f"to '{new_status}'."
            ),
        )

    # -------------------------------------------------------
    # Update payment
    # -------------------------------------------------------

    payment.payment_status = new_status

    db.commit()
    db.refresh(payment)

    return payment