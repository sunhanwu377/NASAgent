# Memory System Design

Date: 2026-07-30
Status: Draft

## Overview

NASAgent 当前没有记忆系统——chat REPL 每次交互都是无状态的，运行结果以独立 JSON 文件保存但互不关联。本设计引入分层记忆架构，支持多轮对话上下文和跨会话持久记忆。

## Requirements

1. **多轮对话记忆**：同一会话内保留对话历史，agent 能引用之前的上下文
2. **跨会话持久记忆**：用户偏好、知识等信息在多次启动间保留
3. **命名会话**：支持创建、切换、列出、删除多个命名会话
4. **自动摘要**：对话历史超阈值时，LLM 自动压缩早期对话为摘要
5. **纯文件存储**：JSON 文件存储，复用现有 RunStateStore 的文件模式，零额外依赖

## Architecture

### Directory Layout

```
src/nasagent/memory/           # 新增模块
├── __init__.py                # 导出 MemoryManager
├── models.py                  # Pydantic 数据模型
├── conversation.py            # ConversationMemory - 短期对话记忆
├── persistent.py              # PersistentMemory - 长期持久记忆
├── session.py                 # SessionStore - 命名会话管理
└── manager.py                 # MemoryManager - 统一门面

存储目录结构（~/.nasagent/memory/）：
├── sessions.json              # 会话索引
├── _current                   # 当前活跃会话 ID
├── sessions/
│   └── <session_id>/
│       ├── messages.json      # 对话历史
│       └── summary.json       # 自动摘要
└── persistent/
    ├── memories.json          # 自由文本持久记忆
    └── preferences.json       # 结构化偏好
```

### Component Design

#### 1. Data Models (`models.py`)

```python
class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)

class Conversation(BaseModel):
    messages: list[Message] = Field(default_factory=list)
    summary: str | None = None
    summary_index: int = 0          # 摘要覆盖到的消息索引

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

#### 2. ConversationMemory (`conversation.py`)

管理当前会话的消息窗口 + 自动摘要。

- `add_message(role, content)`: 追加消息，每次写盘
- `get_messages_for_llm() -> list[dict]`: 返回 LLM 可用格式（摘要 + 窗口消息）
- `maybe_summarize()`: 超过 `summary_threshold`（默认 30 条）时，调用 LLM 生成摘要，替换早期消息
- 持久化到 `{session_path}/messages.json` 和 `summary.json`

摘要流程：
1. 当 `len(messages) - summary_index > threshold` 时触发
2. 取 `[summary_index, summary_index + threshold)` 范围消息调用 LLM
3. 用生成的摘要文本 + 窗口内剩余消息替换，更新 `summary_index`

配置：`max_messages=50`（窗口上限），`summary_threshold=30`（摘要触发阈值）

#### 3. PersistentMemory (`persistent.py`)

跨会话持久记忆。

- `remember(content, tags)`: 添加自由文本记忆
- `forget(entry_id)`: 删除记忆
- `recall(query=None, tags=None)`: 关键词匹配检索（后续可升级 embedding）
- `set_preference(key, value)`: 设置偏好，支持嵌套 key 如 `"nas.default_device"`
- `get_preference(key, default=None)`: 获取偏好
- `delete_preference(key)`: 删除偏好
- `get_all_preferences()`: 返回全部偏好

#### 4. SessionStore (`session.py`)

命名会话管理。

- `create(name) -> SessionMeta`
- `get_current() -> SessionMeta | None`
- `switch(session_id) -> SessionMeta`
- `list_all() -> list[SessionMeta]`
- `delete(session_id)`
- `touch()`: 更新 `last_active_at`

当前活跃会话通过 `~/.nasagent/memory/_current` 文件记录。

#### 5. MemoryManager (`manager.py`)

统一门面，注入到 Agent 和 Chat CLI。

```python
class MemoryManager:
    def __init__(self, storage_dir: Path, llm_provider):
        self.storage_dir = storage_dir
        self.session_store = SessionStore(storage_dir)    # 内部管理 index + sessions/
        self.persistent_memory = PersistentMemory(storage_dir / "persistent")
        self.conversation_memory: ConversationMemory | None = None

    def ensure_session(self, name: str | None = None) -> SessionMeta
    def remember_for_llm(self) -> str                    # 持久记忆转 system prompt 文本
    def inject_context(self) -> list[dict]                # 聚合 conversation + persistent
```

### Integration Points

#### Chat REPL (`cli/commands/chat.py`)

- 启动时初始化 `MemoryManager(storage_dir, provider)`
- 替换现有 `_conversation_messages()` 为 `memory_manager.inject_context()`
- 每次用户消息和 agent 回复后调用 `conversation_memory.add_message()`

#### Agent Graph (`agent/graph/builder.py`)

- `plan_node` 从 `MemoryManager` 获取持久记忆注入到 planner 的 system prompt
- 执行完成后 `conversation_memory.add_message()` 记录执行结果摘要

#### New Slash Commands

| Command | Description |
|---------|-------------|
| `/session new <name>` | 创建新会话并切换 |
| `/session switch <name>` | 切换到指定会话 |
| `/session list` | 列出现有会话 |
| `/session delete <name>` | 删除会话 |
| `/remember <content>` | 添加持久记忆 |
| `/forget <id>` | 删除持久记忆 |
| `/memories` | 列出所有持久记忆 |
| `/pref set <key> <value>` | 设置偏好 |
| `/pref get <key>` | 获取偏好 |
| `/pref list` | 列出所有偏好 |
| `/pref delete <key>` | 删除偏好 |

### Data Flow

```
User Input
    │
    ▼
MemoryManager.inject_context()
    ├── persistent_memory.remember_for_llm()  → system prompt
    ├── conversation_memory.get_messages_for_llm()  → message history
    └── returns [system_msg, ...history, user_msg]
    │
    ▼
LLM / Agent Graph
    │
    ▼
MemoryManager conversation_memory.add_message(user_msg)
MemoryManager conversation_memory.add_message(assistant_msg)
    │
    ▼
conversation_memory.maybe_summarize()  (check threshold)
    │
    ▼
Persist to disk
```

### Concurrency

单用户 CLI 场景，使用文件锁（`fcntl.flock`）保护读写操作，避免异常退出导致的数据损坏：

```python
import fcntl

def _atomic_write(path: Path, data: str):
    with open(path, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(data)
        fcntl.flock(f, fcntl.LOCK_UN)
```

### Error Handling

- 文件读写失败：记录警告日志，降级为内存操作（丢失持久化但不中断使用）
- 摘要 LLM 调用失败：跳过本次摘要，在下次超阈值时重试
- 会话目录损坏：自动创建新会话，旧会话标记为 corrupted

### Testing Strategy

- **单元测试**：每个组件独立测试（Mock LLM provider, 临时目录作为存储）
  - `ConversationMemory`：消息添加、窗口管理、摘要触发/压缩
  - `PersistentMemory`：CRUD 操作、关键词检索、嵌套 key 偏好
  - `SessionStore`：创建/切换/列表/删除 + 并发安全
- **集成测试**：`MemoryManager` 端到端 + 与 agent graph 集成
- **现有测试**：确保 chat REPL 和 agent runner 的已有测试不受影响

### Non-Goals

- 不实现 embedding 向量检索（第一阶段用关键词匹配）
- 不实现记忆过期/自动清理策略（用户手动管理）
- 不支持多用户/多进程并发（单用户 CLI 场景）
- 不实现自动记忆提取（LLM 从对话中提取事实存入持久记忆，列为后续迭代）
