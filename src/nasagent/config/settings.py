import tomllib
from pathlib import Path
from typing import Any, cast

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, EnvSettingsSource, SettingsConfigDict

DEFAULT_CONFIG_PATH = Path("~/.config/nasagent/config.toml")


class LlmSettings(BaseModel):
    provider: str = "openai"
    model: str = "gpt-4.1-mini"
    api_key: str | None = None
    base_url: str | None = None


class SafetySettings(BaseModel):
    default_mode: str = "confirm_destructive"
    allow_auto_write: bool = False
    allow_destructive: bool = False
    require_confirmation_for: tuple[str, ...] = ("delete_file", "upload_file")


class ObservabilitySettings(BaseModel):
    run_log_dir: str = "~/.nasagent/runs"
    redact_sensitive: bool = True

    def expanded_run_log_dir(self) -> Path:
        return Path(self.run_log_dir).expanduser()


class AppEndpointSettings(BaseModel):
    app_type: str
    base_url: str
    credential_key: str | None = None
    frontend_url: str | None = None
    notes: str | None = None


class PluginSettings(BaseModel):
    enabled: bool = True


class NasAgentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NASAGENT_", env_nested_delimiter="__")

    llm: LlmSettings = Field(default_factory=LlmSettings)
    safety: SafetySettings = Field(default_factory=SafetySettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)
    apps: dict[str, AppEndpointSettings] = Field(default_factory=dict)
    plugins: dict[str, PluginSettings] = Field(default_factory=dict)


def default_config_path() -> Path:
    return DEFAULT_CONFIG_PATH.expanduser()


def load_config_file(path: Path | None = None) -> dict[str, object]:
    config_path = path or default_config_path()
    if not config_path.exists():
        return {}
    with config_path.open("rb") as config_file:
        return tomllib.load(config_file)


def load_settings(path: Path | None = None) -> NasAgentSettings:
    data = load_config_file(path)
    _merge_dict(data, EnvSettingsSource(NasAgentSettings)())
    return NasAgentSettings.model_validate(data)


def settings_to_toml_data(settings: NasAgentSettings, *, redact: bool = False) -> dict[str, object]:
    data = settings.model_dump(mode="python", exclude={"apps", "plugins"})
    if redact and data["llm"].get("api_key"):
        data["llm"]["api_key"] = "********"
    if settings.apps:
        data["apps"] = {
            name: endpoint.model_dump(exclude_none=True) for name, endpoint in settings.apps.items()
        }
    if settings.plugins:
        data["plugins"] = {
            name: plugin.model_dump(exclude_none=True) for name, plugin in settings.plugins.items()
        }
    return cast(dict[str, object], _drop_none(data))


def render_toml(data: dict[str, object]) -> str:
    lines: list[str] = []
    _append_toml_sections(lines, (), data)
    return "\n".join(lines) + "\n"


def _append_toml_sections(
    lines: list[str], prefix: tuple[str, ...], values: dict[str, object]
) -> None:
    scalar_items = {key: value for key, value in values.items() if not isinstance(value, dict)}
    nested_items = {key: value for key, value in values.items() if isinstance(value, dict)}

    if prefix and (scalar_items or not nested_items):
        if lines:
            lines.append("")
        lines.append(f"[{_format_toml_section_path(prefix)}]")
        for key, value in scalar_items.items():
            lines.append(f"{_format_toml_key(key)} = {_format_toml_value(value)}")

    for key, value in nested_items.items():
        _append_toml_sections(lines, (*prefix, key), value)


def _drop_none(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _drop_none(item) for key, item in value.items() if item is not None}
    if isinstance(value, tuple):
        return tuple(_drop_none(item) for item in value)
    if isinstance(value, list):
        return [_drop_none(item) for item in value]
    return value


def _merge_dict(target: dict[str, object], source: dict[str, object]) -> None:
    for key, value in source.items():
        current = target.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            _merge_dict(current, value)
        else:
            target[key] = value


def _format_toml_value(value: object) -> str:
    if isinstance(value, str):
        return _format_toml_string(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    if isinstance(value, tuple | list):
        return "[" + ", ".join(_format_toml_value(item) for item in value) + "]"
    raise TypeError(f"Unsupported TOML value: {value!r}")


def _format_toml_section_path(parts: tuple[str, ...]) -> str:
    return ".".join(_format_toml_key(part) for part in parts)


def _format_toml_key(value: str) -> str:
    if value and all(char.isalnum() or char in "_-" for char in value):
        return value
    return _format_toml_string(value)


def _format_toml_string(value: str) -> str:
    escaped: list[str] = []
    for char in value:
        if char == "\\":
            escaped.append("\\\\")
        elif char == '"':
            escaped.append('\\"')
        elif char == "\b":
            escaped.append("\\b")
        elif char == "\t":
            escaped.append("\\t")
        elif char == "\n":
            escaped.append("\\n")
        elif char == "\f":
            escaped.append("\\f")
        elif char == "\r":
            escaped.append("\\r")
        elif ord(char) < 0x20 or ord(char) == 0x7F:
            escaped.append(f"\\u{ord(char):04x}")
        else:
            escaped.append(char)
    return '"' + "".join(escaped) + '"'
