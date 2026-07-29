import pytest

from nasagent.agent.graph.builder import run_agent_once
from nasagent.config.settings import SafetySettings
from nasagent.llm.base import LlmProvider
from nasagent.nas.adapters.simulator.adapter import SimulatorNasAdapter
from nasagent.safety.approvals import ApprovalProvider


class FakeProvider(LlmProvider):
    async def complete(self, messages):  # type: ignore[no-untyped-def]
        return (
            '{"goal":"check storage","steps":[{"id":"s1","description":"Get storage",'
            '"risk":"read","expected_tools":["get_storage_status"]}]}'
        )


class ApprovingProvider(ApprovalProvider):
    def confirm(self, message: str) -> bool:
        return True


@pytest.mark.asyncio
async def test_agent_runs_plan_against_simulator() -> None:
    state = await run_agent_once(
        "check storage",
        adapter=SimulatorNasAdapter(),
        provider=FakeProvider(),
    )

    assert state.goal == "check storage"
    assert state.step_results[0].success is True
    assert "get_storage_status" in state.final_summary


@pytest.mark.asyncio
async def test_agent_persists_sanitized_run_state(tmp_path) -> None:  # type: ignore[no-untyped-def]
    state = await run_agent_once(
        "check storage with token secret-token",
        adapter=SimulatorNasAdapter(),
        provider=FakeProvider(),
        run_log_dir=tmp_path,
    )

    run_files = list(tmp_path.glob("*.json"))
    assert len(run_files) == 1
    persisted = run_files[0].read_text(encoding="utf-8")
    assert state.goal == "check storage with token secret-token"
    assert "secret-token" not in persisted
    assert '"goal": "[REDACTED]"' in persisted


@pytest.mark.asyncio
async def test_agent_uses_configured_safety_settings() -> None:
    class UploadProvider(LlmProvider):
        async def complete(self, messages):  # type: ignore[no-untyped-def]
            return (
                '{"goal":"upload file","steps":[{"id":"s1","description":"Upload file",'
                '"risk":"write","expected_tools":["upload_file"],'
                '"tool_args":{"upload_file":{"local_path":"/tmp/source",'
                '"remote_path":"/upload/source"}}}]}'
            )

    state = await run_agent_once(
        "upload file",
        adapter=SimulatorNasAdapter(),
        provider=UploadProvider(),
        safety_settings=SafetySettings(allow_auto_write=True, require_confirmation_for=()),
        approval_provider=ApprovingProvider(),
    )

    assert state.step_results[0].success is True
    assert state.step_results[0].tool_results[0].tool_name == "upload_file"
