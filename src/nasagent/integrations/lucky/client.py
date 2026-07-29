from dataclasses import dataclass


@dataclass(frozen=True)
class LuckyClient:
    base_url: str
    token: str | None = None

    def is_configured(self) -> bool:
        return bool(self.base_url)
