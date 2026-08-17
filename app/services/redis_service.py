import os

import redis


REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://localhost:6379/0",
)

redis_client = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True,
)


def get_idempotency_key(
    customer_id: int,
    idempotency_key: str,
):
    key = (
        f"idempotency:"
        f"{customer_id}:"
        f"{idempotency_key}"
    )

    return redis_client.get(key)


def set_idempotency_key(
    customer_id: int,
    idempotency_key: str,
    order_id: int,
    ttl_seconds: int,
):
    key = (
        f"idempotency:"
        f"{customer_id}:"
        f"{idempotency_key}"
    )

    redis_client.set(
        key,
        str(order_id),
        ex=ttl_seconds,
    )