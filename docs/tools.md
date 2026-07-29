# Tools

Tools are registered through `ToolRegistry`. Each tool has a name, description, risk level, async handler, confirmation flag, dry-run capability flag, and adapter capability.

The agent graph still builds its default registry with `default_tool_registry()`, which delegates built-in NAS tool registration to `register_builtin_nas_tools()`. This preserves the existing tool names used by planner output, such as `get_storage_status` and `upload_file`.

The platform plugin path uses the same registration helper from the built-in plugin. Loading `PluginManager.load_builtin()` registers the same built-in NAS tools into `PlatformContext.tools`, adds dotted aliases for `device.status` and `storage.status`, and records the `builtin` plugin manifest. This path is available for platform code that creates a `PlatformContext`; it is not automatically invoked by agent graph startup yet.

Phase 1 tools include storage status, device status, list files, search files, upload file, download file, and delete file.

Risk levels drive execution gates:

- `read`: safe to run without approval, for status, listing, searching, and downloads.
- `write`: mutates NAS contents, for uploads; defaults to confirmation unless configured otherwise and the tool itself does not require confirmation.
- `destructive`: deletes data; disabled unless safety settings allow the class of operation and an approval provider confirms it.
- `system`: reserved for future device/service changes and not executable in phase 1.

`SafetyPolicy.evaluate()` uses `allowed=True` only when a tool can execute immediately. Confirmation-required tools are not executed unless an `ApprovalProvider` returns `True`.
