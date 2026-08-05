from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
)
from app.services.auth_service import (
    register_user,
    login_user,
)

from app.api.dependencies import get_current_user
from app.models.users import User
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


# @router.post("/register")
# def register(
#     user_data: RegisterRequest,
#     db: Session = Depends(get_db),
# ):
#     try:
#         user = register_user(db, user_data)
#         return {
#             "message": "User registered successfully",
#             "user_id": user.user_id,
#         }

#     except ValueError as e:
#         raise HTTPException(
#             status_code=400,#http 400 bad request
#             detail=str(e), #enmmail alr registered
#         )

from fastapi import HTTPException

@router.post("/register")
def register(user_data: RegisterRequest, db: Session = Depends(get_db)):

    try:
        user = register_user(db, user_data)

        return {
            "message": "User registered successfully",
            "user_id": user.user_id
        }

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    try:
        token = login_user(
            db,
            form_data.username,   # username field contains the email
            form_data.password,
        )

        return TokenResponse(
            access_token=token,
            token_type="bearer",
        )

    except ValueError as e:
        raise HTTPException(
            status_code=401,
            detail=str(e),
        )


@router.get("/me")
def get_me(
    current_user: User = Depends(get_current_user),
):
    return {
        "user_id": current_user.user_id,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "role": current_user.role,
    }