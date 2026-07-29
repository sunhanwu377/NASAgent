from nasagent.agent.execution.react import MAX_REACT_ITERATIONS, ReActIteration, ReActTrace
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
        react_trace = ReActTrace(max_iterations=MAX_REACT_ITERATIONS)
        if len(step.expected_tools) > MAX_REACT_ITERATIONS:
            return StepResult(
                step_id=step.id,
                success=False,
                error=(
                    f"step expected {len(step.expected_tools)} tools, "
                    f"exceeds maximum ReAct iterations of {MAX_REACT_ITERATIONS}"
                ),
                react_trace=react_trace,
            )

        for tool_name in step.expected_tools:
            tool = self._registry.get(tool_name)
            decision = self._safety_policy.evaluate(tool)
            if not decision.allowed:
                return StepResult(
                    step_id=step.id,
                    success=False,
                    error=decision.reason,
                    react_trace=react_trace,
                )
            if decision.requires_confirmation:
                return StepResult(
                    step_id=step.id,
                    success=False,
                    error=f"confirmation required for tool: {tool.name}",
                    react_trace=react_trace,
                )
            tool_args = step.tool_args.get(tool_name, {})
            result = await tool.handler(context, **tool_args)
            tool_results.append(ToolCallResult(tool_name=tool.name, result=result))
            react_trace.iterations.append(
                ReActIteration(
                    thought=f"Execute planned tool {tool.name}",
                    action=tool.name,
                    observation=result,
                )
            )
        return StepResult(
            step_id=step.id,
            success=True,
            tool_results=tool_results,
            react_trace=react_trace,
        )
