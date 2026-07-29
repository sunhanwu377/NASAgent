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
