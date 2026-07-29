import json
from pathlib import Path
from typing import Any

from nasagent.agent.state.models import AgentState

SENSITIVE_TERMS = ("password", "secret", "token", "api_key", "apikey", "credential")
REDACTED = "[REDACTED]"


def redact_sensitive_values(value: Any, key: str = "") -> Any:
    key_lower = key.lower()
    if any(term in key_lower for term in SENSITIVE_TERMS):
        return REDACTED
    if isinstance(value, dict):
        return {
            item_key: redact_sensitive_values(item_value, str(item_key))
            for item_key, item_value in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive_values(item) for item in value]
    if isinstance(value, str) and any(term in value.lower() for term in SENSITIVE_TERMS):
        return REDACTED
    return value


class RunStateStore:
    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def save(self, run_id: str, state: AgentState) -> Path:
        self._directory.mkdir(parents=True, exist_ok=True)
        path = self._directory / f"{run_id}.json"
        data = redact_sensitive_values(state.model_dump(mode="json"))
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return path
