# Terminal Rich UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an interactive Rich terminal UI for `nasagent chat` and `nasagent run` that clearly distinguishes user input, agent output, system progress, tool activity, task results, and TOML config errors.

**Architecture:** Add a focused `CliRenderer` in `src/nasagent/cli/rendering/renderer.py` and keep reusable Rich panels in `src/nasagent/cli/rendering/panels.py`. Refactor `chat.py` and `run.py` to delegate terminal presentation to the renderer while keeping routing, streaming, planner JSON, and simulator execution behavior unchanged.

**Tech Stack:** Python 3.11+, Typer, Rich, pytest, mypy, ruff, existing OpenAI-compatible LLM streaming path.

## Global Constraints

- Focus on interactive Rich output only.
- Do not implement `--plain`, `--json`, `--quiet`, or `--verbose` modes in this pass.
- Do not implement a full Rich `Live` dashboard.
- Do not stream planner JSON or change agent graph event flow.
- Do not broaden exception swallowing for LLM or tool failures beyond existing `tomllib.TOMLDecodeError` paths.
- Preserve existing discoverable summary text such as `Executed tools: get_storage_status`.
- Use stable labels: `you      >`, `agent    >`, `system   .`, `tool     .`, and `error    !`.
- Show spinner/status feedback for conversational LLM waits and task execution waits.
- Spinner phases must leave stable final transcript lines.
- Keep `chat` and `run` simulator-only behavior unchanged.
- No git commits unless explicitly requested by the user.

---

## File Structure

- Create `src/nasagent/cli/rendering/renderer.py`: owns `CliRenderer`, labels, spinner wrapper, and high-level output methods.
- Modify `src/nasagent/cli/rendering/panels.py`: keep reusable components only: banner panel, task result panel, config error panel.
- Modify `src/nasagent/cli/commands/chat.py`: replace direct Rich rendering with `CliRenderer`; preserve conversation/task routing and streaming.
- Modify `src/nasagent/cli/commands/run.py`: replace direct result panel/error text with `CliRenderer` progress/result/error methods.
- Modify `tests/integration/test_cli.py`: assert stable text output for chat/run role labels, task result panel title, tool lines, and config error panel.

---

### Task 1: Renderer Components

**Files:**
- Create: `src/nasagent/cli/rendering/renderer.py`
- Modify: `src/nasagent/cli/rendering/panels.py`
- Test: `tests/integration/test_cli.py`

**Interfaces:**
- Consumes: `rich.console.Console`, `rich.panel.Panel`, `rich.text.Text`, `nasagent.agent.state.models.AgentState`, `tomllib.TOMLDecodeError`, `pathlib.Path`.
- Produces:
  - `banner_panel(profile: str, provider: str | None, streaming: bool) -> Panel`
  - `task_result_panel(state: AgentState) -> Panel`
  - `config_error_panel(path: Path, error: tomllib.TOMLDecodeError) -> Panel`
  - `class CliRenderer`
  - `CliRenderer(console: Console | None = None) -> None`
  - `CliRenderer.banner(profile: str, provider: str | None, streaming: bool) -> None`
  - `CliRenderer.prompt() -> None`
  - `CliRenderer.agent_start() -> None`
  - `CliRenderer.agent_chunk(chunk: str) -> None`
  - `CliRenderer.agent_end() -> None`
  - `CliRenderer.status(message: str) -> None`
  - `CliRenderer.success(message: str) -> None`
  - `CliRenderer.tool(name: str, *, completed: bool = False) -> None`
  - `CliRenderer.task_result(state: AgentState) -> None`
  - `CliRenderer.config_error(path: Path, error: tomllib.TOMLDecodeError) -> None`
  - `CliRenderer.spinner(label: str, message: str) -> ContextManager[None]`

- [ ] **Step 1: Replace `panels.py` with reusable panel components**

Write this implementation in `src/nasagent/cli/rendering/panels.py`:

```python
import tomllib
from pathlib import Path

from rich.console import Group
from rich.panel import Panel
from rich.text import Text

from nasagent.agent.state.models import AgentState


def banner_panel(profile: str, provider: str | None, streaming: bool) -> Panel:
    provider_label = provider or "offline"
    streaming_label = "streaming on" if streaming else "streaming off"
    return Panel(
        Text("NASAgent", style="bold cyan")
        + Text(f"  {provider_label} · {profile} · {streaming_label}", style="dim"),
        border_style="cyan",
        padding=(0, 1),
    )


def task_result_panel(state: AgentState) -> Panel:
    tool_names = [
        tool_result.tool_name
        for step_result in state.step_results
        for tool_result in step_result.tool_results
    ]
    tools = ", ".join(tool_names) if tool_names else "none"
    return Panel(
        Group(
            Text("Goal   ", style="bold cyan") + Text(state.goal),
            Text("Tools  ", style="bold magenta") + Text(tools),
            Text(""),
            Text(state.final_summary),
        ),
        title="Task Complete",
        border_style="green",
        padding=(0, 1),
    )


def config_error_panel(path: Path, error: tomllib.TOMLDecodeError) -> Panel:
    return Panel(
        Group(
            Text("Invalid TOML config", style="bold red"),
            Text(f"File: {path}"),
            Text(f"Error: {error}"),
            Text("Hint: run `nasagent config show`"),
        ),
        title="Config Error",
        border_style="red",
        padding=(0, 1),
    )
```

- [ ] **Step 2: Add `CliRenderer`**

Create `src/nasagent/cli/rendering/renderer.py`:

```python
import tomllib
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from rich.console import Console
from rich.status import Status
from rich.text import Text

from nasagent.agent.state.models import AgentState
from nasagent.cli.rendering.panels import (
    banner_panel,
    config_error_panel,
    task_result_panel,
)


class CliRenderer:
    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def banner(self, *, profile: str, provider: str | None, streaming: bool) -> None:
        self.console.print(banner_panel(profile, provider, streaming))
        self.console.print("Type exit or quit to leave.", style="dim")

    def prompt(self) -> None:
        self.console.print(_label("you", ">", "bold cyan"), end="")

    def agent_start(self) -> None:
        self.console.print(_label("agent", ">", "bold green"), end="")

    def agent_chunk(self, chunk: str) -> None:
        self.console.print(chunk, end="")

    def agent_end(self) -> None:
        self.console.print()

    def status(self, message: str) -> None:
        self.console.print(_line("system", ".", message, "cyan"))

    def success(self, message: str) -> None:
        self.console.print(_line("system", ".", message, "green"))

    def tool(self, name: str, *, completed: bool = False) -> None:
        suffix = " completed" if completed else ""
        self.console.print(_line("tool", ".", f"{name}{suffix}", "magenta"))

    def task_result(self, state: AgentState) -> None:
        self.console.print(task_result_panel(state))

    def config_error(self, path: Path, error: tomllib.TOMLDecodeError) -> None:
        self.console.print(config_error_panel(path, error))

    @contextmanager
    def spinner(self, label: str, message: str) -> Iterator[None]:
        status = Status(_line(label, ".", message, "cyan"), console=self.console, spinner="dots")
        status.start()
        try:
            yield
        finally:
            status.stop()


def _label(name: str, separator: str, style: str) -> Text:
    return Text(f"{name:<8} ", style=style) + Text(f"{separator} ", style="dim")


def _line(name: str, separator: str, message: str, style: str) -> Text:
    return _label(name, separator, style) + Text(message, style="dim")
```

- [ ] **Step 3: Run targeted import/type checks**

Run: `uv run mypy src/nasagent/cli/rendering src/nasagent/cli/commands/chat.py src/nasagent/cli/commands/run.py`

Expected: success or only failures in command files not yet refactored. If imports fail, fix before proceeding.

- [ ] **Step 4: Run formatting/lint for renderer files**

Run: `uv run ruff check src/nasagent/cli/rendering/panels.py src/nasagent/cli/rendering/renderer.py`

Expected: `All checks passed!`

---

### Task 2: Wire Renderer Into Chat And Run

**Files:**
- Modify: `src/nasagent/cli/commands/chat.py`
- Modify: `src/nasagent/cli/commands/run.py`
- Modify: `tests/integration/test_cli.py`

**Interfaces:**
- Consumes Task 1 `CliRenderer` and panel functions.
- Produces user-facing Rich UI in `nasagent chat` and `nasagent run`.

- [ ] **Step 1: Update chat integration tests first**

Modify `tests/integration/test_cli.py` expectations:

```python
def test_chat_command_runs_until_exit(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(settings_module, "DEFAULT_CONFIG_PATH", tmp_path / "missing.toml")
    runner = CliRunner()

    result = runner.invoke(app, ["chat", "--profile", "simulator"], input="check storage\nexit\n")

    assert result.exit_code == 0
    assert "NASAgent" in result.output
    assert "system" in result.output
    assert "tool" in result.output
    assert "Task Complete" in result.output
    assert "Executed tools: get_storage_status" in result.output
    assert "Goodbye" in result.output
```

Modify conversation test to assert the agent label:

```python
assert "agent" in result.output
assert "RAID is a storage technology." in result.output
assert "Executed tools" not in result.output
```

Modify malformed TOML tests for `chat` and `run`:

```python
assert "Config Error" in result.output
assert "Invalid TOML config" in result.output
assert str(config_path) in result.output
assert "Traceback" not in result.output
```

Modify run tests to assert:

```python
assert "Task Complete" in result.output
assert "Executed tools: get_storage_status" in result.output
```

- [ ] **Step 2: Run tests to verify they fail before wiring**

Run: `uv run pytest tests/integration/test_cli.py -v`

Expected: failures showing missing `Config Error` and/or final renderer output before implementation.

- [ ] **Step 3: Refactor `chat.py` to use `CliRenderer`**

Update imports in `src/nasagent/cli/commands/chat.py`:

```python
from nasagent.cli.rendering.renderer import CliRenderer
```

Remove imports from `nasagent.cli.rendering.panels` in `chat.py`.

In `chat()`, replace `console = Console()` with:

```python
renderer = CliRenderer()
settings_provider = None
try:
    settings_provider = load_settings().llm.provider
except tomllib.TOMLDecodeError:
    settings_provider = None
renderer.banner(profile=profile, provider=settings_provider, streaming=stream)
```

Use `renderer.prompt()` instead of direct prompt printing:

```python
renderer.prompt()
```

For `exit`/`quit`, print:

```python
renderer.status("Goodbye")
```

For local greeting:

```python
renderer.agent_start()
renderer.agent_chunk(response)
renderer.agent_end()
```

For TOML decode errors, replace raw `typer.echo(...)` with:

```python
renderer.config_error(default_config_path(), exc)
raise typer.Exit(1) from exc
```

For task execution, wrap the blocking call:

```python
try:
    with renderer.spinner("system", "planning and running task"):
        state = execute_simulator_task(task, online=online)
except tomllib.TOMLDecodeError as exc:
    renderer.config_error(default_config_path(), exc)
    raise typer.Exit(1) from exc
if state.plan is not None:
    renderer.success(f"plan ready · {len(state.plan.steps)} step(s)")
for step_result in state.step_results:
    for tool_result in step_result.tool_results:
        renderer.tool(tool_result.tool_name, completed=True)
renderer.success("done")
renderer.task_result(state)
```

Update `_print_conversation_response()` to accept `renderer: CliRenderer` instead of `console: Console`:

```python
def _print_conversation_response(
    task: str, *, online: bool | None, stream: bool, renderer: CliRenderer
) -> None:
```

Use `renderer.agent_start()`, `renderer.agent_chunk()`, and `renderer.agent_end()` for both streaming and non-streaming paths. For the offline no-LLM message, render through agent methods.

Update `_stream_conversation_response()`:

```python
async def _stream_conversation_response(
    provider: OpenAiProvider, messages: list[ChatMessage], renderer: CliRenderer
) -> None:
    async for chunk in provider.stream_complete(messages):
        renderer.agent_chunk(chunk)
    renderer.agent_end()
```

- [ ] **Step 4: Refactor `run.py` to use `CliRenderer`**

Update imports:

```python
from nasagent.cli.rendering.renderer import CliRenderer
```

Remove `task_result_panel`/`result_panel` direct imports.

In `run_task()`:

```python
renderer = CliRenderer()
try:
    with renderer.spinner("system", "planning task"):
        state = execute_simulator_task(task, online=online)
except tomllib.TOMLDecodeError as exc:
    renderer.config_error(default_config_path(), exc)
    raise typer.Exit(1) from exc
if state.plan is not None:
    renderer.success(f"plan ready · {len(state.plan.steps)} step(s)")
for step_result in state.step_results:
    for tool_result in step_result.tool_results:
        renderer.tool(tool_result.tool_name, completed=True)
renderer.task_result(state)
```

- [ ] **Step 5: Run integration tests**

Run: `uv run pytest tests/integration/test_cli.py -v`

Expected: all tests pass.

- [ ] **Step 6: Run focused static checks**

Run: `uv run ruff check src/nasagent/cli/commands/chat.py src/nasagent/cli/commands/run.py src/nasagent/cli/rendering tests/integration/test_cli.py`

Expected: `All checks passed!`

Run: `uv run mypy src`

Expected: `Success: no issues found in 74 source files`

---

### Task 3: End-To-End Verification And Polish

**Files:**
- Modify only if verification exposes formatting or output issues:
  - `src/nasagent/cli/rendering/renderer.py`
  - `src/nasagent/cli/rendering/panels.py`
  - `src/nasagent/cli/commands/chat.py`
  - `src/nasagent/cli/commands/run.py`
  - `tests/integration/test_cli.py`

**Interfaces:**
- Consumes Task 1 and Task 2 implementation.
- Produces verified interactive Rich UI.

- [ ] **Step 1: Run real chat conversation smoke test**

Run: `printf '解释一下 RAID 是什么，简短回答\nexit\n' | uv run nasagent chat --profile simulator`

Expected output includes:

```text
NASAgent
you
agent
Goodbye
```

It should not include `Executed tools` for this conversation input.

- [ ] **Step 2: Run real task execution smoke test**

Run: `printf '查看存储状态\nexit\n' | uv run nasagent chat --profile simulator`

Expected output includes:

```text
NASAgent
system
tool
Task Complete
Executed tools: get_storage_status
```

- [ ] **Step 3: Run one-shot run smoke test**

Run: `uv run nasagent run "check storage" --profile simulator`

Expected output includes:

```text
Task Complete
get_storage_status
Executed tools: get_storage_status
```

- [ ] **Step 4: Run full verification**

Run: `uv run ruff format --check .`

Expected: all files formatted.

Run: `uv run ruff check .`

Expected: `All checks passed!`

Run: `uv run mypy src`

Expected: `Success: no issues found in 74 source files`

Run: `uv run pytest`

Expected: full suite passes.

- [ ] **Step 5: Summarize changed behavior**

Report:

- `chat` now shows `you`, `agent`, `system`, and `tool` roles distinctly.
- Conversation responses stream through `agent` output.
- Task waits use Rich spinner/status and leave stable transcript lines.
- `run` uses the same task result panel.
- TOML errors render as `Config Error` panels.
- Verification command outputs.

---

## Plan Self-Review

Spec coverage:

- Centralized `CliRenderer`: Task 1.
- Role labels: Task 1 renderer API and Task 2 tests.
- Spinner/status feedback: Task 1 `spinner()` and Task 2 wrapping task execution.
- Stable completion lines: Task 2 success/tool/done lines.
- Task result panel: Task 1 panel and Task 2 command wiring.
- TOML config error panel: Task 1 panel and Task 2 command wiring/tests.
- Existing output preservation: Task 2/3 tests assert `Executed tools: get_storage_status`.
- No `--plain/--json/quiet/verbose`: Global Constraints and no tasks add these flags.
- Planner JSON remains non-streamed: Global Constraints; no task changes planner flow.

Placeholder scan: no TBD/TODO placeholders are present. All steps name exact files, commands, and expected outputs.

Type consistency: `CliRenderer` method names and panel function names are consistent across Task 1 and Task 2.
