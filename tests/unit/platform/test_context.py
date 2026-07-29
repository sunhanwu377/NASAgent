from nasagent.config.settings import NasAgentSettings
from nasagent.platform.context import create_platform_context


def test_create_platform_context_has_empty_registries() -> None:
    context = create_platform_context(settings=NasAgentSettings())

    assert context.settings.llm.provider == "openai"
    assert context.apps.list() == []
    assert context.commands.list() == []
    assert context.tools.list() == []
