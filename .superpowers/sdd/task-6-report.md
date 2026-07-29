## Pytest Collection Fix

- Root cause: pytest's default import mode loaded duplicate `test_registry.py` basenames as the same top-level module during collection.
- Fix: configured pytest `addopts = ["--import-mode=importlib"]` in `pyproject.toml` so plain `uv run pytest` matches the passing import behavior.
- Verification: `uv run pytest` passed with 26 tests; `uv run python -c "import tomllib; tomllib.load(open('pyproject.toml', 'rb'))"` passed.
