# Final Review Fix Report

Status: DONE

Implementation commit:

- `3b4744638a9adf900c1ee099dfa8e4ccfeae3d0f` - `fix: wire platform plugins into runtime`

## Changes

- Loaded built-in and `nasagent.plugins` entry-point plugins through shared platform startup paths for CLI wrappers, chat slash commands, `nasagent tools list`, and the default agent tool registry.
- Stored plugin manifests and load errors on `PlatformContext` so `/plugins` and `nasagent plugins list` report loaded plugins and isolated entry-point failures instead of hardcoded builtin-only status.
- Made `/tools` render actual `PlatformContext.tools` entries, including Docker, AList, Vaultwarden, legacy NAS tools, and third-party plugin tools.
- Added `CredentialStore` fallback in `load_settings()` for `llm.api_key` only when env/config did not supply an explicit API key.
- Kept config TOML non-sensitive and verified config show redacts credential-store API keys.
- Built planner prompts from the active execution registry's tool names and reused that registry for `StepRunner` execution.
- Preserved simulator task execution through `StepRunner` and `SafetyPolicy`.
- Tightened `GenericNasProbe` to match `nas` as a word or `network attached storage`, avoiding broad substring false positives like `bananas`.
- Updated permanent docs for the changed plugin/tool/settings/agent data flow.

## Files Changed

- `docs/agent-flow.md`
- `docs/architecture.md`
- `docs/cli.md`
- `docs/configuration.md`
- `docs/plugins.md`
- `docs/tools.md`
- `src/nasagent/agent/graph/builder.py`
- `src/nasagent/agent/graph/nodes.py`
- `src/nasagent/agent/planning/planner.py`
- `src/nasagent/agent/planning/prompts.py`
- `src/nasagent/cli/commands/apps.py`
- `src/nasagent/cli/commands/chat.py`
- `src/nasagent/cli/commands/containers.py`
- `src/nasagent/cli/commands/plugins.py`
- `src/nasagent/cli/commands/tools.py`
- `src/nasagent/config/settings.py`
- `src/nasagent/discovery/vendors/generic.py`
- `src/nasagent/platform/context.py`
- `src/nasagent/platform/plugins.py`
- `src/nasagent/plugins/commands.py`
- `tests/integration/test_agent_graph.py`
- `tests/integration/test_cli.py`
- `tests/unit/agent/test_planner.py`
- `tests/unit/config/test_settings.py`
- `tests/unit/discovery/test_vendor_probes.py`
- `tests/unit/platform/test_plugins.py`

## Verification

- RED: `uv run pytest tests/unit/platform/test_plugins.py tests/unit/config/test_settings.py tests/integration/test_cli.py -k "entry_point or platform_plugin_tools or chat_tools_slash or credential_store_api_key or falls_back_to_credential_store or preserves_explicit_api_key" tests/integration/test_agent_graph.py::test_agent_execution_registry_includes_platform_plugin_tools -v`
  - Result: expected failures for missing credential-store fallback, CLI/chat entry-point loading, platform tool listing, and agent registry plugin tools.
- RED: `uv run pytest tests/unit/agent/test_planner.py::test_planner_prompt_accepts_dynamic_tool_names -v`
  - Result: failed because `Planner.__init__()` did not accept `tool_names`.
- RED: `uv run pytest tests/unit/discovery/test_vendor_probes.py::test_generic_probe_uses_word_boundary_for_nas -v`
  - Result: failed after correcting fixture to `bananas service dashboard`, proving the substring false positive.
- GREEN focused: `uv run pytest tests/unit/platform/test_plugins.py tests/unit/config/test_settings.py tests/unit/agent/test_planner.py tests/unit/discovery/test_vendor_probes.py tests/integration/test_cli.py -k "entry_point or platform_plugin_tools or chat_tools_slash or credential_store_api_key or falls_back_to_credential_store or preserves_explicit_api_key or dynamic_tool_names or generic_probe" tests/integration/test_agent_graph.py::test_agent_execution_registry_includes_platform_plugin_tools -v`
  - Result: `13 passed, 55 deselected in 0.51s`.
- Focused suites: `uv run pytest tests/unit/platform tests/unit/config/test_settings.py tests/unit/agent/test_planner.py tests/unit/discovery/test_vendor_probes.py tests/integration/test_cli.py tests/integration/test_agent_graph.py -v`
  - Result: `81 passed in 0.62s`.
- Changed-file lint: `uv run ruff check src/nasagent/platform/context.py src/nasagent/platform/plugins.py src/nasagent/plugins/commands.py src/nasagent/cli/commands/apps.py src/nasagent/cli/commands/plugins.py src/nasagent/cli/commands/containers.py src/nasagent/cli/commands/chat.py src/nasagent/cli/commands/tools.py src/nasagent/config/settings.py src/nasagent/agent/graph/nodes.py src/nasagent/agent/graph/builder.py src/nasagent/agent/planning/prompts.py src/nasagent/agent/planning/planner.py src/nasagent/discovery/vendors/generic.py tests/unit/platform/test_plugins.py tests/unit/config/test_settings.py tests/unit/agent/test_planner.py tests/unit/discovery/test_vendor_probes.py tests/integration/test_cli.py tests/integration/test_agent_graph.py`
  - Result: `All checks passed!`.
- Full tests: `uv run pytest`
  - Result: `139 passed in 0.75s`.
- Full lint: `uv run ruff check .`
  - Result: `All checks passed!`.
- Format check: `uv run ruff format --check .`
  - Result: `155 files already formatted`.
- Type check: `uv run mypy src`
  - Result: `Success: no issues found in 109 source files`.

## Self-Review

- Confirmed third-party entry points are loaded in CLI/chat platform surfaces through one shared helper and test-injected entry points.
- Confirmed `/plugins` and `nasagent plugins list` report manifests and load errors from real plugin manager state.
- Confirmed `/tools` and `nasagent tools list` expose `PlatformContext.tools`, including namespaced Docker/AList/Vaultwarden tools and legacy NAS tools.
- Confirmed runtime settings use stored `llm.api_key` only as a fallback and do not write secrets into config TOML.
- Confirmed agent execution still goes through `StepRunner` and `SafetyPolicy` and simulator storage execution still works.
- Confirmed planner prompt tool names come from the active execution registry.
- Confirmed the Generic NAS matcher no longer matches arbitrary substrings.

## Concerns

- Agent default registry now loads installed third-party entry points during graph construction. Broken plugin loads are isolated in platform state for user-facing plugin listings, but agent registry construction intentionally continues with successfully loaded tools.
