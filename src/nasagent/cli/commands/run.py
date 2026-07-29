import asyncio
import json

import typer
from rich.console import Console

from nasagent.agent.graph.builder import run_agent_once
from nasagent.cli.rendering.panels import result_panel
from nasagent.llm.base import LlmProvider
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


def run_task(task: str, profile: str = typer.Option("simulator", "--profile")) -> None:
    if profile != "simulator":
        raise typer.BadParameter(
            "Only simulator profile is available before real UGREEN API details are configured"
        )
    state = asyncio.run(
        run_agent_once(task, adapter=SimulatorNasAdapter(), provider=OfflinePlannerProvider(task))
    )
    Console().print(result_panel(f"Goal: {state.goal}\n{state.final_summary}"))
