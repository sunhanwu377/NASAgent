from nasagent.tools.nas.device_status import get_device_status_tool
from nasagent.tools.nas.file_management import (
    delete_file_tool,
    download_file_tool,
    list_files_tool,
    search_files_tool,
    upload_file_tool,
)
from nasagent.tools.nas.storage import get_storage_status_tool
from nasagent.tools.registry import ToolRegistry


def register_builtin_nas_tools(registry: ToolRegistry) -> None:
    for tool in [
        get_device_status_tool,
        get_storage_status_tool,
        list_files_tool,
        search_files_tool,
        upload_file_tool,
        download_file_tool,
        delete_file_tool,
    ]:
        registry.register(tool)


def default_tool_registry() -> ToolRegistry:
    from nasagent.config.settings import NasAgentSettings
    from nasagent.platform.context import create_platform_context
    from nasagent.platform.plugins import load_platform_plugins

    context = create_platform_context(settings=NasAgentSettings())
    load_platform_plugins(context)
    return context.tools
