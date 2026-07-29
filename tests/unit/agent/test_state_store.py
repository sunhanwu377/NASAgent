import json

from nasagent.agent.state.models import AgentState, StepResult
from nasagent.agent.state.store import RunStateStore
from nasagent.tools.schemas import ToolCallResult


def test_run_state_store_redacts_sensitive_values(tmp_path) -> None:  # type: ignore[no-untyped-def]
    state = AgentState(
        goal="use token secret-token",
        step_results=[
            StepResult(
                step_id="s1",
                success=True,
                tool_results=[
                    ToolCallResult(
                        tool_name="upload_file",
                        result={
                            "api_token": "secret-token",
                            "nested": {"password": "secret-password"},
                            "safe": "visible",
                        },
                    )
                ],
            )
        ],
    )

    path = RunStateStore(tmp_path).save("run-1", state)

    persisted = path.read_text(encoding="utf-8")
    data = json.loads(persisted)
    result = data["step_results"][0]["tool_results"][0]["result"]
    assert "secret-token" not in persisted
    assert "secret-password" not in persisted
    assert data["goal"] == "[REDACTED]"
    assert result["api_token"] == "[REDACTED]"
    assert result["nested"]["password"] == "[REDACTED]"
    assert result["safe"] == "visible"
