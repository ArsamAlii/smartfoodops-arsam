from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.enums import UserRole
from app.models.users import User
from app.schemas.auth import RegisterRequest


# ------------------------------------------------------------------
# Register User Service
# ------------------------------------------------------------------
def register_user(db: Session, user_data: RegisterRequest) -> User:
    """Check for existing email and create a new user record."""
    existing_user = (
        db.query(User)
        .filter(User.email == user_data.email)
        .first()
    )

    if existing_user:
        raise ValueError("Email already registered")

    new_user = User(
        full_name=user_data.name,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        role=user_data.role,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


# ------------------------------------------------------------------
# Login User Service
# ------------------------------------------------------------------
def login_user(db: Session, email: str, password: str) -> str:
    """Authenticate user credentials and return a signed JWT access token."""
    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if not user:
        raise ValueError("Invalid email or password")

    if not verify_password(password, user.password_hash):
        raise ValueError("Invalid email or password")

    # Ensure role is string serialized for JWT payload
    role_claim = user.role.value if isinstance(user.role, UserRole) else str(user.role)

    # Generate JWT
    access_token = create_access_token(
        {
            "sub": str(user.user_id),
            "role": role_claim,
        }
    )

    return access_token 