from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from nasagent.agent.state.models import AgentState
from nasagent.config.settings import SafetySettings
from nasagent.llm.base import LlmProvider
from nasagent.nas.base import NasAdapter
from nasagent.safety.approvals import ApprovalProvider


class AgentStreamCallback(Protocol):
    def on_plan_start(self) -> None: ...
    def on_plan_ready(self, step_count: int) -> None: ...
    def on_step_start(self, step_id: str, description: str) -> None: ...
    def on_tool_start(self, tool_name: str) -> None: ...
    def on_tool_done(self, tool_name: str) -> None: ...
    def on_summary(self, summary: str) -> None: ...
    def on_error(self, error: str) -> None: ...
    def on_stream_chunk(self, chunk: str) -> None: ...


@dataclass
class LogStreamCallback:
    events: list[str] = field(default_factory=list)

    def on_plan_start(self) -> None:
        self.events.append("plan_start")

    def on_plan_ready(self, step_count: int) -> None:
        self.events.append(f"plan_ready:{step_count}")

    def on_step_start(self, step_id: str, description: str) -> None:
        self.events.append(f"step_start:{step_id}:{description}")

    def on_tool_start(self, tool_name: str) -> None:
        self.events.append(f"tool_start:{tool_name}")

    def on_tool_done(self, tool_name: str) -> None:
        self.events.append(f"tool_done:{tool_name}")

    def on_summary(self, summary: str) -> None:
        self.events.append(f"summary:{summary[:100]}")

    def on_error(self, error: str) -> None:
        self.events.append(f"error:{error}")

    def on_stream_chunk(self, chunk: str) -> None:
        self.events.append(f"chunk:{chunk}")


async def run_agent_with_callback(
    goal: str,
    adapter: NasAdapter,
    provider: LlmProvider,
    safety_settings: SafetySettings | None = None,
    run_log_dir: Path | None = None,
    approval_provider: ApprovalProvider | None = None,
    stream: AgentStreamCallback | None = None,
) -> AgentState:
    from uuid import uuid4

    from nasagent.agent.graph.builder import build_agent_graph
    from nasagent.agent.state.models import AgentState as AS
    from nasagent.agent.state.store import RunStateStore
    from nasagent.config.settings import NasAgentSettings

    cb = stream or LogStreamCallback()
    cb.on_plan_start()

    graph = build_agent_graph(
        adapter=adapter,
        provider=provider,
        safety_settings=safety_settings,
        approval_provider=approval_provider,
    )

    raw_state = await graph.ainvoke({"goal": goal})

    plan = raw_state.get("plan")
    if plan is not None:
        cb.on_plan_ready(len(plan.steps))
        for step in plan.steps:
            cb.on_step_start(step.id, step.description)

    step_results = raw_state.get("step_results", [])
    for step_result in step_results:
        for tool_result in step_result.tool_results:
            cb.on_tool_done(tool_result.tool_name)

    state = AS(
        goal=raw_state["goal"],
        plan=plan,
        step_results=step_results,
        final_summary=raw_state.get("final_summary", ""),
    )

    cb.on_summary(state.final_summary)

    directory = run_log_dir or NasAgentSettings().observability.expanded_run_log_dir()
    RunStateStore(directory).save(str(uuid4()), state)
    return state
