from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_role
from app.db.database import get_db
from app.models.enums import UserRole
from app.models.failed_jobs import FailedJob
from app.models.users import User
from app.workers.tasks.retry_tasks import retry_failed_job


router = APIRouter(
    prefix="/failed-jobs",
    tags=["Failed Jobs"],
)


# ===========================================================
# List Failed Jobs
# ===========================================================

@router.get("/")
def get_failed_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(
            UserRole.ADMIN,
            UserRole.RESTAURANT_ADMIN,
        )
    ),
):
    """
    Return all permanently failed Celery jobs.
    """

    failed_jobs = (
        db.query(FailedJob)
        .order_by(FailedJob.failed_at.desc())
        .all()
    )

    return failed_jobs


# ===========================================================
# Retry Failed Job
# ===========================================================

@router.post("/{task_id}/retry")
def retry_failed_job_endpoint(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(
            UserRole.ADMIN,
            UserRole.RESTAURANT_ADMIN,
        )
    ),
):
    """
    Re-queue a permanently failed Celery task.
    """

    # -------------------------------------------------------
    # Find failed job
    # -------------------------------------------------------

    failed_job = (
        db.query(FailedJob)
        .filter(
            FailedJob.task_id == task_id
        )
        .first()
    )

    if failed_job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Failed job not found.",
        )

    # -------------------------------------------------------
    # Re-queue Celery task
    # -------------------------------------------------------

    result = retry_failed_job.delay(task_id)

    return {
        "status": "requeued",
        "old_task_id": task_id,
        "retry_task_id": result.id,
        "task_name": failed_job.task_name,
    }