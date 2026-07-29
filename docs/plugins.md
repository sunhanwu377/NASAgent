# Plugins

NASAgent plugins are Python packages that expose an entry point in the `nasagent.plugins` group.

```python
def register(plugin: PluginContext) -> None:
    plugin.platform.tools.register(...)
    plugin.platform.commands.register(...)
    plugin.platform.apps.register(...)
```

Plugins should namespace tools, declare risk levels accurately, and never print secrets directly.

Platform-enabled CLI, chat slash commands, and the default agent tool registry load built-in plugins first and then `nasagent.plugins` entry points. `nasagent plugins list` and `/plugins` show loaded plugin manifests plus isolated entry-point load errors.
