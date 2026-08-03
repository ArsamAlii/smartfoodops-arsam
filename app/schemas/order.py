from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict


class OrderStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    PREPARING = "preparing"
    ON_THE_WAY = "on_the_way"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class PaymentMethod(str, Enum):
    COD = "cod"
    CARD = "card"
    ONLINE = "online"


class OrderBase(BaseModel):
    delivery_address: str
    payment_method: PaymentMethod


class OrderCreate(OrderBase):
    pass


class OrderUpdate(BaseModel):
    status: OrderStatus | None = None
    rider_id: int | None = None


class OrderResponse(OrderBase):
    order_id: int
    customer_id: int
    restaurant_id: int
    rider_id: int | None
    status: OrderStatus
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)