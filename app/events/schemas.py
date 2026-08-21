from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class Event(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))

    event_type: str

    correlation_id: str = Field(
        default_factory=lambda: str(uuid4())
    )

    payload: dict[str, Any]

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )