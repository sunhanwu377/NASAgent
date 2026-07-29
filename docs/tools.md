# Tools

Tools are registered through `ToolRegistry`. Each tool has a name, description, risk level, async handler, confirmation flag, dry-run capability flag, and adapter capability.

Phase 1 tools include storage status, device status, list files, search files, upload file, download file, and delete file.

Risk levels drive execution gates:

- `read`: safe to run without approval, for status, listing, searching, and downloads.
- `write`: mutates NAS contents, for uploads; defaults to confirmation unless configured otherwise and the tool itself does not require confirmation.
- `destructive`: deletes data; disabled unless safety settings allow the class of operation and an approval provider confirms it.
- `system`: reserved for future device/service changes and not executable in phase 1.

`SafetyPolicy.evaluate()` uses `allowed=True` only when a tool can execute immediately. Confirmation-required tools are not executed unless an `ApprovalProvider` returns `True`.
