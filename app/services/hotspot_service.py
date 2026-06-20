from __future__ import annotations

from app.core.config import settings
from app.models import HotspotCollection, PlatformHotspots
from app.plugins.registry import PluginRegistry
from app.services.cache import cache


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

        cache.set_json(cache_key, payload.model_dump(mode="json"), settings.cache_ttl_seconds)
        return payload
