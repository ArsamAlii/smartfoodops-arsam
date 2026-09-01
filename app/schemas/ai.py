```python
from pydantic import BaseModel, Field, field_validator


class AIAskRequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=1000,
    )

    order_id: int | None = Field(
        default=None,
        gt=0,
    )

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        # Remove unnecessary whitespace
        value = value.strip()

        # Reject empty / whitespace-only input
        if not value:
            raise ValueError("Question cannot be empty.")

        # Reject extremely short input such as "a" or "?"
        if len(value) < 2:
            raise ValueError("Please provide a meaningful question.")

        # Reject strings containing no alphabetic characters.
        # Examples: "123456", "@@@@", "!!!!"
        if not any(character.isalpha() for character in value):
            raise ValueError("Please provide a meaningful question.")

        # Detect obvious one-word/gibberish requests.
        words = value.split()

        if len(words) == 1:
            word = words[0].strip(".,!?;:'\"()[]{}")

            # Allow useful single-word food queries such as:
            # burger, biryani, pizza, sushi, etc.
            if len(word) < 3:
                raise ValueError(
                    "Please provide a more specific question."
                )

        return value


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
```
