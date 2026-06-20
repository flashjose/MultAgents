from __future__ import annotations

from urllib.parse import quote

from app.core.field_mapper import map_to_hot_item
from app.models import HotItem
from app.plugins.base import HotspotPlugin
from app.services.http_client import http_client


class DouyinHotPlugin(HotspotPlugin):
    name = "douyin"
    display_name = "抖音"
    description = "Douyin hot search list via official web API."

    def fetch(self, limit: int = 20) -> list[HotItem]:
        data = http_client.get_json(
            "https://www.douyin.com/aweme/v1/web/hot/search/list/",
            headers={"Referer": "https://www.douyin.com/"},
        )
        word_list = data.get("data", {}).get("word_list", [])
        if not word_list:
            raise ValueError("No hot topics parsed from Douyin response")

        items: list[HotItem] = []
        for index, record in enumerate(word_list[:limit], start=1):
            word = record.get("word", "")
            items.append(
                map_to_hot_item(
                    self.name,
                    title=word,
                    url=f"https://www.douyin.com/search/{quote(word)}",
                    rank=record.get("position") or index,
                    score=record.get("hot_value"),
                    summary=record.get("sentence_tag") or None,
                    cover_url=(record.get("word_cover") or {}).get("url_list", [None])[0],
                    raw=record,
                )
            )
        return items

    def fallback_items(self, limit: int = 20) -> list[HotItem]:
        samples = ["抖音热点榜暂不可用", "建议配置 Cookie 池后重试"]
        return [
            map_to_hot_item(
                self.name,
                title=title,
                rank=index,
                summary="当前使用降级数据。",
            )
            for index, title in enumerate(samples[:limit], start=1)
        ]
