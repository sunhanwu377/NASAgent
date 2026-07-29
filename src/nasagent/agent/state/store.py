from pathlib import Path

from nasagent.agent.state.models import AgentState


class RunStateStore:
    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def save(self, run_id: str, state: AgentState) -> Path:
        self._directory.mkdir(parents=True, exist_ok=True)
        path = self._directory / f"{run_id}.json"
        path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
        return path
