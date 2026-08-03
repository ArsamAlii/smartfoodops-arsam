from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class MenuItemBase(BaseModel):
    name: str
    description: str | None = None
    price: Decimal = Field(gt=0)
    image_url: str | None = None
    is_available: bool = True


class MenuItemCreate(MenuItemBase):
    pass


class MenuItemUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: Decimal | None = Field(default=None, gt=0)
    image_url: str | None = None
    is_available: bool | None = None


class MenuItemResponse(MenuItemBase):
    item_id: int
    category_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)