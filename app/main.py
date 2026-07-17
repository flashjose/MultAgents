import sys
from pathlib import Path
from urllib.parse import urlparse

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from app.services.http_client import http_client

from app.models import DashboardStats, HotspotCollection, PlatformInfo, SystemStatus
from app.plugins.loader import PluginLoader
from app.plugins.registry import PluginRegistry
from app.schemas import PluginActionResponse, PluginLoadRequest
from app.services.cache import cache, cache_hit_rate
from app.services.hotspot_service import HotspotService, avg_response_time_ms
from app.services.plugin_manager import PluginManager
from app.services.system_status import collect_status


registry = PluginRegistry()
loader = PluginLoader()
plugin_manager = PluginManager(registry, loader)
plugin_manager.bootstrap()
service = HotspotService(registry)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

# --- Image proxy config -----------------------------------------------------
# Cover images live on external CDNs that are often http-only and hotlink
# protected, so the browser cannot load them directly. The /img endpoint
# re-fetches them server-side (correct Referer via http_client) and streams the
# bytes back. The host allowlist below is an SSRF guard: only these known image
# CDNs may be proxied, never arbitrary/internal hosts.
_ALLOWED_IMAGE_HOSTS = (
    "hdslb.com", "bilibili.com",                              # bilibili
    "bdstatic.com", "baidu.com", "bcebos.com",               # baidu
    "sinaimg.cn", "weibocdn.com",                            # weibo
    "pstatp.com", "byteimg.com", "douyinpic.com",            # douyin / bytedance
    "toutiaoimg.com", "toutiaoimg.cn", "ixiguavideo.com",    # toutiao / xigua
    "zhimg.com",                                             # zhihu
    "ithome.com", "ithomeimg.com",                          # ithome
    "qpic.cn",                                              # misc
)
_REFERER_BY_HOST = (
    ("hdslb.com", "https://www.bilibili.com/"),
    ("bilibili.com", "https://www.bilibili.com/"),
    ("douyinpic.com", "https://www.douyin.com/"),
    ("byteimg.com", "https://www.douyin.com/"),
    ("pstatp.com", "https://www.toutiao.com/"),
    ("toutiaoimg.com", "https://www.toutiao.com/"),
    ("toutiaoimg.cn", "https://www.toutiao.com/"),
    ("bdstatic.com", "https://www.baidu.com/"),
    ("bcebos.com", "https://www.baidu.com/"),
    ("baidu.com", "https://www.baidu.com/"),
    ("sinaimg.cn", "https://weibo.com/"),
    ("weibocdn.com", "https://weibo.com/"),
    ("zhimg.com", "https://www.zhihu.com/"),
    ("ithome.com", "https://www.ithome.com/"),
    ("ithomeimg.com", "https://www.ithome.com/"),
)


def _host_matches(host: str, suffix: str) -> bool:
    return host == suffix or host.endswith("." + suffix)


def _pick_referer(host: str, url: str) -> str:
    for suffix, referer in _REFERER_BY_HOST:
        if _host_matches(host, suffix):
            return referer
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}/"

app = FastAPI(
    title="Multi-platform Content Aggregation API",
    description="可插拔多平台内容聚合系统，支持插件热加载、统一数据模型、Redis 缓存与反爬策略。",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.middleware("http")
async def _revalidate_frontend_assets(request: Request, call_next):
    # Force browsers to revalidate the dashboard + static assets via ETag instead
    # of serving a heuristically-cached stale copy, so UI edits show up on a normal
    # reload (no hard-refresh needed). Cheap: unchanged files still return 304.
    response = await call_next(request)
    path = request.url.path
    if path == "/" or path.startswith("/static"):
        response.headers["Cache-Control"] = "no-cache"
    return response


@app.get("/")
def dashboard() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/img")
def image_proxy(url: str = Query(..., min_length=8, max_length=2048)) -> Response:
    """Proxy an external cover image so the browser can display it.

    Guards against SSRF via an image-CDN host allowlist and forwards a
    per-host Referer so hotlink-protected CDNs serve the bytes.
    """
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"} or not host:
        raise HTTPException(status_code=400, detail="Invalid image URL")
    if not any(_host_matches(host, suffix) for suffix in _ALLOWED_IMAGE_HOSTS):
        raise HTTPException(status_code=400, detail="Image host not allowed")
    try:
        resp = http_client.get(url, headers={"Referer": _pick_referer(host, url)})
    except Exception as exc:  # upstream 403/404/timeout -> let the frontend fall back
        raise HTTPException(status_code=404, detail="Image unavailable") from exc
    content_type = resp.headers.get("Content-Type", "image/jpeg")
    if not content_type.startswith("image/"):
        content_type = "image/jpeg"
    return Response(
        content=resp.content,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )


@app.get("/system/status", response_model=SystemStatus)
def system_status() -> SystemStatus:
    return SystemStatus(**collect_status())


@app.get("/stats", response_model=DashboardStats)
def get_stats() -> DashboardStats:
    platforms = registry.platforms()
    # Fast count from cache only — avoids triggering external fetches
    total_items = 0
    for plugin in registry.enabled_plugins():
        cached = cache.get_json(f"hotspots:{plugin.name}:20")
        if cached:
            try:
                collection = HotspotCollection.model_validate(cached)
                total_items += sum(len(p.items) for p in collection.platforms)
            except Exception:
                pass
    return DashboardStats(
        platform_count=len(platforms),
        total_hotspots=total_items,
        avg_response_time_ms=round(avg_response_time_ms(), 1),
        cache_hit_rate=round(cache_hit_rate(), 3),
    )


@app.get("/platforms", response_model=list[PlatformInfo])
def list_platforms() -> list[PlatformInfo]:
    return registry.platforms()


@app.get("/hotspots", response_model=HotspotCollection)
def get_all_hotspots(
    limit: int = Query(default=20, ge=1, le=50),
    refresh: bool = Query(default=False),
) -> HotspotCollection:
    return service.get_all(limit=limit, refresh=refresh)


@app.get("/hotspots/{platform}", response_model=HotspotCollection)
def get_platform_hotspots(
    platform: str,
    limit: int = Query(default=20, ge=1, le=50),
    refresh: bool = Query(default=False),
) -> HotspotCollection:
    if not registry.has(platform):
        raise HTTPException(status_code=404, detail=f"Unknown platform: {platform}")
    return service.get_platform(platform=platform, limit=limit, refresh=refresh)


@app.post("/plugins/reload", response_model=PluginActionResponse)
def reload_all_plugins() -> PluginActionResponse:
    platforms = plugin_manager.reload_all()
    return PluginActionResponse(status="ok", platforms=platforms, message="All plugins reloaded")


@app.post("/plugins/reload/{platform}", response_model=PluginActionResponse)
def reload_plugin(platform: str) -> PluginActionResponse:
    if not registry.has(platform):
        raise HTTPException(status_code=404, detail=f"Unknown platform: {platform}")
    try:
        name = plugin_manager.reload_one(platform)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PluginActionResponse(status="ok", platform=name, message=f"Plugin '{name}' reloaded")


@app.post("/plugins/load", response_model=PluginActionResponse)
def load_plugin(request: PluginLoadRequest) -> PluginActionResponse:
    try:
        name = plugin_manager.load_external(request.path)
    except (FileNotFoundError, ValueError, ImportError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PluginActionResponse(status="ok", platform=name, message=f"Plugin '{name}' loaded")


@app.delete("/plugins/{platform}", response_model=PluginActionResponse)
def unload_plugin(platform: str) -> PluginActionResponse:
    if not registry.has(platform):
        raise HTTPException(status_code=404, detail=f"Unknown platform: {platform}")
    plugin_manager.unload(platform)
    return PluginActionResponse(status="ok", platform=platform, message=f"Plugin '{platform}' unloaded")
