# Packaging

The project uses standard `src` layout and exposes `nasagent = "nasagent.cli.app:app"` as a console script.

Supported local installation patterns:

```bash
uv sync
uv run nasagent chat
uv pip install .
pipx install .
```
