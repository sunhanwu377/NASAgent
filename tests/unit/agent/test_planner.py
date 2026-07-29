import pytest

from nasagent.agent.planning.planner import Planner
from nasagent.agent.planning.schemas import Plan
from nasagent.llm.base import LlmProvider


class FakeProvider(LlmProvider):
    def __init__(self) -> None:
        self.messages = []

    async def complete(self, messages):  # type: ignore[no-untyped-def]
        self.messages = messages
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


@pytest.mark.asyncio
async def test_planner_prompt_includes_exact_schema_and_available_tools() -> None:
    provider = FakeProvider()
    planner = Planner(provider=provider)

    await planner.create_plan("check storage")

    system_prompt = provider.messages[0].content
    assert '"goal"' in system_prompt
    assert '"steps"' in system_prompt
    assert "get_storage_status" in system_prompt
    assert "Do not invent NAS device state" in system_prompt
