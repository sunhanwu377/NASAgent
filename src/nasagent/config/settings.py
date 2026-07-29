from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LlmSettings(BaseModel):
    provider: str = "openai"
    model: str = "gpt-4.1-mini"


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


class NasAgentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NASAGENT_", env_nested_delimiter="__")

    llm: LlmSettings = Field(default_factory=LlmSettings)
    safety: SafetySettings = Field(default_factory=SafetySettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)
