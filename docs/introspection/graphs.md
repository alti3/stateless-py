# Graph Generation

`stateless-py` supports DOT and Mermaid output.

## DOT Graph

```python
dot = sm.generate_dot_graph()
print(dot)
```

Use this output with Graphviz tools.

## Mermaid Graph

```python
mermaid = sm.generate_mermaid_graph()
print(mermaid)
```

Paste into Mermaid-enabled markdown viewers.

## Direct Rendering with Graphviz

```python
sm.visualize(filename="state_machine.gv", format="png", view=True)
```

`visualize(...)` requires:

- Python `graphviz` package (install `stateless-py[graphing]`)
- Graphviz `dot` executable on system PATH

## Graph Content

Generated graphs include:

- initial state marker
- fixed transitions
- ignored triggers (self-loop, labeled as ignored)
- dynamic transitions (self-loop with selector description)
- hierarchical clusters for superstates/substates
- guard descriptions in transition labels
