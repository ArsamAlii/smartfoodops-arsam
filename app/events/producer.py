import json
import os

from kafka import KafkaProducer

from app.events.schemas import Event


KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "localhost:29092",
)


producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda value: json.dumps(value).encode("utf-8"),
)


def publish_event(topic: str, event: Event) -> str:
    future = producer.send(
        topic,
        value=event.model_dump(mode="json"),
    )

    metadata = future.get(timeout=10)

    producer.flush()

    print(
        f"Kafka event published: "
        f"topic={metadata.topic}, "
        f"partition={metadata.partition}, "
        f"offset={metadata.offset}, "
        f"event_id={event.event_id}"
    )

    return event.event_id