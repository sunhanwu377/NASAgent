from pydantic import BaseModel


class PlanStep(BaseModel):
    id: str
    description: str
    risk: str
    expected_tools: list[str]


class Plan(BaseModel):
    goal: str
    steps: list[PlanStep]
