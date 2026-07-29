from nasagent.config.settings import SafetySettings
from nasagent.safety.policy import SafetyPolicy
from nasagent.safety.risk import RiskLevel
from nasagent.tools.base import ToolDefinition


async def noop() -> None:
    return None


def test_read_tool_is_allowed_without_confirmation() -> None:
    tool = ToolDefinition(
        name="status",
        description="status",
        risk_level=RiskLevel.READ,
        handler=noop,
    )
    decision = SafetyPolicy(SafetySettings()).evaluate(tool)

    assert decision.allowed is True
    assert decision.requires_confirmation is False


def test_destructive_tool_is_blocked_by_default() -> None:
    tool = ToolDefinition(
        name="delete_file",
        description="delete",
        risk_level=RiskLevel.DESTRUCTIVE,
        handler=noop,
    )
    decision = SafetyPolicy(SafetySettings()).evaluate(tool, {"path": "/homes/demo/old.txt"})

    assert decision.allowed is False
    assert decision.requires_confirmation is True


def test_destructive_tool_without_target_args_is_blocked_without_confirmation() -> None:
    tool = ToolDefinition(
        name="delete_file",
        description="delete",
        risk_level=RiskLevel.DESTRUCTIVE,
        handler=noop,
    )
    decision = SafetyPolicy(SafetySettings(allow_destructive=True)).evaluate(tool)

    assert decision.allowed is False
    assert decision.requires_confirmation is False
    assert decision.reason == "unsafe destructive target"


def test_destructive_tool_blocks_ambiguous_targets_even_when_enabled() -> None:
    tool = ToolDefinition(
        name="delete_file",
        description="delete",
        risk_level=RiskLevel.DESTRUCTIVE,
        handler=noop,
    )
    policy = SafetyPolicy(SafetySettings(allow_destructive=True))

    for path in ("/", "//", "/..", "/downloads", "/downloads/..", "/./", "*", "/downloads/*"):
        decision = policy.evaluate(tool, {"path": path})

        assert decision.allowed is False
        assert decision.requires_confirmation is False
        assert decision.approval_allowed is False
        assert decision.reason == "unsafe destructive target"


def test_destructive_tool_allows_concrete_target_for_approval() -> None:
    tool = ToolDefinition(
        name="delete_file",
        description="delete",
        risk_level=RiskLevel.DESTRUCTIVE,
        handler=noop,
    )

    decision = SafetyPolicy(SafetySettings(allow_destructive=True)).evaluate(
        tool, {"path": "/downloads/movie.iso"}
    )

    assert decision.allowed is False
    assert decision.requires_confirmation is True
    assert decision.approval_allowed is True


def test_confirmation_required_write_is_not_allowed_without_approval() -> None:
    tool = ToolDefinition(
        name="upload_file",
        description="upload",
        risk_level=RiskLevel.WRITE,
        handler=noop,
    )
    decision = SafetyPolicy(SafetySettings()).evaluate(tool)

    assert decision.allowed is False
    assert decision.requires_confirmation is True


def test_configured_auto_write_allows_write_without_confirmation() -> None:
    tool = ToolDefinition(
        name="upload_file",
        description="upload",
        risk_level=RiskLevel.WRITE,
        handler=noop,
    )
    settings = SafetySettings(allow_auto_write=True, require_confirmation_for=())
    decision = SafetyPolicy(settings).evaluate(tool)

    assert decision.allowed is True
    assert decision.requires_confirmation is False
