from nasagent.config.profiles import NasProfile, ProfileStore


def test_profile_store_returns_named_profile() -> None:
    profile = NasProfile(name="simulator", adapter="simulator")
    store = ProfileStore(profiles={"simulator": profile}, default_profile="simulator")

    assert store.get("simulator") == profile
    assert store.default() == profile


def test_missing_profile_raises_key_error() -> None:
    store = ProfileStore(profiles={}, default_profile=None)

    try:
        store.get("missing")
    except KeyError as exc:
        assert "Unknown NAS profile: missing" in str(exc)
    else:
        raise AssertionError("expected KeyError")
