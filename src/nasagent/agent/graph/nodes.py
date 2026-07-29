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
    registry = ToolRegistry()
    register_builtin_nas_tools(registry)
    return registry
