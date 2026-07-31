from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MenuCategoryBase(BaseModel):
    name: str


class MenuCategoryCreate(MenuCategoryBase):
    pass


class MenuCategoryUpdate(BaseModel):
    name: str | None = None


class MenuCategoryResponse(MenuCategoryBase):
    category_id: int
    restaurant_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)