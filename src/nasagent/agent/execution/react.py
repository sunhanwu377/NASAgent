from pydantic import BaseModel, Field

MAX_REACT_ITERATIONS = 5


class ReActIteration(BaseModel):
    thought: str
    action: str
    observation: dict[str, object]


class ReActTrace(BaseModel):
    max_iterations: int = MAX_REACT_ITERATIONS
    iterations: list[ReActIteration] = Field(default_factory=list)
