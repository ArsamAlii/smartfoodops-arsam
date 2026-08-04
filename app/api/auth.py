from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.auth import RegisterRequest
from app.services.auth_service import register_user


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