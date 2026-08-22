import json
import os
from datetime import datetime

from kafka import KafkaConsumer

from app.db.database import SessionLocal
from app.models.processed_event import ProcessedEvent


KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "localhost:29092",
)


consumer = KafkaConsumer(
    "order-events",
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    group_id="smartfoodops-consumer",
    auto_offset_reset="earliest",
    enable_auto_commit=False,
    value_deserializer=lambda value: json.loads(
        value.decode("utf-8")
    ),
)


def consume_events():
    print("Kafka consumer started...")
    print("Listening to topic: order-events")

    for message in consumer:
        event = message.value

        event_id = event.get("event_id")
        event_type = event.get("event_type")
        payload = event.get("payload", {})

        print(
            f"Kafka event received: "
            f"topic={message.topic}, "
            f"partition={message.partition}, "
            f"offset={message.offset}, "
            f"event_id={event_id}, "
            f"event_type={event_type}"
        )

        db = SessionLocal()

        try:
            # ---------------------------------------------------------
            # 1. Check whether this event has already been processed
            # ---------------------------------------------------------
            processed_event = db.get(
                ProcessedEvent,
                event_id,
            )

            if processed_event is not None:
                print(
                    f"Duplicate event detected. "
                    f"Skipping processing: "
                    f"event_id={event_id}"
                )

                # The event is already safely processed in the DB,
                # so it is safe to acknowledge the Kafka message.
                consumer.commit()

                continue

            # ---------------------------------------------------------
            # 2. Process the event
            # ---------------------------------------------------------
            print(
                f"Processing event: "
                f"event_type={event_type}, "
                f"payload={payload}"
            )

            # ---------------------------------------------------------
            # 3. Record the event as processed
            # ---------------------------------------------------------
            processed_event = ProcessedEvent(
                event_id=event_id,
                event_type=event_type,
                processed_at=datetime.utcnow(),
            )

            db.add(processed_event)
            db.commit()

            # ---------------------------------------------------------
            # 4. Commit Kafka offset only after DB processing succeeds
            # ---------------------------------------------------------
            consumer.commit()

            print(
                f"Event processed successfully: "
                f"event_id={event_id}"
            )

        except Exception as exc:
            db.rollback()

            print(
                f"Error processing event: "
                f"event_id={event_id}, "
                f"error={exc}"
            )

            # Do NOT commit the Kafka offset.
            # Kafka will make the message available again.

        finally:
            db.close()


if __name__ == "__main__":
    consume_events()