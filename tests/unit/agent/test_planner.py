import pytest

from nasagent.agent.planning.planner import Planner
from nasagent.agent.planning.schemas import Plan
from nasagent.llm.base import LlmProvider


class FakeProvider(LlmProvider):
    async def complete(self, messages):  # type: ignore[no-untyped-def]
        return (
            '{"goal":"check storage","steps":[{"id":"s1","description":"Get storage",'
            '"risk":"read","expected_tools":["get_storage_status"]}]}'
        )


@pytest.mark.asyncio
async def test_planner_returns_structured_plan() -> None:
    planner = Planner(provider=FakeProvider())

    plan = await planner.create_plan("check storage")

    assert isinstance(plan, Plan)
    assert plan.steps[0].expected_tools == ["get_storage_status"]
