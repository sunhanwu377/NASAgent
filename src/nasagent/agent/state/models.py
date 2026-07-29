from pydantic import BaseModel, Field

from nasagent.agent.planning.schemas import Plan
from nasagent.tools.schemas import ToolCallResult


class StepResult(BaseModel):
    step_id: str
    success: bool
    tool_results: list[ToolCallResult] = Field(default_factory=list)
    error: str | None = None


class AgentState(BaseModel):
    goal: str
    plan: Plan | None = None
    step_results: list[StepResult] = Field(default_factory=list)
    final_summary: str = ""
