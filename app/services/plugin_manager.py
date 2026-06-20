from __future__ import annotations

from pathlib import Path

from app.core.config import settings
from app.plugins.loader import PluginLoader
from app.plugins.registry import PluginRegistry


class PluginManager:
    def __init__(self, registry: PluginRegistry, loader: PluginLoader) -> None:
        self.registry = registry
        self.loader = loader

    def bootstrap(self) -> None:
        self.registry.clear()
        for plugin in self.loader.discover_builtin_plugins():
            self.registry.register(plugin)
        self._load_external_plugins()

    def reload_all(self) -> list[str]:
        self.registry.clear()
        self.bootstrap()
        return self.registry.names()

    def reload_one(self, platform: str) -> str:
        plugin = self.loader.reload_plugin(platform)
        self.registry.replace(plugin)
        return plugin.name

    def load_external(self, file_path: str) -> str:
        plugin = self.loader.load_from_file(file_path)
        if self.registry.has(plugin.name):
            self.registry.replace(plugin)
        else:
            self.registry.register(plugin)
        return plugin.name

    def unload(self, platform: str) -> None:
        self.registry.unregister(platform)

    def _load_external_plugins(self) -> None:
        plugin_dir = Path(settings.plugin_dir)
        if not plugin_dir.exists():
            return
        for file_path in sorted(plugin_dir.glob("*.py")):
            if file_path.name.startswith("_"):
                continue
            try:
                plugin = self.loader.load_from_file(file_path)
                if self.registry.has(plugin.name):
                    self.registry.replace(plugin)
                else:
                    self.registry.register(plugin)
            except Exception:
                continue
