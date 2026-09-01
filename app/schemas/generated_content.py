from pydantic import BaseModel, Field


class DescriptionGenerationRequest(BaseModel):
    menu_item_id: int | None = Field(
        default=None,
        gt=0,
    )


class PromoGenerationRequest(BaseModel):
    pass


class HighlightsGenerationRequest(BaseModel):
    count: int = Field(
        default=3,
        ge=1,
        le=10,
    )


class HighlightItem(BaseModel):
    item_name: str = Field(
        min_length=1,
        max_length=100,
    )

    tagline: str = Field(
        min_length=1,
        max_length=255,
    )

    appeal: str = Field(
        min_length=1,
        max_length=500,
    )


class HighlightsResponse(BaseModel):
    highlights: list[HighlightItem] = Field(
        min_length=1,
        max_length=10,
    )