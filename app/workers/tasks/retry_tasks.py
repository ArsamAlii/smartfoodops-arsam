import json

from celery import Task

from app.workers.celery_app import celery_app
from app.db.database import SessionLocal
from app.models.failed_jobs import FailedJob


class FailedJobTask(Task):
    max_retries = 3
    autoretry_for = (ConnectionError,)
    retry_backoff = True
    retry_jitter = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        db = SessionLocal()

        try:
            failed_job = FailedJob(
                task_id=task_id,
                task_name=self.name,
                task_args=json.dumps({
                    "args": args,
                    "kwargs": kwargs,
                }),
                error=str(exc),
                traceback=str(einfo),
            )

            db.add(failed_job)
            db.commit()

            print(
                f"Task failed permanently and was saved: "
                f"task_id={task_id}"
            )

        except Exception as db_error:
            db.rollback()

            print(
                f"Failed to save failed job: "
                f"task_id={task_id}, "
                f"error={db_error}"
            )

        finally:
            db.close()


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