# Architecture

NASAgent is split into packages for CLI, agent orchestration, LLM providers, tools, NAS adapters, safety, configuration, and observability.

The agent flow is planning first, then step execution. Each step executes through registered tools and every tool call passes through safety policy before reaching a NAS adapter.

UGREEN support is represented by explicit adapter boundaries. Simulator support is the default test and demo path.

## Platform Kernel

The platform kernel is a lightweight runtime context plus explicit plugin loading, not a full application marketplace or app discovery system. `PlatformContext` groups the supplied `NasAgentSettings` with registries for tools, slash commands, and app endpoints.

`create_platform_context(settings=...)` is the current startup entry point for this kernel. It keeps the loaded settings object and creates new `ToolRegistry`, `CommandRegistry`, and `AppRegistry` instances. Startup creates empty registries; code that needs built-in NAS tools must either use the existing agent graph default registry path or load the built-in plugin with `PluginManager.load_builtin()`.

`AppRegistry` stores `AppEndpoint` records by unique endpoint name and can list all endpoints or filter by `app_type`. `CommandRegistry` stores `CommandDefinition` records by command name, resolves aliases, strips a leading slash during lookup, and dispatches raw command text to the registered handler. `ToolRegistry` is the existing tool registry used by the context; it stores tool definitions by unique tool name and raises for unknown tool lookup.

Current configuration data flow: TOML and `NASAGENT_` environment values are merged into `NasAgentSettings`. Those settings include core LLM/safety/observability models plus `AppEndpointSettings` records and `PluginSettings` records. App endpoint settings can point at a `credential_key`; secret values for those keys are persisted separately through `CredentialStore` in `~/.local/share/nasagent/secrets.toml` with `0600` file permissions.

Current plugin data flow: `PluginManager` receives a `PlatformContext`. `load_builtin()` calls `nasagent.plugins.builtin.register()`, which sets the `builtin` manifest and registers the built-in NAS tools into `context.tools`. `load_entry_points()` discovers the `nasagent.plugins` entry-point group unless explicit entry points are supplied, calls each entry point's register function with a `PluginContext`, records any returned manifest, and stores plugin load failures in `PluginManager.errors` without aborting remaining loads.

Current runtime data flow: startup calls `create_platform_context(settings=...)`, and the resulting `PlatformContext` becomes the shared container that later code can populate with tools, commands, plugins, and app endpoints. Credential lookup, automatic plugin loading during CLI/agent startup, and app endpoint discovery are not wired into startup yet.
