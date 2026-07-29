import pytest

from nasagent.agent.execution.react import MAX_REACT_ITERATIONS
from nasagent.agent.execution.step_runner import StepRunner
from nasagent.agent.planning.schemas import PlanStep
from nasagent.config.settings import SafetySettings
from nasagent.nas.adapters.simulator.adapter import SimulatorNasAdapter
from nasagent.safety.approvals import ApprovalProvider
from nasagent.safety.policy import SafetyPolicy
from nasagent.safety.risk import RiskLevel
from nasagent.tools.base import ToolContext, ToolDefinition
from nasagent.tools.nas.file_management import delete_file_tool, list_files_tool, upload_file_tool
from nasagent.tools.nas.storage import get_storage_status_tool
from nasagent.tools.registry import ToolRegistry


async def echo_path(context: ToolContext, path: str) -> dict[str, object]:
    return {"path": path, "adapter": context.adapter.__class__.__name__}


class StaticApprovalProvider(ApprovalProvider):
    def __init__(self, approved: bool) -> None:
        self.approved = approved
        self.messages: list[str] = []

    def confirm(self, message: str) -> bool:
        self.messages.append(message)
        return self.approved


@pytest.mark.asyncio
async def test_step_runner_executes_expected_read_tool() -> None:
    registry = ToolRegistry()
    registry.register(get_storage_status_tool)
    runner = StepRunner(registry=registry, safety_policy=SafetyPolicy(SafetySettings()))
    step = PlanStep(
        id="s1",
        description="Get storage",
        risk="read",
        expected_tools=["get_storage_status"],
    )

    result = await runner.run_step(step, ToolContext(adapter=SimulatorNasAdapter()))

    assert result.step_id == "s1"
    assert result.success is True
    assert result.tool_results[0].tool_name == "get_storage_status"


@pytest.mark.asyncio
async def test_step_runner_does_not_execute_confirmation_required_tool() -> None:
    registry = ToolRegistry()
    registry.register(upload_file_tool)
    runner = StepRunner(registry=registry, safety_policy=SafetyPolicy(SafetySettings()))
    step = PlanStep(
        id="s1",
        description="Upload file",
        risk="write",
        expected_tools=["upload_file"],
        tool_args={"upload_file": {"local_path": "/tmp/source", "remote_path": "/upload/source"}},
    )
    adapter = SimulatorNasAdapter()

    result = await runner.run_step(step, ToolContext(adapter=adapter))

    assert result.success is False
    assert result.tool_results == []
    assert result.error is not None
    assert "confirmation required" in result.error
    assert await adapter.list_files("/upload") == []


@pytest.mark.asyncio
async def test_step_runner_does_not_execute_when_approval_denied() -> None:
    registry = ToolRegistry()
    registry.register(upload_file_tool)
    approval_provider = StaticApprovalProvider(approved=False)
    runner = StepRunner(
        registry=registry,
        safety_policy=SafetyPolicy(SafetySettings(allow_auto_write=True)),
        approval_provider=approval_provider,
    )
    step = PlanStep(
        id="s1",
        description="Upload file",
        risk="write",
        expected_tools=["upload_file"],
        tool_args={"upload_file": {"local_path": "/tmp/source", "remote_path": "/upload/source"}},
    )
    adapter = SimulatorNasAdapter()

    result = await runner.run_step(step, ToolContext(adapter=adapter))

    assert result.success is False
    assert result.error == "approval denied for tool: upload_file"
    assert approval_provider.messages == [
        "Execute upload_file? Risk: write Target: "
        "local_path=/tmp/source, remote_path=/upload/source"
    ]
    assert await adapter.list_files("/upload") == []


@pytest.mark.asyncio
async def test_step_runner_executes_when_approval_granted() -> None:
    registry = ToolRegistry()
    registry.register(upload_file_tool)
    runner = StepRunner(
        registry=registry,
        safety_policy=SafetyPolicy(SafetySettings(allow_auto_write=True)),
        approval_provider=StaticApprovalProvider(approved=True),
    )
    step = PlanStep(
        id="s1",
        description="Upload file",
        risk="write",
        expected_tools=["upload_file"],
        tool_args={"upload_file": {"local_path": "/tmp/source", "remote_path": "/upload/source"}},
    )
    adapter = SimulatorNasAdapter()

    result = await runner.run_step(step, ToolContext(adapter=adapter))

    assert result.success is True
    assert result.tool_results[0].tool_name == "upload_file"
    assert [file.path for file in await adapter.list_files("/upload")] == ["/upload/source"]


@pytest.mark.asyncio
async def test_step_runner_blocks_destructive_root_target_even_when_approved() -> None:
    registry = ToolRegistry()
    registry.register(delete_file_tool)
    approval_provider = StaticApprovalProvider(approved=True)
    runner = StepRunner(
        registry=registry,
        safety_policy=SafetyPolicy(SafetySettings(allow_destructive=True)),
        approval_provider=approval_provider,
    )
    step = PlanStep(
        id="s1",
        description="Delete root",
        risk="destructive",
        expected_tools=["delete_file"],
        tool_args={"delete_file": {"path": "/"}},
    )

    result = await runner.run_step(step, ToolContext(adapter=SimulatorNasAdapter()))

    assert result.success is False
    assert result.tool_results == []
    assert result.error is not None
    assert "unsafe destructive target" in result.error
    assert approval_provider.messages == []


@pytest.mark.asyncio
async def test_step_runner_blocks_destructive_top_level_target_even_when_approved() -> None:
    registry = ToolRegistry()
    registry.register(delete_file_tool)
    approval_provider = StaticApprovalProvider(approved=True)
    runner = StepRunner(
        registry=registry,
        safety_policy=SafetyPolicy(SafetySettings(allow_destructive=True)),
        approval_provider=approval_provider,
    )
    step = PlanStep(
        id="s1",
        description="Delete downloads collection",
        risk="destructive",
        expected_tools=["delete_file"],
        tool_args={"delete_file": {"path": "/downloads"}},
    )

    result = await runner.run_step(step, ToolContext(adapter=SimulatorNasAdapter()))

    assert result.success is False
    assert result.tool_results == []
    assert result.error is not None
    assert "unsafe destructive target" in result.error
    assert approval_provider.messages == []


@pytest.mark.asyncio
async def test_step_runner_executes_destructive_concrete_file_when_approved() -> None:
    registry = ToolRegistry()
    registry.register(delete_file_tool)
    runner = StepRunner(
        registry=registry,
        safety_policy=SafetyPolicy(SafetySettings(allow_destructive=True)),
        approval_provider=StaticApprovalProvider(approved=True),
    )
    step = PlanStep(
        id="s1",
        description="Delete movie file",
        risk="destructive",
        expected_tools=["delete_file"],
        tool_args={"delete_file": {"path": "/downloads/movie.iso"}},
    )
    adapter = SimulatorNasAdapter()

    result = await runner.run_step(step, ToolContext(adapter=adapter))

    assert result.success is True
    assert result.tool_results[0].tool_name == "delete_file"
    assert [file.path for file in await adapter.list_files("/downloads")] == [
        "/downloads/photos.zip"
    ]


@pytest.mark.asyncio
async def test_step_runner_includes_destructive_target_in_approval_prompt() -> None:
    registry = ToolRegistry()
    registry.register(delete_file_tool)
    approval_provider = StaticApprovalProvider(approved=False)
    runner = StepRunner(
        registry=registry,
        safety_policy=SafetyPolicy(SafetySettings(allow_destructive=True)),
        approval_provider=approval_provider,
    )
    step = PlanStep(
        id="s1",
        description="Delete file",
        risk="destructive",
        expected_tools=["delete_file"],
        tool_args={"delete_file": {"path": "/homes/demo/old.txt"}},
    )

    result = await runner.run_step(step, ToolContext(adapter=SimulatorNasAdapter()))

    assert result.success is False
    assert approval_provider.messages == [
        "Execute delete_file? Risk: destructive Target: path=/homes/demo/old.txt"
    ]


@pytest.mark.asyncio
async def test_step_runner_passes_planned_tool_arguments() -> None:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="echo_path",
            description="Echo a path.",
            risk_level=RiskLevel.READ,
            handler=echo_path,
        )
    )
    runner = StepRunner(registry=registry, safety_policy=SafetyPolicy(SafetySettings()))
    step = PlanStep(
        id="s1",
        description="Echo path",
        risk="read",
        expected_tools=["echo_path"],
        tool_args={"echo_path": {"path": "/homes"}},
    )

    result = await runner.run_step(step, ToolContext(adapter=SimulatorNasAdapter()))

    assert result.success is True
    assert result.tool_results[0].result["path"] == "/homes"


@pytest.mark.asyncio
async def test_step_runner_returns_failure_for_missing_tool_args() -> None:
    registry = ToolRegistry()
    registry.register(list_files_tool)
    runner = StepRunner(registry=registry, safety_policy=SafetyPolicy(SafetySettings()))
    step = PlanStep(
        id="s1",
        description="List files",
        risk="read",
        expected_tools=["list_files"],
    )

    result = await runner.run_step(step, ToolContext(adapter=SimulatorNasAdapter()))

    assert result.success is False
    assert result.tool_results == []
    assert result.error == "invalid arguments for tool list_files: missing required path"


@pytest.mark.asyncio
async def test_step_runner_returns_failure_for_unknown_tool() -> None:
    runner = StepRunner(registry=ToolRegistry(), safety_policy=SafetyPolicy(SafetySettings()))
    step = PlanStep(
        id="s1",
        description="Run unknown tool",
        risk="read",
        expected_tools=["missing_tool"],
    )

    result = await runner.run_step(step, ToolContext(adapter=SimulatorNasAdapter()))

    assert result.success is False
    assert result.tool_results == []
    assert result.error == "unknown tool: missing_tool"


@pytest.mark.asyncio
async def test_step_runner_executes_list_files_with_args() -> None:
    registry = ToolRegistry()
    registry.register(list_files_tool)
    runner = StepRunner(registry=registry, safety_policy=SafetyPolicy(SafetySettings()))
    step = PlanStep(
        id="s1",
        description="List files",
        risk="read",
        expected_tools=["list_files"],
        tool_args={"list_files": {"path": "/downloads"}},
    )

    result = await runner.run_step(step, ToolContext(adapter=SimulatorNasAdapter()))

    assert result.success is True
    assert result.tool_results[0].tool_name == "list_files"
    assert "files" in result.tool_results[0].result


@pytest.mark.asyncio
async def test_step_runner_records_react_trace_for_tool_execution() -> None:
    registry = ToolRegistry()
    registry.register(get_storage_status_tool)
    runner = StepRunner(registry=registry, safety_policy=SafetyPolicy(SafetySettings()))
    step = PlanStep(
        id="s1",
        description="Get storage",
        risk="read",
        expected_tools=["get_storage_status"],
    )

    result = await runner.run_step(step, ToolContext(adapter=SimulatorNasAdapter()))

    assert result.react_trace.max_iterations == 5
    assert len(result.react_trace.iterations) == 1
    iteration = result.react_trace.iterations[0]
    assert iteration.thought == "Execute planned tool get_storage_status"
    assert iteration.action == "get_storage_status"
    assert "total_bytes" in iteration.observation


@pytest.mark.asyncio
async def test_step_runner_fails_when_expected_tools_exceed_react_limit() -> None:
    registry = ToolRegistry()
    registry.register(get_storage_status_tool)
    runner = StepRunner(registry=registry, safety_policy=SafetyPolicy(SafetySettings()))
    step = PlanStep(
        id="s1",
        description="Get storage repeatedly",
        risk="read",
        expected_tools=["get_storage_status"] * (MAX_REACT_ITERATIONS + 1),
    )

    result = await runner.run_step(step, ToolContext(adapter=SimulatorNasAdapter()))

    assert result.success is False
    assert result.error is not None
    assert "exceeds maximum ReAct iterations" in result.error
    assert result.tool_results == []
    assert result.react_trace.iterations == []
