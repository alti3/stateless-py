# Installation

## Requirements

- Python `>=3.10`
- `uv` for dependency and environment management

## Install the Package

```bash
uv add stateless-py
```

If you are developing from source:

```bash
git clone https://github.com/alti3/stateless-py.git
cd stateless-py
uv sync
```

## Development Dependencies

```bash
uv sync --all-extras
```

## Common Dev Commands

```bash
uvx pytest
uvx ruff check .
uvx ruff format .
uvx ty check
```

## Optional Graph Rendering

To render diagrams with Graphviz through `StateMachine.visualize(...)`, install the graphing extra:

```bash
uv add "stateless-py[graphing]"
```

You also need the Graphviz `dot` executable available on your system PATH.
