from celery import Task

from app.workers.celery_app import celery_app


class FailedJobTask(Task):
    max_retries = 3
    autoretry_for = (ConnectionError,)
    retry_backoff = True
    retry_jitter = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        print(
            f"Task failed permanently: "
            f"task_id={task_id}, "
            f"error={exc}"
        )


@celery_app.task(
    bind=True,
    base=FailedJobTask,
)
def test_retry_task(self):
    print(
        f"Running retry test. "
        f"attempt={self.request.retries + 1}"
    )

    raise ConnectionError(
        "Simulated temporary provider failure"
    )