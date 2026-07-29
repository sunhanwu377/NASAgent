from rich.table import Table

from nasagent.tools.registry import ToolRegistry


def tools_table(registry: ToolRegistry) -> Table:
    table = Table(title="NASAgent Tools")
    table.add_column("Name")
    table.add_column("Risk")
    table.add_column("Description")
    for tool in registry.list():
        table.add_row(tool.name, tool.risk_level.value, tool.description)
    return table
