import pytest

from nasagent.agent.execution.step_runner import StepRunner
from nasagent.agent.planning.schemas import PlanStep
from nasagent.config.settings import SafetySettings
from nasagent.nas.adapters.simulator.adapter import SimulatorNasAdapter
from nasagent.safety.policy import SafetyPolicy
from nasagent.tools.base import ToolContext
from nasagent.tools.nas.storage import get_storage_status_tool
from nasagent.tools.registry import ToolRegistry


@pytest.mark.asyncio
async def test_step_runner_executes_expected_read_tool() -> None:
    registry = ToolRegistry()
    registry.register(get_storage_status_tool)
    runner = StepRunner(registry=registry, safety_policy=SafetyPolicy(SafetySettings()))
    step = PlanStep(
        id="s1",
        description="Get storage",
        risk="read",
        expected_tools=["get_storage_status"],
    )

    result = await runner.run_step(step, ToolContext(adapter=SimulatorNasAdapter()))

    assert result.step_id == "s1"
    assert result.success is True
    assert result.tool_results[0].tool_name == "get_storage_status"
