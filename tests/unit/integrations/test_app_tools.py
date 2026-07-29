from nasagent.integrations.alist.tools import alist_tool_definitions
from nasagent.integrations.vaultwarden.tools import vaultwarden_tool_definitions


def test_alist_tool_definitions_are_namespaced() -> None:
    names = {tool.name for tool in alist_tool_definitions()}

    assert {
        "alist.auth.login",
        "alist.fs.list",
        "alist.fs.get",
        "alist.fs.mkdir",
        "alist.fs.upload",
        "alist.fs.remove",
    }.issubset(names)


def test_vaultwarden_tool_definitions_are_namespaced() -> None:
    names = {tool.name for tool in vaultwarden_tool_definitions()}

    assert "vaultwarden.users.list" in names
