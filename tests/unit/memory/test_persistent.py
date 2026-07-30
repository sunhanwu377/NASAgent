import json
from pathlib import Path

from nasagent.memory.persistent import PersistentMemory


class TestPersistentMemoryRemember:
    def test_adds_entry(self, tmp_path: Path):
        pm = PersistentMemory(tmp_path)
        entry = pm.remember("user prefers dark mode", tags=["preference"])
        assert entry.content == "user prefers dark mode"
        assert entry.tags == ["preference"]

    def test_persists_to_disk(self, tmp_path: Path):
        pm = PersistentMemory(tmp_path)
        pm.remember("test")
        data = json.loads((tmp_path / "memories.json").read_text())
        assert data[0]["content"] == "test"


class TestPersistentMemoryForget:
    def test_removes_entry(self, tmp_path: Path):
        pm = PersistentMemory(tmp_path)
        entry = pm.remember("to delete")
        pm.forget(entry.id)
        assert pm.recall() == []

    def test_nonexistent_is_noop(self, tmp_path: Path):
        pm = PersistentMemory(tmp_path)
        pm.forget("does-not-exist")


class TestPersistentMemoryRecall:
    def test_returns_all(self, tmp_path: Path):
        pm = PersistentMemory(tmp_path)
        pm.remember("a")
        pm.remember("b")
        assert len(pm.recall()) == 2

    def test_keyword_match(self, tmp_path: Path):
        pm = PersistentMemory(tmp_path)
        pm.remember("default device nas-pro")
        pm.remember("prefer Chinese")
        results = pm.recall(query="device")
        assert len(results) == 1
        assert "nas-pro" in results[0].content

    def test_tag_filter(self, tmp_path: Path):
        pm = PersistentMemory(tmp_path)
        pm.remember("a", tags=["x"])
        pm.remember("b", tags=["y"])
        pm.remember("c", tags=["x", "y"])
        assert len(pm.recall(tags=["x"])) == 2


class TestPersistentMemoryPreferences:
    def test_set_and_get(self, tmp_path: Path):
        pm = PersistentMemory(tmp_path)
        pm.set_preference("language", "zh")
        assert pm.get_preference("language") == "zh"

    def test_get_default(self, tmp_path: Path):
        assert PersistentMemory(tmp_path).get_preference("x", "fallback") == "fallback"

    def test_delete(self, tmp_path: Path):
        pm = PersistentMemory(tmp_path)
        pm.set_preference("key", "value")
        pm.delete_preference("key")
        assert pm.get_preference("key") is None

    def test_get_all(self, tmp_path: Path):
        pm = PersistentMemory(tmp_path)
        pm.set_preference("a", 1)
        pm.set_preference("b", 2)
        assert pm.get_all_preferences() == {"a": 1, "b": 2}

    def test_persists(self, tmp_path: Path):
        pm = PersistentMemory(tmp_path)
        pm.set_preference("key", "value")
        pm2 = PersistentMemory(tmp_path)
        assert pm2.get_preference("key") == "value"


class TestPersistentMemoryLoad:
    def test_loads_existing(self, tmp_path: Path):
        tmp_path.mkdir(parents=True, exist_ok=True)
        (tmp_path / "memories.json").write_text(json.dumps([
            {"id": "abc", "content": "old", "tags": [], "created_at": "2024-01-01T00:00:00"}
        ]))
        assert PersistentMemory(tmp_path).list_all()[0].content == "old"
