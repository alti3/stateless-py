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


def test_generate_dot_graph_simple():
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


def test_generate_dot_graph_substates():
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
    assert '"A1" [label="A1"]' in dot  # Node inside cluster
    assert '"A2" [label="A2"]' in dot  # Node inside cluster
    assert '"B" [label="B"]' in dot  # Separate node
    assert '"C" [label="C"]' in dot  # Separate node

    assert '__start -> "A1"' in dot  # Initial state is substate

    # Check edges with cluster options
    assert '"A1" -> "A2" [label="X"]' in dot  # Internal to cluster
    assert '"A2" -> "B" [label="Y"][ltail="cluster_A"]' in dot  # Exiting cluster A
    assert (
        '"A" -> "C" [label="Z"]' not in dot
    )  # Should not have edge from "A" node directly if cluster
    # Edges from superstates need careful thought - current impl might add from node "A"
    # assert '"A" -> "C" [label="Z"][ltail="cluster_A"]' in dot # Ideal: edge from cluster boundary

    assert '"B" -> "A1" [label="R"][lhead="cluster_A"]' in dot  # Entering cluster A


def test_generate_mermaid_graph_simple():
    sm = StateMachine[State, Trigger](State.A)
    sm.configure(State.A).permit(Trigger.X, State.B)
    sm.configure(State.B).permit(Trigger.Y, State.A)

    mermaid = sm.generate_mermaid_graph()

    assert "stateDiagram-v2" in mermaid
    assert "[*] --> A" in mermaid
    assert "A --> B : X" in mermaid
    assert "B --> A : Y" in mermaid


def test_generate_mermaid_graph_substates():
    sm = StateMachine[Any, Trigger](SubA.A1)
    sm.configure(SubA.A1).substate_of(State.A).permit(Trigger.X, SubA.A2)
    sm.configure(SubA.A2).substate_of(State.A).permit(Trigger.Y, State.B)
    sm.configure(State.A).permit(Trigger.Z, State.C)
    sm.configure(State.B).permit(Trigger.R, SubA.A1)
    sm.configure(State.C)

    mermaid = sm.generate_mermaid_graph()
    # print(mermaid) # For debugging

    assert 'state "A" {' in mermaid
    assert "A1 --> A2 : X" in mermaid  # Inside A
    assert "} " in mermaid  # Closing A
    assert "A2 --> B : Y" in mermaid  # Exiting A
    assert "A --> C : Z" in mermaid  # From superstate A
    assert "B --> A1 : R" in mermaid  # To substate A1
    assert "[*] --> A1" in mermaid  # Initial state


# TODO: Add tests for DOT and Mermaid graph generation
