import pytest

from nasagent.platform.apps import AppEndpoint, AppRegistry


def test_app_registry_registers_and_lists_endpoint() -> None:
    registry = AppRegistry()
    endpoint = AppEndpoint(
        name="home",
        app_type="alist",
        base_url="http://nas.local:5244",
        credential_key="alist.home.token",
    )

    registry.register(endpoint)

    assert registry.get("home") == endpoint
    assert registry.list(app_type="alist") == [endpoint]


def test_app_registry_rejects_duplicate_name() -> None:
    registry = AppRegistry()
    endpoint = AppEndpoint(name="home", app_type="alist", base_url="http://example.test")
    registry.register(endpoint)

    with pytest.raises(ValueError, match="App endpoint already registered: home"):
        registry.register(endpoint)
