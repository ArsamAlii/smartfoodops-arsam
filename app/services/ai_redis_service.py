import asyncio
import hashlib
import json
import os

import redis


REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://localhost:6379/0",
)

AI_RATE_LIMIT = int(
    os.getenv(
        "AI_RATE_LIMIT_PER_MINUTE",
        "20",
    )
)

AI_CACHE_TTL = int(
    os.getenv(
        "AI_CACHE_TTL_SECONDS",
        "300",
    )
)


redis_client = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True,
)


def normalize_question(
    question: str,
) -> str:
    """
    Normalize a user's question so semantically identical
    whitespace/casing variants can share the same cache entry.
    """
    return " ".join(
        question.strip().lower().split()
    )


def make_ai_cache_key(
    user_id: int,
    question: str,
    order_id: int | None = None,
) -> str:
    """
    Build a deterministic cache key.

    User ID is included so one user's answer is never returned
    to another user.
    """

    normalized = normalize_question(
        question
    )

    raw_key = (
        f"user:{user_id}|"
        f"question:{normalized}|"
        f"order_id:{order_id or 'none'}"
    )

    digest = hashlib.sha256(
        raw_key.encode("utf-8")
    ).hexdigest()

    return f"smartfoodops:ai:cache:{digest}"


def make_rate_limit_key(
    user_id: int,
) -> str:
    """
    Fixed one-minute Redis bucket per user.
    """

    return (
        f"smartfoodops:ai:rate:"
        f"{user_id}"
    )


def _get_cache(
    key: str,
):
    value = redis_client.get(key)

    if value is None:
        return None

    return json.loads(value)


async def get_cached_ai_response(
    key: str,
):
    """
    Async-safe wrapper around synchronous Redis.
    """

    try:
        return await asyncio.to_thread(
            _get_cache,
            key,
        )

    except Exception:
        # Redis failure must never take down AI.
        return None


def _set_cache(
    key: str,
    value: dict,
    ttl: int,
):
    redis_client.setex(
        key,
        ttl,
        json.dumps(
            value,
            ensure_ascii=False,
        ),
    )


async def set_cached_ai_response(
    key: str,
    value: dict,
    ttl: int = AI_CACHE_TTL,
):
    """
    Store an AI response in Redis without blocking
    the FastAPI event loop.
    """

    try:
        await asyncio.to_thread(
            _set_cache,
            key,
            value,
            ttl,
        )

    except Exception:
        # Cache is an optimization, not a dependency.
        pass


def _check_rate_limit(
    key: str,
) -> tuple[bool, int]:
    """
    Increment the current user's one-minute request bucket.

    Returns:
        allowed, current_count
    """

    count = redis_client.incr(key)

    if count == 1:
        redis_client.expire(
            key,
            60,
        )

    return (
        count <= AI_RATE_LIMIT,
        count,
    )


async def check_ai_rate_limit(
    user_id: int,
) -> tuple[bool, int]:
    """
    Async-safe rate-limit check.
    """

    try:

        return await asyncio.to_thread(
            _check_rate_limit,
            make_rate_limit_key(user_id),
        )

    except Exception:
        # Redis outage should not block customers
        # from using the AI endpoint.
        return True, 0