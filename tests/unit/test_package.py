import nasagent


def test_package_has_version() -> None:
    assert isinstance(nasagent.__version__, str)
    assert nasagent.__version__ == "0.1.0"
