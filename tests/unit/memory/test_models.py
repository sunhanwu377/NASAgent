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
