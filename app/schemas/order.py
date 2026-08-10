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


# ------------------------------------------------------------------
# Create Schema
# ------------------------------------------------------------------
class OrderCreate(OrderBase):
    payment_method: PaymentMethod

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
class OrderResponse(BaseModel):
    order_id: int
    customer_id: int
    restaurant_id: int
    rider_id: int | None
    total_amount: Decimal
    status: OrderStatus
    created_at: datetime
    items: list[OrderItemResponse] = Field(
        default_factory=list
    )

    model_config = ConfigDict(
        from_attributes=True
    )

