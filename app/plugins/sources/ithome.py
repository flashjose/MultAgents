from __future__ import annotations

from bs4 import BeautifulSoup

from app.core.field_mapper import map_to_hot_item
from app.models import HotItem
from app.plugins.base import HotspotPlugin
from app.services.http_client import http_client


class IthomeHotPlugin(HotspotPlugin):
    name = "ithome"
    display_name = "IT之家"
    description = "IT Home daily hot rank parsed with BeautifulSoup4."

    def fetch(self, limit: int = 20) -> list[HotItem]:
        html = http_client.get_text(
            "https://www.ithome.com/block/rank.html",
            headers={"Referer": "https://www.ithome.com/"},
        )
        soup = BeautifulSoup(html, "html.parser")
        links = soup.select("ul.bd.order li a")
        items: list[HotItem] = []
        seen_titles: set[str] = set()
        for link in links:
            title = link.get("title") or link.get_text(strip=True)
            href = link.get("href")
            if not title or not href or title in seen_titles:
                continue
            if href.startswith("//"):
                url = f"https:{href}"
            elif href.startswith("/"):
                url = f"https://www.ithome.com{href}"
            else:
                url = href
            seen_titles.add(title)
            items.append(
                map_to_hot_item(
                    self.name,
                    title=title,
                    url=url,
                    rank=len(items) + 1,
                    raw={"href": href},
                )
            )
            if len(items) >= limit:
                break
        if not items:
            raise ValueError("No hot topics parsed from IT Home rank page")
        return items

    def fallback_items(self, limit: int = 20) -> list[HotItem]:
        return [
            map_to_hot_item(
                self.name,
                title="IT之家热点暂不可用",
                rank=1,
                summary="页面结构可能发生变化，请稍后重试。",
            )
        ][:limit]
