from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# ------------------------------------------------------------------
# Base Schema
# Shared fields for creating, updating and returning menu items
# ------------------------------------------------------------------
class MenuItemBase(BaseModel):
    name: str
    description: str | None = None
    price: Decimal = Field(gt=0)
    stock: int | None = Field(default=None, ge=0)
    order_index: int = Field(default=0, ge=0)
    image_url: str | None = None
    is_available: bool = True


# ------------------------------------------------------------------
# Create Schema
# Used when creating a new menu item
# ------------------------------------------------------------------
class MenuItemCreate(MenuItemBase):
    pass


# ------------------------------------------------------------------
# Update Schema
# All fields are optional because users may update only one field
# ------------------------------------------------------------------
class MenuItemUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: Decimal | None = Field(default=None, gt=0)
    stock: int | None = Field(default=None, ge=0)
    order_index: int | None = Field(default=None, ge=0)
    image_url: str | None = None
    is_available: bool | None = None


# ------------------------------------------------------------------
# Response Schema
# Returned to the client after fetching or creating a menu item
# ------------------------------------------------------------------
class MenuItemResponse(MenuItemBase):
    menu_item_id: int
    category_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
