# NASAgent Platform Kernel Design

## Summary

NASAgent will evolve from a simulator-first NAS CLI agent into an extensible NAS automation platform. The first phase prioritizes the platform foundation: LAN NAS discovery, initialization guidance, credential persistence, command extensibility, plugin/tool loading, and minimal verifiable built-in tools for Docker, AList, Lucky, and Vaultwarden.

The goal is not to cover every external API immediately. The goal is to create stable extension points so built-in apps and third-party plugins use the same mechanisms.

## Goals

- Discover NAS and common NAS app services during `nasagent config init`.
- Support protocol-based discovery through mDNS/Bonjour and SSDP/UPnP, with controlled fallback probing.
- Support vendor-specific NAS probing for UGREEN, FNOS, Synology, Zspace, and future vendors.
- Persist app tokens and API keys in a local permission-protected secrets file.
- Add a plugin system based on Python package entry points.
- Let plugins register tools, commands, app metadata, and configuration requirements.
- Add an extensible command system shared by CLI subcommands and chat slash commands.
- Add Docker SDK based tools plus guarded Docker Compose commands.
- Add minimal AList, Lucky, and Vaultwarden client/tool skeletons.
- Document the architecture and data flow in project documentation.
- Rewrite the GitHub README in the style of high-star open source projects.

## Non-Goals For First Phase

- Full API coverage for AList, Lucky, Vaultwarden, Cloudflare, or sun-panel.
- Fake or guessed Lucky API implementations before the target API is verified.
- A complete public plugin marketplace.
- Automatic whole-network aggressive scanning.
- Replacing the existing `StepRunner` and `SafetyPolicy` execution model.

## Architecture

The platform is organized around a small kernel and extension registries.

- `core registry`: owns shared registries for tools, commands, apps, plugin metadata, and config declarations.
- `plugin system`: loads built-in and third-party plugins. Built-ins use the same registration path as external plugins.
- `discovery`: finds NAS and app services through protocol discovery, vendor probes, and limited fallback HTTP probing.
- `credentials`: stores sensitive token/session/API key data in a local secrets file and returns redacted summaries for display.
- `commands`: defines command handlers once and exposes them through both Typer CLI commands and chat slash commands.
- `tools`: keeps agent-callable tools as `ToolDefinition` objects and routes execution through the existing safety layer.
- `clients`: wraps external APIs for AList, Lucky, Vaultwarden, Docker, and future Cloudflare/sun-panel integrations.

The existing simulator adapter remains useful for local development and tests. The new platform layer should not force every external app integration into the NAS adapter protocol. NAS adapters remain for NAS device operations; app integrations live behind clients and tools.

## Plugin System

Plugins expose a registration function through Python entry points using the group `nasagent.plugins`.

```python
def register(plugin: PluginContext) -> None:
    plugin.tools.register(...)
    plugin.commands.register(...)
    plugin.apps.register(...)
    plugin.config.register(...)
```

Core models:

- `PluginManifest`: name, version, description, author, permissions, provided apps, tools, and commands.
- `PluginContext`: shared registration context given to each plugin.
- `ToolProvider`: returns `ToolDefinition` instances and reuses `ToolRegistry` plus `SafetyPolicy`.
- `CommandProvider`: registers command definitions for CLI and chat slash dispatch.
- `AppProvider`: declares configured NAS apps such as `alist`, `lucky`, `vaultwarden`, `cloudflare`, and `sun-panel`.
- `ConfigProvider`: declares config keys and credential keys required by the plugin.

Tool names use namespaces to avoid collisions:

- `docker.containers.list`
- `docker.containers.inspect`
- `docker.images.pull`
- `alist.fs.list`
- `alist.fs.upload`
- `lucky.reverse_proxy.create`
- `vaultwarden.users.list`
- `cloudflare.dns.create_record`

Built-in plugins are registered through `nasagent.plugins.builtin`. A future third-party Cloudflare package should only need to depend on the NASAgent SDK, expose the entry point, and then appear in `nasagent plugins list`, `/plugins`, `/help`, and the tool registry.

## Safety Model

The existing risk levels remain the base policy:

- `read`: list, query, inspect, status.
- `write`: create DNS records, create reverse proxies, upload files, start containers.
- `destructive`: delete files, delete containers, delete DNS records.
- `system`: Docker Compose, service restarts, NAS system configuration.

Safety policy evaluation should also be aware of tool namespace and capability metadata. Compose operations are `system` risk and require confirmation by default.

## Discovery And Initialization

`nasagent.discovery` provides LAN discovery during `nasagent config init`.

Discovery sources:

- mDNS/Bonjour for `_http._tcp.local`, `_https._tcp.local`, and common NAS/app service names.
- SSDP/UPnP for media servers, NAS devices, routers, Docker gateways, and app gateways.
- Generic HTTP/HTTPS probing for constrained fallback scanning.
- Vendor-specific probes for common NAS brands.

Fallback probing constraints:

- Limit to the local subnet or a user-provided range.
- Use configurable timeouts and concurrency limits.
- Use a small port set by default, such as `80`, `443`, `5000`, `5001`, `5244`, and `16601`.
- Avoid intrusive scanning and never scan broad external networks by default.

Discovery results normalize into a common model:

```python
@dataclass(frozen=True)
class DiscoveredService:
    host: str
    port: int
    scheme: str
    service_type: str
    name: str | None
    source: str
    confidence: float
    login_url: str | None
    admin_url: str | None
```

`nasagent config init` flow:

1. Prompt for LLM provider, model, base URL, and API key.
2. Ask whether to scan the LAN.
3. Run discovery if approved.
4. Display discovered NAS and app services.
5. Let the user choose services to save as profiles or app endpoints.
6. If no service is found, guide manual NAS backend URL, frontend URL, username, and notes.
7. For AList, Lucky, and Vaultwarden, allow endpoint storage without requiring immediate token entry.

## Vendor NAS Probes

Vendor-specific discovery lives in `nasagent.discovery.vendors`, separate from the initialization flow.

Module structure:

- `nasagent.discovery.protocols`: mDNS, SSDP, and generic HTTP/HTTPS probing.
- `nasagent.discovery.vendors`: vendor probe implementations.
- `VendorProbeRegistry`: registers and executes vendor probes.

Probe interface:

```python
@dataclass(frozen=True)
class ProbeTarget:
    host: str
    ports: tuple[int, ...]
    schemes: tuple[str, ...]
    paths: tuple[str, ...] = ("/",)


@dataclass(frozen=True)
class VendorProbeResult:
    vendor: str
    service_type: str
    admin_url: str | None
    login_url: str | None
    confidence: float
    evidence: dict[str, str]


class VendorProbe(Protocol):
    vendor: str

    def targets(self, host: str) -> list[ProbeTarget]: ...

    async def match(self, response: ProbeHttpResponse) -> VendorProbeResult | None: ...
```

Initial built-in probes:

- `UgreenProbe`: tries `http://host:9999` and `https://host:9443`, then matches UGREEN login/admin page evidence.
- `SynologyProbe`: reserves DSM common ports and paths, including `5000` and `5001`.
- `FnosProbe`: reserves FNOS rules in an isolated probe module.
- `ZspaceProbe`: reserves Zspace rules in an isolated probe module.
- `GenericNasProbe`: fallback for generic NAS or web admin pages.

Adding a new vendor should require a new probe file plus registration only. The discovery orchestrator and `config init` should not need vendor-specific conditionals.

## Credential Persistence

Persistent data is split into non-sensitive config and sensitive secrets.

- `~/.config/nasagent/config.toml`: profiles, app endpoints, plugin enabled state, and non-sensitive settings.
- `~/.local/share/nasagent/secrets.toml`: token, session, and API key values.

The secrets file must be created and written with `0600` permissions. If permissions are unsafe, NASAgent refuses to read real secret values and explains how to fix the file mode.

Credential access goes through a unified store:

```python
CredentialStore.get("alist.default.token")
CredentialStore.set("lucky.home.token", value)
CredentialStore.redacted_summary()
```

`config show`, `apps list`, `plugins list`, and run logs should use redacted output by default. The existing `observability.redact_sensitive` setting continues to govern logs.

## Command System

Commands are registered once and exposed in both CLI and chat.

```python
@dataclass(frozen=True)
class CommandDefinition:
    name: str
    description: str
    usage: str
    handler: CommandHandler
    aliases: tuple[str, ...] = ()
    plugin: str | None = None
```

First-phase built-in commands:

- `/help` and CLI help integration: list core commands, plugin commands, and tool namespaces.
- `/apps` and `nasagent apps list`: list configured app endpoints and login status with redaction.
- `/containers` and `nasagent containers list`: list Docker containers.
- `/plugins` and `nasagent plugins list`: list enabled plugins, versions, tools, commands, and load errors.
- `/tools` and `nasagent tools list`: list agent-callable tools.

Chat slash commands should dispatch before normal LLM conversation or task execution. Unknown slash commands should return a concise help message with closest known command names when possible.

## Docker Tools

Docker structured operations use the Python Docker SDK.

First-phase tools:

- `docker.containers.list`
- `docker.containers.inspect`
- `docker.containers.start`
- `docker.containers.stop`
- `docker.images.pull`
- `docker.networks.list`
- `docker.volumes.list`

Docker Compose is handled separately because Compose v2 is primarily CLI/plugin behavior rather than plain Docker Engine SDK behavior.

First-phase Compose tools:

- `docker.compose.config`: validate a Compose file.
- `docker.compose.up`: run `docker compose up -d` through a controlled subprocess.
- `docker.compose.down`: run `docker compose down` through a controlled subprocess.

Compose subprocess execution must avoid shell interpolation, use explicit argument lists, restrict paths to user-provided files or directories, and require confirmation due to `system` risk.

## Built-In App Tools

The first phase establishes client and tool structure with minimal verifiable operations.

AList:

- `alist.auth.login`
- `alist.fs.list`
- `alist.fs.get`
- `alist.fs.mkdir`
- `alist.fs.upload`
- `alist.fs.remove`

Lucky:

- Add `LuckyClient` and endpoint/token management.
- Only expose tools for API endpoints verified against the target Lucky deployment or confirmed documentation.
- Do not implement guessed reverse proxy or DDNS calls until verified.

Vaultwarden:

- Target Vaultwarden, not official Bitwarden cloud APIs.
- Prioritize admin-token or API-token based basic status and user listing if supported by the configured instance.
- Keep official Bitwarden API assumptions out of Vaultwarden tools unless explicitly verified.

Cloudflare:

- Do not build into core during this phase.
- Use Cloudflare as the reference third-party plugin path for future `cloudflare.dns.*` tools.

## Data Flow

Startup and execution flow:

1. Start CLI or chat.
2. Load `NasAgentSettings`, profiles, app endpoints, and `CredentialStore`.
3. Create `PlatformContext`.
4. Load built-in plugins.
5. Load entry point plugins from `nasagent.plugins`.
6. Plugins register tools, commands, apps, and config declarations.
7. CLI commands, chat slash commands, and agent planner resolve capabilities from registries.
8. Tool execution goes through the existing `StepRunner` and `SafetyPolicy`.
9. External API clients fetch tokens from `CredentialStore` only at execution time.
10. UI output and logs render sensitive values through redaction helpers.

Initialization data flow:

1. `config init` collects LLM settings.
2. User optionally starts discovery.
3. Discovery combines protocol results, vendor probe results, and generic fallback results.
4. Results are deduplicated by host, port, scheme, and service type.
5. User selects discovered services or enters manual endpoints.
6. Non-sensitive endpoint/profile data is written to config TOML.
7. Sensitive token/session/API key values are written to secrets TOML with `0600` mode.

Plugin data flow:

1. `PluginManager` loads each entry point.
2. The plugin registration function receives `PluginContext`.
3. Manifest and provided capabilities are recorded.
4. Capability registries reject duplicate names unless explicitly namespaced by different plugins.
5. Plugin load errors are captured and shown in plugin status without breaking unrelated plugins.

## Error Handling

- Built-in core plugin load failures are startup errors.
- Third-party plugin load failures are isolated as `PluginLoadError` records.
- `plugins list` shows disabled/error status for failed plugins.
- Credential file permission problems refuse secret reads and explain the required `0600` permission.
- Discovery network errors are grouped by host or service instead of printed one by one.
- Docker daemon unavailable errors return clear Docker-specific messages and do not affect non-Docker tools.
- External API `401` or `403` responses prompt the user to reconfigure credentials.
- Unverified Lucky API tools remain unavailable rather than pretending to work.
- Compose subprocess failures include command, exit code, and sanitized stderr.

## Documentation Requirements

The implementation must update permanent project documentation, not only code comments.

Required documentation updates:

- `docs/architecture.md`: platform kernel architecture, plugin system, command registry, discovery layer, credential layer.
- `docs/agent-flow.md`: updated execution flow showing registry resolution before `StepRunner` execution.
- `docs/tools.md`: namespace conventions, plugin-provided tools, risk classification, Docker/AList examples.
- `docs/cli.md`: new CLI subcommands and chat slash commands.
- `docs/configuration.md`: app endpoints, plugin state, secrets file path, permission behavior, redaction.
- New discovery documentation if the architecture doc becomes too large, likely `docs/discovery.md`.
- New plugin author guide if needed, likely `docs/plugins.md`.

Architecture diagrams are not required as generated images, but the docs must include readable flow descriptions and examples that make the architecture and data flow clear.

## README Rewrite Requirement

The current README is too sparse for a GitHub open source project. It should be rewritten in a high-star open source style after the platform changes are planned.

README sections should include:

- Clear project tagline and value proposition.
- Feature highlights.
- Current status and roadmap transparency.
- Quick start with `uv` commands.
- Example CLI usage.
- Example chat/slash command usage.
- Plugin system overview.
- Supported integrations table with status labels such as simulator, planned, minimal, experimental.
- Safety model summary.
- Configuration and secrets overview.
- Documentation links.
- Development setup and test commands.
- Contributing guide pointer.
- License/status section if available.

The README should be honest about incomplete integrations. It should not claim production-ready support for APIs that are still unverified.

## Testing Strategy

- Registry tests: duplicate registration, namespace behavior, list/filter, plugin metadata.
- Command tests: same handler callable from CLI and slash command dispatch.
- CredentialStore tests: create file with `0600`, read/write values, redacted summaries, unsafe permission refusal.
- Discovery tests: mDNS/SSDP parsing, vendor probe match logic, timeout handling, error aggregation, deduplication.
- PluginManager tests: built-in plugin loading, mocked entry point loading, failed plugin isolation.
- Docker tests: Docker SDK client mocked; Compose subprocess argument whitelist and confirmation requirement.
- App client tests: AList and Vaultwarden through mock HTTP; Lucky endpoint/token management without unverified API calls.
- CLI smoke tests: `config init` with simulated input, `plugins list`, `apps list`, `tools list`, and chat slash command dispatch.
- Documentation checks: README and docs links should remain valid where practical.

## Implementation Order Recommendation

1. Add platform context and registries.
2. Add credential store and config models.
3. Add command registry and chat slash dispatch.
4. Add plugin manager and built-in plugin registration path.
5. Move existing built-in NAS tools into the built-in plugin path without changing behavior.
6. Add discovery models, protocol scanners, and vendor probe registry.
7. Extend `config init` to use discovery and endpoint persistence.
8. Add Docker SDK and Compose tools.
9. Add AList, Lucky, and Vaultwarden client/tool skeletons.
10. Update architecture, data flow, CLI, tools, configuration, plugin/discovery docs.
11. Rewrite README in GitHub open source style.

## Open Questions Deferred To Implementation

- Exact Lucky API endpoints depend on verified documentation or a target deployment.
- Exact FNOS and Zspace identification rules may need real device pages or community documentation.
- Compose support may require checking user environments for Docker Compose v2 availability.
- Cloudflare should be implemented as a separate plugin after the SDK surface is stable.
