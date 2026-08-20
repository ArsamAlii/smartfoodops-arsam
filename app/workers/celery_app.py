import os

from celery import Celery


CELERY_BROKER_URL = os.getenv(
    "CELERY_BROKER_URL",
    "redis://localhost:6379/1",
)

CELERY_RESULT_BACKEND = os.getenv(
    "CELERY_RESULT_BACKEND",
    "redis://localhost:6379/2",
)


celery_app = Celery(
    "smartfoodops",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=[
        "app.workers.tasks.test_tasks",
        "app.workers.tasks.analytics_tasks",
        "app.workers.tasks.retry_tasks",
    ],
)


celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    beat_schedule={
        "analytics-rollup-every-minute": {
            "task": "app.workers.tasks.analytics_tasks.analytics_rollup",
            "schedule": 60.0,
        },
    },
)