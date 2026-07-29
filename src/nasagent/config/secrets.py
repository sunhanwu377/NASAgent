import os
from dataclasses import dataclass


@dataclass(frozen=True)
class SecretValue:
    name: str
    value: str

    def redacted(self) -> str:
        return "********"


def load_env_secret(name: str) -> SecretValue | None:
    value = os.getenv(name)
    if value is None:
        return None
    return SecretValue(name=name, value=value)
