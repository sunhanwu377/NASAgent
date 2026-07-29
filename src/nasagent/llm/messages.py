from typing import Literal

from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: Literal["system", "developer", "user", "assistant"]
    content: str

    def to_openai_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}
