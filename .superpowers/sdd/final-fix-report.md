Status: DONE

Final review fixes:
- Implemented `nasagent chat --profile simulator` as a minimal interactive REPL that runs tasks until `exit` or `quit`.
- Wired sanitized run-state persistence into `run_agent_once` using configured/default run-log directories.
- Added safety settings and approval-provider injection through graph execution and `StepRunner`.
- Updated safety semantics so `allowed=True` means executable without further approval.
- Redacted `UgreenCredentials.password` from repr output.
- Expanded CLI, tools, and configuration docs with risk, usage, profile, run-log, and safety details.

Verification:
- `uv run pytest`: PASSED, 39 passed.
- `uv run ruff check .`: PASSED.
- `uv run ruff format --check .`: PASSED, 102 files already formatted.
- `uv run mypy src`: PASSED, no issues found in 74 source files.
- `uv run nasagent run "check storage" --profile simulator`: PASSED.

Concerns:
- None.
