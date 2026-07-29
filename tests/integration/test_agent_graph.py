import pytest

from nasagent.agent.graph.builder import run_agent_once
from nasagent.llm.base import LlmProvider
from nasagent.nas.adapters.simulator.adapter import SimulatorNasAdapter


class FakeProvider(LlmProvider):
    async def complete(self, messages):  # type: ignore[no-untyped-def]
        return (
            '{"goal":"check storage","steps":[{"id":"s1","description":"Get storage",'
            '"risk":"read","expected_tools":["get_storage_status"]}]}'
        )


@pytest.mark.asyncio
async def test_agent_runs_plan_against_simulator() -> None:
    state = await run_agent_once(
        "check storage",
        adapter=SimulatorNasAdapter(),
        provider=FakeProvider(),
    )

    assert state.goal == "check storage"
    assert state.step_results[0].success is True
    assert "get_storage_status" in state.final_summary
