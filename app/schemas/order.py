from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.order_item import (
    OrderItemCreate,
    OrderItemResponse,
)


# ------------------------------------------------------------------
# Order Status
# ------------------------------------------------------------------
class OrderStatus(str, Enum):
    PLACED = "placed"
    ACCEPTED = "accepted"
    PREPARING = "preparing"
    ON_THE_WAY = "on_the_way"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


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
class OrderBase(BaseModel):
    restaurant_id: int
    payment_method: PaymentMethod


# ------------------------------------------------------------------
# Create Schema
# ------------------------------------------------------------------
class OrderCreate(OrderBase):
    items: list[OrderItemCreate] = Field(
        min_length=1
    )


# ------------------------------------------------------------------
# Update Schema
# ------------------------------------------------------------------
class OrderUpdate(BaseModel):
    status: OrderStatus | None = None
    rider_id: int | None = None


# ------------------------------------------------------------------
# Response Schema
# ------------------------------------------------------------------
class OrderResponse(OrderBase):
    order_id: int
    customer_id: int
    rider_id: int | None
    total_amount: Decimal
    status: OrderStatus
    created_at: datetime
    items: list[OrderItemResponse] = []

    model_config = ConfigDict(from_attributes=True)