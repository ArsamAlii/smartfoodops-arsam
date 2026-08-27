from pydantic import BaseModel, Field


class AIAskRequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=1000,
    )

    limit: int = Field(
        default=5,
        ge=1,
        le=10,
    )

    similarity_threshold: float = Field(
        default=0.30,
        ge=0.0,
        le=1.0,
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