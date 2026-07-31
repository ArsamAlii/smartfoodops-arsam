from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRole(str, Enum):
    CUSTOMER = "customer"
    OWNER = "owner"
    RIDER = "rider"


class UserBase(BaseModel):
    full_name: str
    email: EmailStr
    role: UserRole


class UserCreate(UserBase):
    password: str = Field(min_length=8)


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    password: Optional[str] = None


class UserResponse(UserBase):
    user_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)