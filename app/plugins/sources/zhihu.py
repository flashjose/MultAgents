from __future__ import annotations

import re

from app.core.field_mapper import map_to_hot_item
from app.models import HotItem
from app.plugins.base import HotspotPlugin
from app.services.http_client import http_client


class ZhihuHotPlugin(HotspotPlugin):
    name = "zhihu"
    display_name = "知乎"
    description = "Zhihu hot list."

    def fetch(self, limit: int = 20) -> list[HotItem]:
        data = http_client.get_json(
            "https://api.zhihu.com/topstory/hot-lists/total",
            params={"limit": limit},
            headers={"Referer": "https://www.zhihu.com/hot"},
        )
        records = data.get("data", [])
        if not records:
            raise ValueError("No hot topics parsed from Zhihu response")

        items: list[HotItem] = []
        for index, record in enumerate(records[:limit], start=1):
            target = record.get("target", {})
            title = target.get("title") or target.get("title_area", {}).get("text", "")
            url = self._normalize_url(target.get("url"))
            summary = target.get("excerpt") or target.get("excerpt_area", {}).get("text")
            score = record.get("detail_text") or target.get("metrics_area", {}).get("text")
            items.append(
                map_to_hot_item(
                    self.name,
                    title=title,
                    url=url,
                    rank=index,
                    score=score,
                    summary=summary,
                    raw=record,
                )
            )
        return items

    @staticmethod
    def _normalize_url(url: str | None) -> str | None:
        if not url:
            return None
        match = re.search(r"/questions/(\d+)", url)
        if match:
            return f"https://www.zhihu.com/question/{match.group(1)}"
        return url.replace("api.zhihu.com/questions", "www.zhihu.com/question")

    def fallback_items(self, limit: int = 20) -> list[HotItem]:
        return [
            map_to_hot_item(
                self.name,
                title="知乎热榜暂不可用",
                rank=1,
                summary="稍后可刷新重试。",
            )
        ][:limit]
