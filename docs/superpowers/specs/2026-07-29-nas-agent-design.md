# NAS Agent Design

Date: 2026-07-29

## Goal

Build a Python CLI AI agent that helps users operate NAS devices, with UGREEN NAS as the first real-device target. The first implementation phase should deliver a runnable, extensible framework with real UGREEN integration boundaries, simulator-backed development, OpenAI LLM support, planning-execution orchestration, ReAct execution inside each step, rich CLI output, tests, documentation, packaging structure, and GitHub/Gitea CI readiness.

This project is not a generic chatbot or code-generation agent. Its product value comes from safe, observable, NAS-specific operations against real devices.

## Confirmed Scope

- Use Python full stack with `uv` project management.
- Use OpenAI-compatible LLM APIs as the primary model provider.
- Use LangGraph for planning-execution orchestration.
- Use ReAct inside each planned step.
- Provide CLI-first usage with rich formatted output.
- Provide both `nasagent chat` and `nasagent run "<task>"`, with REPL/chat as the main experience.
- Make every core area package-first and easy to extend.
- Implement a UGREEN NAS adapter structure for real integration, but do not invent unknown private APIs.
- Support capture-derived UGREEN API completion later through clear client/auth/endpoint boundaries.
- Provide simulator adapter for CI, tests, demos, and local development without a real NAS.
- First NAS functions cover login/session boundaries, file listing, search, upload, download, delete, storage status, and device status.
- Use configurable safety policy: safe defaults with explicit options for automation.
- Provide architecture and code documentation.
- Prepare for later package installation with `uv`, `uv pip`, `pip`, and `pipx`.
- Prepare GitHub and Gitea CI/CD workflows and dual-remote push documentation.

## Non-Goals For Phase 1

- Do not build a web UI.
- Do not implement unsupported UGREEN endpoints without verified API details from documentation or packet capture.
- Do not run real UGREEN device tests in CI by default.
- Do not implement complex long-term memory beyond local run logs and summaries.
- Do not implement multi-agent frameworks such as CrewAI or AutoGen in phase 1.
- Do not publish to PyPI in phase 1, but keep packaging files ready.

## Recommended Architecture

Use LangGraph as the orchestration layer, modular NAS adapters as the device abstraction layer, and Rich/Typer as the CLI layer.

The architecture has three differentiating layers:

1. NAS Domain Layer: stable device and file-operation abstractions for authentication, files, storage, status, and later vendor-specific capabilities.
2. Safety and Execution Layer: hard checks around write, destructive, and system operations before any real adapter call.
3. Agent Orchestration Layer: planning first, then ReAct execution within each step, with structured state and observable tool calls.

Alternative approaches considered:

- Lightweight self-built OpenAI tool loop: simpler dependencies but more custom state, recovery, and observability work.
- Multi-agent framework such as CrewAI or AutoGen: useful for role collaboration but heavier than needed for a CLI NAS operator.

LangGraph is preferred because it directly models planning-execution workflows, supports stateful graphs, and leaves room for checkpoints and human-in-the-loop approval.

## Package-First Project Structure

Every extensible domain should be a package, not a single growing module.

```text
pyproject.toml
uv.lock
README.md
src/nasagent/
  __init__.py
  cli/
    __init__.py
    app.py
    commands/
      __init__.py
      chat.py
      run.py
      config.py
      profiles.py
      tools.py
    rendering/
      __init__.py
      panels.py
      tables.py
      progress.py
      theme.py
  agent/
    __init__.py
    graph/
      __init__.py
      builder.py
      nodes.py
      edges.py
    planning/
      __init__.py
      planner.py
      prompts.py
      schemas.py
    execution/
      __init__.py
      react.py
      step_runner.py
      errors.py
    synthesis/
      __init__.py
      synthesizer.py
      prompts.py
    state/
      __init__.py
      models.py
      store.py
  tools/
    __init__.py
    base.py
    registry.py
    schemas.py
    builtin/
      __init__.py
      file_tools.py
      device_tools.py
      task_tools.py
    nas/
      __init__.py
      file_management.py
      device_status.py
      storage.py
    system/
      __init__.py
      time.py
      confirmation.py
  nas/
    __init__.py
    base.py
    registry.py
    models.py
    adapters/
      __init__.py
      ugreen/
        __init__.py
        adapter.py
        client.py
        auth.py
        models.py
        errors.py
      simulator/
        __init__.py
        adapter.py
        fixtures.py
  llm/
    __init__.py
    base.py
    openai_provider.py
    messages.py
    token_budget.py
  safety/
    __init__.py
    policy.py
    risk.py
    approvals.py
    audit.py
  config/
    __init__.py
    settings.py
    profiles.py
    secrets.py
  observability/
    __init__.py
    events.py
    logger.py
    traces.py
tests/
  unit/
  integration/
  fixtures/
docs/
  architecture.md
  agent-flow.md
  adapters.md
  tools.md
  cli.md
  configuration.md
  development.md
  packaging.md
.github/workflows/
.gitea/workflows/
```

Package responsibilities:

- `cli.commands.*`: one command package per CLI feature so new commands can be added without changing the app shell.
- `cli.rendering.*`: all Rich rendering code, avoiding display logic inside agent or command packages.
- `agent.graph.*`: LangGraph graph construction, nodes, and edges.
- `agent.planning.*`: structured planning, planning prompt, and plan schema.
- `agent.execution.*`: ReAct loop and step execution.
- `agent.synthesis.*`: final user-facing result synthesis.
- `agent.state.*`: state models and run-state persistence.
- `tools.*`: agent-callable tool definitions and registry.
- `nas.*`: real device abstractions and vendor adapters.
- `safety.*`: risk classification, confirmation, audit, and hard execution gates.
- `config.*`: settings, profiles, and secret loading.
- `observability.*`: events, logs, traces, and redaction.

Cross-package interaction should use Pydantic models, Protocols, or base classes instead of concrete implementation imports where practical.

## Agent Flow

The system supports `nasagent chat` and `nasagent run "<task>"`.

Execution flow:

1. Context Build: load settings, active NAS profile, tools, safety policy, previous session summary if available, and non-sensitive run context.
2. Planning: use OpenAI to generate a structured plan with goal, steps, risk level, expected tools, and success criteria.
3. Plan Review: display the plan in the CLI. Read-only plans may auto-continue; high-risk plans require confirmation depending on policy.
4. Step Execution: execute each step through a ReAct loop.
5. Tool Execution: route tool calls through `ToolRegistry`, `SafetyPolicy`, adapter execution, and audit logging.
6. Result Synthesis: summarize completed operations, observations, failures, and next actions.
7. State Persistence: store sanitized run metadata under the configured run-log directory.

Example plan schema:

```json
{
  "goal": "Check NAS storage and find the largest files under downloads",
  "steps": [
    {
      "id": "s1",
      "description": "Get storage status",
      "risk": "read",
      "expected_tools": ["get_storage_status"]
    },
    {
      "id": "s2",
      "description": "List and sort files under downloads",
      "risk": "read",
      "expected_tools": ["list_files", "search_files"]
    },
    {
      "id": "s3",
      "description": "Summarize cleanup recommendations",
      "risk": "read",
      "expected_tools": []
    }
  ]
}
```

ReAct loop within each step:

```text
Thought -> Tool Call -> Observation -> Thought -> Tool Call -> Observation -> Final Step Result
```

Execution controls:

- Max iterations per step.
- Timeout per tool call.
- Timeout per step.
- Retry only for safe transient read failures.
- No automatic retry for destructive operations.
- Redaction of credentials, tokens, cookies, and sensitive headers.
- Failure result that records tool, adapter, and error category.

## NAS Adapter Design

NAS capabilities are split into adapter and tool layers.

- `nas.adapters.*` communicates with specific devices and APIs.
- `tools.nas.*` exposes safe, schema-driven tool functions to the agent.

The LLM never calls a vendor client directly.

Base adapter capabilities:

```text
NasAdapter
  authenticate()
  get_device_status()
  get_storage_status()
  list_files(path)
  search_files(query, path?)
  upload_file(local_path, remote_path)
  download_file(remote_path, local_path)
  delete_file(path)
```

UGREEN adapter package:

```text
nas/adapters/ugreen/
  client.py      # httpx client, base URL, headers, cookies, tokens, request wrapper
  auth.py        # login, logout, session refresh
  adapter.py     # implements NasAdapter
  models.py      # UGREEN request/response mappings
  errors.py      # auth, network, schema, and API errors
```

UGREEN integration policy:

- Do not fabricate endpoint paths, payloads, or response schemas.
- Provide client/session/auth extension points so packet-captured API details can be added cleanly.
- Document the packet-capture data needed: login endpoint, auth payload, token/cookie behavior, file listing endpoint, search endpoint, upload/download behavior, delete endpoint, storage endpoint, device-status endpoint, headers, CSRF fields if any, and session refresh behavior.
- Default tests and demos use the simulator until real UGREEN details are verified.
- Real-device tests are manual or opt-in through a pytest marker and local credentials.

Simulator adapter package:

```text
nas/adapters/simulator/
  adapter.py     # deterministic fake NAS implementing NasAdapter
  fixtures.py    # fake file tree, storage state, device status
```

The simulator must be deterministic so agent graph tests and CLI snapshots are stable.

## Tool Design

First-phase NAS tools:

```text
tools.nas.device_status
  get_device_status
  get_storage_status

tools.nas.file_management
  list_files
  search_files
  upload_file
  download_file
  delete_file
```

Each tool has metadata:

```text
name
description
args_schema
risk_level: read | write | destructive | system
requires_confirmation
supports_dry_run
adapter_capability
```

Risk levels:

- `read`: `get_device_status`, `get_storage_status`, `list_files`, `search_files`, `download_file`.
- `write`: `upload_file`.
- `destructive`: `delete_file`.
- `system`: reserved for restart, shutdown, service changes, and configuration mutation.

`ToolRegistry` responsibilities:

- Register built-in and NAS tools.
- Expose tool schemas to the LLM.
- Resolve tool names to Python callables.
- Attach risk metadata.
- Validate tool arguments before execution.
- Prepare for future plugin discovery through package entry points.

## NAS-Specific Product Behavior

NAS-specific behavior lives in these packages:

- `nas/`: device protocols, vendor adapters, domain models.
- `tools/nas/`: NAS operations exposed to the agent.
- `safety/`: real-device risk policy and confirmations.
- `agent.*.prompts`: NAS operation guidance, no hallucinated device state, no guessed APIs, path disambiguation, and destructive operation constraints.
- `cli.rendering/`: operations-oriented display of plans, tool calls, paths, devices, risk, and results.
- `config/`: multi-device profiles, credentials, default paths, and safety defaults.

This keeps the orchestration core general while making NAS behavior explicit and testable.

## CLI Design

First-phase commands:

```text
nasagent chat
nasagent run "<task>"
nasagent config show
nasagent config init
nasagent profiles list
nasagent profiles add
nasagent tools list
```

`chat` is the primary daily-use interface. `run` supports one-shot and scriptable usage.

Output uses Typer and Rich.

Default output:

- Plan panel with goal, steps, risk, and expected tools.
- Step progress with current step and concise observations.
- Tool call summaries without sensitive values.
- Final result summary with completed operations, key findings, failures, and recommendations.

Optional output modes:

- `--verbose`: display ReAct thought/tool/observation details that are safe to show.
- `--json`: future structured output for automation.
- `--profile <name>`: select NAS profile.
- `--dry-run`: show planned and allowed operations without mutating device state.

Example confirmation prompt:

```text
Operation: delete_file
Profile: home
Path: /downloads/movie.iso
Risk: destructive
Reason: deletion may not be recoverable
Execute? [y/N]
```

## Configuration And Secrets

Default local paths:

```text
~/.config/nasagent/config.toml
~/.config/nasagent/profiles.toml
~/.config/nasagent/secrets.toml
~/.nasagent/runs/
```

Phase 1 can support `.env` and TOML secrets. A later phase can add system keyring support.

Example config:

```toml
[llm]
provider = "openai"
model = "gpt-4.1-mini"

[safety]
default_mode = "confirm_destructive"
allow_auto_write = false
allow_destructive = false
require_confirmation_for = ["delete_file", "upload_file"]

[observability]
run_log_dir = "~/.nasagent/runs"
redact_sensitive = true
```

Example profiles:

```toml
[profiles.home]
adapter = "ugreen"
base_url = "https://nas.local"
username = "user"
default_download_dir = "/downloads"

[profiles.simulator]
adapter = "simulator"
```

Secrets must not be written to logs, prompts, run state, or committed files.

## Safety Policy

Safety mode is configurable, with conservative defaults.

Default behavior:

- `read`: auto-execute.
- `write`: require confirmation unless explicitly configured otherwise.
- `destructive`: require confirmation and remain disabled unless allowed by configuration.
- `system`: disabled in phase 1 unless explicitly enabled by a future implementation.

Execution chain:

```text
Tool Call -> RiskClassifier -> SafetyPolicy -> ApprovalProvider -> Adapter -> AuditLog
```

The model cannot bypass `SafetyPolicy`. Even if the plan asks for a dangerous action, execution must stop at the safety layer until approval is granted.

Additional safety rules:

- Display device profile and target path before mutating operations.
- Ask for confirmation on ambiguous paths.
- Reject destructive operations against root or broad paths unless explicitly supported by a future high-friction flow.
- Support dry-run metadata for tools even when the first implementation only simulates selected operations.
- Redact credentials, tokens, cookies, and sensitive headers in logs and CLI output.

## Observability And State

Phase 1 stores sanitized run data under `.nasagent/runs/` or the configured run-log directory.

Run data includes:

- Run id.
- User goal.
- Selected profile.
- Plan.
- Step results.
- Tool calls with redacted arguments.
- Error categories.
- Final summary.

State is for debugging and future recovery. It is not a full long-term memory system in phase 1.

## Dependencies

Core dependencies:

```text
python >= 3.11
openai
langgraph
langchain-core
rich
pydantic
pydantic-settings
httpx
```

Development dependencies:

```text
pytest
pytest-cov
ruff
mypy or pyright
respx or pytest-httpx
```

The exact dependency set can be finalized during implementation based on compatibility.

## Testing Strategy

Test layers:

```text
unit:
  planner schema validation
  tool registry
  safety policy
  config loading
  simulator adapter

integration:
  LangGraph flow with simulator adapter
  CLI run command with simulator profile
  OpenAI provider mocked

manual:
  UGREEN real-device smoke tests
```

Real UGREEN tests are opt-in:

```text
pytest -m ugreen_real
```

CI should not require private devices or credentials.

Default CI checks:

```text
uv sync --all-extras --dev
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run mypy src
```

If mypy creates too much initial overhead, it can be introduced with a focused config and gradually tightened. The design should still use type annotations from the beginning.

## Documentation

First-phase docs:

```text
docs/architecture.md
docs/agent-flow.md
docs/adapters.md
docs/tools.md
docs/cli.md
docs/configuration.md
docs/development.md
docs/packaging.md
```

Documentation expectations:

- Architecture diagrams can be textual in phase 1.
- Public base classes, Protocols, and Pydantic models should have concise docstrings.
- Adapter documentation must explain how to add a new NAS vendor.
- UGREEN documentation must explain which API details are still needed from packet capture.
- Tool documentation must include risk level and examples.

## Packaging And Installation

Use standard `src` layout and `pyproject.toml` metadata.

Planned script entry point:

```toml
[project.scripts]
nasagent = "nasagent.cli.app:app"
```

Optional dependencies:

```toml
[project.optional-dependencies]
dev = [...]
ugreen = []
```

Supported local usage patterns:

```text
uv sync
uv run nasagent chat
uv run nasagent run "check storage"
uv pip install .
pipx install .
```

Publishing to PyPI is not required in phase 1, but the layout should not block it.

## GitHub And Gitea CI/CD

Maintain separate workflow files:

```text
.github/workflows/ci.yml
.gitea/workflows/ci.yml
```

Both workflows should run the same logical checks:

```text
uv sync --all-extras --dev
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run mypy src
```

Repository sync is handled through two remotes, not hard-coded application logic:

```text
origin -> GitHub
gitea  -> Gitea
```

Document normal push flow:

```text
git push origin main
git push gitea main
```

Gitea and GitHub secrets should be configured independently. No repository workflow should require real NAS credentials for default CI.

## Extension Points

Planned extension points:

- New CLI commands under `cli.commands`.
- New Rich renderers under `cli.rendering`.
- New tools under `tools.nas`, `tools.system`, or future packages.
- New NAS vendors under `nas.adapters`.
- New LLM providers under `llm`.
- New safety policies under `safety`.
- Plugin discovery through Python package entry points in a later phase.
- Future checkpointing and resume support in `agent.state`.
- Future human-in-the-loop workflows using LangGraph and `ApprovalProvider`.

## Implementation Phasing

Phase 1 should be implemented in small increments:

1. Project skeleton, packaging, lint/test tooling, CI files.
2. Config and profile loading.
3. NAS base adapter, simulator adapter, and UGREEN adapter skeleton.
4. Tool base classes, registry, and NAS tools backed by simulator.
5. Safety policy and approval provider.
6. OpenAI LLM provider abstraction.
7. Planner, ReAct executor, synthesizer, and LangGraph assembly.
8. CLI commands and Rich rendering.
9. Documentation set.
10. UGREEN real-device integration points once verified API details are available.

## Open Inputs Needed Later

UGREEN real-device implementation needs verified API details from documentation or packet capture:

- Login endpoint and payload.
- Session token, cookie, CSRF, or signature behavior.
- Session refresh or logout behavior.
- File list endpoint and response schema.
- File search endpoint and response schema.
- Upload and download API behavior.
- Delete API behavior.
- Storage status endpoint and response schema.
- Device status endpoint and response schema.
- Error response formats.
- Required headers and origin/referrer constraints.

Until those details are known, UGREEN code should provide clear extension points and fail with explicit unsupported-operation errors rather than guessing.

## Acceptance Criteria

The phase 1 implementation is acceptable when:

- `uv sync` succeeds.
- `uv run nasagent chat` starts an interactive CLI.
- `uv run nasagent run "check storage" --profile simulator` executes through planning, ReAct step execution, tool calls, and final synthesis.
- Simulator-backed file and device tools are covered by tests.
- Safety policy prevents unconfirmed destructive operations.
- OpenAI provider reads configuration without exposing secrets in logs.
- UGREEN adapter package exists with client/auth/adapter boundaries and explicit unsupported behavior for unknown endpoints.
- Docs explain architecture, agent flow, adapters, tools, CLI, configuration, development, and packaging.
- GitHub and Gitea CI workflow files exist and run lint/test checks without real NAS credentials.
