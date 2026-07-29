from dataclasses import dataclass


@dataclass(frozen=True)
class AppEndpoint:
    name: str
    app_type: str
    base_url: str
    credential_key: str | None = None
    frontend_url: str | None = None
    notes: str | None = None


class AppRegistry:
    def __init__(self) -> None:
        self._apps: dict[str, AppEndpoint] = {}

    def register(self, endpoint: AppEndpoint) -> None:
        if endpoint.name in self._apps:
            raise ValueError(f"App endpoint already registered: {endpoint.name}")
        self._apps[endpoint.name] = endpoint

    def get(self, name: str) -> AppEndpoint | None:
        return self._apps.get(name)

    def list(self, *, app_type: str | None = None) -> list[AppEndpoint]:
        endpoints = list(self._apps.values())
        if app_type is not None:
            return [endpoint for endpoint in endpoints if endpoint.app_type == app_type]
        return endpoints
