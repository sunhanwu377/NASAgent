from typing import Protocol

from nasagent.llm.messages import ChatMessage


class LlmProvider(Protocol):
    async def complete(self, messages: list[ChatMessage]) -> str:
        raise NotImplementedError
