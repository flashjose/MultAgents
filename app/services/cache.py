from __future__ import annotations

import json
from time import time
from typing import Any

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings


class CacheBackend:
    def get_json(self, key: str) -> dict[str, Any] | None:
        raise NotImplementedError

    def set_json(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        raise NotImplementedError


class MemoryCache(CacheBackend):
    def __init__(self) -> None:
        self._store: dict[str, tuple[float, dict[str, Any]]] = {}

    def get_json(self, key: str) -> dict[str, Any] | None:
        record = self._store.get(key)
        if not record:
            return None
        expires_at, value = record
        if expires_at < time():
            self._store.pop(key, None)
            return None
        return value

    def set_json(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        self._store[key] = (time() + ttl_seconds, value)


class RedisCache(CacheBackend):
    def __init__(self, url: str) -> None:
        self.client = Redis.from_url(url, decode_responses=True)

    def get_json(self, key: str) -> dict[str, Any] | None:
        try:
            cached = self.client.get(key)
        except RedisError:
            return None
        if not cached:
            return None
        return json.loads(cached)

    def set_json(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        try:
            self.client.setex(key, ttl_seconds, json.dumps(value, ensure_ascii=False))
        except RedisError:
            return


def build_cache() -> CacheBackend:
    if settings.redis_url:
        return RedisCache(settings.redis_url)
    return MemoryCache()


cache = build_cache()
