import asyncio

import typer
from rich.console import Console

from nasagent.agent.graph.builder import run_agent_once
from nasagent.cli.rendering.panels import result_panel
from nasagent.llm.base import LlmProvider
from nasagent.nas.adapters.simulator.adapter import SimulatorNasAdapter


class OfflinePlannerProvider(LlmProvider):
    async def complete(self, messages):  # type: ignore[no-untyped-def]
        return (
            '{"goal":"check storage","steps":[{"id":"s1","description":"Get storage",'
            '"risk":"read","expected_tools":["get_storage_status"]}]}'
        )


def run_task(task: str, profile: str = typer.Option("simulator", "--profile")) -> None:
    if profile != "simulator":
        raise typer.BadParameter(
            "Only simulator profile is available before real UGREEN API details are configured"
        )
    state = asyncio.run(
        run_agent_once(task, adapter=SimulatorNasAdapter(), provider=OfflinePlannerProvider())
    )
    Console().print(result_panel(state.final_summary))
