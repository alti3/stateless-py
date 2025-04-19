from enum import Enum, auto
from typing import Any
from stateless import StateMachine

# --- Test Setup ---


class State(Enum):
    A = auto()
    B = auto()
    C = auto()


class SubA(Enum):
    A1 = auto()
    A2 = auto()


class Trigger(Enum):
    X = auto()
    Y = auto()
    Z = auto()
    R = auto()


# --- Tests ---


def test_generate_dot_graph_simple() -> None:
    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit(Trigger.X, State.B)
    sm.configure(State.B).permit(Trigger.Y, State.A)

    dot = sm.generate_dot_graph()

    assert "digraph StateMachine" in dot
    assert '"A" [label="A"]' in dot
    assert '"B" [label="B"]' in dot
    assert '__start -> "A"' in dot  # Initial state
    assert '"A" -> "B" [label="X"]' in dot
    assert '"B" -> "A" [label="Y"]' in dot


def test_generate_dot_graph_features() -> None:
    """Tests DOT graph includes guards, internal, ignored, dynamic."""
    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit_if(Trigger.X, State.B, lambda: True, "GuardX").ignore(
        Trigger.Y
    ).internal_transition(Trigger.Z, lambda: None).dynamic(Trigger.R, lambda: State.C)
    sm.configure(State.B)
    sm.configure(State.C)

    dot = sm.generate_dot_graph()
    # print(dot) # For debugging

    # Guard
    assert '"A" -> "B" [label="X [GuardX]"]' in dot

    # Ignored - Should be a self-loop with (ignored)
    assert '"A" -> "A" [label="Y (ignored)"]' in dot

    # Internal - Should be a self-loop
    assert '"A" -> "A" [label="Z"]' in dot

    # Dynamic - Should be a self-loop, dashed, showing selector
    assert '"A" -> "A" [label="R -> (<lambda>)", style=dashed]' in dot


def test_generate_dot_graph_substates() -> None:
    sm = StateMachine[Any, Trigger](SubA.A1)
    sm.configure(SubA.A1).substate_of(State.A).permit(Trigger.X, SubA.A2)
    sm.configure(SubA.A2).substate_of(State.A).permit(Trigger.Y, State.B)
    sm.configure(State.A).permit(Trigger.Z, State.C)  # Transition from superstate
    sm.configure(State.B).permit(Trigger.R, SubA.A1)  # Transition to substate
    sm.configure(State.C)

    dot = sm.generate_dot_graph()
    # print(dot) # For debugging

    assert 'subgraph "cluster_A"' in dot
    assert 'label="A"' in dot
    assert '"A1" [label="A1"]' in dot
    assert '"A2" [label="A2"]' in dot
    assert '"B" [label="B"]' in dot
    assert '"C" [label="C"]' in dot

    assert '__start -> "A1"' in dot

    # Check edges with cluster options
    assert '"A1" -> "A2" [label="X"]' in dot
    assert '"A2" -> "B" [label="Y", ltail="cluster_A"]' in dot
    assert '"A" -> "C" [label="Z"]' in dot
    assert '"B" -> "A1" [label="R", lhead="cluster_A"]' in dot


def test_generate_mermaid_graph_simple() -> None:
    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit(Trigger.X, State.B)
    sm.configure(State.B).permit(Trigger.Y, State.A)

    mermaid = sm.generate_mermaid_graph()

    assert "stateDiagram-v2" in mermaid
    assert "[*] --> A" in mermaid
    assert "A --> B : X" in mermaid
    assert "B --> A : Y" in mermaid


def test_generate_mermaid_graph_features() -> None:
    """Tests Mermaid graph includes guards, internal, ignored, dynamic."""
    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit_if(Trigger.X, State.B, lambda: True, "GuardX").ignore(
        Trigger.Y
    ).internal_transition(Trigger.Z, lambda: None).dynamic(Trigger.R, lambda: State.C)
    sm.configure(State.B)
    sm.configure(State.C)

    mermaid = sm.generate_mermaid_graph()
    # print(mermaid) # For debugging

    # Guard
    assert "A --> B : X [GuardX]" in mermaid

    # Ignored - Should be a self-loop with (ignored)
    assert "A --> A : Y (ignored)" in mermaid

    # Internal - Should be a self-loop
    assert "A --> A : Z" in mermaid

    # Dynamic - Should be a self-loop showing selector
    assert "A --> A : R -> (<lambda>)" in mermaid


def test_generate_mermaid_graph_substates() -> None:
    sm = StateMachine[Any, Trigger](SubA.A1)
    sm.configure(SubA.A1).substate_of(State.A).permit(Trigger.X, SubA.A2)
    sm.configure(SubA.A2).substate_of(State.A).permit(Trigger.Y, State.B)
    sm.configure(State.A).permit(Trigger.Z, State.C)
    sm.configure(State.B).permit(Trigger.R, SubA.A1)
    sm.configure(State.C)

    mermaid = sm.generate_mermaid_graph()
    # print(mermaid) # For debugging

    assert 'state "A" {' in mermaid
    assert "A1 --> A2 : X" in mermaid
    assert "} " in mermaid
    assert "A2 --> B : Y" in mermaid
    assert "A --> C : Z" in mermaid
    assert "B --> A1 : R" in mermaid
    assert "[*] --> A1" in mermaid


# TODO: Add tests for DOT and Mermaid graph generation
