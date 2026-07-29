# Agent Flow

The flow is context build, planning, plan display, step execution, tool execution, synthesis, and sanitized state persistence.

Each planned step can execute one or more tools. The first phase uses expected tools from the plan as a constrained ReAct-style loop. The safety layer decides whether a tool can execute.

Before a tool is executed, the current agent graph resolves the tool name from its active `ToolRegistry`, which is built with `default_tool_registry()` for normal agent execution. The existing `StepRunner` validates arguments, evaluates `SafetyPolicy`, asks for confirmation when required, and records the trace. Platform plugin tools are registered for platform CLI and chat slash-command surfaces today; wiring those platform-registered tools directly into planner-selected agent execution is a future integration point unless the caller explicitly supplies that registry.
