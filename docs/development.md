# Development

```bash
uv sync --all-extras --dev
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy src
```

Real UGREEN tests are opt-in with `pytest -m ugreen_real` and must not run in default CI.
