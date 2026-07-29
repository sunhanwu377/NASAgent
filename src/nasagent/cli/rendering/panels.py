from rich.panel import Panel


def result_panel(summary: str) -> Panel:
    return Panel(summary, title="NASAgent Result")
