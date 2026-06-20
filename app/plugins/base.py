from __future__ import annotations

from abc import ABC, abstractmethod

from app.models import HotItem, PlatformInfo


class HotspotPlugin(ABC):
    name: str
    display_name: str
    description: str
    enabled: bool = True

    @abstractmethod
    def fetch(self, limit: int = 20) -> list[HotItem]:
        raise NotImplementedError

    def fallback_items(self, limit: int = 20) -> list[HotItem]:
        return []

    def info(self) -> PlatformInfo:
        return PlatformInfo(
            name=self.name,
            display_name=self.display_name,
            description=self.description,
            enabled=self.enabled,
        )
