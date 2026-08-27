from decimal import Decimal

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(
        min_length=1,
        max_length=500,
    )

    limit: int = Field(
        default=5,
        ge=1,
        le=50,
    )

    similarity_threshold: float = Field(
        default=0.30,
        ge=0.0,
        le=1.0,
    )


class SearchResult(BaseModel):
    menu_item_id: int
    restaurant_id: int
    restaurant: str
    category: str
    cuisine: str
    price: Decimal
    is_available: bool
    similarity: float
    text: str


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]