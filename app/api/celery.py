from fastapi import APIRouter
from pydantic import BaseModel

from app.workers.celery_app import celery_app
from app.workers.tasks.basic_tasks import hello_celery
from app.workers.tasks.retry_tasks import test_retry_task


router = APIRouter(
    prefix="/celery",
    tags=["Celery"],
)


class CeleryTestRequest(BaseModel):
    message: str


@router.post("/test")
def run_celery_test(payload: CeleryTestRequest):
    """
    Queue a simple Celery task.

    The task is sent to Redis and executed by the separate
    Celery worker container.
    """

    result = hello_celery.delay(payload.message)

    return {
        "status": "queued",
        "task_id": result.id,
        "task_name": "app.workers.tasks.basic_tasks.hello_celery",
        "message": payload.message,
    }


@router.post("/retry-test")
def run_retry_test():
    """
    Queue the simulated retry task.

    The task intentionally raises ConnectionError so that
    Celery's automatic retry mechanism can be demonstrated.
    """

    result = test_retry_task.delay()

    return {
        "status": "queued",
        "task_id": result.id,
        "task_name": "app.workers.tasks.retry_tasks.test_retry_task",
        "message": (
            "Retry test queued. "
            "The worker will retry the task and save it to failed_jobs "
            "after the maximum retry attempts."
        ),
    }


@router.get("/tasks/{task_id}")
def get_celery_task_status(task_id: str):
    """
    Check the current Celery task status and result.
    """

    result = celery_app.AsyncResult(task_id)

    response = {
        "task_id": task_id,
        "status": result.status,
    }

    if result.successful():
        response["result"] = result.result

    elif result.failed():
        response["error"] = str(result.result)

    return response
