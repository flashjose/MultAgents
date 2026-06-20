from __future__ import annotations

from app.models import HotItem
from app.plugins.base import HotspotPlugin
from app.services.http_client import http_client


class WeiboHotPlugin(HotspotPlugin):
    name = "weibo"
    display_name = "微博"
    description = "Weibo realtime hot search list."

    def fetch(self, limit: int = 20) -> list[HotItem]:
        data = http_client.get_json(
            "https://weibo.com/ajax/side/hotSearch",
            headers={"Referer": "https://weibo.com/newlogin?tabtype=search"},
        )
        realtime = data.get("data", {}).get("realtime", [])
        items: list[HotItem] = []
        for index, topic in enumerate(realtime[:limit], start=1):
            word = topic.get("word") or topic.get("note") or ""
            items.append(
                HotItem(
                    platform=self.name,
                    title=word,
                    url=f"https://s.weibo.com/weibo?q={word}",
                    rank=index,
                    score=topic.get("num"),
                    summary=topic.get("word_scheme") or None,
                    raw=topic,
                )
            )
        return items

    def fallback_items(self, limit: int = 20) -> list[HotItem]:
        return [
            HotItem(platform=self.name, title="微博热搜暂不可用", rank=1, summary="可能需要稍后重试。")
        ][:limit]
