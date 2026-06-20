from __future__ import annotations

import json
import os
import random
from threading import Lock
from urllib.parse import urlparse


class CookiePool:
    """Per-host cookie rotation pool for anti-scraping."""

    def __init__(self, pool_config: dict[str, list[str]] | None = None) -> None:
        self._pools: dict[str, list[str]] = pool_config or {}
        self._round_robin_index: dict[str, int] = {}
        self._lock = Lock()

    @classmethod
    def from_env(cls, env_name: str = "COOKIE_POOL") -> CookiePool:
        raw = os.getenv(env_name)
        if not raw:
            return cls()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return cls()
        if not isinstance(data, dict):
            return cls()
        pools: dict[str, list[str]] = {}
        for host, cookies in data.items():
            if isinstance(cookies, str):
                pools[host] = [cookies]
            elif isinstance(cookies, list):
                pools[host] = [str(item) for item in cookies if item]
        return cls(pools)

    def add(self, host: str, cookie: str) -> None:
        with self._lock:
            self._pools.setdefault(host, []).append(cookie)

    def remove_host(self, host: str) -> None:
        with self._lock:
            self._pools.pop(host, None)
            self._round_robin_index.pop(host, None)

    def hosts(self) -> list[str]:
        return sorted(self._pools.keys())

    def count(self, host: str | None = None) -> int:
        if host is None:
            return sum(len(items) for items in self._pools.values())
        return len(self._pools.get(host, []))

    def get_cookie(self, url: str, strategy: str = "round_robin") -> str | None:
        host = urlparse(url).netloc or "default"
        cookies = self._resolve_cookies(host)
        if not cookies:
            return None
        if strategy == "random":
            return random.choice(cookies)
        with self._lock:
            index = self._round_robin_index.get(host, 0)
            cookie = cookies[index % len(cookies)]
            self._round_robin_index[host] = index + 1
            return cookie

    def _resolve_cookies(self, host: str) -> list[str]:
        if host in self._pools:
            return self._pools[host]
        for key, cookies in self._pools.items():
            if key != "*" and host.endswith(key):
                return cookies
        return self._pools.get("*", [])
