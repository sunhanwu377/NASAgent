from pydantic import BaseModel


class ToolCallResult(BaseModel):
    tool_name: str
    result: dict[str, object]
