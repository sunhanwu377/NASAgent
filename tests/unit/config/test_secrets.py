from nasagent.config.secrets import SecretValue


def test_secret_value_repr_redacts_secret() -> None:
    secret = SecretValue(name="NASAGENT_API_KEY", value="super-secret-token")

    rendered = repr(secret)

    assert "super-secret-token" not in rendered
    assert "********" in rendered
