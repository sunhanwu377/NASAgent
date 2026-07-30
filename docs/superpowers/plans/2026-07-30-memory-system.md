# Memory System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a three-layer memory system (conversation history, session management, persistent memories) to NASAgent using JSON file storage.

**Architecture:** New `nasagent/memory/` module (6 files) + config extension + chat/graph integration + slash commands. Pydantic models, dataclass components, fcntl-locked file persistence.

**Tech Stack:** Python 3.11+, Pydantic 2.7+, existing LlmProvider protocol, fcntl locking

---

### Task 1: Memory Data Models

**Files:**
- Create: `src/nasagent/memory/models.py`
- Create: `tests/unit/memory/__init__.py` (empty file)
- Create: `tests/unit/memory/test_models.py`

- [ ] **Step 1: Write test file**

```python
from datetime import datetime

from nasagent.memory.models import Conversation, MemoryEntry, Message, Preferences, SessionMeta


class TestMessage:
    def test_creates_with_default_timestamp(self):
        msg = Message(role="user", content="hello")
        assert msg.role == "user"
        assert msg.content == "hello"
        assert isinstance(msg.timestamp, datetime)

    def test_serializes_to_dict(self):
        msg = Message(role="assistant", content="hi there")
        data = msg.model_dump(mode="json")
        assert data["role"] == "assistant"
        assert data["content"] == "hi there"
        assert "timestamp" in data


class TestConversation:
    def test_default_values(self):
        conv = Conversation()
        assert conv.messages == []
        assert conv.summary is None
        assert conv.summary_index == 0

    def test_with_messages(self):
        msg = Message(role="user", content="hi")
        conv = Conversation(messages=[msg], summary="prior", summary_index=5)
        assert len(conv.messages) == 1
        assert conv.summary == "prior"
        assert conv.summary_index == 5


class TestSessionMeta:
    def test_creates_session(self):
        now = datetime.now()
        meta = SessionMeta(session_id="abc", name="s", created_at=now, last_active_at=now)
        assert meta.session_id == "abc"
        assert meta.message_count == 0

    def test_serialization_roundtrip(self):
        now = datetime.now()
        meta = SessionMeta(
            session_id="abc", name="t", created_at=now, last_active_at=now, message_count=5
        )
        restored = SessionMeta.model_validate_json(meta.model_dump_json())
        assert restored.name == "t"
        assert restored.message_count == 5


class TestMemoryEntry:
    def test_generates_id(self):
        entry = MemoryEntry(content="remember this")
        assert len(entry.id) == 12
        assert entry.tags == []

    def test_with_tags(self):
        entry = MemoryEntry(content="pref", tags=["preference", "workflow"])
        assert entry.tags == ["preference", "workflow"]


class TestPreferences:
    def test_default_empty(self):
        assert Preferences().data == {}

    def test_with_data(self):
        prefs = Preferences(data={"lang": "zh"})
        assert prefs.data["lang"] == "zh"
```

- [ ] **Step 2: Run tests, expect failure**

```bash
pytest tests/unit/memory/test_models.py -v --no-header
```

- [ ] **Step 3: Create empty init file**

```bash
touch tests/unit/memory/__init__.py
```

- [ ] **Step 4: Write `src/nasagent/memory/models.py`**

```python
from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)


class Conversation(BaseModel):
    messages: list[Message] = Field(default_factory=list)
    summary: str | None = None
    summary_index: int = 0


class SessionMeta(BaseModel):
    session_id: str
    name: str
    created_at: datetime
    last_active_at: datetime
    message_count: int = 0


class MemoryEntry(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    content: str
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)


class Preferences(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)
```

- [ ] **Step 5: Run tests, expect pass**

```bash
pytest tests/unit/memory/test_models.py -v --no-header
```

- [ ] **Step 6: Commit**

```bash
git add tests/unit/memory/__init__.py tests/unit/memory/test_models.py src/nasagent/memory/models.py
git commit -m "feat: add memory data models"
```

---

### Task 2: SessionStore

**Files:**
- Create: `src/nasagent/memory/session.py`
- Create: `tests/unit/memory/test_session.py`

- [ ] **Step 1: Write test file**

```python
import json
from datetime import datetime
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
        (tmp_path / "sessions.json").write_text(
            json.dumps(
                [
                    {
                        "session_id": "pre",
                        "name": "old",
                        "created_at": "2024-01-01T00:00:00",
                        "last_active_at": "2024-01-01T00:00:00",
                        "message_count": 3,
                    }
                ]
            )
        )
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
```

- [ ] **Step 2: Run tests, expect failure**

```bash
pytest tests/unit/memory/test_session.py -v --no-header
```

- [ ] **Step 3: Write `src/nasagent/memory/session.py`**

```python
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
        meta = SessionMeta(session_id=session_id, name=name, created_at=now, last_active_at=now)
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
            session_id=meta.session_id,
            name=meta.name,
            created_at=meta.created_at,
            last_active_at=now,
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
        current = self.get_current()
        if current and current.session_id == session_id:
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
            session_id=current.session_id,
            name=current.name,
            created_at=current.created_at,
            last_active_at=now,
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
        self._write_json(
            self._index_path, [meta.model_dump(mode="json") for meta in self._index.values()]
        )

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
```

- [ ] **Step 4: Run tests, expect pass**

```bash
pytest tests/unit/memory/test_session.py -v --no-header
```

- [ ] **Step 5: Commit**

```bash
git add src/nasagent/memory/session.py tests/unit/memory/test_session.py
git commit -m "feat: add SessionStore for named session management"
```

---

### Task 3: PersistentMemory

**Files:**
- Create: `src/nasagent/memory/persistent.py`
- Create: `tests/unit/memory/test_persistent.py`

- [ ] **Step 1: Write test file**

```python
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
        (tmp_path / "memories.json").write_text(
            json.dumps(
                [{"id": "abc", "content": "old", "tags": [], "created_at": "2024-01-01T00:00:00"}]
            )
        )
        assert PersistentMemory(tmp_path).list_all()[0].content == "old"
```

- [ ] **Step 2: Run tests, expect failure**

```bash
pytest tests/unit/memory/test_persistent.py -v --no-header
```

- [ ] **Step 3: Write `src/nasagent/memory/persistent.py`**

```python
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
            return (
                [MemoryEntry.model_validate(item) for item in data]
                if isinstance(data, list)
                else []
            )
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
```

- [ ] **Step 4: Run tests, expect pass**

```bash
pytest tests/unit/memory/test_persistent.py -v --no-header
```

- [ ] **Step 5: Commit**

```bash
git add src/nasagent/memory/persistent.py tests/unit/memory/test_persistent.py
git commit -m "feat: add PersistentMemory for long-term memories and preferences"
```

---

### Task 4: ConversationMemory

**Files:**
- Create: `src/nasagent/memory/conversation.py`
- Create: `tests/unit/memory/test_conversation.py`

- [ ] **Step 1: Write test file**

```python
import asyncio
import json
from collections.abc import AsyncIterator
from pathlib import Path

from nasagent.llm.messages import ChatMessage
from nasagent.memory.conversation import ConversationMemory


class FakeLlm:
    def __init__(self, responses=None):
        self.responses = responses or ["summary"]
        self.calls: list[list[ChatMessage]] = []

    async def complete(self, messages: list[ChatMessage]) -> str:
        self.calls.append(messages)
        return self.responses.pop(0) if self.responses else "summary"

    def stream_complete(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        raise NotImplementedError


def _make(tmp_path: Path, llm=None, **kw):
    return ConversationMemory(tmp_path, llm or FakeLlm(), **kw)


class TestAddMessage:
    def test_adds(self, tmp_path: Path):
        cm = _make(tmp_path)
        cm.add_message("user", "hello")
        assert len(cm.get_history()) == 1
        assert cm.get_history()[0].content == "hello"

    def test_persists(self, tmp_path: Path):
        cm = _make(tmp_path)
        cm.add_message("user", "hi")
        cm2 = ConversationMemory(tmp_path, FakeLlm())
        assert len(cm2.get_history()) == 1


class TestGetMessagesForLlm:
    def test_returns_with_system(self, tmp_path: Path):
        cm = _make(tmp_path)
        cm.add_message("user", "q")
        msgs = cm.get_messages_for_llm()
        assert msgs[0]["role"] == "system"
        assert "NASAgent" in msgs[0]["content"]
        assert msgs[1]["role"] == "user"

    def test_includes_summary(self, tmp_path: Path):
        cm = _make(tmp_path)
        cm._conversation.summary = "NAS discussion"
        cm._conversation.summary_index = 5
        assert "NAS discussion" in cm.get_messages_for_llm()[0]["content"]

    def test_empty_returns_system_only(self, tmp_path: Path):
        assert len(_make(tmp_path).get_messages_for_llm()) == 1


class TestSummarize:
    def test_triggers_over_threshold(self, tmp_path: Path):
        llm = FakeLlm(["*summary*"])
        cm = _make(tmp_path, llm, summary_threshold=5)
        for i in range(6):
            cm.add_message("user", f"msg {i}")
        asyncio.run(cm.maybe_summarize())
        assert len(llm.calls) == 1
        assert cm._conversation.summary == "*summary*"
        assert cm._conversation.summary_index == 5

    def test_no_trigger_below_threshold(self, tmp_path: Path):
        llm = FakeLlm()
        cm = _make(tmp_path, llm, summary_threshold=10)
        for i in range(5):
            cm.add_message("user", f"msg {i}")
        asyncio.run(cm.maybe_summarize())
        assert len(llm.calls) == 0

    def test_llm_failure_is_graceful(self, tmp_path: Path):
        class FailingLlm:
            async def complete(self, messages):
                raise RuntimeError("boom")

            def stream_complete(self, messages):
                raise NotImplementedError

        cm = _make(tmp_path, FailingLlm(), summary_threshold=3)
        for i in range(5):
            cm.add_message("user", f"msg {i}")
        asyncio.run(cm.maybe_summarize())


class TestLoad:
    def test_loads_messages(self, tmp_path: Path):
        tmp_path.mkdir(parents=True, exist_ok=True)
        (tmp_path / "messages.json").write_text(
            json.dumps([{"role": "user", "content": "hi", "timestamp": "2024-01-01T00:00:00"}])
        )
        cm = ConversationMemory(tmp_path, FakeLlm())
        assert cm.get_history()[0].content == "hi"

    def test_loads_summary(self, tmp_path: Path):
        tmp_path.mkdir(parents=True, exist_ok=True)
        (tmp_path / "summary.json").write_text(json.dumps({"summary": "old", "summary_index": 10}))
        cm = ConversationMemory(tmp_path, FakeLlm())
        assert cm._conversation.summary == "old"
        assert cm._conversation.summary_index == 10
```

- [ ] **Step 2: Run tests, expect failure**

```bash
pytest tests/unit/memory/test_conversation.py -v --no-header
```

- [ ] **Step 3: Write `src/nasagent/memory/conversation.py`**

```python
import fcntl
import json
from pathlib import Path

from nasagent.llm.messages import ChatMessage
from nasagent.memory.models import Conversation, Message


class ConversationMemory:
    def __init__(
        self,
        session_path: Path,
        llm_provider,
        max_messages: int = 50,
        summary_threshold: int = 30,
    ) -> None:
        self._path = session_path
        self._llm = llm_provider
        self._max_messages = max_messages
        self._summary_threshold = summary_threshold
        self._conversation = self._load()

    @property
    def _messages_path(self) -> Path:
        return self._path / "messages.json"

    @property
    def _summary_path(self) -> Path:
        return self._path / "summary.json"

    def add_message(self, role: str, content: str) -> None:
        msg = Message(role=role, content=content)
        self._conversation.messages.append(msg)
        self._save()

    def get_history(self) -> list[Message]:
        return list(self._conversation.messages)

    def get_messages_for_llm(self) -> list[dict]:
        system_content = "You are NASAgent, a helpful NAS management assistant."
        if self._conversation.summary:
            system_content += f" Previous conversation summary: {self._conversation.summary}"
        messages: list[dict] = [{"role": "system", "content": system_content}]
        for msg in self._conversation.messages:
            messages.append({"role": msg.role, "content": msg.content})
        return messages

    async def maybe_summarize(self) -> None:
        summary = self._conversation.summary
        start = self._conversation.summary_index
        messages = self._conversation.messages
        if len(messages) - start < self._summary_threshold:
            return
        to_summarize = messages[start : start + self._summary_threshold]
        if not to_summarize:
            return
        try:
            message_list = [ChatMessage(role=m.role, content=m.content) for m in to_summarize]
            prompt = (
                "Summarize the following conversation in 2-3 sentences, "
                "preserving key facts, decisions, and context. "
                "Respond with only the summary text, no preamble."
            )
            if summary:
                prompt = f"Previous summary: {summary}\n\n{prompt}"
            message_list.append(ChatMessage(role="user", content=prompt))
            new_summary = await self._llm.complete(message_list)
            self._conversation.summary = new_summary
            self._conversation.summary_index = start + self._summary_threshold
            self._save()
        except Exception:
            pass

    def _load(self) -> Conversation:
        conv = Conversation()
        if self._messages_path.exists():
            try:
                data = self._read_json(self._messages_path)
                if isinstance(data, list):
                    conv.messages = [Message.model_validate(item) for item in data]
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        if self._summary_path.exists():
            try:
                data = self._read_json(self._summary_path)
                if isinstance(data, dict):
                    conv.summary = data.get("summary")
                    conv.summary_index = data.get("summary_index", 0)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        return conv

    def _save(self) -> None:
        self._path.mkdir(parents=True, exist_ok=True)
        self._write_json(
            self._messages_path,
            [m.model_dump(mode="json") for m in self._conversation.messages],
        )
        self._write_json(
            self._summary_path,
            {
                "summary": self._conversation.summary,
                "summary_index": self._conversation.summary_index,
            },
        )

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
```

- [ ] **Step 4: Run tests, expect pass**

```bash
pytest tests/unit/memory/test_conversation.py -v --no-header
```

- [ ] **Step 5: Commit**

```bash
git add src/nasagent/memory/conversation.py tests/unit/memory/test_conversation.py
git commit -m "feat: add ConversationMemory with auto-summarization"
```

---

### Task 5: MemoryManager + Module Init + Config

**Files:**
- Create: `src/nasagent/memory/manager.py`
- Create: `tests/unit/memory/test_manager.py`
- Create: `src/nasagent/memory/__init__.py`
- Modify: `src/nasagent/config/settings.py`

- [ ] **Step 1: Write test file**

```python
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
```

- [ ] **Step 2: Run tests, expect failure**

```bash
pytest tests/unit/memory/test_manager.py -v --no-header
```

- [ ] **Step 3: Write `src/nasagent/memory/manager.py`**

```python
from pathlib import Path

from nasagent.memory.conversation import ConversationMemory
from nasagent.memory.models import SessionMeta
from nasagent.memory.persistent import PersistentMemory
from nasagent.memory.session import SessionStore


class MemoryManager:
    def __init__(self, storage_dir: Path, llm_provider) -> None:
        self.storage_dir = storage_dir
        self.session_store = SessionStore(storage_dir)
        self.persistent_memory = PersistentMemory(storage_dir / "persistent")
        self._llm = llm_provider
        self.conversation_memory: ConversationMemory | None = None
        self._current_id: str | None = None

    def ensure_session(self, name: str | None = None) -> SessionMeta:
        name = name or "default"
        existing = self.session_store.get_current()
        if existing is not None and existing.name == name:
            self._load_conversation(existing.session_id)
            return existing
        for meta in self.session_store.list_all():
            if meta.name == name:
                self.session_store.switch(meta.session_id)
                self._load_conversation(meta.session_id)
                return meta
        meta = self.session_store.create(name)
        self._load_conversation(meta.session_id)
        return meta

    def remember_for_llm(self) -> str:
        parts: list[str] = []
        memories = self.persistent_memory.list_all()
        if memories:
            parts.append("Known user context:")
            for m in memories:
                parts.append(f"- {m.content}")
        prefs = self.persistent_memory.get_all_preferences()
        if prefs:
            parts.append("User preferences:")
            for k, v in prefs.items():
                parts.append(f"- {k}: {v}")
        return "\n".join(parts)

    def inject_context(self) -> list[dict]:
        memory_text = self.remember_for_llm()
        if self.conversation_memory is not None:
            messages = self.conversation_memory.get_messages_for_llm()
        else:
            messages = [{"role": "system", "content": "You are NASAgent."}]
        if memory_text:
            messages[0]["content"] = messages[0]["content"] + "\n\n" + memory_text
        return messages

    def _load_conversation(self, session_id: str) -> None:
        if self._current_id == session_id and self.conversation_memory is not None:
            return
        session_path = self.storage_dir / "sessions" / session_id
        self.conversation_memory = ConversationMemory(session_path, self._llm)
        self._current_id = session_id
```

- [ ] **Step 4: Write `src/nasagent/memory/__init__.py`**

```python
from nasagent.memory.manager import MemoryManager

__all__ = ["MemoryManager"]
```

- [ ] **Step 5: Add `memory_dir` to `ObservabilitySettings` in `src/nasagent/config/settings.py`**

Edit the `ObservabilitySettings` class — add `memory_dir` and `expanded_memory_dir()`:

```python
class ObservabilitySettings(BaseModel):
    run_log_dir: str = "~/.nasagent/runs"
    memory_dir: str = "~/.nasagent/memory"
    redact_sensitive: bool = True

    def expanded_run_log_dir(self) -> Path:
        return Path(self.run_log_dir).expanduser()

    def expanded_memory_dir(self) -> Path:
        return Path(self.memory_dir).expanduser()
```

- [ ] **Step 6: Run all memory tests**

```bash
pytest tests/unit/memory/ -v --no-header
```

Expected: all tests PASS

- [ ] **Step 7: Verify existing tests still pass**

```bash
pytest tests/unit/ -v --no-header -x
```

- [ ] **Step 8: Commit**

```bash
git add src/nasagent/memory/manager.py tests/unit/memory/test_manager.py src/nasagent/memory/__init__.py src/nasagent/config/settings.py
git commit -m "feat: add MemoryManager, module init, and memory_dir config"
```

---

### Task 6: Memory Slash Commands

**Files:**
- Modify: `src/nasagent/plugins/commands.py`
- Create: `tests/unit/memory/test_memory_commands.py`

- [ ] **Step 1: Write test file**

```python
from nasagent.config.settings import NasAgentSettings
from nasagent.memory.manager import MemoryManager
from nasagent.platform.context import create_platform_context
from nasagent.plugins.commands import register_memory_commands


class FakeLlm:
    async def complete(self, messages):
        return "ok"

    def stream_complete(self, messages):
        raise NotImplementedError


def _make_ctx(tmp_path):
    ctx = create_platform_context(settings=NasAgentSettings())
    mgr = MemoryManager(tmp_path, FakeLlm())
    mgr.ensure_session("default")
    register_memory_commands(ctx, mgr)
    return ctx


class TestSessionCommands:
    def test_new(self, tmp_path):
        r = _make_ctx(tmp_path).commands.dispatch("/session new proj")
        assert r.exit_code == 0
        assert "proj" in r.message

    def test_list(self, tmp_path):
        ctx = _make_ctx(tmp_path)
        ctx.commands.dispatch("/session new a")
        ctx.commands.dispatch("/session new b")
        r = ctx.commands.dispatch("/session list")
        assert "a" in r.message
        assert "b" in r.message

    def test_switch(self, tmp_path):
        ctx = _make_ctx(tmp_path)
        ctx.commands.dispatch("/session new first")
        r = ctx.commands.dispatch("/session switch first")
        assert r.exit_code == 0

    def test_delete(self, tmp_path):
        ctx = _make_ctx(tmp_path)
        ctx.commands.dispatch("/session new temp")
        r = ctx.commands.dispatch("/session delete temp")
        assert r.exit_code == 0


class TestRememberCommands:
    def test_adds_entry(self, tmp_path):
        r = _make_ctx(tmp_path).commands.dispatch("/remember likes dark mode")
        assert r.exit_code == 0

    def test_lists_entries(self, tmp_path):
        ctx = _make_ctx(tmp_path)
        ctx.commands.dispatch("/remember test memory")
        r = ctx.commands.dispatch("/memories")
        assert "test memory" in r.message

    def test_forgets_entry(self, tmp_path):
        ctx = _make_ctx(tmp_path)
        ctx.commands.dispatch("/remember temp mem")
        r = ctx.commands.dispatch("/memories")
        line = r.message.strip().split("\n")[1]
        mem_id = line.strip().split(":")[0]
        r2 = ctx.commands.dispatch(f"/forget {mem_id}")
        assert r2.exit_code == 0


class TestPreferenceCommands:
    def test_set_get(self, tmp_path):
        ctx = _make_ctx(tmp_path)
        ctx.commands.dispatch("/pref set lang zh")
        assert "zh" in ctx.commands.dispatch("/pref get lang").message

    def test_list(self, tmp_path):
        ctx = _make_ctx(tmp_path)
        ctx.commands.dispatch("/pref set a 1")
        r = ctx.commands.dispatch("/pref list")
        assert "a" in r.message

    def test_delete(self, tmp_path):
        ctx = _make_ctx(tmp_path)
        ctx.commands.dispatch("/pref set key val")
        ctx.commands.dispatch("/pref delete key")
        assert "(not set)" in ctx.commands.dispatch("/pref get key").message
```

- [ ] **Step 2: Run tests, expect failure**

```bash
pytest tests/unit/memory/test_memory_commands.py -v --no-header
```

- [ ] **Step 3: Add `register_memory_commands` to `src/nasagent/plugins/commands.py`**

Append to the end of `commands.py`:

```python
from nasagent.memory.manager import MemoryManager


def register_memory_commands(context: PlatformContext, memory_manager: MemoryManager) -> None:
    context.commands.register(
        CommandDefinition(
            "session",
            "Manage chat sessions",
            "/session new|switch|list|delete <name>",
            lambda args: _session(memory_manager, args),
            aliases=("sessions",),
        )
    )
    context.commands.register(
        CommandDefinition(
            "remember",
            "Add persistent memory",
            "/remember <content>",
            lambda args: _remember(memory_manager, args),
        )
    )
    context.commands.register(
        CommandDefinition(
            "forget",
            "Delete persistent memory by ID",
            "/forget <id>",
            lambda args: _forget(memory_manager, args),
        )
    )
    context.commands.register(
        CommandDefinition(
            "memories",
            "List all persistent memories",
            "/memories",
            lambda args: _memories(memory_manager, args),
        )
    )
    context.commands.register(
        CommandDefinition(
            "pref",
            "Manage user preferences",
            "/pref set|get|list|delete <key> [value]",
            lambda args: _pref(memory_manager, args),
            aliases=("prefs", "preference"),
        )
    )


def _session(mgr: MemoryManager, args: tuple[str, ...]) -> CommandResult:
    if not args:
        return CommandResult("Usage: /session new|switch|list|delete <name>", exit_code=1)
    action = args[0]
    if action == "new":
        if len(args) < 2:
            return CommandResult("Usage: /session new <name>", exit_code=1)
        meta = mgr.session_store.create(args[1])
        mgr.ensure_session(args[1])
        return CommandResult(f"Session created: {meta.name} ({meta.session_id})")
    elif action == "switch":
        if len(args) < 2:
            return CommandResult("Usage: /session switch <name>", exit_code=1)
        try:
            target = next(s for s in mgr.session_store.list_all() if s.name == args[1])
        except StopIteration:
            return CommandResult(f"Session not found: {args[1]}", exit_code=1)
        meta = mgr.ensure_session(args[1])
        return CommandResult(f"Switched to session: {meta.name} ({meta.session_id})")
    elif action == "list":
        sessions = mgr.session_store.list_all()
        if not sessions:
            return CommandResult("No sessions.")
        current = mgr.session_store.get_current()
        lines = ["Sessions:"]
        for s in sessions:
            marker = " *" if current and s.session_id == current.session_id else ""
            lines.append(f"  {s.name} ({s.session_id}){marker}")
        return CommandResult("\n".join(lines))
    elif action == "delete":
        if len(args) < 2:
            return CommandResult("Usage: /session delete <name>", exit_code=1)
        try:
            target = next(s for s in mgr.session_store.list_all() if s.name == args[1])
        except StopIteration:
            return CommandResult(f"Session not found: {args[1]}", exit_code=1)
        mgr.session_store.delete(target.session_id)
        return CommandResult(f"Session deleted: {target.name}")
    else:
        return CommandResult(f"Unknown action: {action}", exit_code=1)


def _remember(mgr: MemoryManager, args: tuple[str, ...]) -> CommandResult:
    if not args:
        return CommandResult("Usage: /remember <content>", exit_code=1)
    entry = mgr.persistent_memory.remember(" ".join(args))
    return CommandResult(f"Memory saved: {entry.id}")


def _forget(mgr: MemoryManager, args: tuple[str, ...]) -> CommandResult:
    if not args:
        return CommandResult("Usage: /forget <id>", exit_code=1)
    mgr.persistent_memory.forget(args[0])
    return CommandResult(f"Memory removed: {args[0]}")


def _memories(mgr: MemoryManager, args: tuple[str, ...]) -> CommandResult:
    entries = mgr.persistent_memory.list_all()
    if not entries:
        return CommandResult("No persistent memories.")
    lines = ["Persistent memories:"]
    for e in entries:
        lines.append(f"  {e.id}: {e.content}")
    return CommandResult("\n".join(lines))


def _pref(mgr: MemoryManager, args: tuple[str, ...]) -> CommandResult:
    if not args:
        return CommandResult("Usage: /pref set|get|list|delete <key> [value]", exit_code=1)
    action = args[0]
    if action == "set":
        if len(args) < 3:
            return CommandResult("Usage: /pref set <key> <value>", exit_code=1)
        mgr.persistent_memory.set_preference(args[1], args[2])
        return CommandResult(f"Preference set: {args[1]} = {args[2]}")
    elif action == "get":
        if len(args) < 2:
            return CommandResult("Usage: /pref get <key>", exit_code=1)
        value = mgr.persistent_memory.get_preference(args[1])
        return CommandResult(
            f"{args[1]} = {value}" if value is not None else f"{args[1]} (not set)"
        )
    elif action == "list":
        prefs = mgr.persistent_memory.get_all_preferences()
        if not prefs:
            return CommandResult("No preferences set.")
        lines = ["Preferences:"]
        for k, v in prefs.items():
            lines.append(f"  {k}: {v}")
        return CommandResult("\n".join(lines))
    elif action == "delete":
        if len(args) < 2:
            return CommandResult("Usage: /pref delete <key>", exit_code=1)
        mgr.persistent_memory.delete_preference(args[1])
        return CommandResult(f"Preference deleted: {args[1]}")
    else:
        return CommandResult(f"Unknown action: {action}", exit_code=1)
```

- [ ] **Step 4: Run tests, expect pass**

```bash
pytest tests/unit/memory/test_memory_commands.py -v --no-header
```

- [ ] **Step 5: Commit**

```bash
git add src/nasagent/plugins/commands.py tests/unit/memory/test_memory_commands.py
git commit -m "feat: add /session, /remember, /forget, /memories, /pref slash commands"
```

---

### Task 7: Integrate MemoryManager into Chat REPL

**Files:**
- Modify: `src/nasagent/cli/commands/chat.py`

- [ ] **Step 1: Add imports in `chat.py`**

Add these imports (after existing imports):

```python
from nasagent.memory import MemoryManager
from nasagent.plugins.commands import register_memory_commands
```

- [ ] **Step 2: Modify `chat()` function — add memory initialization after settings loading**

Replace the section after `settings_provider = settings.llm.provider` (line 91) up to `renderer.banner` (line 95):

```python
    # Initialize memory
    memory_manager = MemoryManager(settings.observability.expanded_memory_dir(), None)
    memory_manager.ensure_session("default")
```

- [ ] **Step 3: Modify the slash command handler in `chat()` to register memory commands**

Find the block at line 108-113:
```python
        if task.startswith("/"):
            context = create_platform_context(settings=load_settings())
            load_platform_plugins(context)
            result = context.commands.dispatch(task)
            renderer.agent_message(result.message)
            continue
```

Replace with:
```python
        if task.startswith("/"):
            context = create_platform_context(settings=load_settings())
            load_platform_plugins(context)
            register_memory_commands(context, memory_manager)
            result = context.commands.dispatch(task)
            renderer.agent_message(result.message)
            continue
```

- [ ] **Step 4: Modify `_print_conversation_response` signature and body to use memory**

Replace the function signature at line 162 from:
```python
def _print_conversation_response(
    task: str, *, online: bool | None, stream: bool, renderer: CliRenderer
) -> None:
```
To:
```python
def _print_conversation_response(
    task: str, *, online: bool | None, stream: bool, renderer: CliRenderer,
    memory_manager: MemoryManager,
) -> None:
```

Replace the `messages` assignment from:
```python
    messages = _conversation_messages(task)
```
To:
```python
    messages = [_to_chat_message(m) for m in memory_manager.inject_context()]
```

Add the helper function before `_print_conversation_response`:
```python
def _to_chat_message(msg: dict) -> ChatMessage:
    return ChatMessage(role=msg["role"], content=msg["content"])
```

After receiving the LLM response, add (after `renderer.agent_message(response)` at line 180 and after `renderer.agent_end()` at line 207 in streaming mode):
```python
    memory_manager.conversation_memory.add_message("assistant", response)
```

- [ ] **Step 5: Modify the streaming function signature similarly**

Change `_stream_conversation_response` from:
```python
async def _stream_conversation_response(
    provider: OpenAiProvider, messages: list[ChatMessage], renderer: CliRenderer
) -> None:
```
To:
```python
async def _stream_conversation_response(
    provider: OpenAiProvider, messages: list[ChatMessage], renderer: CliRenderer,
    memory_manager: MemoryManager,
) -> None:
```

After line 195 (empty response case), add:
```python
        memory_manager.conversation_memory.add_message("assistant", "")
```

After line 200 (markdown case) and line 207 (stream end), add:
```python
        memory_manager.conversation_memory.add_message("assistant", "".join(chunks))
```

- [ ] **Step 6: Add conversation recording around task execution in `chat()`**

After the user message check at line 117, add recording and pass memory_manager:
```python
        if not _looks_like_execution_intent(task):
            try:
                memory_manager.conversation_memory.add_message("user", task)
                _print_conversation_response(task, online=online, stream=stream,
                    renderer=renderer, memory_manager=memory_manager)
```

And around task execution at line 126, record messages:
```python
        try:
            with renderer.spinner("system", "planning and running task"):
                memory_manager.conversation_memory.add_message("user", task)
                state = execute_simulator_task(task, online=online)
                memory_manager.conversation_memory.add_message(
                    "assistant", state.final_summary or "Task completed."
                )
```

- [ ] **Step 7: Remove `_conversation_messages` function**

Delete lines 210-220 (the `_conversation_messages` function definition).

- [ ] **Step 8: Verify existing tests still pass**

```bash
pytest tests/unit/ tests/integration/ -v --no-header -x
```

- [ ] **Step 9: Commit**

```bash
git add src/nasagent/cli/commands/chat.py
git commit -m "feat: integrate MemoryManager into chat REPL"
```

---

### Task 8: Integrate MemoryManager into Agent Graph

**Files:**
- Modify: `src/nasagent/agent/graph/builder.py`

- [ ] **Step 1: Modify `plan_node` in `build_agent_graph`**

The `plan_node` currently creates a fresh `Planner` with no memory context. Inject persistent memory into the planner's system prompt.

In `builder.py`, modify `plan_node` (lines 37-40):

```python
    async def plan_node(state: GraphState) -> GraphState:
        tool_names = tuple(tool.name for tool in tool_registry.list())
        memory_text = memory_manager.remember_for_llm() if memory_manager else ""
        planner = Planner(provider=provider, tool_names=tool_names, extra_context=memory_text)
        return {"plan": await planner.create_plan(state["goal"])}
```

Modify `build_agent_graph` signature to accept optional `memory_manager`:

```python
def build_agent_graph(
    adapter: NasAdapter,
    provider: LlmProvider,
    safety_settings: SafetySettings | None = None,
    approval_provider: ApprovalProvider | None = None,
    memory_manager: "MemoryManager | None" = None,
) -> Any:
```

And update `run_agent_once` similarly:

```python
async def run_agent_once(
    goal: str,
    adapter: NasAdapter,
    provider: LlmProvider,
    safety_settings: SafetySettings | None = None,
    run_log_dir: Path | None = None,
    approval_provider: ApprovalProvider | None = None,
    memory_manager: "MemoryManager | None" = None,
) -> AgentState:
    graph = build_agent_graph(
        adapter=adapter,
        provider=provider,
        safety_settings=safety_settings,
        approval_provider=approval_provider,
        memory_manager=memory_manager,
    )
```

- [ ] **Step 2: Modify the Planner class to accept `extra_context`**

In `src/nasagent/agent/planning/planner.py`, modify `Planner.__init__` and `create_plan`:

```python
class Planner:
    def __init__(
        self,
        provider: LlmProvider,
        tool_names: tuple[str, ...] | None = None,
        extra_context: str = "",
    ) -> None:
        self._provider = provider
        self._tool_names = tool_names
        self._extra_context = extra_context

    async def create_plan(self, goal: str) -> Plan:
        system_prompt = (
            build_planner_system_prompt(self._tool_names)
            if self._tool_names is not None
            else build_planner_system_prompt()
        )
        if self._extra_context:
            system_prompt = self._extra_context + "\n\n" + system_prompt
        content = await self._provider.complete(
            [
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=goal),
            ]
        )
        return Plan.model_validate_json(content)
```

- [ ] **Step 3: Verify tests pass**

```bash
pytest tests/unit/agent/ -v --no-header -x
pytest tests/integration/test_agent_graph.py -v --no-header -x
```

- [ ] **Step 4: Commit**

```bash
git add src/nasagent/agent/graph/builder.py src/nasagent/agent/planning/planner.py
git commit -m "feat: integrate MemoryManager into agent graph planning"
```

---

### Task 9: Final Verification

- [ ] **Step 1: Run all tests**

```bash
pytest tests/ -v --no-header
```

Expected: all tests PASS

- [ ] **Step 2: Run linting and type checking**

```bash
ruff check src/nasagent/memory/ tests/unit/memory/
mypy src/nasagent/memory/ --ignore-missing-imports
```

- [ ] **Step 3: Commit any remaining changes**

```bash
git status
git add -A
git commit -m "chore: final verification and cleanup for memory system"
```
