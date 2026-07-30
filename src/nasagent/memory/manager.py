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
