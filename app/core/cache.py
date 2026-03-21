import json
from typing import Any

import redis

from app.core.config import settings


def get_redis_client():
    try:
        client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        client.ping()
        return client
    except Exception:
        return None


def get_cache(key: str) -> Any:
    client = get_redis_client()
    if not client:
        return None

    value = client.get(key)
    if value is None:
        return None

    return json.loads(value)


def set_cache(key: str, value: Any, ttl: int = 300) -> None:
    client = get_redis_client()
    if not client:
        return

    client.setex(key, ttl, json.dumps(value))


def delete_cache(key: str) -> None:
    client = get_redis_client()
    if not client:
        return

    client.delete(key)
