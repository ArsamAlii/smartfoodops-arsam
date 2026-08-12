from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.order import Order
from app.models.payment import Payment


class PaymentAuthorizationError(Exception):
    """Raised when payment authorization fails."""
    pass


class PaymentAuthorizer:
    """
    Simulated payment authorization service.

    Authorization is idempotent at the payment/order level:
    if a payment already exists for the order, the existing
    payment is returned instead of creating another payment.
    """

    def __init__(self, db: Session):
        self.db = db

    def authorize(
        self,
        order: Order,
        idempotency_key: str,
        payment_method: str,
    ) -> Payment:

        # ---------------------------------------------------
        # 1. Check for an existing payment
        # ---------------------------------------------------
        existing_payment = (
            self.db.query(Payment)
            .filter(
                Payment.order_id == order.order_id
            )
            .first()
        )

        if existing_payment:
            return existing_payment

        # ---------------------------------------------------
        # 2. Get order total
        # ---------------------------------------------------
        total_amount = Decimal(order.total_amount)

        # ---------------------------------------------------
        # 3. Determine tax
        # ---------------------------------------------------
        if payment_method == "cod":
            tax_percentage = Decimal("10.00")

        elif payment_method == "online":
            tax_percentage = Decimal("6.00")

        elif payment_method == "card":
            tax_percentage = Decimal("3.00")

        else:
            raise PaymentAuthorizationError(
                "Unsupported payment method."
            )

        # ---------------------------------------------------
        # 4. Simulated payment failure
        # ---------------------------------------------------
        # This amount is ONLY for testing failure handling.
        if total_amount == Decimal("9999.99"):
            raise PaymentAuthorizationError(
                "Payment authorization failed."
            )

        # ---------------------------------------------------
        # 5. Calculate tax
        # ---------------------------------------------------
        tax_amount = (
            total_amount
            * tax_percentage
            / Decimal("100")
        )

        final_amount = (
            total_amount + tax_amount
        )

        # ---------------------------------------------------
        # 6. Create payment
        # ---------------------------------------------------
        payment = Payment(
            order_id=order.order_id,
            payment_method=payment_method,
            tax_percentage=tax_percentage,
            tax_amount=tax_amount,
            final_amount=final_amount,
            payment_status="authorized",
        )

        self.db.add(payment)

        # Flush so the payment gets its ID before returning.
        self.db.flush()

        return payment