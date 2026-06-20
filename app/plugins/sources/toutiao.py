from __future__ import annotations

from app.core.field_mapper import map_to_hot_item
from app.models import HotItem
from app.plugins.base import HotspotPlugin
from app.services.http_client import http_client


class ToutiaoHotPlugin(HotspotPlugin):
    name = "toutiao"
    display_name = "今日头条"
    description = "Toutiao hot board via public hot-list API."

    def fetch(self, limit: int = 20) -> list[HotItem]:
        data = http_client.get_json(
            "https://www.toutiao.com/hot-event/hot-board/",
            params={"origin": "toutiao_pc"},
            headers={"Referer": "https://www.toutiao.com/"},
        )
        records = data.get("data", [])
        items: list[HotItem] = []
        for index, record in enumerate(records[:limit], start=1):
            title = record.get("Title") or record.get("title") or ""
            url = record.get("Url") or record.get("url")
            if not url and title:
                url = f"https://www.toutiao.com/search?keyword={title}"
            items.append(
                map_to_hot_item(
                    self.name,
                    title=title,
                    url=url,
                    rank=index,
                    score=record.get("HotValue") or record.get("hot_value"),
                    summary=record.get("Label") or record.get("label"),
                    raw=record,
                )
            )
        return items

    def fallback_items(self, limit: int = 20) -> list[HotItem]:
        return [
            map_to_hot_item(
                self.name,
                title="今日头条热榜暂不可用",
                rank=1,
                summary="可能需要配置 Cookie 池后重试。",
            )
        ][:limit]
