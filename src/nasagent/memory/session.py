import fcntl
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from nasagent.memory.models import SessionMeta


class SessionStore:
    def __init__(self, storage_dir: Path) -> None:
        self._dir = storage_dir
        self._dir.mkdir(parents=True, exist_ok=True)
        self._index: dict[str, SessionMeta] = self._load_index()

    @property
    def _index_path(self) -> Path:
        return self._dir / "sessions.json"

    @property
    def _current_path(self) -> Path:
        return self._dir / "_current"

    def create(self, name: str) -> SessionMeta:
        session_id = uuid4().hex[:12]
        now = datetime.now(timezone.utc)
        meta = SessionMeta(
            session_id=session_id, name=name, created_at=now, last_active_at=now
        )
        self._index[session_id] = meta
        self._save_index()
        self._set_current(session_id)
        return meta

    def get_current(self) -> SessionMeta | None:
        try:
            current_id = self._current_path.read_text().strip()
        except FileNotFoundError:
            return None
        return self._index.get(current_id)

    def switch(self, session_id: str) -> SessionMeta:
        if session_id not in self._index:
            raise ValueError(f"Session not found: {session_id}")
        now = datetime.now(timezone.utc)
        meta = self._index[session_id]
        updated = SessionMeta(
            session_id=meta.session_id, name=meta.name,
            created_at=meta.created_at, last_active_at=now,
            message_count=meta.message_count,
        )
        self._index[session_id] = updated
        self._save_index()
        self._set_current(session_id)
        return updated

    def list_all(self) -> list[SessionMeta]:
        return sorted(self._index.values(), key=lambda s: s.created_at)

    def delete(self, session_id: str) -> SessionMeta:
        if session_id not in self._index:
            raise ValueError(f"Session not found: {session_id}")
        meta = self._index.pop(session_id)
        self._save_index()
        try:
            current_id = self._current_path.read_text().strip()
        except FileNotFoundError:
            current_id = None
        if current_id == session_id:
            remaining = self.list_all()
            if remaining:
                self._set_current(remaining[0].session_id)
            else:
                self._current_path.unlink(missing_ok=True)
        return meta

    def touch(self) -> None:
        current = self.get_current()
        if current is None:
            return
        now = datetime.now(timezone.utc)
        updated = SessionMeta(
            session_id=current.session_id, name=current.name,
            created_at=current.created_at, last_active_at=now,
            message_count=current.message_count,
        )
        self._index[current.session_id] = updated
        self._save_index()

    def _set_current(self, session_id: str) -> None:
        self._current_path.write_text(session_id)

    def _load_index(self) -> dict[str, SessionMeta]:
        if not self._index_path.exists():
            return {}
        data = self._read_json(self._index_path)
        if not isinstance(data, list):
            return {}
        result: dict[str, SessionMeta] = {}
        for item in data:
            try:
                meta = SessionMeta.model_validate(item)
                result[meta.session_id] = meta
            except Exception:
                continue
        return result

    def _save_index(self) -> None:
        self._write_json(self._index_path, [
            meta.model_dump(mode="json") for meta in self._index.values()
        ])

    def _read_json(self, path: Path) -> object:
        with open(path, "r", encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            result = json.load(f)
            fcntl.flock(f, fcntl.LOCK_UN)
        return result

    def _write_json(self, path: Path, data: object) -> None:
        with open(path, "w", encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            json.dump(data, f, indent=2, default=str)
            fcntl.flock(f, fcntl.LOCK_UN)
