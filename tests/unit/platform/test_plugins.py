from nasagent.config.settings import NasAgentSettings
from nasagent.platform.context import create_platform_context
from nasagent.platform.plugins import PluginManager, PluginManifest
from nasagent.safety.risk import RiskLevel
from nasagent.tools.base import ToolDefinition


async def _fake_tool() -> dict[str, str]:
    return {"status": "ok"}


def test_plugin_manager_loads_builtin_plugin_tools() -> None:
    context = create_platform_context(settings=NasAgentSettings())
    manager = PluginManager(context)

    manager.load_builtin()

    tool_names = {tool.name for tool in context.tools.list()}
    assert "storage.status" in tool_names
    assert "device.status" in tool_names
    assert "docker.compose.up" in tool_names
    assert manager.manifests["builtin"].name == "builtin"


def test_plugin_manager_records_failed_entry_point() -> None:
    context = create_platform_context(settings=NasAgentSettings())
    manager = PluginManager(context)

    class BrokenEntryPoint:
        name = "broken"

        def load(self):  # type: ignore[no-untyped-def]
            raise RuntimeError("boom")

    manager.load_entry_points(entry_points=[BrokenEntryPoint()])

    assert manager.errors[0].plugin == "broken"
    assert "boom" in manager.errors[0].message


def test_plugin_manager_loads_entry_point_manifest_and_tool() -> None:
    context = create_platform_context(settings=NasAgentSettings())
    manager = PluginManager(context)

    def register(plugin_context):  # type: ignore[no-untyped-def]
        plugin_context.manifest = PluginManifest(name="third-party", version="1.2.3")
        plugin_context.platform.tools.register(
            ToolDefinition("example.ping", "Ping example plugin", RiskLevel.READ, _fake_tool)
        )

    class FakeEntryPoint:
        name = "third-party"

        def load(self):  # type: ignore[no-untyped-def]
            return register

    manager.load_entry_points(entry_points=[FakeEntryPoint()])

    assert manager.manifests["third-party"].version == "1.2.3"
    assert context.tools.get("example.ping").description == "Ping example plugin"
