from collections.abc import AsyncIterator, Callable
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
        json_object: bool = False,
    ) -> None:
        self._settings = settings
        self._json_object = json_object
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
        kwargs: dict[str, Any] = {
            "model": self._settings.model,
            "messages": cast(Any, [message.to_openai_dict() for message in messages]),
        }
        if self._json_object:
            kwargs["response_format"] = {"type": "json_object"}
        response = await self._client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        return content or ""

    async def stream_complete(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        stream = await self._client.chat.completions.create(
            model=self._settings.model,
            messages=cast(Any, [message.to_openai_dict() for message in messages]),
            stream=True,
        )
        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                yield content
