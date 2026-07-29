from collections.abc import Callable, Iterable
from dataclasses import dataclass
from importlib.metadata import entry_points
from typing import Protocol, cast

from nasagent.platform.context import PlatformContext

PluginRegister = Callable[["PluginContext"], None]


class PluginEntryPoint(Protocol):
    name: str

    def load(self) -> PluginRegister: ...


@dataclass(frozen=True)
class PluginManifest:
    name: str
    version: str
    description: str = ""
    author: str | None = None
    permissions: tuple[str, ...] = ()


@dataclass(frozen=True)
class PluginLoadError:
    plugin: str
    message: str


@dataclass
class PluginContext:
    platform: PlatformContext
    manifest: PluginManifest | None = None


class PluginManager:
    def __init__(self, context: PlatformContext) -> None:
        self.context = context
        self.manifests = cast(dict[str, PluginManifest], context.plugin_manifests)
        self.errors = cast(list[PluginLoadError], context.plugin_errors)

    def register_manifest(self, manifest: PluginManifest) -> None:
        self.manifests[manifest.name] = manifest

    def load_builtin(self) -> None:
        from nasagent.plugins.builtin import register

        plugin_context = PluginContext(platform=self.context)
        register(plugin_context)
        if plugin_context.manifest is not None:
            self.register_manifest(plugin_context.manifest)

    def load_entry_points(self, *, entry_points: Iterable[PluginEntryPoint] | None = None) -> None:
        discovered = entry_points
        if discovered is None:
            discovered = entry_points_select()
        for entry_point in discovered:
            name = str(getattr(entry_point, "name", "unknown"))
            try:
                register = entry_point.load()
                plugin_context = PluginContext(platform=self.context)
                register(plugin_context)
                if plugin_context.manifest is not None:
                    self.register_manifest(plugin_context.manifest)
            except Exception as exc:
                self.errors.append(PluginLoadError(plugin=name, message=str(exc)))


def load_platform_plugins(
    context: PlatformContext,
    *,
    entry_points: Iterable[PluginEntryPoint] | None = None,
) -> PluginManager:
    manager = PluginManager(context)
    manager.load_builtin()
    manager.load_entry_points(entry_points=entry_points)
    return manager


def entry_points_select() -> Iterable[PluginEntryPoint]:
    return entry_points(group="nasagent.plugins")
