# Plugins

NASAgent plugins are Python packages that expose an entry point in the `nasagent.plugins` group.

```python
def register(plugin: PluginContext) -> None:
    plugin.platform.tools.register(...)
    plugin.platform.commands.register(...)
    plugin.platform.apps.register(...)
```

Plugins should namespace tools, declare risk levels accurately, and never print secrets directly.
