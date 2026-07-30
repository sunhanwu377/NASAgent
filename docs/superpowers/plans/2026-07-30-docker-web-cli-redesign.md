# Docker + Web + CLI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Docker deployment, Web service with config UI, and Textual TUI CLI — all sharing the same agent core.

**Architecture:** `nasagent.agent` remains the shared core called by both `nasagent.cli` (Textual TUI) and `nasagent.web` (FastAPI + Jinja2 + WebSocket). Streaming callbacks enable real-time output in both frontends. Docker packs the web server; pip install gives the CLI tool.

**Tech Stack:** Python 3.11, Textual, FastAPI, Jinja2, WebSocket via `websockets`, uv, Docker

---

### Task 1: Create Feature Branch

**Files:** none (git operation)

- [ ] **Step 1: Create the feature branch from main**

```bash
git checkout main
git checkout -b feat/docker-web-cli
```

Expected: new branch `feat/docker-web-cli` created.

- [ ] **Step 2: Push branch to remote**

```bash
git push -u origin feat/docker-web-cli
```

- [ ] **Step 3: Commit**

```bash
# No code changes, branch created
```

---

### Task 2: Update pyproject.toml with New Dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add textual, fastapi, websockets, jinja2 to dependencies and optional-deps**

Read the current `pyproject.toml` and update the `[project]` table:

```toml
[project]
name = "nasagent"
version = "0.1.0"
description = "CLI AI agent for operating NAS devices"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
  "docker>=7.1",
  "httpx>=0.27",
  "langchain-core>=0.3",
  "langgraph>=0.2",
  "openai>=1.0",
  "pydantic>=2.7",
  "pydantic-settings>=2.3",
  "rich>=13.7",
  "socksio>=1.0",
  "textual>=1.0",
  "typer>=0.12",
]

[project.optional-dependencies]
dev = [
  "mypy>=1.10",
  "pytest>=8.2",
  "pytest-asyncio>=0.23",
  "pytest-cov>=5.0",
  "pytest-httpx>=0.30",
  "ruff>=0.5",
]
web = [
  "fastapi>=0.115",
  "uvicorn[standard]>=0.30",
  "jinja2>=3.1",
  "python-multipart>=0.0.9",
]
ugreen = []

[project.scripts]
nasagent = "nasagent.cli.app:app"
nasagent-web = "nasagent.web.server:main"
```

- [ ] **Step 2: Run uv sync to verify**

```bash
uv sync --all-extras --dev
```

Expected: succeeds, all new packages installed.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: add textual, fastapi, websockets, jinja2 dependencies"
```

---

### Task 3: Create Dockerfile

**Files:**
- Create: `docker/Dockerfile`

- [ ] **Step 1: Create the Dockerfile**

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.5.18 /uv /usr/local/bin/uv

WORKDIR /app

ENV UV_PROJECT_ENVIRONMENT=/usr/local

COPY pyproject.toml uv.lock ./
RUN uv sync --extra web --frozen --no-dev

COPY src/ ./src/

ENV NASAGENT_OBSERVABILITY__RUN_LOG_DIR=/data/runs
ENV NASAGENT_OBSERVABILITY__MEMORY_DIR=/data/memory

VOLUME ["/root/.config/nasagent", "/root/.local/share/nasagent", "/data"]

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["nasagent-web"]
```

- [ ] **Step 2: Build Docker image locally to verify it builds**

```bash
docker build -t nasagent:local -f docker/Dockerfile .
```

Expected: image builds successfully.

- [ ] **Step 3: Commit**

```bash
git add docker/Dockerfile
git commit -m "feat: add Dockerfile for NAS deployment"
```

---

### Task 4: Create docker-compose.yml

**Files:**
- Create: `docker/docker-compose.yml`

- [ ] **Step 1: Create docker-compose.yml**

```yaml
version: "3.9"

services:
  nasagent:
    image: ghcr.io/nasagent/nasagent:latest
    container_name: nasagent
    ports:
      - "8000:8000"
    volumes:
      - nasagent_config:/root/.config/nasagent
      - nasagent_secrets:/root/.local/share/nasagent
      - nasagent_data:/data
      - /var/run/docker.sock:/var/run/docker.sock
    restart: unless-stopped
    environment:
      - TZ=Asia/Shanghai

volumes:
  nasagent_config:
  nasagent_secrets:
  nasagent_data:
```

- [ ] **Step 2: Commit**

```bash
git add docker/docker-compose.yml
git commit -m "feat: add docker-compose for NAS deployment"
```

---

### Task 5: Add GitHub Release Workflow (Docker Build + Push)

**Files:**
- Create: `.github/workflows/release.yml`

- [ ] **Step 1: Create release workflow**

```yaml
name: Release

on:
  release:
    types: [published]

env:
  REGISTRY: ghcr.io

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ github.repository }}
          tags: |
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=raw,value=latest,enable={{is_default_branch}}

      - name: Build and push Docker image
        uses: docker/build-push-action@v6
        with:
          context: .
          file: docker/Dockerfile
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "ci: add GitHub release workflow for Docker build and push"
```

---

### Task 6: Add Gitea Release Workflow (Docker Build + Push)

**Files:**
- Create: `.gitea/workflows/release.yml`

- [ ] **Step 1: Create Gitea release workflow**

```yaml
name: Release

on:
  release:
    types: [published]

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    container:
      image: catthehacker/ubuntu:act-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to Gitea Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.GITEA_SERVER_URL }}
          username: ${{ gitea.actor }}
          password: ${{ secrets.GITEA_TOKEN }}

      - name: Extract metadata
        id: meta
        run: |
          echo "tags=${{ env.GITEA_SERVER_URL }}/${GITHUB_REPOSITORY_OWNER,,}/nasagent:${{ github.ref_name }}" >> $GITHUB_OUTPUT
          echo "tags=${{ env.GITEA_SERVER_URL }}/${GITHUB_REPOSITORY_OWNER,,}/nasagent:latest" >> $GITHUB_OUTPUT

      - name: Build and push Docker image
        uses: docker/build-push-action@v6
        with:
          context: .
          file: docker/Dockerfile
          push: true
          tags: ${{ steps.meta.outputs.tags }}
```

- [ ] **Step 2: Commit**

```bash
git add .gitea/workflows/release.yml
git commit -m "ci: add Gitea release workflow for Docker build and push"
```

---

### Task 7: Enhance GitHub + Gitea CI for PR Static Checks

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `.gitea/workflows/ci.yml`

- [ ] **Step 1: Update GitHub CI to ensure PR trigger is explicit**

Read `.github/workflows/ci.yml` (currently triggers on push and pull_request — stays the same). No structural change needed; the existing `ruff check`, `ruff format --check`, `pytest`, `mypy` already cover static checks and tests on PR. Add a name clarifying it's the PR check job:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint-and-test:
    name: Lint & Test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: uv sync --all-extras --dev
      - run: uv run ruff check .
      - run: uv run ruff format --check .
      - run: uv run pytest
      - run: uv run mypy src
```

- [ ] **Step 2: Apply same update to `.gitea/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint-and-test:
    name: Lint & Test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: uv sync --all-extras --dev
      - run: uv run ruff check .
      - run: uv run ruff format --check .
      - run: uv run pytest
      - run: uv run mypy src
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml .gitea/workflows/ci.yml
git commit -m "ci: enhance CI with explicit branch filters and job naming"
```

---

### Task 8: Extract Shared Agent Runner Interface

**Files:**
- Create: `src/nasagent/agent/runner.py`
- Modify: `src/nasagent/cli/commands/run.py` (import from new module)
- Modify: `src/nasagent/cli/commands/chat.py` (import from new module)

The goal is a streaming callback interface so both CLI and Web can receive intermediate outputs.

- [ ] **Step 1: Create `src/nasagent/agent/runner.py` with streaming callbacks**

```python
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from nasagent.agent.state.models import AgentState
from nasagent.config.settings import SafetySettings
from nasagent.llm.base import LlmProvider
from nasagent.llm.messages import ChatMessage
from nasagent.nas.base import NasAdapter
from nasagent.safety.approvals import ApprovalProvider


class AgentStreamCallback(Protocol):
    def on_plan_start(self) -> None: ...
    def on_plan_ready(self, step_count: int) -> None: ...
    def on_step_start(self, step_id: str, description: str) -> None: ...
    def on_tool_start(self, tool_name: str) -> None: ...
    def on_tool_done(self, tool_name: str) -> None: ...
    def on_summary(self, summary: str) -> None: ...
    def on_error(self, error: str) -> None: ...
    def on_stream_chunk(self, chunk: str) -> None: ...


@dataclass
class LogStreamCallback:
    events: list[str] = field(default_factory=list)

    def on_plan_start(self) -> None:
        self.events.append("plan_start")

    def on_plan_ready(self, step_count: int) -> None:
        self.events.append(f"plan_ready:{step_count}")

    def on_step_start(self, step_id: str, description: str) -> None:
        self.events.append(f"step_start:{step_id}:{description}")

    def on_tool_start(self, tool_name: str) -> None:
        self.events.append(f"tool_start:{tool_name}")

    def on_tool_done(self, tool_name: str) -> None:
        self.events.append(f"tool_done:{tool_name}")

    def on_summary(self, summary: str) -> None:
        self.events.append(f"summary:{summary[:100]}")

    def on_error(self, error: str) -> None:
        self.events.append(f"error:{error}")

    def on_stream_chunk(self, chunk: str) -> None:
        self.events.append(f"chunk:{chunk}")


async def run_agent_with_callback(
    goal: str,
    adapter: NasAdapter,
    provider: LlmProvider,
    safety_settings: SafetySettings | None = None,
    run_log_dir: Path | None = None,
    approval_provider: ApprovalProvider | None = None,
    stream: AgentStreamCallback | None = None,
) -> AgentState:
    from nasagent.agent.graph.builder import build_agent_graph
    from nasagent.agent.state.models import AgentState as AS
    from nasagent.agent.state.store import RunStateStore
    from nasagent.config.settings import NasAgentSettings
    from uuid import uuid4

    cb = stream or LogStreamCallback()
    cb.on_plan_start()

    graph = build_agent_graph(
        adapter=adapter,
        provider=provider,
        safety_settings=safety_settings,
        approval_provider=approval_provider,
    )

    raw_state = await graph.ainvoke({"goal": goal})

    plan = raw_state.get("plan")
    if plan is not None:
        cb.on_plan_ready(len(plan.steps))
        for step in plan.steps:
            cb.on_step_start(step.id, step.description)

    step_results = raw_state.get("step_results", [])
    for step_result in step_results:
        for tool_result in step_result.tool_results:
            cb.on_tool_done(tool_result.tool_name)

    state = AS(
        goal=raw_state["goal"],
        plan=plan,
        step_results=step_results,
        final_summary=raw_state.get("final_summary", ""),
    )

    cb.on_summary(state.final_summary)

    directory = run_log_dir or NasAgentSettings().observability.expanded_run_log_dir()
    RunStateStore(directory).save(str(uuid4()), state)
    return state
```

- [ ] **Step 2: Update `src/nasagent/cli/commands/run.py` to use new runner**

Add import and update `execute_simulator_task`:

```python
from nasagent.agent.runner import run_agent_with_callback


# Replace the body of execute_simulator_task:
def execute_simulator_task(
    task: str,
    settings: NasAgentSettings | None = None,
    *,
    online: bool | None = None,
    provider_factory: ProviderFactory = default_online_provider_factory,
) -> AgentState:
    active_settings = settings or load_settings()
    return asyncio.run(
        run_agent_with_callback(
            task,
            adapter=SimulatorNasAdapter(),
            provider=select_planner_provider(
                task,
                active_settings,
                online=online,
                provider_factory=provider_factory,
            ),
            safety_settings=active_settings.safety,
            run_log_dir=active_settings.observability.expanded_run_log_dir(),
        )
    )
```

- [ ] **Step 3: Run existing tests to verify refactor doesn't break anything**

```bash
uv run pytest tests/ -v
```

Expected: all existing tests pass.

- [ ] **Step 4: Commit**

```bash
git add src/nasagent/agent/runner.py src/nasagent/cli/commands/run.py
git commit -m "refactor: extract shared agent runner with streaming callback"
```

---

### Task 9: Create Web Module — FastAPI Server Entry Point

**Files:**
- Create: `src/nasagent/web/__init__.py`
- Create: `src/nasagent/web/server.py`

- [ ] **Step 1: Create `src/nasagent/web/__init__.py`**

```python
"""NASAgent Web server module."""
```

- [ ] **Step 2: Create `src/nasagent/web/server.py`**

```python
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from nasagent.web.routes import chat as chat_routes
from nasagent.web.routes import config as config_routes
from nasagent.web.routes import health as health_routes


def create_app() -> FastAPI:
    app = FastAPI(title="NASAgent", version="0.1.0")

    static_dir = Path(__file__).parent / "static"
    templates_dir = Path(__file__).parent / "templates"

    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    app.include_router(health_routes.router)
    app.include_router(chat_routes.router)
    app.include_router(config_routes.router, prefix="/settings")

    from nasagent.web.templates import configure_templates

    configure_templates(app, str(templates_dir))

    return app


def main():
    import uvicorn

    uvicorn.run("nasagent.web.server:create_app", host="0.0.0.0", port=8000, factory=True)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run ruff check to verify syntax**

```bash
uv run ruff check src/nasagent/web/
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add src/nasagent/web/__init__.py src/nasagent/web/server.py
git commit -m "feat: add FastAPI web server entry point"
```

---

### Task 10: Create Web Templates Module

**Files:**
- Create: `src/nasagent/web/templates.py`
- Create: `src/nasagent/web/templates/base.html`
- Create: `src/nasagent/web/templates/chat.html`

- [ ] **Step 1: Create `src/nasagent/web/templates.py`**

```python
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates


templates: Jinja2Templates | None = None


def configure_templates(app: FastAPI, templates_dir: str) -> None:
    global templates
    templates = Jinja2Templates(directory=templates_dir)


def get_templates() -> Jinja2Templates:
    if templates is None:
        raise RuntimeError("Templates not configured")
    return templates
```

- [ ] **Step 2: Create `src/nasagent/web/templates/base.html`**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NASAgent - {% block title %}Home{% endblock %}</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <header class="topbar">
        <div class="topbar-left">
            <a href="/" class="logo">NASAgent</a>
            <span class="version">v0.1.0</span>
        </div>
        <nav class="topbar-nav">
            <a href="/" class="{% if request.url.path == '/' %}active{% endif %}">Chat</a>
            <a href="/settings" class="{% if request.url.path.startswith('/settings') %}active{% endif %}">Settings</a>
        </nav>
    </header>
    <main class="main-content">
        {% block content %}{% endblock %}
    </main>
</body>
</html>
```

- [ ] **Step 3: Create `src/nasagent/web/templates/chat.html`**

```html
{% extends "base.html" %}
{% block title %}Chat{% endblock %}
{% block content %}
<div class="chat-container">
    <div class="chat-messages" id="chat-messages">
        <div class="message system">Welcome to NASAgent. Type a message to get started.</div>
    </div>
    <div class="chat-input-bar">
        <form id="chat-form" class="chat-form">
            <input type="text" id="chat-input" placeholder="Type your message..." autocomplete="off" autofocus>
            <button type="submit">Send</button>
        </form>
    </div>
    <div class="chat-status" id="chat-status">
        <span id="profile-label">Profile: simulator</span>
        <span id="llm-label">LLM: offline</span>
    </div>
</div>

<script>
const ws = new WebSocket(`ws://${location.host}/ws/chat`);
const messagesEl = document.getElementById('chat-messages');
const form = document.getElementById('chat-form');
const input = document.getElementById('chat-input');
const statusEl = document.getElementById('chat-status');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    const div = document.createElement('div');
    div.className = `message ${data.type}`;
    div.textContent = `${data.type}: ${data.content}`;
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
};

form.onsubmit = (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    const div = document.createElement('div');
    div.className = 'message user';
    div.textContent = `you: ${text}`;
    messagesEl.appendChild(div);
    ws.send(text);
    input.value = '';
    messagesEl.scrollTop = messagesEl.scrollHeight;
};
</script>
{% endblock %}
```

- [ ] **Step 4: Commit**

```bash
git add src/nasagent/web/templates.py src/nasagent/web/templates/base.html src/nasagent/web/templates/chat.html
git commit -m "feat: add web templates — base layout and chat page with WebSocket"
```

---

### Task 11: Create Web Route Modules — Health, Chat, Config

**Files:**
- Create: `src/nasagent/web/routes/__init__.py`
- Create: `src/nasagent/web/routes/health.py`
- Create: `src/nasagent/web/routes/chat.py`
- Create: `src/nasagent/web/routes/config.py`

- [ ] **Step 1: Create `src/nasagent/web/routes/__init__.py`**

```python
"""NASAgent Web route modules."""
```

- [ ] **Step 2: Create `src/nasagent/web/routes/health.py`**

```python
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    return {"status": "ok"}
```

- [ ] **Step 3: Create `src/nasagent/web/routes/chat.py`**

```python
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
            await websocket.send_json(
                {"type": "system", "content": f"Received: {text}. Agent processing..."}
            )
            await asyncio.sleep(0.5)
            await websocket.send_json({"type": "agent", "content": f"Echo: {text}"})
    except WebSocketDisconnect:
        pass
```

- [ ] **Step 4: Create `src/nasagent/web/routes/config.py`**

```python
import tomllib

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from nasagent.web.templates import get_templates

router = APIRouter(tags=["config"])


@router.get("", response_class=HTMLResponse)
async def settings_page(request: Request):
    return get_templates().TemplateResponse("settings.html", {"request": request})
```

- [ ] **Step 5: Create placeholder config template `src/nasagent/web/templates/settings.html`**

```html
{% extends "base.html" %}
{% block title %}Settings{% endblock %}
{% block content %}
<div class="settings-container">
    <h1>Settings</h1>
    <p>Configuration pages will be added here.</p>
</div>
{% endblock %}
```

- [ ] **Step 6: Run ruff check**

```bash
uv run ruff check src/nasagent/web/
```

Expected: no errors.

- [ ] **Step 7: Verify web server starts**

```bash
timeout 5 uv run nasagent-web 2>&1 || true
```

Expected: starts on port 8000 (kill after 5s).

- [ ] **Step 8: Commit**

```bash
git add src/nasagent/web/routes/ src/nasagent/web/templates/settings.html
git commit -m "feat: add web route modules — health, chat with WebSocket, config placeholder"
```

---

### Task 12: Create Web Static CSS

**Files:**
- Create: `src/nasagent/web/static/style.css`

- [ ] **Step 1: Create `src/nasagent/web/static/style.css`**

```css
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
    --bg: #1a1a2e;
    --surface: #16213e;
    --border: #0f3460;
    --text: #e0e0e0;
    --dim: #888;
    --accent: #00d4aa;
    --accent-dim: #009977;
    --user: #4fc3f7;
    --agent: #00d4aa;
    --system: #ffb74d;
    --error: #ef5350;
    --input-bg: #0d1b2a;
}

html, body {
    height: 100%;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace;
    font-size: 14px;
    background: var(--bg);
    color: var(--text);
}

.topbar {
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 16px; height: 44px; background: var(--surface);
    border-bottom: 1px solid var(--border);
    position: fixed; top: 0; left: 0; right: 0; z-index: 100;
}
.topbar-left { display: flex; align-items: center; gap: 12px; }
.logo { font-weight: bold; color: var(--accent); text-decoration: none; font-size: 16px; }
.version { color: var(--dim); font-size: 12px; }
.topbar-nav { display: flex; gap: 16px; }
.topbar-nav a { color: var(--dim); text-decoration: none; padding: 4px 8px; border-radius: 4px; }
.topbar-nav a.active, .topbar-nav a:hover { color: var(--text); background: var(--border); }

.main-content { padding-top: 44px; height: 100%; }

.chat-container { display: flex; flex-direction: column; height: calc(100vh - 44px); }
.chat-messages { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 8px; }
.message { padding: 6px 12px; border-radius: 6px; max-width: 85%; word-break: break-word; }
.message.system { color: var(--system); font-size: 12px; align-self: center; background: transparent; }
.message.user { background: var(--border); color: var(--user); align-self: flex-end; }
.message.agent { background: var(--surface); color: var(--agent); align-self: flex-start; border: 1px solid var(--border); }
.message.error { color: var(--error); align-self: center; }

.chat-input-bar { padding: 8px 16px; background: var(--surface); border-top: 1px solid var(--border); }
.chat-form { display: flex; gap: 8px; }
.chat-form input { flex: 1; padding: 10px 14px; border: 1px solid var(--border); border-radius: 6px; background: var(--input-bg); color: var(--text); outline: none; font-size: 14px; }
.chat-form input:focus { border-color: var(--accent); }
.chat-form button { padding: 10px 20px; background: var(--accent); color: var(--bg); border: none; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 14px; }
.chat-form button:hover { background: var(--accent-dim); }

.chat-status { display: flex; justify-content: space-between; padding: 4px 16px; font-size: 11px; color: var(--dim); background: var(--surface); }

.settings-container { padding: 24px; max-width: 800px; margin: 0 auto; }
.settings-container h1 { margin-bottom: 16px; color: var(--accent); }
```

- [ ] **Step 2: Commit**

```bash
git add src/nasagent/web/static/style.css
git commit -m "feat: add web static CSS (dark theme)"
```

---

### Task 13: Implement Agent Integration in WebSocket Chat

**Files:**
- Modify: `src/nasagent/web/routes/chat.py` (integrate agent runner)

- [ ] **Step 1: Update chat WebSocket to use agent runner**

Replace the echo handler in `src/nasagent/web/routes/chat.py` with real agent integration:

```python
import asyncio
import json

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from nasagent.agent.runner import run_agent_with_callback, AgentStreamCallback
from nasagent.config.settings import load_settings
from nasagent.llm.openai_provider import OpenAiProvider
from nasagent.llm.messages import ChatMessage
from nasagent.memory import MemoryManager
from nasagent.nas.adapters.simulator.adapter import SimulatorNasAdapter
from nasagent.web.templates import get_templates

router = APIRouter(tags=["chat"])


@router.get("/", response_class=HTMLResponse)
async def chat_page(request: Request):
    return get_templates().TemplateResponse("chat.html", {"request": request})


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
            stream_cb = WebSocketStreamCallback(websocket)

            try:
                response = await provider.complete(messages)
                await websocket.send_json({"type": "agent", "content": response})
                memory_manager.conversation_memory.add_message("user", text)
                memory_manager.conversation_memory.add_message("assistant", response)
            except Exception as e:
                await websocket.send_json({"type": "error", "content": str(e)})
    except WebSocketDisconnect:
        pass
```

- [ ] **Step 2: Run ruff check**

```bash
uv run ruff check src/nasagent/web/
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add src/nasagent/web/routes/chat.py
git commit -m "feat: integrate agent runner into WebSocket chat"
```

---

### Task 14: Implement Web Config Settings Pages

**Files:**
- Create: `src/nasagent/web/routes/config_api.py`
- Create: `src/nasagent/web/templates/settings_llm.html`
- Create: `src/nasagent/web/templates/settings_safety.html`
- Create: `src/nasagent/web/templates/settings_apps.html`
- Modify: `src/nasagent/web/routes/config.py` (add sub-pages)
- Modify: `src/nasagent/web/server.py` (include config_api router)

- [ ] **Step 1: Create `src/nasagent/web/routes/config_api.py` with REST endpoints**

```python
from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse

from nasagent.config.secrets import CredentialStore
from nasagent.config.settings import (
    load_config_file,
    load_settings,
    render_toml,
    settings_to_toml_data,
    persist_app_config,
    default_config_path,
)

api_router = APIRouter(prefix="/api/config", tags=["config_api"])


@api_router.get("/show")
async def config_show():
    settings = load_settings()
    return settings_to_toml_data(settings, redact=True)


@api_router.post("/llm")
async def config_llm(
    provider: str = Form("openai"),
    model: str = Form("gpt-4.1-mini"),
    api_key: str = Form(""),
    base_url: str = Form(""),
):
    config_data = load_config_file()
    llm = config_data.setdefault("llm", {})
    llm["provider"] = provider
    llm["model"] = model
    if base_url:
        llm["base_url"] = base_url
    elif "base_url" in llm:
        del llm["base_url"]

    target = default_config_path()
    target.write_text(render_toml(config_data), encoding="utf-8")

    if api_key:
        CredentialStore().set("llm.api_key", api_key)

    return HTMLResponse("<script>alert('LLM settings saved'); window.location='/settings'</script>")


@api_router.post("/safety")
async def config_safety(
    default_mode: str = Form("confirm_destructive"),
    allow_auto_write: bool = Form(False),
    allow_destructive: bool = Form(False),
    require_confirmation_for: str = Form(""),
):
    config_data = load_config_file()
    safety = config_data.setdefault("safety", {})
    safety["default_mode"] = default_mode
    safety["allow_auto_write"] = allow_auto_write
    safety["allow_destructive"] = allow_destructive
    if require_confirmation_for:
        safety["require_confirmation_for"] = [
            t.strip() for t in require_confirmation_for.split(",") if t.strip()
        ]
    elif "require_confirmation_for" in safety:
        del safety["require_confirmation_for"]

    target = default_config_path()
    target.write_text(render_toml(config_data), encoding="utf-8")
    return HTMLResponse(
        "<script>alert('Safety settings saved'); window.location='/settings'</script>"
    )


@api_router.post("/app/add")
async def config_app_add(
    name: str = Form(...),
    app_type: str = Form(...),
    base_url: str = Form(...),
    credential_key: str = Form(""),
):
    persist_app_config(name, app_type, base_url, credential_key=credential_key or None)
    return HTMLResponse(f"<script>alert('App {name} added'); window.location='/settings'</script>")


@api_router.get("/")
async def config_current():
    settings = load_settings()
    return settings_to_toml_data(settings, redact=True)
```

- [ ] **Step 2: Update `src/nasagent/web/routes/config.py` to add settings sub-pages**

```python
import tomllib

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from nasagent.config.settings import (
    load_config_file,
    load_settings,
    settings_to_toml_data,
    KNOWN_APP_TYPES,
)
from nasagent.web.templates import get_templates

router = APIRouter(tags=["config"])


@router.get("", response_class=HTMLResponse)
async def settings_page(request: Request):
    return get_templates().TemplateResponse("settings.html", {"request": request})


@router.get("/llm", response_class=HTMLResponse)
async def settings_llm(request: Request):
    settings = load_settings()
    return get_templates().TemplateResponse(
        "settings_llm.html",
        {
            "request": request,
            "settings": settings,
        },
    )


@router.get("/safety", response_class=HTMLResponse)
async def settings_safety(request: Request):
    settings = load_settings()
    return get_templates().TemplateResponse(
        "settings_safety.html",
        {
            "request": request,
            "settings": settings,
        },
    )


@router.get("/apps", response_class=HTMLResponse)
async def settings_apps(request: Request):
    settings = load_settings()
    return get_templates().TemplateResponse(
        "settings_apps.html",
        {
            "request": request,
            "apps": settings.apps,
            "app_types": KNOWN_APP_TYPES,
        },
    )
```

- [ ] **Step 3: Update `src/nasagent/web/server.py` to include config API router**

Add after the existing `config_routes` include:

```python
from nasagent.web.routes import config_api as config_api_routes

app.include_router(config_api_routes.api_router)
```

- [ ] **Step 4: Create `src/nasagent/web/templates/settings.html` (main settings page)**

```html
{% extends "base.html" %}
{% block title %}Settings{% endblock %}
{% block content %}
<div class="settings-container">
    <h1>Settings</h1>
    <div class="settings-grid">
        <a href="/settings/llm" class="settings-card">
            <h2>LLM</h2>
            <p>Configure AI provider, model, and API key</p>
        </a>
        <a href="/settings/safety" class="settings-card">
            <h2>Safety</h2>
            <p>Safety policy and confirmation settings</p>
        </a>
        <a href="/settings/apps" class="settings-card">
            <h2>Apps</h2>
            <p>Manage NAS app endpoints (AList, Vaultwarden, etc.)</p>
        </a>
    </div>
</div>
{% endblock %}
```

- [ ] **Step 5: Create `src/nasagent/web/templates/settings_llm.html`**

```html
{% extends "base.html" %}
{% block title %}LLM Settings{% endblock %}
{% block content %}
<div class="settings-container">
    <h1>LLM Configuration</h1>
    <form method="post" action="/settings/api/config/llm" class="settings-form">
        <label>Provider <input name="provider" value="{{ settings.llm.provider }}"></label>
        <label>Model <input name="model" value="{{ settings.llm.model }}"></label>
        <label>Base URL <input name="base_url" value="{{ settings.llm.base_url or '' }}" placeholder="https://api.openai.com/v1"></label>
        <label>API Key <input name="api_key" type="password" placeholder="Leave blank to keep existing"></label>
        <button type="submit">Save</button>
        <a href="/settings" class="btn-back">Back</a>
    </form>
</div>
{% endblock %}
```

- [ ] **Step 6: Create `src/nasagent/web/templates/settings_safety.html`**

```html
{% extends "base.html" %}
{% block title %}Safety Settings{% endblock %}
{% block content %}
<div class="settings-container">
    <h1>Safety Configuration</h1>
    <form method="post" action="/settings/api/config/safety" class="settings-form">
        <label>Default Mode
            <select name="default_mode">
                <option value="confirm_destructive" {% if settings.safety.default_mode == "confirm_destructive" %}selected{% endif %}>Confirm Destructive</option>
                <option value="allow_all" {% if settings.safety.default_mode == "allow_all" %}selected{% endif %}>Allow All</option>
                <option value="strict" {% if settings.safety.default_mode == "strict" %}selected{% endif %}>Strict</option>
            </select>
        </label>
        <label><input type="checkbox" name="allow_auto_write" {% if settings.safety.allow_auto_write %}checked{% endif %}> Allow Auto Write</label>
        <label><input type="checkbox" name="allow_destructive" {% if settings.safety.allow_destructive %}checked{% endif %}> Allow Destructive</label>
        <label>Require Confirmation For <input name="require_confirmation_for" value="{{ settings.safety.require_confirmation_for | join(', ') }}" placeholder="tool names comma-separated"></label>
        <button type="submit">Save</button>
        <a href="/settings" class="btn-back">Back</a>
    </form>
</div>
{% endblock %}
```

- [ ] **Step 7: Create `src/nasagent/web/templates/settings_apps.html`**

```html
{% extends "base.html" %}
{% block title %}App Settings{% endblock %}
{% block content %}
<div class="settings-container">
    <h1>App Endpoints</h1>
    <table class="app-table">
        <thead><tr><th>Name</th><th>Type</th><th>URL</th></tr></thead>
        <tbody>
        {% for name, app in apps.items() %}
        <tr><td>{{ name }}</td><td>{{ app.app_type }}</td><td>{{ app.base_url }}</td></tr>
        {% endfor %}
        </tbody>
    </table>
    <h2 style="margin-top:24px">Add App</h2>
    <form method="post" action="/settings/api/config/app/add" class="settings-form">
        <label>Name <input name="name" required></label>
        <label>Type
            <select name="app_type">
                {% for key, info in app_types.items() %}
                <option value="{{ key }}">{{ key }} — {{ info.description }}</option>
                {% endfor %}
            </select>
        </label>
        <label>Base URL <input name="base_url" required placeholder="http://nas.local:5244"></label>
        <label>Credential Key <input name="credential_key" placeholder="optional"></label>
        <button type="submit">Add</button>
        <a href="/settings" class="btn-back">Back</a>
    </form>
</div>
{% endblock %}
```

- [ ] **Step 8: Add settings CSS to `src/nasagent/web/static/style.css`**

Append to the existing CSS:

```css
.settings-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px; margin-top: 16px; }
.settings-card { display: block; padding: 20px; background: var(--surface); border: 1px solid var(--border); border-radius: 8px; text-decoration: none; color: var(--text); transition: border-color 0.2s; }
.settings-card:hover { border-color: var(--accent); }
.settings-card h2 { color: var(--accent); margin-bottom: 8px; font-size: 16px; }
.settings-card p { color: var(--dim); font-size: 13px; }

.settings-form { display: flex; flex-direction: column; gap: 16px; max-width: 500px; }
.settings-form label { display: flex; flex-direction: column; gap: 4px; font-size: 13px; color: var(--dim); }
.settings-form input, .settings-form select { padding: 10px 12px; border: 1px solid var(--border); border-radius: 6px; background: var(--input-bg); color: var(--text); font-size: 14px; }
.settings-form input:focus, .settings-form select:focus { border-color: var(--accent); outline: none; }
.settings-form input[type="checkbox"] { width: auto; margin-right: 8px; }
.settings-form button { padding: 12px 24px; background: var(--accent); color: var(--bg); border: none; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 14px; align-self: flex-start; }
.settings-form button:hover { background: var(--accent-dim); }
.btn-back { color: var(--dim); text-decoration: none; font-size: 13px; padding-left: 8px; }

.app-table { width: 100%; border-collapse: collapse; }
.app-table th, .app-table td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--border); font-size: 13px; }
.app-table th { color: var(--dim); font-weight: 600; }
```

- [ ] **Step 9: Run ruff check**

```bash
uv run ruff check src/nasagent/web/
```

Expected: no errors.

- [ ] **Step 10: Commit**

```bash
git add src/nasagent/web/routes/config.py src/nasagent/web/routes/config_api.py src/nasagent/web/server.py src/nasagent/web/templates/settings*.html src/nasagent/web/static/style.css
git commit -m "feat: add web config settings pages — LLM, Safety, Apps management"
```

---

### Task 15: Redesign CLI with Textual TUI

**Files:**
- Create: `src/nasagent/cli/tui/__init__.py`
- Create: `src/nasagent/cli/tui/app.py` (Textual App with chat UI)
- Modify: `src/nasagent/cli/commands/chat.py` (add `chat --tui` flag, keep legacy REPL as fallback)
- Modify: `src/nasagent/cli/app.py` (typer entry point update)

- [ ] **Step 1: Create `src/nasagent/cli/tui/__init__.py`**

```python
"""Textual TUI for NASAgent CLI."""
```

- [ ] **Step 2: Create `src/nasagent/cli/tui/app.py` — the Textual TUI application**

```python
import asyncio
from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Container
from textual.widgets import Header, Footer, Input, RichLog, Static, Label


class StatusBar(Static):
    def compose(self) -> ComposeResult:
        yield Label("", id="status-repo")
        yield Label("", id="status-version")


class InfoPanel(Static):
    def compose(self) -> ComposeResult:
        yield Static("Info Panel", id="info-title")
        yield Label("Current Step: idle", id="info-step")
        yield Label("Recent Tool: none", id="info-tool")
        yield Label("LLM: offline", id="info-llm")
        yield Label("Profile: simulator", id="info-profile")


class NasaGentTui(App):
    CSS = """
    StatusBar {
        dock: top;
        height: 1;
        background: $surface;
        color: $text-muted;
    }
    StatusBar Label { margin: 0 2; }
    #status-repo { color: $accent; }
    #status-version { color: $text-muted; }

    InfoPanel {
        width: 28;
        dock: right;
        background: $surface;
        border-left: solid $primary-background;
        padding: 1;
    }
    #info-title { text-style: bold; color: $accent; margin-bottom: 1; }

    Vertical#chat-area { height: 1fr; }
    RichLog { border: none; }
    Horizontal#input-area { height: 3; }
    #chat-input { dock: left; width: 1fr; }
    """

    def compose(self) -> ComposeResult:
        yield StatusBar()
        yield Container(
            Vertical(
                RichLog(id="chat-log", highlight=True, markup=True),
                Horizontal(
                    Input(placeholder="Type your message...", id="chat-input"),
                    id="input-area",
                ),
                id="chat-area",
            ),
            InfoPanel(),
        )

    def on_mount(self) -> None:
        self._update_status()
        self._update_info()

    @on(Input.Submitted)
    async def handle_input(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return
        chat_log = self.query_one("#chat-log", RichLog)
        chat_input = self.query_one("#chat-input", Input)

        if text.lower() in ("exit", "quit"):
            self.exit()
            return

        if text.startswith("/"):
            chat_log.write(f"[bold dim]system[/] > [dim]{text}[/]")
        else:
            chat_log.write(f"[bold green]you[/] > {text}")
            chat_log.write("[bold dim]system[/] > [dim]processing...[/]")
            # Execute task via shared agent runner
            try:
                from nasagent.cli.commands.run import execute_simulator_task
                from nasagent.config.settings import load_settings

                settings = load_settings()
                state = await asyncio.to_thread(execute_simulator_task, text, settings)
                for step_result in state.step_results:
                    for tool_result in step_result.tool_results:
                        chat_log.write(f"[bold magenta]tool[/] > [dim]{tool_result.tool_name}[/]")
                if state.final_summary:
                    chat_log.write(f"[bold cyan]agent[/] > {state.final_summary}")
            except Exception as e:
                chat_log.write(f"[bold red]error[/] > {e}")

        chat_input.value = ""
        chat_log.scroll_end()

    def _update_status(self) -> None:
        try:
            repo = Path.cwd().name
        except Exception:
            repo = "unknown"
        self.query_one("#status-repo", Label).update(f"repo: {repo}")
        self.query_one("#status-version", Label).update("nasagent v0.1.0")

    def _update_info(self) -> None:
        try:
            from nasagent.config.settings import load_settings

            settings = load_settings()
            provider = settings.llm.provider or "offline"
            model = settings.llm.model
            llm_text = f"{provider}/{model}" if provider != "offline" else "offline"
            self.query_one("#info-llm", Label).update(f"LLM: {llm_text}")
        except Exception:
            pass
```

- [ ] **Step 3: Update `src/nasagent/cli/commands/chat.py` to add `--tui` option**

At the top of `chat()` function, add:

```python
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
        False,
        "--tui/--no-tui",
        help="Use Textual TUI interface instead of simple REPL.",
    ),
) -> None:
    if tui:
        from nasagent.cli.tui.app import NasaGentTui

        app = NasaGentTui()
        app.run()
        return
    # ... existing REPL code ...
```

- [ ] **Step 4: Verify Textual TUI runs**

```bash
uv run nasagent chat --tui
```

Expected: Textual TUI launches with status bar, chat area, info panel, and input field. Type "exit" to quit.

- [ ] **Step 5: Run ruff check**

```bash
uv run ruff check src/nasagent/cli/
```

Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add src/nasagent/cli/tui/ src/nasagent/cli/commands/chat.py
git commit -m "feat: add Textual TUI with status bar, info panel, and scrollable chat"
```

---

### Task 16: Add Web Module Tests

**Files:**
- Create: `tests/unit/web/test_server.py`
- Create: `tests/unit/web/test_config_routes.py`

- [ ] **Step 1: Create `tests/unit/web/__init__.py`**

```python
```

- [ ] **Step 2: Create `tests/unit/web/test_server.py`**

```python
from fastapi.testclient import TestClient

from nasagent.web.server import create_app


def test_health_endpoint():
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_page_returns_html():
    client = TestClient(create_app())
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "NASAgent" in response.text


def test_settings_page_returns_html():
    client = TestClient(create_app())
    response = client.get("/settings")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_settings_llm_page():
    client = TestClient(create_app())
    response = client.get("/settings/llm")
    assert response.status_code == 200


def test_settings_safety_page():
    client = TestClient(create_app())
    response = client.get("/settings/safety")
    assert response.status_code == 200


def test_settings_apps_page():
    client = TestClient(create_app())
    response = client.get("/settings/apps")
    assert response.status_code == 200


def test_static_files_served():
    client = TestClient(create_app())
    response = client.get("/static/style.css")
    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]
```

- [ ] **Step 3: Create `tests/unit/web/test_config_routes.py`**

```python
from fastapi.testclient import TestClient
from nasagent.web.server import create_app


def test_config_api_show():
    client = TestClient(create_app())
    response = client.get("/settings/api/config/show")
    assert response.status_code == 200


def test_config_llm_post():
    client = TestClient(create_app())
    response = client.post(
        "/settings/api/config/llm",
        data={
            "provider": "openai",
            "model": "gpt-4.1-mini",
            "api_key": "test-key",
            "base_url": "https://api.openai.com/v1",
        },
    )
    assert response.status_code == 200


def test_config_safety_post():
    client = TestClient(create_app())
    response = client.post(
        "/settings/api/config/safety",
        data={
            "default_mode": "confirm_destructive",
            "allow_auto_write": "on",
        },
    )
    assert response.status_code == 200


def test_config_app_add():
    client = TestClient(create_app())
    response = client.post(
        "/settings/api/config/app/add",
        data={
            "name": "test_alist",
            "app_type": "alist",
            "base_url": "http://localhost:5244",
        },
    )
    assert response.status_code == 200
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/unit/web/ -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add tests/unit/web/
git commit -m "test: add web module tests — server health, chat pages, config routes"
```

---

### Task 17: Add CLI TUI Tests

**Files:**
- Create: `tests/unit/cli/test_tui.py`

- [ ] **Step 1: Create `tests/unit/cli/__init__.py`**

```python
```

- [ ] **Step 2: Create `tests/unit/cli/test_tui.py`**

```python
from nasagent.cli.tui.app import NasaGentTui


async def test_tui_can_mount():
    app = NasaGentTui()
    async with app.run_test() as pilot:
        assert pilot.app is not None


async def test_tui_has_status_bar():
    app = NasaGentTui()
    async with app.run_test() as pilot:
        status = pilot.app.query_one("#status-repo")
        assert status is not None
        assert "repo" in str(status.renderable)


async def test_tui_has_info_panel():
    app = NasaGentTui()
    async with app.run_test() as pilot:
        info = pilot.app.query_one("#info-step")
        assert info is not None


async def test_tui_has_chat_log():
    app = NasaGentTui()
    async with app.run_test() as pilot:
        chat = pilot.app.query_one("#chat-log")
        assert chat is not None


async def test_tui_has_input():
    app = NasaGentTui()
    async with app.run_test() as pilot:
        inp = pilot.app.query_one("#chat-input")
        assert inp is not None


async def test_tui_exit_on_quit():
    app = NasaGentTui()
    async with app.run_test() as pilot:
        inp = pilot.app.query_one("#chat-input")
        inp.value = "exit"
        await inp.action_submit()
        await pilot.pause()
        assert app._exit
```

- [ ] **Step 3: Run TUI tests**

```bash
uv run pytest tests/unit/cli/test_tui.py -v
```

Expected: all tests pass (tests run in headless mode via textual testing).

- [ ] **Step 4: Commit**

```bash
git add tests/unit/cli/
git commit -m "test: add Textual TUI component tests"
```

---

### Task 18: Final Verification — Full Test Suite + Lint

**Files:** none (verification only)

- [ ] **Step 1: Run full test suite**

```bash
uv run pytest tests/ -v
```

Expected: all tests pass (existing + new web/CLI tests).

- [ ] **Step 2: Run ruff check**

```bash
uv run ruff check .
```

Expected: no errors.

- [ ] **Step 3: Run ruff format check**

```bash
uv run ruff format --check .
```

Expected: no formatting issues.

- [ ] **Step 4: Run mypy type check**

```bash
uv run mypy src
```

Expected: no type errors (or only pre-existing ones).

- [ ] **Step 5: Build Docker image**

```bash
docker build -t nasagent:test -f docker/Dockerfile .
```

Expected: image builds successfully.

- [ ] **Step 6: Verify Docker image starts and health check passes**

```bash
docker run --rm -d --name nasagent-test -p 8000:8000 nasagent:test && sleep 5 && curl -f http://localhost:8000/health && docker stop nasagent-test
```

Expected: `{"status":"ok"}`, container stops cleanly.

- [ ] **Step 7: Commit**

```bash
git commit -m "chore: final verification — all tests pass, lint clean, Docker builds"
```

---

### Task 19: Push Branch and Create PR

**Files:** none (git operations)

- [ ] **Step 1: Push all commits**

```bash
git push origin feat/docker-web-cli
```

- [ ] **Step 2: Verify CI runs**

Check that both GitHub Actions and Gitea Actions trigger `lint-and-test` jobs and pass.

- [ ] **Step 3: Create PR**

Open a PR from `feat/docker-web-cli` into `main` on both GitHub and Gitea.
