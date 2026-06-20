"""示例插件：可通过热加载 API 动态注册，无需重启服务。

加载方式：
POST /plugins/load
{"path": "examples/sample_plugin.py"}
"""

from __future__ import annotations

from app.core.field_mapper import map_to_hot_item
from app.models import HotItem
from app.plugins.base import HotspotPlugin


class SampleHotPlugin(HotspotPlugin):
    name = "sample"
    display_name = "示例平台"
    description = "Demonstrates hot-loading a custom plugin at runtime."

    def fetch(self, limit: int = 20) -> list[HotItem]:
        samples = [
            ("多平台内容聚合 API", "https://example.com/docs"),
            ("插件热加载无需重启", "https://example.com/plugins"),
            ("统一 HotItem 数据模型", "https://example.com/models"),
        ]
        return [
            map_to_hot_item(
                self.name,
                title=title,
                url=url,
                rank=index,
                summary="这是一个可通过 /plugins/load 热加载的示例插件。",
            )
            for index, (title, url) in enumerate(samples[:limit], start=1)
        ]
