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
        with open(path, encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            result = json.load(f)
            fcntl.flock(f, fcntl.LOCK_UN)
        return result

    def _write_json(self, path: Path, data: object) -> None:
        with open(path, "w", encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            json.dump(data, f, indent=2, default=str)
            fcntl.flock(f, fcntl.LOCK_UN)
