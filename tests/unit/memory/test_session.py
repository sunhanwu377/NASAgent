import json
from pathlib import Path

import pytest

from nasagent.memory.session import SessionStore


def _make_store(tmp_path: Path) -> SessionStore:
    return SessionStore(tmp_path)


class TestSessionStoreCreate:
    def test_creates_and_sets_current(self, tmp_path: Path):
        store = _make_store(tmp_path)
        meta = store.create("my-session")
        assert meta.name == "my-session"
        assert (tmp_path / "_current").read_text().strip() == meta.session_id

    def test_creates_multiple(self, tmp_path: Path):
        store = _make_store(tmp_path)
        store.create("first")
        store.create("second")
        assert len(store.list_all()) == 2

    def test_persists_index(self, tmp_path: Path):
        store = _make_store(tmp_path)
        store.create("persisted")
        data = json.loads((tmp_path / "sessions.json").read_text())
        assert data[0]["name"] == "persisted"


class TestSessionStoreSwitch:
    def test_switches_existing(self, tmp_path: Path):
        store = _make_store(tmp_path)
        s1 = store.create("first")
        store.create("second")
        switched = store.switch(s1.session_id)
        assert switched.session_id == s1.session_id

    def test_switch_nonexistent_raises(self, tmp_path: Path):
        store = _make_store(tmp_path)
        with pytest.raises(ValueError, match="not found"):
            store.switch("nonexistent")


class TestSessionStoreListAll:
    def test_empty(self, tmp_path: Path):
        assert _make_store(tmp_path).list_all() == []

    def test_returns_all(self, tmp_path: Path):
        store = _make_store(tmp_path)
        for name in ["a", "b", "c"]:
            store.create(name)
        assert [s.name for s in store.list_all()] == ["a", "b", "c"]


class TestSessionStoreDelete:
    def test_deletes(self, tmp_path: Path):
        store = _make_store(tmp_path)
        s = store.create("to-delete")
        store.delete(s.session_id)
        assert store.get_current() is None
        assert len(store.list_all()) == 0

    def test_switches_to_remaining(self, tmp_path: Path):
        store = _make_store(tmp_path)
        s1 = store.create("keep")
        s2 = store.create("remove")
        store.delete(s2.session_id)
        assert store.get_current().session_id == s1.session_id


class TestSessionStoreLoad:
    def test_loads_existing(self, tmp_path: Path):
        tmp_path.mkdir(parents=True, exist_ok=True)
        (tmp_path / "sessions.json").write_text(json.dumps([
            {"session_id": "pre", "name": "old", "created_at": "2024-01-01T00:00:00",
             "last_active_at": "2024-01-01T00:00:00", "message_count": 3}
        ]))
        (tmp_path / "_current").write_text("pre")
        store = SessionStore(tmp_path)
        assert store.list_all()[0].name == "old"
        assert store.get_current().session_id == "pre"


class TestSessionStoreTouch:
    def test_updates_last_active(self, tmp_path: Path):
        store = _make_store(tmp_path)
        s = store.create("active")
        import time
        time.sleep(0.01)
        store.touch()
        current = store.get_current()
        assert current.last_active_at > s.last_active_at
