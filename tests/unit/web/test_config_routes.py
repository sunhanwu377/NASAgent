from fastapi.testclient import TestClient

from nasagent.web.server import create_app


def test_config_api_show():
    client = TestClient(create_app())
    response = client.get("/settings/api/config/show")
    assert response.status_code == 200


def test_config_llm_post():
    client = TestClient(create_app())
    response = client.post(
        "/settings/api/config/llm",
        data={
            "provider": "openai",
            "model": "gpt-4.1-mini",
            "api_key": "test-key",
            "base_url": "https://api.openai.com/v1",
        },
    )
    assert response.status_code == 200


def test_config_safety_post():
    client = TestClient(create_app())
    response = client.post(
        "/settings/api/config/safety",
        data={
            "default_mode": "confirm_destructive",
            "allow_auto_write": "on",
        },
    )
    assert response.status_code == 200


def test_config_app_add():
    client = TestClient(create_app())
    response = client.post(
        "/settings/api/config/app/add",
        data={
            "name": "test_alist",
            "app_type": "alist",
            "base_url": "http://localhost:5244",
        },
    )
    assert response.status_code == 200
