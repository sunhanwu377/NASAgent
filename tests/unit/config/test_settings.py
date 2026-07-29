from pathlib import Path

from nasagent.config.settings import LlmSettings, NasAgentSettings


def test_default_settings_are_safe() -> None:
    settings = NasAgentSettings()

    assert settings.llm.provider == "openai"
    assert settings.safety.allow_auto_write is False
    assert settings.safety.allow_destructive is False
    assert settings.safety.require_confirmation_for == ("delete_file", "upload_file")


def test_run_log_dir_expands_user() -> None:
    settings = NasAgentSettings()

    assert settings.observability.expanded_run_log_dir() == Path("~/.nasagent/runs").expanduser()


def test_llm_settings_include_openai_compatible_endpoint_options() -> None:
    settings = LlmSettings()

    assert settings.api_key is None
    assert settings.base_url is None
