from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RestaurantBase(BaseModel):
    name: str
    cuisine: str
    address: str


class RestaurantCreate(RestaurantBase):
    pass


class RestaurantUpdate(BaseModel):
    name: str | None = None
    cuisine: str | None = None
    address: str | None = None
    is_open: bool | None = None


class RestaurantResponse(RestaurantBase):
    restaurant_id: int
    user_id: int
    is_open: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)