from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict


class PaymentMethod(str, Enum):
    COD = "cod"
    CARD = "card"
    ONLINE = "online"


class PaymentBase(BaseModel):
    payment_method: PaymentMethod


class PaymentCreate(PaymentBase):
    pass


class PaymentResponse(PaymentBase):
    payment_id: int
    order_id: int
    tax_percentage: Decimal
    tax_amount: Decimal
    final_amount: Decimal
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)