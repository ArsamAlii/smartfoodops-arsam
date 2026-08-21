import json
import os

from kafka import KafkaConsumer


KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "localhost:29092",
)

consumer = KafkaConsumer(
    "order-events",
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    group_id="smartfoodops-consumer",
    auto_offset_reset="earliest",
    enable_auto_commit=True,
    value_deserializer=lambda value: json.loads(
        value.decode("utf-8")
    ),
)


def consume_events():
    print("Kafka consumer started...")
    print("Listening to topic: order-events")

    for message in consumer:
        event = message.value

        print(
            f"Kafka event received: "
            f"topic={message.topic}, "
            f"partition={message.partition}, "
            f"offset={message.offset}, "
            f"event_id={event.get('event_id')}, "
            f"event_type={event.get('event_type')}"
        )

        print(
            f"Payload: {event.get('payload')}"
        )


if __name__ == "__main__":
    consume_events()