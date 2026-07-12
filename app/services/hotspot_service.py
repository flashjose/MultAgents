from __future__ import annotations

from time import monotonic

from app.core.config import settings
from app.models import HotspotCollection, PlatformHotspots
from app.plugins.registry import PluginRegistry
from app.services.cache import cache, cache_hit_rate


_response_times: list[float] = []


def avg_response_time_ms() -> float:
    if not _response_times:
        return 0.0
    return sum(_response_times) / len(_response_times) * 1000


class HotspotService:
    def __init__(self, registry: PluginRegistry) -> None:
        self.registry = registry

    def get_all(self, limit: int, refresh: bool = False) -> HotspotCollection:
        platforms = [
            self.get_platform(plugin.name, limit=limit, refresh=refresh).platforms[0]
            for plugin in self.registry.enabled_plugins()
        ]
        return HotspotCollection(platforms=platforms)

    def get_platform(self, platform: str, limit: int, refresh: bool = False) -> HotspotCollection:
        plugin = self.registry.get(platform)
        cache_key = f"hotspots:{platform}:{limit}"
        if not refresh:
            cached = cache.get_json(cache_key)
            if cached:
                return HotspotCollection.model_validate(cached)

        t0 = monotonic()
        ok = True
        try:
            items = plugin.fetch(limit=limit)
            payload = HotspotCollection(
                platforms=[
                    PlatformHotspots(
                        platform=plugin.name,
                        display_name=plugin.display_name,
                        items=items[:limit],
                    )
                ]
            )
        except Exception as exc:
            ok = False
            payload = HotspotCollection(
                platforms=[
                    PlatformHotspots(
                        platform=plugin.name,
                        display_name=plugin.display_name,
                        source_status="error",
                        items=plugin.fallback_items(limit=limit),
                        error=str(exc),
                    )
                ]
            )
        elapsed = monotonic() - t0
        _response_times.append(elapsed)
        if len(_response_times) > 200:
            _response_times.pop(0)

        # Cache successes for the full TTL; cache errors only briefly so a transient
        # failure recovers on the next request instead of sticking for cache_ttl_seconds.
        ttl = settings.cache_ttl_seconds if ok else settings.error_cache_ttl_seconds
        cache.set_json(cache_key, payload.model_dump(mode="json"), ttl)
        return payload
