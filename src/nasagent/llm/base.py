from collections.abc import AsyncIterator
from typing import Protocol

from nasagent.llm.messages import ChatMessage


class LlmProvider(Protocol):
    async def complete(self, messages: list[ChatMessage]) -> str:
        raise NotImplementedError

    def stream_complete(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        raise NotImplementedError
