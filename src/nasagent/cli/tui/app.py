import asyncio
import re
from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Input, Label, RichLog, Static

from nasagent.cli.commands.chat import (
    CHINESE_TASK_ACTION_KEYWORDS,
    ENGLISH_TASK_ACTION_KEYWORDS,
    GREETING_INPUTS,
    TASK_RESOURCE_KEYWORDS,
)
from nasagent.config.settings import load_settings


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

        # Slash commands
        if text.startswith("/"):
            chat_log.write(f"[bold dim]system[/] > [dim]{text}[/]")
            from nasagent.memory import MemoryManager
            from nasagent.platform.context import create_platform_context
            from nasagent.platform.plugins import load_platform_plugins
            from nasagent.plugins.commands import register_memory_commands

            settings = load_settings()
            ctx = create_platform_context(settings=settings)
            load_platform_plugins(ctx)
            memory_dir = settings.observability.expanded_memory_dir()
            mm = MemoryManager(memory_dir, None)
            mm.ensure_session("default")
            register_memory_commands(ctx, mm)
            result = ctx.commands.dispatch(text)
            chat_log.write(f"[bold cyan]agent[/] > {result.message}")
            chat_input.value = ""
            chat_log.scroll_end()
            return

        chat_log.write(f"[bold green]you[/] > {text}")

        # Local greeting
        if self._is_greeting(text):
            chat_log.write(
                "[bold cyan]agent[/] > Hello. "
                "I can help with NAS operations like checking storage or device status."
            )
            chat_input.value = ""
            chat_log.scroll_end()
            return

        # Conversation vs task execution
        if not self._looks_like_execution_intent(text):
            await self._conversation_response(text, chat_log)
        else:
            await self._execute_task(text, chat_log)

        chat_input.value = ""
        chat_log.scroll_end()

    def _is_greeting(self, text: str) -> bool:
        normalized = text.casefold().strip(" !?.。！？")
        return normalized in GREETING_INPUTS

    def _looks_like_execution_intent(self, text: str) -> bool:
        normalized = text.casefold()
        has_action = any(
            re.search(rf"\b{re.escape(keyword)}\b", normalized)
            for keyword in ENGLISH_TASK_ACTION_KEYWORDS
        ) or any(keyword in normalized for keyword in CHINESE_TASK_ACTION_KEYWORDS)
        has_resource = any(
            re.search(rf"\b{re.escape(keyword)}\b", normalized)
            for keyword in TASK_RESOURCE_KEYWORDS if keyword.isascii()
        ) or any(
            keyword in normalized
            for keyword in TASK_RESOURCE_KEYWORDS if not keyword.isascii()
        )
        return has_action and has_resource

    async def _conversation_response(self, text: str, chat_log: RichLog) -> None:
        settings = load_settings()
        if not settings.llm.api_key:
            chat_log.write(
                "[bold cyan]agent[/] > I can chat when an LLM is configured. "
                "For NAS tasks, ask me to check storage or device status."
            )
            return
        try:
            from nasagent.llm.messages import ChatMessage
            from nasagent.llm.openai_provider import OpenAiProvider
            from nasagent.memory import MemoryManager

            memory_dir = settings.observability.expanded_memory_dir()
            mm = MemoryManager(memory_dir, None)
            mm.ensure_session("default")
            provider = OpenAiProvider(settings.llm)
            messages = [
                ChatMessage(role=m["role"], content=m["content"])
                for m in mm.inject_context()
            ]
            messages.append(ChatMessage(role="user", content=text))

            response = await provider.complete(messages)
            chat_log.write(f"[bold cyan]agent[/] > {response}")
            if mm.conversation_memory:
                mm.conversation_memory.add_message("user", text)
                mm.conversation_memory.add_message("assistant", response)
        except Exception as e:
            chat_log.write(f"[bold red]error[/] > {e}")

    async def _execute_task(self, text: str, chat_log: RichLog) -> None:
        chat_log.write("[bold dim]system[/] > [dim]planning and running task...[/]")
        try:
            from nasagent.cli.commands.run import execute_simulator_task

            settings = load_settings()
            state = await asyncio.to_thread(execute_simulator_task, text, settings)
            for step_result in state.step_results:
                for tool_result in step_result.tool_results:
                    chat_log.write(
                        f"[bold magenta]tool[/] > "
                        f"[dim]{tool_result.tool_name} completed[/]"
                    )
            if state.final_summary:
                chat_log.write(f"[bold cyan]agent[/] > {state.final_summary}")
        except Exception as e:
            chat_log.write(f"[bold red]error[/] > {e}")

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
