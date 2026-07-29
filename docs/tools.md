# Tools

Tools are registered through `ToolRegistry`. Each tool has a name, description, risk level, async handler, confirmation flag, dry-run capability flag, and adapter capability.

The agent graph still builds its default registry with `default_tool_registry()`, which delegates built-in NAS tool registration to `register_builtin_nas_tools()`. This preserves the existing tool names used by planner output, such as `get_storage_status` and `upload_file`.

The platform plugin path uses the same registration helper from the built-in plugin. Loading `PluginManager.load_builtin()` registers the same built-in NAS tools into `PlatformContext.tools`, adds dotted aliases for `device.status` and `storage.status`, registers Docker container/image/network/volume and Compose tool definitions, registers minimal AList and Vaultwarden tool definitions, and records the `builtin` plugin manifest. This path is available for platform code that creates a `PlatformContext`; it is not automatically invoked by agent graph startup yet.

Phase 1 tools include storage status, device status, list files, search files, upload file, download file, delete file, Docker tool definitions, AList tool definitions, and a Vaultwarden users-list definition for planning and safety handling. Docker, AList, and Vaultwarden handlers are placeholders until endpoint-backed integration is wired in.

Docker Compose helpers build `docker compose` calls as explicit subprocess argument lists and do not invoke a shell. Compose file arguments must be relative paths and must not contain `..` traversal segments; absolute paths are rejected before argv construction.

Risk levels drive execution gates:

- `read`: safe to run without approval, for status, listing, searching, and downloads.
- `write`: mutates NAS contents, for uploads; defaults to confirmation unless configured otherwise and the tool itself does not require confirmation.
- `destructive`: deletes data; disabled unless safety settings allow the class of operation and an approval provider confirms it.
- `system`: reserved for device/service changes. Docker Compose config/up/down tools use this risk level and require confirmation.

AList currently exposes `alist.auth.login`, `alist.fs.list`, `alist.fs.get`, `alist.fs.mkdir`, `alist.fs.upload`, and `alist.fs.remove` tool definitions. Vaultwarden currently exposes `vaultwarden.users.list`. Lucky has a client skeleton for endpoint/token storage but no tool definitions until verified API behavior is added.

`SafetyPolicy.evaluate()` uses `allowed=True` only when a tool can execute immediately. Confirmation-required tools are not executed unless an `ApprovalProvider` returns `True`.
