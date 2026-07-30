from fastapi.testclient import TestClient

from nasagent.web.server import create_app


def test_health_endpoint():
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_page_returns_html():
    client = TestClient(create_app())
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "NASAgent" in response.text


def test_settings_page_returns_html():
    client = TestClient(create_app())
    response = client.get("/settings")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_settings_llm_page():
    client = TestClient(create_app())
    response = client.get("/settings/llm")
    assert response.status_code == 200


def test_settings_safety_page():
    client = TestClient(create_app())
    response = client.get("/settings/safety")
    assert response.status_code == 200


def test_settings_apps_page():
    client = TestClient(create_app())
    response = client.get("/settings/apps")
    assert response.status_code == 200


def test_static_files_served():
    client = TestClient(create_app())
    response = client.get("/static/style.css")
    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]
