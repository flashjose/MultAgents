from __future__ import annotations

from urllib.parse import quote

from app.core.field_mapper import map_to_hot_item
from app.models import HotItem
from app.plugins.base import HotspotPlugin
from app.services.http_client import http_client


class BaiduHotPlugin(HotspotPlugin):
    name = "baidu"
    display_name = "百度"
    description = "Baidu realtime hot search board."

    def fetch(self, limit: int = 20) -> list[HotItem]:
        data = http_client.get_json(
            "https://top.baidu.com/api/board",
            params={"platform": "wise", "tab": "realtime"},
            headers={"Referer": "https://top.baidu.com/board?tab=realtime"},
        )
        entries = self._extract_entries(data.get("data", {}).get("cards", []))
        if not entries:
            raise ValueError("No hot topics parsed from Baidu response")

        items: list[HotItem] = []
        for index, entry in enumerate(entries[:limit], start=1):
            word = entry.get("word") or entry.get("query") or ""
            url = entry.get("url") or entry.get("rawUrl")
            if not url and word:
                url = f"https://www.baidu.com/s?wd={quote(word)}"
            items.append(
                map_to_hot_item(
                    self.name,
                    title=word,
                    url=url,
                    rank=index,
                    score=entry.get("hotScore") or entry.get("hotTag"),
                    summary=entry.get("desc") or entry.get("brief"),
                    cover_url=entry.get("img"),
                    raw=entry,
                )
            )
        return items

    @staticmethod
    def _extract_entries(cards: list[dict]) -> list[dict]:
        entries: list[dict] = []
        for card in cards:
            content = card.get("content", [])
            for block in content:
                if not isinstance(block, dict):
                    continue
                nested = block.get("content")
                if isinstance(nested, list) and nested:
                    entries.extend(item for item in nested if isinstance(item, dict))
                elif block.get("word") or block.get("query"):
                    entries.append(block)
        return entries

    def fallback_items(self, limit: int = 20) -> list[HotItem]:
        return [
            map_to_hot_item(
                self.name,
                title="百度热搜暂不可用",
                rank=1,
                summary="稍后可刷新重试。",
            )
        ][:limit]
