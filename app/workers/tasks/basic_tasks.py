import logging

from app.workers.celery_app import celery_app


logger = logging.getLogger(__name__)


@celery_app.task
def hello_celery(name: str = "SmartFoodOps"):
    message = f"Hello from Celery, {name}!"
    logger.info(message)
    return message
