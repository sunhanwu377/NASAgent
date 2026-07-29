import subprocess
from pathlib import PurePosixPath, PureWindowsPath
from typing import Literal

ComposeAction = Literal["config", "up", "down"]


def compose_command_args(action: ComposeAction, *, compose_file: str) -> list[str]:
    posix_path = PurePosixPath(compose_file)
    windows_path = PureWindowsPath(compose_file)
    if (
        posix_path.is_absolute()
        or windows_path.is_absolute()
        or ".." in posix_path.parts
        or ".." in windows_path.parts
    ):
        raise ValueError("compose file path must be relative and must not contain '..'")
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
