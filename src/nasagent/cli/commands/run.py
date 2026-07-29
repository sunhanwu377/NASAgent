import asyncio
import json
from collections.abc import Callable

import typer
from rich.console import Console

from nasagent.agent.graph.builder import run_agent_once
from nasagent.agent.state.models import AgentState
from nasagent.cli.rendering.panels import result_panel
from nasagent.config.settings import LlmSettings, NasAgentSettings
from nasagent.llm.base import LlmProvider
from nasagent.llm.openai_provider import OpenAiProvider
from nasagent.nas.adapters.simulator.adapter import SimulatorNasAdapter


class OfflinePlannerProvider(LlmProvider):
    def __init__(self, task: str) -> None:
        self._task = task

    async def complete(self, messages):  # type: ignore[no-untyped-def]
        task = self._task.lower()
        steps: list[dict[str, object]] = []
        if "storage" in task:
            steps.append(
                {
                    "id": "s1",
                    "description": "Get storage",
                    "risk": "read",
                    "expected_tools": ["get_storage_status"],
                }
            )
        elif "device" in task or "status" in task:
            steps.append(
                {
                    "id": "s1",
                    "description": "Get device status",
                    "risk": "read",
                    "expected_tools": ["get_device_status"],
                }
            )
        return json.dumps({"goal": self._task, "steps": steps})


ProviderFactory = Callable[[LlmSettings], LlmProvider]


def default_online_provider_factory(settings: LlmSettings) -> LlmProvider:
    return OpenAiProvider(settings)


def select_planner_provider(
    task: str,
    settings: NasAgentSettings,
    *,
    online: bool | None,
    provider_factory: ProviderFactory = default_online_provider_factory,
) -> LlmProvider:
    use_online = online if online is not None else settings.llm.api_key is not None
    if use_online:
        return provider_factory(settings.llm)
    return OfflinePlannerProvider(task)


def execute_simulator_task(
    task: str,
    settings: NasAgentSettings | None = None,
    *,
    online: bool | None = None,
    provider_factory: ProviderFactory = default_online_provider_factory,
) -> AgentState:
    active_settings = settings or NasAgentSettings()
    return asyncio.run(
        run_agent_once(
            task,
            adapter=SimulatorNasAdapter(),
            provider=select_planner_provider(
                task,
                active_settings,
                online=online,
                provider_factory=provider_factory,
            ),
            safety_settings=active_settings.safety,
            run_log_dir=active_settings.observability.expanded_run_log_dir(),
        )
    )


def run_task(
    task: str,
    profile: str = typer.Option("simulator", "--profile"),
    online: bool | None = typer.Option(
        None,
        "--online/--offline",
        help="Use configured OpenAI-compatible LLM or force deterministic offline planner.",
    ),
) -> None:
    if profile != "simulator":
        raise typer.BadParameter(
            "Only simulator profile is available before real UGREEN API details are configured"
        )
    state = execute_simulator_task(task, online=online)
    Console().print(result_panel(f"Goal: {state.goal}\n{state.final_summary}"))
