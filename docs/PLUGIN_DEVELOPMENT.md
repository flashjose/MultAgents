# 插件开发指南

本文档说明如何为多平台内容聚合 API 系统开发、注册与热加载数据源插件。

## 架构概览

```
app/plugins/
├── base.py          # HotspotPlugin 抽象基类
├── loader.py        # 插件发现与热加载
├── registry.py      # 插件注册表
└── sources/         # 内置插件目录（启动时自动发现）
```

每个插件负责从目标平台抓取热点数据，并映射为统一的 `HotItem` 模型。

## 统一数据模型

所有插件必须返回 `HotItem` 列表：

| 字段 | 类型 | 说明 |
|------|------|------|
| platform | str | 平台标识，与插件 `name` 一致 |
| title | str | 标题（必填） |
| url | str | 原文链接 |
| rank | int | 排名 |
| score | str/int/float | 热度值 |
| summary | str | 摘要 |
| cover_url | str | 封面图 |
| author | str | 作者 |
| raw | dict | 原始字段，便于调试 |

推荐使用 `app.core.field_mapper.map_to_hot_item()` 做字段标准化。

## 最小插件示例

```python
from app.core.field_mapper import map_to_hot_item
from app.models import HotItem
from app.plugins.base import HotspotPlugin
from app.services.http_client import http_client


class ExampleHotPlugin(HotspotPlugin):
    name = "example"
    display_name = "示例平台"
    description = "Example hot list plugin."

    def fetch(self, limit: int = 20) -> list[HotItem]:
        data = http_client.get_json("https://api.example.com/hot")
        items = []
        for index, row in enumerate(data["items"][:limit], start=1):
            items.append(
                map_to_hot_item(
                    self.name,
                    title=row["title"],
                    url=row.get("url"),
                    rank=index,
                    score=row.get("heat"),
                    raw=row,
                )
            )
        return items

    def fallback_items(self, limit: int = 20) -> list[HotItem]:
        return [
            map_to_hot_item(
                self.name,
                title="示例平台暂不可用",
                rank=1,
                summary="接口异常时的降级数据。",
            )
        ][:limit]
```

## 注册方式

### 1. 内置插件（推荐）

将插件文件放入 `app/plugins/sources/`，继承 `HotspotPlugin` 即可。服务启动时会自动扫描注册。

### 2. 外部插件目录

将 `.py` 文件放入项目根目录的 `plugins/`（可通过环境变量 `PLUGIN_DIR` 修改），启动时自动加载。

### 3. 运行时热加载

无需重启，通过 REST API 动态加载：

```bash
# 从文件热加载
curl -X POST http://127.0.0.1:8000/plugins/load \
  -H "Content-Type: application/json" \
  -d "{\"path\": \"examples/sample_plugin.py\"}"

# 重载单个内置插件
curl -X POST http://127.0.0.1:8000/plugins/reload/weibo

# 重载全部插件
curl -X POST http://127.0.0.1:8000/plugins/reload

# 卸载插件
curl -X DELETE http://127.0.0.1:8000/plugins/sample
```

## HTTP 客户端与反爬策略

插件应统一使用 `app.services.http_client.http_client`，已内置：

- **User-Agent 轮换**：每次请求随机选择 UA
- **按 host 限流**：默认同一域名最小间隔 1 秒（`MIN_REQUEST_INTERVAL_SECONDS`）
- **Cookie 池**：通过环境变量 `COOKIE_POOL` 注入

Cookie 池配置示例：

```bash
export COOKIE_POOL='{"weibo.com":["cookie_a","cookie_b"],"zhihu.com":["cookie_c"],"*":["default_cookie"]}'
export COOKIE_STRATEGY=round_robin  # 或 random
```

## 缓存

`HotspotService` 会自动将结果写入 Redis（或内存回退缓存），默认 TTL 900 秒。客户端可通过 `?refresh=true` 强制刷新。

## 开发建议

1. 优先使用平台公开 JSON API，HTML 解析作为备选（参考 `douyin.py`、`ithome.py`）。
2. 在 `fetch()` 中抛出异常即可触发降级逻辑，不要阻塞其他平台。
3. 实现 `fallback_items()` 提供可识别的占位数据。
4. 将平台特有字段保留在 `raw` 中，便于后续扩展。
5. 开发完成后运行 `pytest tests/` 验证注册与 API 行为。

## 参考实现

| 插件 | 文件 | 采集方式 |
|------|------|----------|
| Bilibili | `sources/bilibili.py` | 官方 JSON API |
| 微博 | `sources/weibo.py` | 官方 JSON API |
| 知乎 | `sources/zhihu.py` | 官方 JSON API |
| 抖音 | `sources/douyin.py` | BeautifulSoup4 解析 |
| 百度 | `sources/baidu.py` | 官方 JSON API |
| 今日头条 | `sources/toutiao.py` | 官方 JSON API |
| IT之家 | `sources/ithome.py` | BeautifulSoup4 解析 |
| 示例 | `examples/sample_plugin.py` | 热加载演示 |
