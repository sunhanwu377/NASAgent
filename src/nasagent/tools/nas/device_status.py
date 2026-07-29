from nasagent.safety.risk import RiskLevel
from nasagent.tools.base import ToolContext, ToolDefinition


async def get_device_status(context: ToolContext) -> dict[str, object]:
    status = await context.adapter.get_device_status()
    return status.model_dump()


get_device_status_tool = ToolDefinition(
    name="get_device_status",
    description="Get NAS device status.",
    risk_level=RiskLevel.READ,
    handler=get_device_status,
    adapter_capability="get_device_status",
)
