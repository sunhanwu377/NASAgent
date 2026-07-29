import os
import tomllib
from pathlib import Path

import pytest

from nasagent.config.secrets import CredentialFilePermissionError, CredentialStore, SecretValue


def test_secret_value_repr_redacts_secret() -> None:
    secret = SecretValue(name="NASAGENT_API_KEY", value="super-secret-token")

    rendered = repr(secret)

    assert "super-secret-token" not in rendered
    assert "********" in rendered


def test_credential_store_writes_file_with_0600(tmp_path: Path) -> None:
    path = tmp_path / "secrets.toml"
    store = CredentialStore(path)

    store.set("alist.home.token", "secret-token")

    assert store.get("alist.home.token") == "secret-token"
    assert oct(path.stat().st_mode & 0o777) == "0o600"


def test_credential_store_creates_new_file_securely_without_chmod(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "secrets.toml"
    store = CredentialStore(path)

    def fail_chmod(_path: Path, _mode: int) -> None:
        raise AssertionError(
            "new secrets files must be created with 0600, not chmodded after write"
        )

    monkeypatch.setattr(os, "chmod", fail_chmod)

    store.set("alist.home.token", "secret-token")

    assert store.get("alist.home.token") == "secret-token"
    assert oct(path.stat().st_mode & 0o777) == "0o600"


def test_credential_store_round_trips_toml_sensitive_keys_and_values(tmp_path: Path) -> None:
    path = tmp_path / "secrets.toml"
    store = CredentialStore(path)
    key = 'alist."home".token\\name'
    value = 'quote:" backslash:\\ newline:\n tab:\t nul:\0 end'

    store.set(key, value)

    assert store.get(key) == value
    assert tomllib.loads(path.read_text(encoding="utf-8"))["secrets"][key] == value


def test_credential_store_redacted_summary_hides_values(tmp_path: Path) -> None:
    path = tmp_path / "secrets.toml"
    store = CredentialStore(path)
    store.set("alist.home.token", "secret-token")

    summary = store.redacted_summary()

    assert summary == {"alist.home.token": "********"}
    assert "secret-token" not in repr(summary)


def test_credential_store_refuses_unsafe_permissions(tmp_path: Path) -> None:
    path = tmp_path / "secrets.toml"
    path.write_text('[secrets]\n"alist.home.token" = "secret-token"\n')
    os.chmod(path, 0o644)

    store = CredentialStore(path)

    with pytest.raises(CredentialFilePermissionError, match="must be 0600"):
        store.get("alist.home.token")
