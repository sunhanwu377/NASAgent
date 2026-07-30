import asyncio
import atexit
import locale
import re
import readline
import sys
import tomllib
from pathlib import Path

import typer

from nasagent.cli.commands.run import execute_simulator_task
from nasagent.cli.rendering.renderer import CliRenderer, looks_like_markdown
from nasagent.config.settings import default_config_path, load_settings
from nasagent.llm.messages import ChatMessage
from nasagent.llm.openai_provider import OpenAiProvider
from nasagent.memory import MemoryManager
from nasagent.platform.context import create_platform_context
from nasagent.platform.plugins import load_platform_plugins
from nasagent.plugins.commands import register_memory_commands

GREETING_INPUTS = {"hello", "hi", "hey", "你好", "您好", "嗨"}
ENGLISH_TASK_ACTION_KEYWORDS = {
    "check",
    "show",
    "get",
    "list",
    "search",
    "upload",
    "download",
    "delete",
}
CHINESE_TASK_ACTION_KEYWORDS = {
    "查看",
    "检查",
    "获取",
    "列出",
    "搜索",
    "上传",
    "下载",
    "删除",
}
TASK_RESOURCE_KEYWORDS = {
    "nas",
    "storage",
    "device",
    "status",
    "file",
    "files",
    "folder",
    "folders",
    "directory",
    "directories",
    "share",
    "shares",
    "volume",
    "volumes",
    "disk",
    "disks",
    "drive",
    "drives",
    "pool",
    "pools",
    "存储",
    "设备",
    "状态",
    "文件",
    "文件夹",
    "目录",
    "共享",
    "卷",
    "磁盘",
    "硬盘",
}


def chat(
    profile: str = typer.Option("simulator", "--profile"),
    online: bool | None = typer.Option(
        None,
        "--online/--offline",
        help="Use configured OpenAI-compatible LLM or force deterministic offline planner.",
    ),
    stream: bool = typer.Option(
        True,
        "--stream/--no-stream",
        help="Stream conversational LLM responses as they are generated.",
    ),
    tui: bool = typer.Option(
        True,
        "--tui/--no-tui",
        help="Use Textual TUI interface instead of simple REPL.",
    ),
) -> None:
    if tui:
        from nasagent.cli.tui.app import NasaGentTui

        app = NasaGentTui()
        app.run()
        return

    if profile != "simulator":
        raise typer.BadParameter(
            "Only simulator profile is available before real UGREEN API details are configured"
        )
    renderer = CliRenderer()
    settings_provider = None
    try:
        settings = load_settings()
        settings_provider = settings.llm.provider
    except tomllib.TOMLDecodeError as exc:
        config_path = default_config_path()
        renderer.config_error(config_path, exc)
        raise typer.Exit(1) from exc
    # Initialize memory
    memory_dir = settings.observability.expanded_memory_dir()
    memory_manager = MemoryManager(memory_dir, None)
    memory_manager.ensure_session("default")

    # Initialize command history
    _configure_readline()
    _init_readline_history(memory_dir / "history")

    renderer.banner(profile=profile, provider=settings_provider, streaming=stream)
    while True:
        renderer.prompt()
        try:
            task = input()
        except EOFError:
            break
        if task.strip():
            readline.add_history(task)
        task = task.strip()
        if task:
            renderer.user_input(task)
        if task.lower() in {"exit", "quit"}:
            renderer.status("Goodbye")
            break
        if not task:
            continue
        if task.startswith("/"):
            context = create_platform_context(settings=load_settings())
            load_platform_plugins(context)
            register_memory_commands(context, memory_manager)
            result = context.commands.dispatch(task)
            renderer.agent_message(result.message)
            continue
        if response := _local_chat_response(task):
            renderer.agent_message(response)
            continue
        if not _looks_like_execution_intent(task):
            try:
                if memory_manager.conversation_memory:
                    memory_manager.conversation_memory.add_message("user", task)
                _print_conversation_response(
                    task,
                    online=online,
                    stream=stream,
                    renderer=renderer,
                    memory_manager=memory_manager,
                )
            except tomllib.TOMLDecodeError as exc:
                config_path = default_config_path()
                renderer.config_error(config_path, exc)
                raise typer.Exit(1) from exc
            continue
        try:
            with renderer.spinner("system", "planning and running task"):
                if memory_manager.conversation_memory:
                    memory_manager.conversation_memory.add_message("user", task)
                state = execute_simulator_task(task, online=online)
                if memory_manager.conversation_memory:
                    memory_manager.conversation_memory.add_message(
                        "assistant", state.final_summary or "Task completed."
                    )
        except tomllib.TOMLDecodeError as exc:
            config_path = default_config_path()
            renderer.config_error(config_path, exc)
            raise typer.Exit(1) from exc
        if state.plan is not None:
            renderer.success(f"plan ready · {len(state.plan.steps)} step(s)")
        for step_result in state.step_results:
            for tool_result in step_result.tool_results:
                renderer.tool(tool_result.tool_name, completed=True)
        renderer.success("done")
        renderer.task_result(state)


def _local_chat_response(task: str) -> str | None:
    normalized = task.casefold().strip(" !?.。！？")
    if normalized in GREETING_INPUTS:
        return "Hello. I can help with NAS operations like checking storage or device status."
    return None


def _looks_like_execution_intent(task: str) -> bool:
    normalized = task.casefold()
    has_action = any(
        re.search(rf"\b{re.escape(keyword)}\b", normalized)
        for keyword in ENGLISH_TASK_ACTION_KEYWORDS
    ) or any(keyword in normalized for keyword in CHINESE_TASK_ACTION_KEYWORDS)
    has_resource = any(
        re.search(rf"\b{re.escape(keyword)}\b", normalized)
        for keyword in TASK_RESOURCE_KEYWORDS
        if keyword.isascii()
    ) or any(keyword in normalized for keyword in TASK_RESOURCE_KEYWORDS if not keyword.isascii())
    return has_action and has_resource


def _to_chat_message(msg: dict) -> ChatMessage:
    return ChatMessage(role=msg["role"], content=msg["content"])


def _print_conversation_response(
    task: str,
    *,
    online: bool | None,
    stream: bool,
    renderer: CliRenderer,
    memory_manager: MemoryManager,
) -> None:
    settings = load_settings()
    use_online = online if online is not None else settings.llm.api_key is not None
    if not use_online:
        renderer.agent_message(
            "I can chat when an LLM is configured. "
            "For NAS tasks, ask me to check storage or device status."
        )
        return
    provider = OpenAiProvider(settings.llm)
    messages = [_to_chat_message(m) for m in memory_manager.inject_context()]
    if stream:
        asyncio.run(_stream_conversation_response(provider, messages, renderer, memory_manager))
        return
    with renderer.spinner("system", "waiting for LLM"):
        response = asyncio.run(provider.complete(messages))
    renderer.agent_message(response)
    if memory_manager.conversation_memory:
        memory_manager.conversation_memory.add_message("assistant", response)


async def _stream_conversation_response(
    provider: OpenAiProvider,
    messages: list[ChatMessage],
    renderer: CliRenderer,
    memory_manager: MemoryManager,
) -> None:
    stream = provider.stream_complete(messages)
    chunks: list[str] = []
    with renderer.spinner("system", "waiting for LLM"):
        for _ in range(2):
            try:
                chunks.append(await anext(stream))
            except StopAsyncIteration:
                break
    if not chunks:
        renderer.agent_message("")
        if memory_manager.conversation_memory:
            memory_manager.conversation_memory.add_message("assistant", "")
        return
    if looks_like_markdown("".join(chunks)):
        async for chunk in stream:
            chunks.append(chunk)
        full = "".join(chunks)
        renderer.agent_message(full)
        if memory_manager.conversation_memory:
            memory_manager.conversation_memory.add_message("assistant", full)
        return
    renderer.agent_start()
    for chunk in chunks:
        renderer.agent_chunk(chunk)
    async for chunk in stream:
        renderer.agent_chunk(chunk)
    renderer.agent_end()
    if memory_manager.conversation_memory:
        memory_manager.conversation_memory.add_message("assistant", "".join(chunks))


HISTORY_LIMIT = 1000


def _configure_readline() -> None:
    try:
        locale.setlocale(locale.LC_ALL, "")
    except locale.Error:
        pass
    if sys.platform == "darwin":
        try:
            readline.parse_and_bind("set byte-oriented off")
        except Exception:
            pass


def _init_readline_history(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        readline.read_history_file(str(path))
    except FileNotFoundError:
        pass
    readline.set_history_length(HISTORY_LIMIT)
    atexit.register(readline.write_history_file, str(path))
