from collections.abc import Callable
from typing import Any, cast

from openai import AsyncOpenAI

from nasagent.config.settings import LlmSettings
from nasagent.llm.messages import ChatMessage


class OpenAiProvider:
    def __init__(
        self,
        settings: LlmSettings,
        client: AsyncOpenAI | None = None,
        client_factory: Callable[..., AsyncOpenAI] = AsyncOpenAI,
    ) -> None:
        self._settings = settings
        client_kwargs = {
            key: value
            for key, value in {
                "api_key": settings.api_key,
                "base_url": settings.base_url,
            }.items()
            if value is not None
        }
        self._client = client or client_factory(**client_kwargs)

    async def complete(self, messages: list[ChatMessage]) -> str:
        response = await self._client.chat.completions.create(
            model=self._settings.model,
            messages=cast(Any, [message.to_openai_dict() for message in messages]),
        )
        content = response.choices[0].message.content
        return content or ""
