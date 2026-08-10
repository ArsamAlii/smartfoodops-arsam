```python
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# ------------------------------------------------------------------
# Base Schema
# ------------------------------------------------------------------
class OrderItemBase(BaseModel):
    menu_item_id: int
    quantity: int = Field(gt=0)


# ------------------------------------------------------------------
# Create Schema
# ------------------------------------------------------------------
class OrderItemCreate(OrderItemBase):
    pass


# ------------------------------------------------------------------
# Update Schema
# ------------------------------------------------------------------
class OrderItemUpdate(BaseModel):
    quantity: int | None = Field(
        default=None,
        gt=0,
    )


# ------------------------------------------------------------------
# Response Schema
# ------------------------------------------------------------------
class OrderItemResponse(OrderItemBase):
    order_item_id: int
    order_id: int
    unit_price: Decimal

    model_config = ConfigDict(from_attributes=True)
```
