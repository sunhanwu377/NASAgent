from nasagent.agent.planning.prompts import PLANNER_SYSTEM_PROMPT
from nasagent.agent.planning.schemas import Plan
from nasagent.llm.base import LlmProvider
from nasagent.llm.messages import ChatMessage


class Planner:
    def __init__(self, provider: LlmProvider) -> None:
        self._provider = provider

    async def create_plan(self, goal: str) -> Plan:
        content = await self._provider.complete(
            [
                ChatMessage(role="system", content=PLANNER_SYSTEM_PROMPT),
                ChatMessage(role="user", content=goal),
            ]
        )
        return Plan.model_validate_json(content)
