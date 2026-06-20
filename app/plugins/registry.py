from __future__ import annotations

from app.models import PlatformInfo
from app.plugins.base import HotspotPlugin


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, HotspotPlugin] = {}

    def register(self, plugin: HotspotPlugin) -> None:
        if plugin.name in self._plugins:
            raise ValueError(f"Duplicate plugin name: {plugin.name}")
        self._plugins[plugin.name] = plugin

    def replace(self, plugin: HotspotPlugin) -> None:
        self._plugins[plugin.name] = plugin

    def unregister(self, name: str) -> HotspotPlugin:
        if name not in self._plugins:
            raise KeyError(f"Unknown plugin: {name}")
        return self._plugins.pop(name)

    def has(self, name: str) -> bool:
        return name in self._plugins

    def get(self, name: str) -> HotspotPlugin:
        return self._plugins[name]

    def names(self) -> list[str]:
        return sorted(self._plugins.keys())

    def platforms(self) -> list[PlatformInfo]:
        return [plugin.info() for plugin in self._plugins.values()]

    def enabled_plugins(self) -> list[HotspotPlugin]:
        return [plugin for plugin in self._plugins.values() if plugin.enabled]

    def clear(self) -> None:
        self._plugins.clear()
