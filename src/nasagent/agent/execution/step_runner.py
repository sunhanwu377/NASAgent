from nasagent.agent.planning.schemas import PlanStep
from nasagent.agent.state.models import StepResult
from nasagent.safety.policy import SafetyPolicy
from nasagent.tools.base import ToolContext
from nasagent.tools.registry import ToolRegistry
from nasagent.tools.schemas import ToolCallResult


class StepRunner:
    def __init__(self, registry: ToolRegistry, safety_policy: SafetyPolicy) -> None:
        self._registry = registry
        self._safety_policy = safety_policy

    async def run_step(self, step: PlanStep, context: ToolContext) -> StepResult:
        tool_results: list[ToolCallResult] = []
        for tool_name in step.expected_tools:
            tool = self._registry.get(tool_name)
            decision = self._safety_policy.evaluate(tool)
            if not decision.allowed:
                return StepResult(step_id=step.id, success=False, error=decision.reason)
            result = await tool.handler(context)
            tool_results.append(ToolCallResult(tool_name=tool.name, result=result))
        return StepResult(step_id=step.id, success=True, tool_results=tool_results)
