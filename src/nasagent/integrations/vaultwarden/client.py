from dataclasses import dataclass


@dataclass(frozen=True)
class VaultwardenClient:
    base_url: str
    admin_token: str | None = None
