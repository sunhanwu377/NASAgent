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

`nasagent apps list`, `nasagent plugins list`, and `nasagent containers list` are CLI wrappers around the same shared command registry used by chat slash commands. They create a platform context, load the built-in plugin, dispatch the matching slash command, and print the returned message.
