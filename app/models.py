from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class PlatformInfo(BaseModel):
    name: str
    display_name: str
    description: str
    enabled: bool = True


class HotItem(BaseModel):
    platform: str
    title: str
    url: HttpUrl | None = None
    rank: int | None = None
    score: str | int | float | None = None
    summary: str | None = None
    cover_url: HttpUrl | None = None
    author: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class PlatformHotspots(BaseModel):
    platform: str
    display_name: str
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_status: str = "live"
    items: list[HotItem]
    error: str | None = None


class HotspotCollection(BaseModel):
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    platforms: list[PlatformHotspots]
