from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class UgreenClient:
    base_url: str

    def build_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self.base_url, timeout=30.0)
