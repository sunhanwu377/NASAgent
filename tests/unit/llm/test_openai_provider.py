from typing import Any, cast

from openai import AsyncOpenAI

from nasagent.config.settings import LlmSettings
from nasagent.llm.openai_provider import OpenAiProvider


def test_openai_provider_passes_configured_auth_and_endpoint_to_client_factory() -> None:
    captured_kwargs: dict[str, Any] = {}

    def client_factory(**kwargs: Any) -> AsyncOpenAI:
        captured_kwargs.update(kwargs)
        return cast(AsyncOpenAI, object())

    OpenAiProvider(
        settings=LlmSettings(
            api_key="test-key",
            base_url="https://openai-compatible.example/v1",
        ),
        client_factory=client_factory,
    )

    assert captured_kwargs == {
        "api_key": "test-key",
        "base_url": "https://openai-compatible.example/v1",
    }


def test_openai_provider_requests_json_object_responses() -> None:
    class FakeCompletions:
        def __init__(self) -> None:
            self.kwargs: dict[str, Any] = {}

        async def create(self, **kwargs: Any) -> object:
            self.kwargs.update(kwargs)

            class Message:
                content = "{}"

            class Choice:
                message = Message()

            class Response:
                choices = [Choice()]

            return Response()

    class FakeChat:
        def __init__(self) -> None:
            self.completions = FakeCompletions()

    class FakeClient:
        def __init__(self) -> None:
            self.chat = FakeChat()

    client = FakeClient()
    provider = OpenAiProvider(
        settings=LlmSettings(), client=cast(AsyncOpenAI, client), json_object=True
    )

    import asyncio

    asyncio.run(provider.complete([]))

    assert client.chat.completions.kwargs["response_format"] == {"type": "json_object"}


def test_openai_provider_uses_text_responses_by_default() -> None:
    class FakeCompletions:
        def __init__(self) -> None:
            self.kwargs: dict[str, Any] = {}

        async def create(self, **kwargs: Any) -> object:
            self.kwargs.update(kwargs)

            class Message:
                content = "hello"

            class Choice:
                message = Message()

            class Response:
                choices = [Choice()]

            return Response()

    class FakeChat:
        def __init__(self) -> None:
            self.completions = FakeCompletions()

    class FakeClient:
        def __init__(self) -> None:
            self.chat = FakeChat()

    client = FakeClient()
    provider = OpenAiProvider(settings=LlmSettings(), client=cast(AsyncOpenAI, client))

    import asyncio

    asyncio.run(provider.complete([]))

    assert "response_format" not in client.chat.completions.kwargs


def test_openai_provider_streams_text_chunks() -> None:
    class Delta:
        def __init__(self, content: str | None) -> None:
            self.content = content

    class Choice:
        def __init__(self, content: str | None) -> None:
            self.delta = Delta(content)

    class Chunk:
        def __init__(self, content: str | None) -> None:
            self.choices = [Choice(content)]

    class FakeStream:
        def __init__(self) -> None:
            self._chunks = iter([Chunk("hel"), Chunk(None), Chunk("lo")])

        def __aiter__(self):  # type: ignore[no-untyped-def]
            return self

        async def __anext__(self):  # type: ignore[no-untyped-def]
            try:
                return next(self._chunks)
            except StopIteration as exc:
                raise StopAsyncIteration from exc

    class FakeCompletions:
        def __init__(self) -> None:
            self.kwargs: dict[str, Any] = {}

        async def create(self, **kwargs: Any) -> object:
            self.kwargs.update(kwargs)
            return FakeStream()

    class FakeChat:
        def __init__(self) -> None:
            self.completions = FakeCompletions()

    class FakeClient:
        def __init__(self) -> None:
            self.chat = FakeChat()

    async def collect() -> list[str]:
        return [chunk async for chunk in provider.stream_complete([])]

    client = FakeClient()
    provider = OpenAiProvider(settings=LlmSettings(), client=cast(AsyncOpenAI, client))

    import asyncio

    chunks = asyncio.run(collect())

    assert chunks == ["hel", "lo"]
    assert client.chat.completions.kwargs["stream"] is True
    assert "response_format" not in client.chat.completions.kwargs
