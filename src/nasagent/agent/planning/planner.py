from nasagent.agent.planning.prompts import build_planner_system_prompt
from nasagent.agent.planning.schemas import Plan
from nasagent.llm.base import LlmProvider
from nasagent.llm.messages import ChatMessage


class Planner:
    def __init__(self, provider: LlmProvider, tool_names: tuple[str, ...] | None = None) -> None:
        self._provider = provider
        self._tool_names = tool_names

    async def create_plan(self, goal: str) -> Plan:
        system_prompt = (
            build_planner_system_prompt(self._tool_names)
            if self._tool_names is not None
            else build_planner_system_prompt()
        )
        content = await self._provider.complete(
            [
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=goal),
            ]
        )
        return Plan.model_validate_json(content)
