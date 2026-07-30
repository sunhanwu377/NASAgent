from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from nasagent.config.settings import load_settings
from nasagent.llm.messages import ChatMessage
from nasagent.llm.openai_provider import OpenAiProvider
from nasagent.memory import MemoryManager
from nasagent.web.templates import get_templates

router = APIRouter(tags=["chat"])


@router.get("/", response_class=HTMLResponse)
async def chat_page(request: Request):
    return get_templates().TemplateResponse(request, "chat.html", {"request": request})


class WebSocketStreamCallback:
    def __init__(self, ws: WebSocket):
        self._ws = ws
        self._chunks: list[str] = []

    async def _send(self, msg_type: str, content: str):
        await self._ws.send_json({"type": msg_type, "content": content})

    async def on_plan_start(self) -> None:
        await self._send("system", "Planning...")

    async def on_plan_ready(self, step_count: int) -> None:
        await self._send("system", f"Plan ready · {step_count} step(s)")

    async def on_step_start(self, step_id: str, description: str) -> None:
        await self._send("system", f"Step: {description}")

    async def on_tool_start(self, tool_name: str) -> None:
        await self._send("system", f"Tool: {tool_name}")

    async def on_tool_done(self, tool_name: str) -> None:
        await self._send("system", f"Tool completed: {tool_name}")

    async def on_summary(self, summary: str) -> None:
        await self._send("agent", summary)

    async def on_error(self, error: str) -> None:
        await self._send("error", error)

    async def on_stream_chunk(self, chunk: str) -> None:
        self._chunks.append(chunk)


@router.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket):
    await websocket.accept()
    settings = load_settings()
    memory_dir = settings.observability.expanded_memory_dir()
    memory_manager = MemoryManager(memory_dir, None)
    memory_manager.ensure_session("default")

    try:
        while True:
            text = await websocket.receive_text()
            await websocket.send_json({"type": "user", "content": text})

            provider = OpenAiProvider(settings.llm)
            messages = [ChatMessage(**m) for m in memory_manager.inject_context()]
            messages.append(ChatMessage(role="user", content=text))

            try:
                response = await provider.complete(messages)
                await websocket.send_json({"type": "agent", "content": response})
                if memory_manager.conversation_memory:
                    memory_manager.conversation_memory.add_message("user", text)
                    memory_manager.conversation_memory.add_message("assistant", response)
            except Exception as e:
                await websocket.send_json({"type": "error", "content": str(e)})
    except WebSocketDisconnect:
        pass
