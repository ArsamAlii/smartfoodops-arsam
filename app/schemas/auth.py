from pydantic import BaseModel, EmailStr
from app.models.enums import UserRole


# ------------------------------------------------------------------
# Registration Request Schema
# ------------------------------------------------------------------
class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.CUSTOMER


# ------------------------------------------------------------------
# Authentication Schemas
# ------------------------------------------------------------------
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer" 