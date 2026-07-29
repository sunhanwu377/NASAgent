from dataclasses import dataclass


@dataclass(frozen=True)
class UgreenCredentials:
    username: str
    password: str
