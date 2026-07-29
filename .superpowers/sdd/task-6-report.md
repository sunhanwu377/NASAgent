## Pytest Collection Fix

- Root cause: pytest's default import mode loaded duplicate `test_registry.py` basenames as the same top-level module during collection.
- Fix: configured pytest `addopts = ["--import-mode=importlib"]` in `pyproject.toml` so plain `uv run pytest` matches the passing import behavior.
- Verification: `uv run pytest` passed with 26 tests; `uv run python -c "import tomllib; tomllib.load(open('pyproject.toml', 'rb'))"` passed.

## Re-review StepRunner Iteration Cap Fix

- Root cause: `StepRunner.run_step` sliced `step.expected_tools` to `MAX_REACT_ITERATIONS`, skipped excess planned tools, and still returned `success=True`.
- Fix: added a preflight limit check that returns `success=False` with a clear error before executing any tools when a step exceeds the ReAct iteration cap.
- Verification: `uv run pytest tests/unit/agent/test_step_runner.py tests/unit/agent/test_state_store.py tests/integration/test_agent_graph.py -v`, `uv run ruff check .`, and `uv run mypy src` passed.

## Platform Kernel Task 6 Implementation

- Implemented `DiscoveryOptions` and `DiscoveryScanner` with vendor match conversion, service deduplication, and conservative protocol-placeholder orchestration through `scan_hosts`.
- Added `discover_mdns_services` and `discover_ssdp_services` placeholders that return no services and introduce no network dependencies.
- Extended `config init` with the required LAN discovery confirmation prompt and safe opt-in messaging; the scan path calls `DiscoveryScanner` but does not perform aggressive host probing.
- Preserved existing config-init behavior by updating existing tests to explicitly skip LAN discovery and adding a new smoke test for the no-scan path.
- TDD evidence: `uv run pytest tests/unit/discovery/test_scanner.py -v` first failed because `nasagent.discovery.scanner` did not exist; `uv run pytest tests/integration/test_cli.py::test_config_init_can_skip_lan_discovery -v` first failed because the LAN prompt was missing; the added protocol orchestration test first failed because the scanner did not expose protocol discovery calls.
- Verification: `uv run pytest tests/unit/discovery/test_scanner.py tests/integration/test_cli.py -v` passed with 39 tests; `uv run ruff check src/nasagent/discovery src/nasagent/cli/commands/config.py tests/unit/discovery tests/integration/test_cli.py` passed.
- Self-review: changes are limited to the requested scanner foundation, conservative protocol placeholders, and `config init` integration. No `StepRunner`, `SafetyPolicy`, simulator execution, or credential persistence behavior was changed.
- Concerns: none.
