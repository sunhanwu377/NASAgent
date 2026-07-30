from pathlib import Path

from fastapi.testclient import TestClient

from nasagent.web.routes.config_api import get_config_path
from nasagent.web.server import create_app


def _make_client(tmp_dir: Path):
    tmp_config = tmp_dir / "config.toml"
    app = create_app()
    app.dependency_overrides[get_config_path] = lambda: tmp_config
    return TestClient(app), tmp_config


def test_config_api_show(tmp_path):
    client, _ = _make_client(tmp_path)
    response = client.get("/settings/api/config/show")
    assert response.status_code == 200


def test_config_llm_post(tmp_path):
    client, config_path = _make_client(tmp_path)
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
    assert config_path.exists()
    content = config_path.read_text()
    assert "openai" in content


def test_config_safety_post(tmp_path):
    client, config_path = _make_client(tmp_path)
    response = client.post(
        "/settings/api/config/safety",
        data={
            "default_mode": "strict",
            "allow_auto_write": "on",
        },
    )
    assert response.status_code == 200
    assert config_path.exists()
    content = config_path.read_text()
    assert "strict" in content


def test_config_app_add(tmp_path):
    client, config_path = _make_client(tmp_path)
    response = client.post(
        "/settings/api/config/app/add",
        data={
            "name": "test_alist",
            "app_type": "alist",
            "base_url": "http://localhost:5244",
        },
    )
    assert response.status_code == 200
    assert config_path.exists()
    content = config_path.read_text()
    assert "test_alist" in content
