import pytest

from nasagent.nas.adapters.simulator.adapter import SimulatorNasAdapter
from nasagent.tools.base import ToolContext
from nasagent.tools.nas.storage import get_storage_status_tool


@pytest.mark.asyncio
async def test_storage_tool_uses_adapter() -> None:
    context = ToolContext(adapter=SimulatorNasAdapter())
    result = await get_storage_status_tool.handler(context)

    assert result["free_bytes"] == 2_900_000_000_000
