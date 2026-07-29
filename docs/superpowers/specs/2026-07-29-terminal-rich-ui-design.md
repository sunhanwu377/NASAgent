# Terminal Rich UI Design

## Goal

Improve the interactive terminal experience for `nasagent chat` and `nasagent run` so users can quickly distinguish their input, agent responses, system progress, tool activity, and errors. The UI should reduce perceived waiting time during LLM planning and tool execution without changing core agent behavior.

## Scope

This design focuses on interactive Rich output only.

In scope:

- A centralized `CliRenderer` for interactive terminal output.
- Clear role labels for user input, agent output, system status, tool status, success, and error states.
- Spinner/status feedback while waiting for conversational LLM responses, task planning, and task execution.
- Stable completion lines after spinners finish.
- A structured task result panel for `chat` task execution and `run`.
- A structured TOML config error panel for existing malformed-config handling.
- Tests that preserve existing key output expectations such as `Executed tools: get_storage_status`.

Out of scope for this pass:

- `--plain`, `--json`, `--quiet`, or `--verbose` modes.
- A full Rich `Live` dashboard.
- Agent graph event streaming.
- Broader exception swallowing for LLM or tool failures beyond the existing TOML decode paths.
- Real NAS profile UX beyond the current simulator-only commands.

## UX Rules

The terminal output uses stable role labels:

- `you      >` for user input prompts, styled cyan.
- `agent    >` for natural-language assistant output, styled green.
- `system   .` for planning, waiting, and general progress, styled dim/cyan.
- `tool     .` for tool execution, styled magenta.
- `error    !` for errors, styled red.

Interactive symbols can use Rich styling, but the text content should remain readable in captured test output. The implementation should prefer simple labels and ASCII-compatible separators over decorative output that makes logs hard to read.

## Chat UX

Startup:

```text
╭─ NASAgent ─────────────────────────────╮
│ <provider> · simulator · streaming on   │
╰────────────────────────────────────────╯

Type exit or quit to leave.
```

Plain conversation:

```text
you      > RAID 是什么？
agent    > RAID 是一种将多块硬盘组合成一个逻辑存储单元的技术...
```

Task execution:

```text
you      > 查看存储状态
system   . planning task
system   . plan ready · 1 step
tool     . get_storage_status
tool     . get_storage_status completed
agent    > Executed tools: get_storage_status
```

Behavior requirements:

- Normal conversation should stream through the existing LLM streaming path.
- Before the first streamed token, show a spinner/status for waiting on the LLM.
- The spinner must resolve to normal output and leave stable text in the terminal transcript.
- Task planning remains non-streaming JSON planner execution.
- Task execution should show a progress status before blocking on planning/execution.
- Once execution completes, show stable plan/tool/done lines and a result panel.

## Run UX

`nasagent run "check storage"` should use the same renderer but without an input prompt:

```text
system   . planning task
system   . plan ready · 1 step
tool     . get_storage_status

╭─ Task Complete ────────────────────────╮
│ Goal   check storage                    │
│ Tools  get_storage_status               │
│                                      │
│ Executed tools: get_storage_status      │
╰────────────────────────────────────────╯
```

The `run` command should continue to print the final summary text so existing users and tests can find `Executed tools: ...`.

## Error UX

Malformed TOML config should be rendered as a structured Rich panel instead of raw text:

```text
╭─ Config Error ─────────────────────────╮
│ Invalid TOML config                     │
│ File: ~/.config/nasagent/config.toml    │
│ Hint: run `nasagent config show`         │
╰────────────────────────────────────────╯
```

The command should still exit non-zero and should not print a traceback. The implementation should keep using the current `tomllib.TOMLDecodeError` catch points in `chat` and `run`.

## Code Structure

Add `src/nasagent/cli/rendering/renderer.py` with a focused `CliRenderer` class. Existing `src/nasagent/cli/rendering/panels.py` should contain reusable Rich components only.

Proposed renderer API:

```python
class CliRenderer:
    def __init__(self, console: Console | None = None) -> None: ...
    def banner(self, *, profile: str, provider: str | None, streaming: bool) -> None: ...
    def prompt(self) -> None: ...
    def agent_start(self) -> None: ...
    def agent_chunk(self, chunk: str) -> None: ...
    def agent_end(self) -> None: ...
    def status(self, message: str) -> None: ...
    def success(self, message: str) -> None: ...
    def tool(self, name: str, *, completed: bool = False) -> None: ...
    def task_result(self, state: AgentState) -> None: ...
    def config_error(self, path: Path, error: tomllib.TOMLDecodeError) -> None: ...
    def spinner(self, label: str, message: str) -> ContextManager[None]: ...
```

`chat.py` responsibilities after refactor:

- Validate profile.
- Read user input.
- Route greeting, conversation, or task execution.
- Call renderer methods for output.
- Keep LLM streaming and task execution logic intact.

`run.py` responsibilities after refactor:

- Validate profile.
- Execute simulator task.
- Call renderer for progress, result, and config errors.

## Spinner Behavior

Use Rich `Console.status()` for blocking phases:

- Conversation: `waiting for LLM` before streamed chunks begin.
- Task execution: `planning and running task` around the current synchronous `execute_simulator_task()` call.

After a spinner completes, output stable lines:

- `system   . plan ready · N step(s)` when a plan exists.
- `tool     . <tool_name> completed` for each executed tool result.
- `system   . done` before the final result panel.

This avoids terminal transcripts that only show transient spinner frames.

## Testing

Update integration tests to assert stable textual output rather than exact box drawing:

- `chat` startup contains `NASAgent`.
- Conversation output contains `agent` and the fake streamed response.
- Task execution output contains `system`, `tool`, `Task Complete`, and `Executed tools: get_storage_status`.
- `run` output contains `Task Complete` and `Executed tools: get_storage_status`.
- Malformed TOML output contains `Config Error`, the config path, and no `Traceback`.

Keep existing unit tests for LLM streaming. Add renderer unit tests only if integration tests become too broad; otherwise prefer integration coverage because Rich output is mostly user-facing behavior.

## Success Criteria

- Users can visually distinguish input, agent output, system progress, tool activity, and errors.
- Long waits during LLM conversation and task execution show a spinner or status line.
- Spinner phases leave stable final transcript lines.
- Existing chat conversation streaming still works.
- Existing planner JSON path is not streamed.
- Existing task summaries remain discoverable in output.
- `uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy src`, and `uv run pytest` pass.
