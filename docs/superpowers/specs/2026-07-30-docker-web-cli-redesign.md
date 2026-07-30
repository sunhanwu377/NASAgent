# NASAgent Docker + Web + CLI Redesign

## Overview

将 NASAgent 从纯 CLI 工具升级为双形态产品：(1) pip 安装的 CLI TUI 工具，(2) Docker 部署的 Web 服务。CLI 和 Web 共享同一套 agent 核心逻辑。同时建立完整的 Docker 部署体系和 CI/CD 流程。

## 1. Repository Structure

新增 `web/` 和 `docker/` 目录，CLI 从简单 REPL 升级为 Textual TUI：

```
nasaagent/
├── src/nasagent/
│   ├── agent/           # 共享 agent 核心 (不变)
│   ├── cli/             # CLI - 升级为 Textual TUI
│   ├── config/          # 共享配置管理 (不变)
│   ├── web/             # **新增** Web 服务
│   │   ├── __init__.py
│   │   ├── server.py    # FastAPI app 入口
│   │   ├── routes/      # REST API + WebSocket
│   │   ├── templates/   # Jinja2 模板
│   │   └── static/      # CSS 静态文件
│   └── ...
├── docker/              # **新增**
│   ├── Dockerfile
│   └── docker-compose.yml
├── .github/workflows/
│   ├── ci.yml           # 扩展：lint + test on PR
│   └── release.yml      # **新增** docker build + push on release
├── .gitea/workflows/
│   ├── ci.yml           # 扩展
│   └── release.yml      # **新增**
└── pyproject.toml       # 扩展：web optional-deps
```

## 2. Shared Agent Core

CLI 和 Web 使用同一套 agent 后端。`nasagent.agent` 模块保持不变，提供核心接口：

- `execute_simulator_task(task, online)` — 执行 NAS 任务
- `OpenAiProvider` — LLM 对话
- `MemoryManager` — 会话记忆

CLI 的 Textual TUI 和 Web 的 FastAPI handler 都调用相同的 agent 接口。流式输出通过适配器分别驱动 Textual widget 和 WebSocket。

## 3. CLI Layout (Textual TUI)

使用 Textual 框架实现三面板固定布局：

```
┌──────────────────────────────────────────────────────────────────┐
│ 📂 ~/nas-repo  │  main  │  nasagent v0.1.0                       │  ← 状态栏（顶部固定）
├──────────────────────────────────────────────┬───────────────────┤
│                                              │ 📋 Info Panel     │
│  agent: Hello, I can help...                 │                   │
│                                              │ 当前步骤: idle     │
│  you > check storage                         │ 最近工具调用:     │
│                                              │   - 无             │
│  agent: Storage pool 'main' has 480GB free.  │ LLM: gpt-4.1-mini │
│                                              │ Profile: simulator│
│                                              │                   │
├──────────────────────────────────────────────┴───────────────────┤
│ > █                                                              │  ← 输入栏（底部固定）
└──────────────────────────────────────────────────────────────────┘
```

**固定不变区域：**
- 顶部状态栏：代码仓路径、分支、agent 版本号（后续可扩展更多状态项）
- 右侧信息面板：当前步骤状态、最近工具调用、LLM 配置、Profile 等元信息
- 底部输入栏：用户输入

**滚动区域：**
- 中间聊天区：所有对话流、工具调用结果、agent 响应

采用 Textual 的 `Header` + `ContentSwitcher` + `Footer` + `Dock` 组件实现布局。

## 4. Web Layout

### 4.1 Chat 页面

```
┌─────────────────────────────────────────────────────────┐
│  NASAgent Web                                    v0.1.0 │  ← 顶栏
├─────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────┐    │
│  │ agent: Hello, I can help with NAS operations.   │    │
│  │ you > check storage                             │    │
│  │ tool · check_storage completed                  │    │
│  │ agent: Storage pool 'main' has 480GB free.      │    │
│  └─────────────────────────────────────────────────┘    │  ← 聊天区（滚动）
│  ┌─────────────────────────────────────────────────┐    │
│  │ > Type your message...                    [Send] │    │  ← 输入栏（固定底部）
│  └─────────────────────────────────────────────────┘    │
│  Profile: simulator | LLM: gpt-4.1-mini                 │  ← 状态栏
└─────────────────────────────────────────────────────────┘
```

- WebSocket 实时流式推送 agent 输出
- 支持简易 Markdown 渲染（agent 响应）

### 4.2 Settings 页面

左侧导航 + 右侧表单的配置编辑界面。覆盖所有配置项：

| Section | 配置项 |
|---------|--------|
| LLM | provider, model, base_url, api_key |
| Safety | default_mode, allow_auto_write, allow_destructive, require_confirmation_for |
| Observability | run_log_dir, redact_sensitive |
| Apps | 端点列表（CRUD）: app_type, base_url, credential_key |
| Plugins | 列表 + 启用/禁用开关 |
| Credentials | 密钥管理（masked input，只写入不显示） |

配置通过 REST API 读写 `config.toml` 和 `secrets.toml`。

## 5. Docker Deployment

### 5.1 Dockerfile

基于 Python 3.11 slim，使用 uv 管理依赖：

- COPY 阶段：pyproject.toml + uv.lock 先复制安装依赖（利用 Docker layer cache）
- COPY 源码
- Entry point：`nasagent-web` console script 启动 FastAPI + uvicorn
- 暴露端口 8000

### 5.2 docker-compose.yml

- 挂载 docker.sock 以便容器内操作宿主机 docker
- volume 持久化 config、data、memory 目录
- restart: unless-stopped

### 5.3 Package Dependencies

```toml
[project]
dependencies = ["textual", "rich", "typer", "langgraph", ...]

[project.optional-dependencies]
web = ["fastapi", "uvicorn[standard]", "jinja2", "python-multipart"]

[project.scripts]
nasagent = "nasagent.cli.app:app"
nasagent-web = "nasagent.web.server:main"
```

- `pip install nasagent` → 仅 CLI
- `pip install nasagent[web]` → CLI + Web
- Docker 镜像安装 `nasagent[web]`

## 6. CI/CD

### 6.1 PR 静态检查 + 单测 (GitHub + Gitea 各一份)

```yaml
on: [pull_request, push]
jobs:
  test:
    - checkout
    - setup uv + python 3.11
    - uv sync --all-extras --dev
    - ruff check + format --check
    - mypy src
    - pytest
```

### 6.2 Release 自动 Docker 构建推送

```yaml
on:
  release:
    types: [published]
jobs:
  docker:
    - checkout
    - docker/build-push-action
    - tags: ghcr.io/owner/nasagent:latest + :<version>
```

- GitHub release → 推送到 GHCR
- Gitea release → 推送到 Gitea Package Registry

## 7. Branch Strategy

从 `main` 创建新分支 `feat/docker-web-cli` 进行所有开发，完成后通过 PR 合入 `main`。
