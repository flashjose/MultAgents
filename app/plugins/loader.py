from __future__ import annotations

import importlib
import importlib.util
import inspect
import pkgutil
import sys
from pathlib import Path
from types import ModuleType

from app.plugins.base import HotspotPlugin


class PluginLoader:
    """Discover and hot-load HotspotPlugin implementations without service restart."""

    def __init__(self, builtin_package: str = "app.plugins.sources") -> None:
        self.builtin_package = builtin_package
        self._loaded_modules: dict[str, str] = {}

    def discover_builtin_plugins(self) -> list[HotspotPlugin]:
        plugins: list[HotspotPlugin] = []
        package = importlib.import_module(self.builtin_package)
        for module_info in pkgutil.iter_modules(package.__path__, f"{self.builtin_package}."):
            if module_info.name.endswith(".__init__"):
                continue
            module = importlib.import_module(module_info.name)
            for plugin in self._extract_plugins(module):
                plugins.append(plugin)
                self._loaded_modules[plugin.name] = module_info.name
        return plugins

    def reload_plugin(self, platform: str) -> HotspotPlugin:
        module_name = self._loaded_modules.get(platform)
        if not module_name:
            raise KeyError(f"Plugin not loaded: {platform}")
        module = importlib.reload(sys.modules[module_name])
        plugins = self._extract_plugins(module)
        matched = next((plugin for plugin in plugins if plugin.name == platform), None)
        if not matched:
            raise ValueError(f"No plugin named '{platform}' found in module {module_name}")
        return matched

    def load_from_file(self, file_path: str | Path) -> HotspotPlugin:
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Plugin file not found: {path}")
        if path.suffix != ".py":
            raise ValueError("Plugin file must be a .py module")

        module_name = f"dynamic_plugin_{path.stem}_{abs(hash(str(path))) % 10_000_000}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Unable to load plugin module from {path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        plugins = self._extract_plugins(module)
        if not plugins:
            raise ValueError(f"No HotspotPlugin subclass found in {path}")
        if len(plugins) > 1:
            raise ValueError(f"Multiple HotspotPlugin subclasses found in {path}")

        plugin = plugins[0]
        self._loaded_modules[plugin.name] = module_name
        return plugin

    def loaded_modules(self) -> dict[str, str]:
        return dict(self._loaded_modules)

    @staticmethod
    def _extract_plugins(module: ModuleType) -> list[HotspotPlugin]:
        plugins: list[HotspotPlugin] = []
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if not issubclass(obj, HotspotPlugin) or obj is HotspotPlugin:
                continue
            if inspect.isabstract(obj):
                continue
            plugins.append(obj())
        return plugins
