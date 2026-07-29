import os
from dataclasses import dataclass, field


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
