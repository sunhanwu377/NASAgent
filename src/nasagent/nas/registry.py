from collections.abc import Callable

from nasagent.nas.base import NasAdapter

AdapterFactory = Callable[[], NasAdapter]


class AdapterRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, AdapterFactory] = {}

    def register(self, name: str, factory: AdapterFactory) -> None:
        self._factories[name] = factory

    def create(self, name: str) -> NasAdapter:
        try:
            factory = self._factories[name]
        except KeyError as exc:
            raise KeyError(f"Unknown NAS adapter: {name}") from exc
        return factory()
