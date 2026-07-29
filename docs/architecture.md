# Architecture

NASAgent is split into packages for CLI, agent orchestration, LLM providers, tools, NAS adapters, safety, configuration, and observability.

The agent flow is planning first, then step execution. Each step executes through registered tools and every tool call passes through safety policy before reaching a NAS adapter.

UGREEN support is represented by explicit adapter boundaries. Simulator support is the default test and demo path.

## Platform Kernel

NASAgent has a `PlatformContext` for startup paths that opt into the platform kernel. The context owns registries for tools, commands, app endpoints, and plugin metadata. Built-in capabilities and third-party plugins register through the same APIs when those plugin loaders are invoked.

The platform kernel is a lightweight runtime context plus explicit plugin loading, not a full application marketplace or app discovery system. `PlatformContext` groups the supplied `NasAgentSettings` with registries for tools, slash commands, and app endpoints.

`create_platform_context(settings=...)` is the current startup entry point for this kernel. It keeps the loaded settings object, creates new `ToolRegistry`, `CommandRegistry`, and `AppRegistry` instances, and hydrates `AppRegistry` from configured `settings.apps` endpoints. Code that needs built-in NAS tools or slash commands must either use the existing agent graph default registry path or load the built-in plugin with `PluginManager.load_builtin()`.

`AppRegistry` stores `AppEndpoint` records by unique endpoint name and can list all endpoints or filter by `app_type`. `CommandRegistry` stores `CommandDefinition` records by command name, resolves aliases, strips a leading slash during lookup, and dispatches raw command text to the registered handler. `ToolRegistry` is the existing tool registry used by the context; it stores tool definitions by unique tool name and raises for unknown tool lookup.

Current configuration data flow: `nasagent config init` writes non-sensitive LLM/safety/observability settings to `~/.config/nasagent/config.toml`. If the user enters an LLM API key, the CLI persists it through `CredentialStore` as `llm.api_key` in `~/.local/share/nasagent/secrets.toml`, which is created and read with `0600` file permissions. `load_settings()` reads config TOML and `NASAGENT_` environment values into `NasAgentSettings`; if `settings.llm.api_key` is still empty, it falls back to `CredentialStore.get("llm.api_key")`. Those settings include core LLM/safety/observability models plus `AppEndpointSettings` records and `PluginSettings` records. App endpoint settings can point at a `credential_key`, with secret values for those keys kept in the credential store rather than in config TOML.

Current discovery/config-init data flow: `nasagent config init` prompts before discovery and defaults to no LAN scan. If discovery is enabled, it calls the discovery scanner with safe limits and reports discovered services if any are returned. mDNS and SSDP functions are conservative placeholders today, so they do not discover services yet. `DiscoveryScanner.scan_hosts(hosts)` supports explicit-host probing through registered vendor and generic probe targets, deduplicates matches, and does not enumerate whole subnets by itself. When discovery finds nothing, the CLI directs users to add app endpoints manually in `config.toml`.

Current plugin data flow: `PluginManager` receives a `PlatformContext`. Platform-enabled CLI, chat, and agent registry startup paths load the built-in plugin and then entry points from the `nasagent.plugins` group. `load_builtin()` calls `nasagent.plugins.builtin.register()`, which sets the `builtin` manifest, registers the built-in NAS tools, Docker tool definitions, minimal AList tool definitions, and minimal Vaultwarden tool definitions into `context.tools`, and registers shared command handlers into `context.commands`. Docker Compose config/up/down tools are registered as `system` risk tools that require confirmation; their command helpers keep Compose file paths as explicit subprocess arguments, reject absolute paths and `..` traversal, and do not use shell command strings. AList and Vaultwarden tool handlers currently report missing endpoint/token configuration rather than calling external APIs. Lucky has a small endpoint/token client skeleton but no registered tools until API behavior is verified. `load_entry_points()` discovers the `nasagent.plugins` entry-point group unless explicit entry points are supplied, calls each entry point's register function with a `PluginContext`, records any returned manifest, and stores plugin load failures in `PluginManager.errors` without aborting remaining loads.

Current command data flow: `nasagent.plugins.commands.register_builtin_commands()` registers `/help`, `/apps`, `/plugins`, `/tools`, and `/containers`. Observed CLI command contexts for apps, plugins, tools, containers, and chat slash commands create a platform context from loaded settings, load built-in and entry-point plugins, dispatch or render from the shared registry, and print the result. `/plugins` shows loaded manifests and entry-point load errors; `/tools` lists agent-callable tools from `PlatformContext.tools`. The chat REPL uses the same path when input starts with `/`, before local greeting, conversational LLM, or simulator execution handling.

Current runtime data flow: startup calls `create_platform_context(settings=...)`, and the resulting `PlatformContext` becomes the shared container that plugin loaders populate with tools, commands, plugin manifests, load errors, and additional app endpoints. Configured app endpoints are available immediately in `context.apps`; LLM API keys fall back to `CredentialStore` when absent from env/config, and platform CLI/chat/agent registry startup paths load built-in plus entry-point plugins.

## Data Flow

1. CLI or chat starts.
2. `load_settings()` loads config TOML and `NASAGENT_` environment values, then reads `llm.api_key` from `CredentialStore` only if it is still unset.
3. Platform-enabled CLI, chat, and agent registry startup paths load built-in and entry-point plugins.
4. CLI commands, chat slash commands, planner prompts, and planner-selected tools resolve through platform registries where a platform context has loaded those commands and tools.
5. Agent-callable tools execute through `StepRunner` and `SafetyPolicy`.
6. Logs and UI output use redaction for sensitive values.
