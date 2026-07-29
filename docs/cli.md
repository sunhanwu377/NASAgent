# CLI

Commands:

```bash
nasagent chat
nasagent run "check storage" --profile simulator
nasagent config show
nasagent config init
nasagent apps list
nasagent plugins list
nasagent containers list
nasagent tools list
nasagent profiles list
nasagent profiles add home
```

`nasagent chat --profile simulator` starts a small REPL. Enter a task such as `check storage`; type `exit` or `quit` to leave.

The chat REPL dispatches slash commands before local chat or task execution. Supported built-in slash commands are `/help`, `/apps`, `/plugins`, `/tools`, and `/containers`.

`nasagent run "check storage" --profile simulator` executes one task and exits. Phase 1 uses the simulator profile for default demos and CI, so no real NAS credentials are needed.

Both `chat` and `run` execute through planning, safety policy, simulator-backed tools, synthesis, and sanitized run-state persistence under the configured run-log directory.

`nasagent apps list`, `nasagent plugins list`, `nasagent tools list`, and `nasagent containers list` use the same platform registries as chat slash commands. They create a platform context, load built-in and `nasagent.plugins` entry-point plugins, dispatch or render from the shared registry, and print the returned message. `/plugins` and `nasagent plugins list` include loaded plugin manifests and entry-point load errors.
