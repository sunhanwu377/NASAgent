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
