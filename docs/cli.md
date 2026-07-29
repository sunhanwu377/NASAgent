# CLI

Commands:

```bash
nasagent chat
nasagent run "check storage" --profile simulator
nasagent config show
nasagent config init
nasagent profiles list
nasagent profiles add home
nasagent tools list
```

`nasagent chat --profile simulator` starts a small REPL. Enter a task such as `check storage`; type `exit` or `quit` to leave.

`nasagent run "check storage" --profile simulator` executes one task and exits. Phase 1 uses the simulator profile for default demos and CI, so no real NAS credentials are needed.

Both `chat` and `run` execute through planning, safety policy, simulator-backed tools, synthesis, and sanitized run-state persistence under the configured run-log directory.
