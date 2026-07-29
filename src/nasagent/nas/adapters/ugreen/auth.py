from dataclasses import dataclass, field


@dataclass(frozen=True)
class UgreenCredentials:
    username: str
    password: str = field(repr=False)

    def __repr__(self) -> str:
        return f"UgreenCredentials(username={self.username!r}, password='[REDACTED]')"
