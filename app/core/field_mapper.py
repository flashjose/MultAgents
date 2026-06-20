from __future__ import annotations

from typing import Any

from app.models import HotItem


def map_to_hot_item(
    platform: str,
    *,
    title: Any,
    url: str | None = None,
    rank: int | None = None,
    score: str | int | float | None = None,
    summary: str | None = None,
    cover_url: str | None = None,
    author: str | None = None,
    raw: dict[str, Any] | None = None,
) -> HotItem:
    """Normalize platform-specific fields into the unified HotItem model."""
    normalized_title = str(title or "").strip()
    if not normalized_title:
        raise ValueError("Hot item title cannot be empty")

    normalized_summary = str(summary).strip() if summary else None
    normalized_author = str(author).strip() if author else None

    return HotItem(
        platform=platform,
        title=normalized_title,
        url=url or None,
        rank=rank,
        score=score,
        summary=normalized_summary or None,
        cover_url=cover_url or None,
        author=normalized_author or None,
        raw=raw or {},
    )


def map_batch(
    platform: str,
    records: list[dict[str, Any]],
    *,
    title_key: str = "title",
    url_key: str = "url",
    rank_key: str = "rank",
    score_key: str = "score",
    summary_key: str = "summary",
    cover_url_key: str = "cover_url",
    author_key: str = "author",
    limit: int = 20,
) -> list[HotItem]:
    items: list[HotItem] = []
    for index, record in enumerate(records[:limit], start=1):
        items.append(
            map_to_hot_item(
                platform,
                title=record.get(title_key, ""),
                url=record.get(url_key),
                rank=record.get(rank_key, index),
                score=record.get(score_key),
                summary=record.get(summary_key),
                cover_url=record.get(cover_url_key),
                author=record.get(author_key),
                raw=record,
            )
        )
    return items
