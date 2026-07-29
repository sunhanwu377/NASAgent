## Pytest Collection Fix

- Root cause: pytest's default import mode loaded duplicate `test_registry.py` basenames as the same top-level module during collection.
- Fix: configured pytest `addopts = ["--import-mode=importlib"]` in `pyproject.toml` so plain `uv run pytest` matches the passing import behavior.
- Verification: `uv run pytest` passed with 26 tests; `uv run python -c "import tomllib; tomllib.load(open('pyproject.toml', 'rb'))"` passed.

## Re-review StepRunner Iteration Cap Fix

- Root cause: `StepRunner.run_step` sliced `step.expected_tools` to `MAX_REACT_ITERATIONS`, skipped excess planned tools, and still returned `success=True`.
- Fix: added a preflight limit check that returns `success=False` with a clear error before executing any tools when a step exceeds the ReAct iteration cap.
- Verification: `uv run pytest tests/unit/agent/test_step_runner.py tests/unit/agent/test_state_store.py tests/integration/test_agent_graph.py -v`, `uv run ruff check .`, and `uv run mypy src` passed.
