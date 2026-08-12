from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.database import get_db
from app.models.enums import UserRole
from app.models.users import User
from app.schemas.user import UserAvailabilityUpdate

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


# ===========================================================
# Update Rider Availability
# ===========================================================

@router.patch(
    "/me/availability",
)
def update_my_availability(
    availability_data: UserAvailabilityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # -------------------------------------------------------
    # Only riders can change their availability
    # -------------------------------------------------------

    if current_user.role != UserRole.RIDER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only riders can update their availability.",
        )

    # -------------------------------------------------------
    # Update availability
    # -------------------------------------------------------

    current_user.is_available = availability_data.is_available

    db.commit()
    db.refresh(current_user)

    return {
        "user_id": current_user.user_id,
        "role": current_user.role.value,
        "is_available": current_user.is_available,
    }