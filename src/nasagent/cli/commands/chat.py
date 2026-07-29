import asyncio
import re
import tomllib

import typer

from nasagent.cli.commands.run import execute_simulator_task
from nasagent.cli.rendering.renderer import CliRenderer, looks_like_markdown
from nasagent.config.settings import default_config_path, load_settings
from nasagent.llm.messages import ChatMessage
from nasagent.llm.openai_provider import OpenAiProvider

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
) -> None:
    if profile != "simulator":
        raise typer.BadParameter(
            "Only simulator profile is available before real UGREEN API details are configured"
        )
    renderer = CliRenderer()
    settings_provider = None
    try:
        settings_provider = load_settings().llm.provider
    except tomllib.TOMLDecodeError as exc:
        config_path = default_config_path()
        renderer.config_error(config_path, exc)
        raise typer.Exit(1) from exc
    renderer.banner(profile=profile, provider=settings_provider, streaming=stream)
    while True:
        renderer.prompt()
        try:
            task = input()
        except EOFError:
            break
        task = task.strip()
        if task.lower() in {"exit", "quit"}:
            renderer.status("Goodbye")
            break
        if not task:
            continue
        if response := _local_chat_response(task):
            renderer.agent_message(response)
            continue
        if not _looks_like_execution_intent(task):
            try:
                _print_conversation_response(task, online=online, stream=stream, renderer=renderer)
            except tomllib.TOMLDecodeError as exc:
                config_path = default_config_path()
                renderer.config_error(config_path, exc)
                raise typer.Exit(1) from exc
            continue
        try:
            with renderer.spinner("system", "planning and running task"):
                state = execute_simulator_task(task, online=online)
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


def _print_conversation_response(
    task: str, *, online: bool | None, stream: bool, renderer: CliRenderer
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
    messages = _conversation_messages(task)
    if stream:
        asyncio.run(_stream_conversation_response(provider, messages, renderer))
        return
    with renderer.spinner("system", "waiting for LLM"):
        response = asyncio.run(provider.complete(messages))
    renderer.agent_message(response)


async def _stream_conversation_response(
    provider: OpenAiProvider, messages: list[ChatMessage], renderer: CliRenderer
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
        return
    if looks_like_markdown("".join(chunks)):
        async for chunk in stream:
            chunks.append(chunk)
        renderer.agent_message("".join(chunks))
        return
    renderer.agent_start()
    for chunk in chunks:
        renderer.agent_chunk(chunk)
    async for chunk in stream:
        renderer.agent_chunk(chunk)
    renderer.agent_end()


def _conversation_messages(task: str) -> list[ChatMessage]:
    return [
        ChatMessage(
            role="system",
            content=(
                "You are NASAgent's chat assistant. Answer conversational questions "
                "directly. Do not claim that tools were executed."
            ),
        ),
        ChatMessage(role="user", content=task),
    ]
