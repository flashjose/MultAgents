from __future__ import annotations

from pathlib import Path

from app.plugins.loader import PluginLoader
from app.plugins.registry import PluginRegistry
from app.services.plugin_manager import PluginManager


def test_discover_builtin_plugins() -> None:
    loader = PluginLoader()
    plugins = loader.discover_builtin_plugins()
    names = {plugin.name for plugin in plugins}

    assert len(plugins) >= 5
    assert {"bilibili", "weibo", "zhihu", "baidu", "toutiao"}.issubset(names)


def test_hot_load_external_plugin() -> None:
    registry = PluginRegistry()
    manager = PluginManager(registry, PluginLoader())
    sample_path = Path("examples/sample_plugin.py")

    name = manager.load_external(str(sample_path))

    assert name == "sample"
    assert registry.has("sample")
    assert registry.get("sample").display_name == "示例平台"


def test_reload_single_plugin() -> None:
    registry = PluginRegistry()
    manager = PluginManager(registry, PluginLoader())
    manager.bootstrap()

    assert registry.has("weibo")
    reloaded = manager.reload_one("weibo")

    assert reloaded == "weibo"
    assert registry.get("weibo").name == "weibo"


def test_unload_plugin() -> None:
    registry = PluginRegistry()
    manager = PluginManager(registry, PluginLoader())
    manager.bootstrap()

    manager.unload("douyin")
    assert not registry.has("douyin")
