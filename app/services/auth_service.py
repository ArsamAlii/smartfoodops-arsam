from sqlalchemy.orm import Session

from app.models.users import User
from app.schemas.auth import RegisterRequest
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
)


# function: register user
def register_user(db: Session, user_data: RegisterRequest) -> User:

    # check if email already exists
    existing_user = (
        db.query(User)
        .filter(User.email == user_data.email)
        .first()
    )

    if existing_user:
        raise ValueError("Email already registered")

    # create user object
    new_user = User(
        full_name=user_data.name,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        role=user_data.role
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


def login_user(db: Session, email: str, password: str) -> str:
    # Find user by email
    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if not user:
        raise ValueError("Invalid email or password")

    # Verify password
    if not verify_password(password, user.password_hash):
        raise ValueError("Invalid email or password")

    # Generate JWT
    access_token = create_access_token(
        {
            "sub": str(user.user_id),
            "role": user.role,
        }
    )

    return access_token