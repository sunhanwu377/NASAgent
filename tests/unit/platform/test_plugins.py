from nasagent.config.settings import NasAgentSettings
from nasagent.platform.context import create_platform_context
from nasagent.platform.plugins import PluginManager


def test_plugin_manager_loads_builtin_plugin_tools() -> None:
    context = create_platform_context(settings=NasAgentSettings())
    manager = PluginManager(context)

    manager.load_builtin()

    tool_names = {tool.name for tool in context.tools.list()}
    assert "storage.status" in tool_names
    assert "device.status" in tool_names
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
