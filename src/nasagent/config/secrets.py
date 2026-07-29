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
            lines.append(f"{_format_toml_string(key)} = {_format_toml_string(str(data[key]))}")
        content = "\n".join(lines) + "\n"
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(self.path, flags, 0o600)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                fd = -1
                handle.write(content)
        finally:
            if fd != -1:
                os.close(fd)


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
