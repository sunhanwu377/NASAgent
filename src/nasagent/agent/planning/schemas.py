from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    id: str
    description: str
    risk: str
    expected_tools: list[str]
    tool_args: dict[str, dict[str, object]] = Field(default_factory=dict)


class Plan(BaseModel):
    goal: str
    steps: list[PlanStep]
