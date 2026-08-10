from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict


# ------------------------------------------------------------------
# Payment Method
# ------------------------------------------------------------------
class PaymentMethod(str, Enum):
    COD = "cod"
    CARD = "card"
    ONLINE = "online"


# ------------------------------------------------------------------
# Base Schema
# ------------------------------------------------------------------
class PaymentBase(BaseModel):
    payment_method: PaymentMethod


# ------------------------------------------------------------------
# Create Schema
# ------------------------------------------------------------------
class PaymentCreate(PaymentBase):
    pass


# ------------------------------------------------------------------
# Response Schema
# ------------------------------------------------------------------
class PaymentResponse(PaymentBase):
    payment_id: int
    order_id: int
    tax_percentage: Decimal
    tax_amount: Decimal
    final_amount: Decimal
    payment_status: str
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )
