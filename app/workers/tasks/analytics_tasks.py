from app.workers.celery_app import celery_app


@celery_app.task
def analytics_rollup():
    print("Running periodic analytics rollup")

    return "Analytics rollup completed"