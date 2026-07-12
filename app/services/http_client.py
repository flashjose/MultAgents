from __future__ import annotations

import random
from time import sleep

import requests

from app.core.config import settings
from app.core.cookie_pool import CookiePool
from app.core.rate_limiter import HostRateLimiter


DEFAULT_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
]


class HttpClient:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.trust_env = settings.trust_env_proxy
        self.rate_limiter = HostRateLimiter(settings.min_request_interval_seconds)
        self.cookie_pool = CookiePool.from_env()

    def get_json(self, url: str, **kwargs) -> dict:
        response = self.get(url, **kwargs)
        return response.json()

    def get_text(self, url: str, **kwargs) -> str:
        response = self.get(url, **kwargs)
        return response.text

    def get(self, url: str, **kwargs) -> requests.Response:
        extra_headers = kwargs.pop("headers", {})
        attempts = settings.request_max_retries + 1
        last_exc: Exception | None = None
        for attempt in range(attempts):
            self.rate_limiter.wait_for_slot(url)
            headers = {
                "User-Agent": random.choice(DEFAULT_USER_AGENTS),
                "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }
            cookie = self.cookie_pool.get_cookie(url, strategy=settings.cookie_strategy)
            if cookie:
                headers["Cookie"] = cookie
            headers.update(extra_headers)
            try:
                response = self.session.get(
                    url,
                    timeout=settings.request_timeout_seconds,
                    headers=headers,
                    **kwargs,
                )
                response.raise_for_status()
                return response
            except (requests.ConnectionError, requests.Timeout) as exc:
                # Transient network errors (SSL EOF, RST, timeout): back off and retry
                # with a fresh User-Agent so one blip does not fail the whole platform.
                last_exc = exc
                if attempt + 1 >= attempts:
                    raise
                sleep(settings.request_retry_backoff_seconds * (attempt + 1))
        raise last_exc  # pragma: no cover - loop either returns or raises above


http_client = HttpClient()
