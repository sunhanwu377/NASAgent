import typer
from rich.console import Console

from nasagent.cli.commands.run import execute_simulator_task


def chat(
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
    console = Console()
    console.print("NASAgent chat. Type exit or quit to leave.")
    while True:
        typer.echo("nasagent> ", nl=False)
        try:
            task = input()
        except EOFError:
            break
        task = task.strip()
        if task.lower() in {"exit", "quit"}:
            console.print("Goodbye")
            break
        if not task:
            continue
        state = execute_simulator_task(task, online=online)
        console.print(f"Goal: {state.goal}\n{state.final_summary}")
