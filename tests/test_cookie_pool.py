from __future__ import annotations

import pytest

from app.core.cookie_pool import CookiePool


def test_cookie_pool_round_robin() -> None:
    pool = CookiePool({"example.com": ["a=1", "b=2"]})

    first = pool.get_cookie("https://example.com/hot")
    second = pool.get_cookie("https://example.com/hot")
    third = pool.get_cookie("https://example.com/hot")

    assert first == "a=1"
    assert second == "b=2"
    assert third == "a=1"


def test_cookie_pool_wildcard_fallback() -> None:
    pool = CookiePool({"*": ["default=1"]})

    assert pool.get_cookie("https://unknown.example/hot") == "default=1"


def test_cookie_pool_add_and_remove() -> None:
    pool = CookiePool()
    pool.add("weibo.com", "session=abc")

    assert pool.count("weibo.com") == 1
    pool.remove_host("weibo.com")
    assert pool.get_cookie("https://weibo.com/hot") is None
