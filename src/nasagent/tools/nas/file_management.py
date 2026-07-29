from nasagent.safety.risk import RiskLevel
from nasagent.tools.base import ToolContext, ToolDefinition


async def list_files(context: ToolContext, path: str) -> dict[str, object]:
    files = await context.adapter.list_files(path)
    return {"files": [file.model_dump() for file in files]}


async def search_files(
    context: ToolContext,
    query: str,
    path: str | None = None,
) -> dict[str, object]:
    files = await context.adapter.search_files(query=query, path=path)
    return {"files": [file.model_dump() for file in files]}


async def upload_file(context: ToolContext, local_path: str, remote_path: str) -> dict[str, object]:
    file = await context.adapter.upload_file(local_path=local_path, remote_path=remote_path)
    return file.model_dump()


async def download_file(
    context: ToolContext,
    remote_path: str,
    local_path: str,
) -> dict[str, object]:
    file = await context.adapter.download_file(remote_path=remote_path, local_path=local_path)
    return file.model_dump()


async def delete_file(context: ToolContext, path: str) -> dict[str, object]:
    await context.adapter.delete_file(path)
    return {"deleted": path}


list_files_tool = ToolDefinition(
    "list_files",
    "List files in a NAS path.",
    RiskLevel.READ,
    list_files,
    adapter_capability="list_files",
)
search_files_tool = ToolDefinition(
    "search_files",
    "Search files on NAS.",
    RiskLevel.READ,
    search_files,
    adapter_capability="search_files",
)
upload_file_tool = ToolDefinition(
    "upload_file",
    "Upload a local file to NAS.",
    RiskLevel.WRITE,
    upload_file,
    requires_confirmation=True,
    adapter_capability="upload_file",
)
download_file_tool = ToolDefinition(
    "download_file",
    "Download a NAS file.",
    RiskLevel.READ,
    download_file,
    adapter_capability="download_file",
)
delete_file_tool = ToolDefinition(
    "delete_file",
    "Delete a NAS file.",
    RiskLevel.DESTRUCTIVE,
    delete_file,
    requires_confirmation=True,
    adapter_capability="delete_file",
)
