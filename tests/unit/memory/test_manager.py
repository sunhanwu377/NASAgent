from pathlib import Path

from nasagent.memory.manager import MemoryManager


class FakeLlm:
    async def complete(self, messages):
        return "ok"

    def stream_complete(self, messages):
        raise NotImplementedError


def _make(tmp_path: Path) -> MemoryManager:
    return MemoryManager(tmp_path, FakeLlm())


class TestEnsureSession:
    def test_creates_default(self, tmp_path: Path):
        mgr = _make(tmp_path)
        meta = mgr.ensure_session()
        assert meta.name == "default"
        assert mgr.conversation_memory is not None

    def test_creates_named(self, tmp_path: Path):
        meta = _make(tmp_path).ensure_session("my-project")
        assert meta.name == "my-project"

    def test_reuses_existing(self, tmp_path: Path):
        mgr = _make(tmp_path)
        s1 = mgr.ensure_session("existing")
        s2 = mgr.ensure_session("existing")
        assert s1.session_id == s2.session_id
        assert len(mgr.session_store.list_all()) == 1


class TestRememberForLlm:
    def test_empty_when_no_memories(self, tmp_path: Path):
        assert _make(tmp_path).remember_for_llm() == ""

    def test_formats_memories(self, tmp_path: Path):
        mgr = _make(tmp_path)
        mgr.persistent_memory.remember("user likes dark mode")
        text = mgr.remember_for_llm()
        assert "dark mode" in text
        assert "Known user context" in text

    def test_includes_preferences(self, tmp_path: Path):
        mgr = _make(tmp_path)
        mgr.persistent_memory.set_preference("lang", "zh")
        assert "lang" in mgr.remember_for_llm()


class TestInjectContext:
    def test_injects_persistent_memory(self, tmp_path: Path):
        mgr = _make(tmp_path)
        mgr.ensure_session("test")
        mgr.persistent_memory.remember("user is Alice")
        msgs = mgr.inject_context()
        assert "Alice" in msgs[0]["content"]

    def test_includes_history(self, tmp_path: Path):
        mgr = _make(tmp_path)
        mgr.ensure_session("test")
        mgr.conversation_memory.add_message("user", "prev q")
        mgr.conversation_memory.add_message("assistant", "prev a")
        msgs = mgr.inject_context()
        assert len(msgs) >= 3
