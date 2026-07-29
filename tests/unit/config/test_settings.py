import tomllib
from pathlib import Path

from nasagent.config.settings import (
    LlmSettings,
    NasAgentSettings,
    load_config_file,
    load_settings,
    render_toml,
    settings_to_toml_data,
)


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


def test_load_config_file_reads_toml(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        '[llm]\nmodel = "gpt-4o-mini"\n\n[observability]\nrun_log_dir = "/tmp/nasagent"\n',
        encoding="utf-8",
    )

    data = load_config_file(config_path)

    assert data == {
        "llm": {"model": "gpt-4o-mini"},
        "observability": {"run_log_dir": "/tmp/nasagent"},
    }


def test_load_config_file_returns_empty_dict_when_missing(tmp_path: Path) -> None:
    assert load_config_file(tmp_path / "missing.toml") == {}


def test_load_settings_uses_config_file_values(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        '[llm]\nprovider = "openai"\nmodel = "gpt-4o-mini"\napi_key = "file-key"\n',
        encoding="utf-8",
    )

    settings = load_settings(config_path)

    assert settings.llm.provider == "openai"
    assert settings.llm.model == "gpt-4o-mini"
    assert settings.llm.api_key == "file-key"


def test_environment_overrides_config_file_values(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    config_path = tmp_path / "config.toml"
    config_path.write_text('[llm]\nmodel = "file-model"\n', encoding="utf-8")
    monkeypatch.setenv("NASAGENT_LLM__MODEL", "env-model")

    settings = load_settings(config_path)

    assert settings.llm.model == "env-model"


def test_settings_to_toml_data_omits_unset_optional_values() -> None:
    settings = NasAgentSettings(llm=LlmSettings(api_key=None, base_url=None))

    data = settings_to_toml_data(settings)

    assert data["llm"] == {"provider": "openai", "model": "gpt-4.1-mini"}


def test_settings_to_toml_data_redacts_api_key() -> None:
    settings = NasAgentSettings(llm=LlmSettings(api_key="secret-api-key"))

    data = settings_to_toml_data(settings, redact=True)

    assert data["llm"]["api_key"] == "********"


def test_render_toml_outputs_sections_and_arrays() -> None:
    output = render_toml(
        {
            "llm": {"provider": "openai", "model": "gpt-4.1-mini"},
            "safety": {"require_confirmation_for": ("delete_file", "upload_file")},
        }
    )

    assert "[llm]" in output
    assert 'provider = "openai"' in output
    assert "[safety]" in output
    assert 'require_confirmation_for = ["delete_file", "upload_file"]' in output


def test_render_toml_escapes_common_control_characters() -> None:
    value = "nul:\0 backspace:\b formfeed:\f newline:\n carriage:\r tab:\t end"

    output = render_toml({"llm": {"model": value}})

    assert (
        'model = "nul:\\u0000 backspace:\\b formfeed:\\f newline:\\n carriage:\\r tab:\\t end"'
        in output
    )
    assert tomllib.loads(output)["llm"]["model"] == value
