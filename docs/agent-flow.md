# Agent Flow

The flow is context build, planning, plan display, step execution, tool execution, synthesis, and sanitized state persistence.

Each planned step can execute one or more tools. The first phase uses expected tools from the plan as a constrained ReAct-style loop. The safety layer decides whether a tool can execute.

Before a tool is executed, the current agent graph resolves the tool name from its active `ToolRegistry`, which is built with `default_tool_registry()` for normal agent execution. That registry loads built-in tools and `nasagent.plugins` entry-point plugins through the platform plugin path. The planner prompt is generated from the active registry's tool names, then the existing `StepRunner` validates arguments, evaluates `SafetyPolicy`, asks for confirmation when required, and records the trace.
