from nasagent.safety.risk import RiskLevel
from nasagent.tools.base import ToolContext, ToolDefinition


async def get_storage_status(context: ToolContext) -> dict[str, int]:
    status = await context.adapter.get_storage_status()
    return status.model_dump()


get_storage_status_tool = ToolDefinition(
    name="get_storage_status",
    description="Get NAS storage capacity and usage.",
    risk_level=RiskLevel.READ,
    handler=get_storage_status,
    adapter_capability="get_storage_status",
)
