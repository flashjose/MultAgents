from __future__ import annotations

from app.models import HotItem
from app.plugins.base import HotspotPlugin
from app.services.http_client import http_client


class BilibiliHotPlugin(HotspotPlugin):
    name = "bilibili"
    display_name = "Bilibili"
    description = "Bilibili popular video ranking."

    def fetch(self, limit: int = 20) -> list[HotItem]:
        data = http_client.get_json(
            "https://api.bilibili.com/x/web-interface/popular",
            params={"ps": limit, "pn": 1},
            headers={"Referer": "https://www.bilibili.com/"},
        )
        videos = data.get("data", {}).get("list", [])
        items: list[HotItem] = []
        for index, video in enumerate(videos[:limit], start=1):
            bvid = video.get("bvid")
            url = f"https://www.bilibili.com/video/{bvid}" if bvid else None
            stat = video.get("stat", {})
            items.append(
                HotItem(
                    platform=self.name,
                    title=video.get("title", ""),
                    url=url,
                    rank=index,
                    score=stat.get("view"),
                    summary=video.get("desc") or None,
                    cover_url=video.get("pic") or None,
                    author=(video.get("owner") or {}).get("name"),
                    raw={"bvid": bvid, "duration": video.get("duration"), "stat": stat},
                )
            )
        return items

    def fallback_items(self, limit: int = 20) -> list[HotItem]:
        return [
            HotItem(platform=self.name, title="Bilibili 热门视频暂不可用", rank=1, summary="稍后可刷新重试。")
        ][:limit]
