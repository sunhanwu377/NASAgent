import asyncio
import json
import tomllib
from collections.abc import AsyncIterator, Callable

import typer

from nasagent.agent.runner import run_agent_with_callback
from nasagent.agent.state.models import AgentState
from nasagent.cli.rendering.renderer import CliRenderer
from nasagent.config.settings import (
    LlmSettings,
    NasAgentSettings,
    default_config_path,
    load_settings,
)
from nasagent.llm.base import LlmProvider
from nasagent.llm.messages import ChatMessage
from nasagent.llm.openai_provider import OpenAiProvider
from nasagent.nas.adapters.simulator.adapter import SimulatorNasAdapter


class OfflinePlannerProvider(LlmProvider):
    def __init__(self, task: str) -> None:
        self._task = task

    async def complete(self, messages: list[ChatMessage]) -> str:
        task = self._task.lower()
        steps: list[dict[str, object]] = []
        if "storage" in task or "存储" in task:
            steps.append(
                {
                    "id": "s1",
                    "description": "Get storage",
                    "risk": "read",
                    "expected_tools": ["get_storage_status"],
                }
            )
        elif "device" in task or "status" in task or "设备" in task or "状态" in task:
            steps.append(
                {
                    "id": "s1",
                    "description": "Get device status",
                    "risk": "read",
                    "expected_tools": ["get_device_status"],
                }
            )
        return json.dumps({"goal": self._task, "steps": steps})

    async def stream_complete(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        yield await self.complete(messages)


ProviderFactory = Callable[[LlmSettings], LlmProvider]


def default_online_provider_factory(settings: LlmSettings) -> LlmProvider:
    return OpenAiProvider(settings, json_object=True)


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
    active_settings = settings or load_settings()
    return asyncio.run(
        run_agent_with_callback(
            task,
            adapter=SimulatorNasAdapter(),
            provider=select_planner_provider(
                task, active_settings, online=online, provider_factory=provider_factory,
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
    renderer = CliRenderer()
    try:
        with renderer.spinner("system", "planning task"):
            state = execute_simulator_task(task, online=online)
    except tomllib.TOMLDecodeError as exc:
        config_path = default_config_path()
        renderer.config_error(config_path, exc)
        raise typer.Exit(1) from exc
    if state.plan is not None:
        renderer.success(f"plan ready · {len(state.plan.steps)} step(s)")
    for step_result in state.step_results:
        for tool_result in step_result.tool_results:
            renderer.tool(tool_result.tool_name, completed=True)
    renderer.task_result(state)
