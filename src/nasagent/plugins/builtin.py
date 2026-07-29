from dataclasses import replace

from nasagent.agent.graph.nodes import register_builtin_nas_tools
from nasagent.platform.plugins import PluginContext, PluginManifest
from nasagent.plugins.commands import register_builtin_commands
from nasagent.tools.nas.device_status import get_device_status_tool
from nasagent.tools.nas.storage import get_storage_status_tool


def register(plugin: PluginContext) -> None:
    plugin.manifest = PluginManifest(
        name="builtin",
        version="0.1.0",
        description="NASAgent built-in tools and commands",
        permissions=("nas",),
    )
    register_builtin_nas_tools(plugin.platform.tools)
    register_builtin_commands(plugin.platform)
    plugin.platform.tools.register(replace(get_device_status_tool, name="device.status"))
    plugin.platform.tools.register(replace(get_storage_status_tool, name="storage.status"))
