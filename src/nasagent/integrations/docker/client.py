import subprocess
from typing import Literal

ComposeAction = Literal["config", "up", "down"]


def compose_command_args(action: ComposeAction, *, compose_file: str) -> list[str]:
    if action == "config":
        return ["docker", "compose", "-f", compose_file, "config"]
    if action == "up":
        return ["docker", "compose", "-f", compose_file, "up", "-d"]
    return ["docker", "compose", "-f", compose_file, "down"]


def run_compose(action: ComposeAction, *, compose_file: str) -> str:
    result = subprocess.run(
        compose_command_args(action, compose_file=compose_file),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"docker compose {action} failed with exit code {result.returncode}: "
            f"{result.stderr.strip()}"
        )
    return result.stdout
