# Architecture

NASAgent is split into packages for CLI, agent orchestration, LLM providers, tools, NAS adapters, safety, configuration, and observability.

The agent flow is planning first, then step execution. Each step executes through registered tools and every tool call passes through safety policy before reaching a NAS adapter.

UGREEN support is represented by explicit adapter boundaries. Simulator support is the default test and demo path.

## Platform Kernel

The platform kernel introduced at this stage is a lightweight runtime context, not a full plugin system yet. `PlatformContext` groups the supplied `NasAgentSettings` with empty registries for tools, slash commands, and app endpoints.

`create_platform_context(settings=...)` is the current startup entry point for this kernel. It keeps the loaded settings object and creates new `ToolRegistry`, `CommandRegistry`, and `AppRegistry` instances. Task 1 does not pre-register built-in tools, commands, or NAS app endpoints during startup.

`AppRegistry` stores `AppEndpoint` records by unique endpoint name and can list all endpoints or filter by `app_type`. `CommandRegistry` stores `CommandDefinition` records by command name, resolves aliases, strips a leading slash during lookup, and dispatches raw command text to the registered handler. `ToolRegistry` is the existing tool registry used by the context; it stores tool definitions by unique tool name and raises for unknown tool lookup.

Current data flow: configuration is loaded into `NasAgentSettings`, startup calls `create_platform_context`, and the resulting `PlatformContext` becomes the shared container that later code can populate with tools, commands, and app endpoints.
