from app.workers.celery_app import celery_app


@celery_app.task
def hello_celery(name: str = "SmartFoodOps"):
    message = f"Hello from Celery, {name}!"

    print(message)

    return message