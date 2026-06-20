from app.plugins.registry import PluginRegistry
from app.plugins.sources.bilibili import BilibiliHotPlugin


def test_register_platform() -> None:
    registry = PluginRegistry()
    plugin = BilibiliHotPlugin()

    registry.register(plugin)

    assert registry.has("bilibili")
    assert registry.get("bilibili") is plugin
    assert registry.platforms()[0].display_name == "Bilibili"
