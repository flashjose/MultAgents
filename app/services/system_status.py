from __future__ import annotations

import socket
from time import time
from urllib.parse import urlparse

from app.core.config import settings

# Recorded at import (server startup) — used for real process uptime.
_START_TIME = time()


def uptime_seconds() -> int:
    return int(time() - _START_TIME)


def _probe_redis() -> tuple[str, str]:
    """Real Redis health via PING. Falls back honestly to the memory cache label."""
    if not settings.redis_url:
        return "memory", "内存缓存回退（未配置 REDIS_URL）"
    try:
        from redis import Redis

        client = Redis.from_url(
            settings.redis_url, socket_connect_timeout=1.5, socket_timeout=1.5
        )
        client.ping()
        return "online", "PING 正常"
    except Exception as exc:  # noqa: BLE001 - report any probe failure as offline
        return "offline", str(exc)[:80]


def _probe_tcp(url: str | None, default_port: int) -> tuple[str, str]:
    """Dependency-free reachability check: does the host:port accept a TCP connection?"""
    if not url:
        return "not_configured", "未配置"
    parsed = urlparse(url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or default_port
    try:
        with socket.create_connection((host, port), timeout=1.5):
            return "online", f"{host}:{port} 可达"
    except OSError:
        return "offline", f"{host}:{port} 不可达"


def collect_status() -> dict:
    redis_status, redis_detail = _probe_redis()
    mysql_status, mysql_detail = _probe_tcp(settings.mysql_url, 3306)
    return {
        "uptime_seconds": uptime_seconds(),
        "components": [
            {"name": "fastapi", "status": "online", "detail": "服务运行中"},
            {"name": "redis", "status": redis_status, "detail": redis_detail},
            {"name": "mysql", "status": mysql_status, "detail": mysql_detail},
        ],
    }
