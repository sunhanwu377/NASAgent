# Agent Flow

The flow is context build, planning, plan display, step execution, tool execution, synthesis, and sanitized state persistence.

Each planned step can execute one or more tools. The first phase uses expected tools from the plan as a constrained ReAct-style loop. The safety layer decides whether a tool can execute.

Before a tool is executed, NASAgent resolves the tool name from the active platform tool registry. The existing `StepRunner` still validates arguments, evaluates `SafetyPolicy`, asks for confirmation when required, and records the trace.
