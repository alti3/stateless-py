# Development

## Local Setup

```bash
git clone https://github.com/alti3/stateless-py.git
cd stateless-py
uv sync
```

## Quality Gates

```bash
uvx pytest
uvx ruff check .
uvx ruff format .
uvx ty check
```

## Documentation

Preview or build the docs locally with Zensical:

```bash
uv run zensical serve
# or
uv run zensical build --clean --strict
```

If Zensical is not installed in your environment, sync the development dependencies first:

```bash
uv sync --dev
```
