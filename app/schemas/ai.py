from pydantic import BaseModel, Field


class AIAskRequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=1000,
    )


class AISource(BaseModel):
    menu_item_id: int
    restaurant_id: int
    restaurant: str
    name: str
    category: str
    price: str
    is_available: bool
    similarity: float


class AIAskResponse(BaseModel):
    question: str
    answer: str
    sources: list[AISource]