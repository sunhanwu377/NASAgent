import asyncio
from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Input, Label, RichLog, Static


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
