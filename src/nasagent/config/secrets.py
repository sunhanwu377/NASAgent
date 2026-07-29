import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SecretValue:
    name: str
    value: str = field(repr=False)

    def __repr__(self) -> str:
        return f"SecretValue(name={self.name!r}, value={self.redacted()!r})"

    def redacted(self) -> str:
        return "********"


def load_env_secret(name: str) -> SecretValue | None:
    value = os.getenv(name)
    if value is None:
        return None
    return SecretValue(name=name, value=value)


class CredentialFilePermissionError(RuntimeError):
    pass


def default_secrets_path() -> Path:
    return Path.home() / ".local" / "share" / "nasagent" / "secrets.toml"


class CredentialStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_secrets_path()

    def get(self, key: str) -> str | None:
        data = self._read()
        value = data.get(key)
        if value is None:
            return None
        return str(value)

    def set(self, key: str, value: str) -> None:
        data = self._read(allow_missing=True)
        data[key] = value
        self._write(data)

    def redacted_summary(self) -> dict[str, str]:
        return {key: "********" for key in self._read(allow_missing=True)}

    def _read(self, *, allow_missing: bool = False) -> dict[str, Any]:
        if not self.path.exists():
            if allow_missing:
                return {}
            return {}
        mode = self.path.stat().st_mode & 0o777
        if mode != 0o600:
            raise CredentialFilePermissionError(f"Secrets file {self.path} must be 0600")
        with self.path.open("rb") as handle:
            parsed = tomllib.load(handle)
        secrets = parsed.get("secrets", {})
        if not isinstance(secrets, dict):
            return {}
        return dict(secrets)

    def _write(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lines = ["[secrets]"]
        for key in sorted(data):
            escaped_key = key.replace('"', '\\"')
            escaped_value = str(data[key]).replace('"', '\\"')
            lines.append(f'"{escaped_key}" = "{escaped_value}"')
        self.path.write_text("\n".join(lines) + "\n")
        os.chmod(self.path, 0o600)
