import asyncio

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from nasagent.web.templates import get_templates

router = APIRouter(tags=["chat"])


@router.get("/", response_class=HTMLResponse)
async def chat_page(request: Request):
    return get_templates().TemplateResponse("chat.html", {"request": request})


@router.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            text = await websocket.receive_text()
            await websocket.send_json({"type": "system", "content": f"Received: {text}. Agent processing..."})
            await asyncio.sleep(0.5)
            await websocket.send_json({"type": "agent", "content": f"Echo: {text}"})
    except WebSocketDisconnect:
        pass
