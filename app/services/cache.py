from __future__ import annotations

import json
from time import time
from typing import Any

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings

_hits = 0
_misses = 0


def cache_hit_rate() -> float:
    total = _hits + _misses
    if total == 0:
        return 1.0
    return _hits / total


class CacheBackend:
    def get_json(self, key: str) -> dict[str, Any] | None:
        raise NotImplementedError

    def set_json(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        raise NotImplementedError


class MemoryCache(CacheBackend):
    def __init__(self) -> None:
        self._store: dict[str, tuple[float, dict[str, Any]]] = {}

    def get_json(self, key: str) -> dict[str, Any] | None:
        global _hits, _misses
        record = self._store.get(key)
        if not record:
            _misses += 1
            return None
        expires_at, value = record
        if expires_at < time():
            _misses += 1
            self._store.pop(key, None)
            return None
        _hits += 1
        return value

    def set_json(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        self._store[key] = (time() + ttl_seconds, value)


class RedisCache(CacheBackend):
    def __init__(self, url: str) -> None:
        self.client = Redis.from_url(url, decode_responses=True)

    def get_json(self, key: str) -> dict[str, Any] | None:
        global _hits, _misses
        try:
            cached = self.client.get(key)
        except RedisError:
            _misses += 1
            return None
        if not cached:
            _misses += 1
            return None
        _hits += 1
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
