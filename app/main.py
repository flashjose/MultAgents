from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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

app = FastAPI(
    title="Multi-platform Content Aggregation API",
    description="可插拔多平台内容聚合系统，支持插件热加载、统一数据模型、Redis 缓存与反爬策略。",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def dashboard() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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
