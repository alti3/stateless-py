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

Build docs locally with MkDocs:

```bash
uv run mkdocs serve
# or
uv run mkdocs build
```

If MkDocs dependencies are not installed in your environment, add them first:

```bash
uv add --dev mkdocs mkdocs-material mkdocstrings[python] pymdown-extensions
```
