from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RestaurantBase(BaseModel):
    name: str
    address: str
    phone_number: str


class RestaurantCreate(RestaurantBase):
    logo_url: str | None = None


class RestaurantUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    phone_number: str | None = None
    logo_url: str | None = None
    is_active: bool | None = None


class RestaurantResponse(RestaurantBase):
    restaurant_id: int
    user_id: int
    logo_url: str | None = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)