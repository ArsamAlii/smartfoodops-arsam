from app.workers.celery_app import celery_app
from app.db.database import SessionLocal
from app.models.notification import Notification


@celery_app.task
def create_notification(
    recipient_id: int,
    recipient_type: str,
    notification_type: str,
    message: str,
):
    db = SessionLocal()

    try:
        notification = Notification(
            recipient_id=recipient_id,
            recipient_type=recipient_type,
            notification_type=notification_type,
            message=message,
        )

        db.add(notification)
        db.commit()
        db.refresh(notification)

        return {
            "notification_id": notification.notification_id,
            "recipient_id": notification.recipient_id,
            "recipient_type": notification.recipient_type,
            "notification_type": notification.notification_type,
            "message": notification.message,
        }

    finally:
        db.close()