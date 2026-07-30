import fcntl
import json
from pathlib import Path
from typing import Any

from nasagent.memory.models import MemoryEntry, Preferences


class PersistentMemory:
    def __init__(self, storage_dir: Path) -> None:
        self._dir = storage_dir
        self._dir.mkdir(parents=True, exist_ok=True)
        self._memories: list[MemoryEntry] = self._load_memories()
        self._preferences = self._load_preferences()

    @property
    def _memories_path(self) -> Path:
        return self._dir / "memories.json"

    @property
    def _preferences_path(self) -> Path:
        return self._dir / "preferences.json"

    def remember(self, content: str, tags: list[str] | None = None) -> MemoryEntry:
        entry = MemoryEntry(content=content, tags=tags or [])
        self._memories.append(entry)
        self._save_memories()
        return entry

    def forget(self, entry_id: str) -> None:
        self._memories = [m for m in self._memories if m.id != entry_id]
        self._save_memories()

    def recall(self, query: str | None = None, tags: list[str] | None = None) -> list[MemoryEntry]:
        results = self._memories
        if query is not None:
            q = query.lower()
            results = [m for m in results if q in m.content.lower()]
        if tags is not None:
            tag_set = set(tags)
            results = [m for m in results if tag_set.intersection(m.tags)]
        return results

    def list_all(self) -> list[MemoryEntry]:
        return list(self._memories)

    def set_preference(self, key: str, value: Any) -> None:
        self._preferences.data[key] = value
        self._save_preferences()

    def get_preference(self, key: str, default: Any = None) -> Any:
        return self._preferences.data.get(key, default)

    def delete_preference(self, key: str) -> None:
        self._preferences.data.pop(key, None)
        self._save_preferences()

    def get_all_preferences(self) -> dict[str, Any]:
        return dict(self._preferences.data)

    def _load_memories(self) -> list[MemoryEntry]:
        if not self._memories_path.exists():
            return []
        try:
            data = self._read_json(self._memories_path)
            return [MemoryEntry.model_validate(item) for item in data] if isinstance(data, list) else []
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _load_preferences(self) -> Preferences:
        if not self._preferences_path.exists():
            return Preferences()
        try:
            data = self._read_json(self._preferences_path)
            return Preferences(data=data) if isinstance(data, dict) else Preferences()
        except (json.JSONDecodeError, FileNotFoundError):
            return Preferences()

    def _save_memories(self) -> None:
        self._write_json(self._memories_path, [m.model_dump(mode="json") for m in self._memories])

    def _save_preferences(self) -> None:
        self._write_json(self._preferences_path, self._preferences.data)

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
