"""
Contains functions for generating graph representations (DOT, Mermaid) of the state machine.
"""

from typing import TYPE_CHECKING, TypeVar, Enum
from .reflection import GuardInfo

if TYPE_CHECKING:
    from .state_machine import StateMachine  # Avoid circular import
    from .reflection import (
        StateMachineInfo,
        StateInfo,
    )

StateT = TypeVar("StateT")
TriggerT = TypeVar("TriggerT")


def _get_state_name(state: str | Enum) -> str:
    """Helper to get a string representation for a state."""
    if isinstance(state, Enum):
        return state.name
    return str(state)


def _get_trigger_name(trigger: str | Enum) -> str:
    """Helper to get a string representation for a trigger."""
    if isinstance(trigger, Enum):
        return trigger.name
    return str(trigger)


def _format_guards(guards: list[GuardInfo]) -> str:
    """Formats guard conditions for display."""
    if not guards:
        return ""
    descriptions = [g.method_description.description for g in guards]
    return f" [{', '.join(descriptions)}]"


def generate_dot_graph(sm_info: "StateMachineInfo") -> str:
    """Generates a DOT graph representation of the state machine."""
    lines = ["digraph StateMachine {", "  compound=true; // Allow edges to clusters"]
    node_lines = []
    edge_lines = []
    cluster_nodes: dict[
        str, str
    ] = {}  # Map state name to cluster name if it's a cluster

    processed_states = set()

    def add_nodes_and_edges(
        states: list[StateInfo], parent_cluster_name: str | None = None
    ) -> None:
        nonlocal node_lines, edge_lines, cluster_nodes
        for state_info in states:
            state_name = _get_state_name(state_info.underlying_state)
            if state_name in processed_states:
                continue
            processed_states.add(state_name)

            node_id = f'"{state_name}"'  # Ensure names are quoted

            if state_info.substates:
                # Define as cluster
                current_cluster_name = f"cluster_{state_name}"
                cluster_nodes[state_name] = current_cluster_name  # Register as cluster
                lines.append(f'  subgraph "{current_cluster_name}" {{')
                lines.append(f'    label="{state_name}";')
                # Add initial transition node *inside* the cluster if needed
                if state_info.initial_transition_target is not None:
                    entry_node_id = f'"{current_cluster_name}_entry"'
                    lines.append(
                        f'    {entry_node_id} [label="", shape=point, width=0.1, height=0.1, style=invis];'
                    )  # Invisible entry point
                add_nodes_and_edges(state_info.substates, current_cluster_name)
                lines.append("  }")
            else:
                # Define as simple node
                node_lines.append(f'  {node_id} [label="{state_name}"];')

            # Add edges originating from this state
            # If state is a cluster, edges should originate from the cluster boundary
            edge_origin_node = node_id
            origin_cluster = cluster_nodes.get(state_name)
            origin_opts = f'ltail="{origin_cluster}"' if origin_cluster else ""

            # Fixed Transitions
            for trans in state_info.fixed_transitions:
                trigger_name = _get_trigger_name(trans.trigger.underlying_trigger)
                dest_name = _get_state_name(trans.destination_state)
                dest_node_id = f'"{dest_name}"'
                guards_str = _format_guards(trans.guard_conditions)
                # Add lhead if destination is a cluster
                dest_cluster = cluster_nodes.get(dest_name)
                dest_opts = f'lhead="{dest_cluster}"' if dest_cluster else ""
                opts = (
                    f"[{origin_opts}{',' if origin_opts and dest_opts else ''}{dest_opts}]"
                    if origin_opts or dest_opts
                    else ""
                )
                edge_lines.append(
                    f'  {edge_origin_node} -> {dest_node_id} [label="{trigger_name}{guards_str}"]{opts};'
                )

            # Ignored Triggers (Self-loop)
            for ignored in state_info.ignored_triggers:
                trigger_name = _get_trigger_name(ignored.trigger.underlying_trigger)
                guards_str = _format_guards(ignored.guard_conditions)
                # Self-loop doesn't need ltail/lhead
                edge_lines.append(
                    f'  {edge_origin_node} -> {edge_origin_node} [label="{trigger_name}{guards_str} (ignored)"];'
                )

            # Dynamic Transitions (Self-loop, dashed)
            for dyn in state_info.dynamic_transitions:
                trigger_name = _get_trigger_name(dyn.trigger.underlying_trigger)
                guards_str = _format_guards(dyn.guard_conditions)
                selector_desc = dyn.destination_state_selector_description.description
                edge_lines.append(
                    f'  {edge_origin_node} -> {edge_origin_node} [label="{trigger_name}{guards_str} -> ({selector_desc})", style=dashed];'
                )

            # Initial Transition *within* a Superstate
            if (
                state_info.initial_transition_target is not None
                and state_info.substates
            ):
                target_name = _get_state_name(state_info.initial_transition_target)
                target_node_id = f'"{target_name}"'
                entry_node_id = (
                    f'"{cluster_nodes[state_name]}_entry"'  # Use the invisible node ID
                )
                # Add lhead if target is also a cluster
                target_cluster = cluster_nodes.get(target_name)
                target_opts = f'lhead="{target_cluster}"' if target_cluster else ""
                edge_lines.append(
                    f'  {entry_node_id} -> {target_node_id} [label="initial"{"," if target_opts else ""}{target_opts}];'
                )

    # Add overall initial state marker
    initial_state_name = _get_state_name(sm_info.initial_state)
    initial_node_id = f'"{initial_state_name}"'
    node_lines.append(
        '  __start [label="", shape=circle, fillcolor=black, width=0.2, height=0.2, style=filled];'
    )
    # Add lhead if initial state is a cluster
    initial_cluster = cluster_nodes.get(
        initial_state_name
    )  # Check after processing all nodes
    initial_opts = f'[lhead="{initial_cluster}"]' if initial_cluster else ""
    edge_lines.append(f"  __start -> {initial_node_id}{initial_opts};")

    # Process all states (needs to happen before adding initial edge options)
    add_nodes_and_edges(sm_info.states)

    # Re-check initial state cluster after processing
    initial_cluster = cluster_nodes.get(initial_state_name)
    initial_opts = f'[lhead="{initial_cluster}"]' if initial_cluster else ""
    # Find and update the initial edge line (this is a bit hacky)
    for i, line in enumerate(edge_lines):
        if line.strip().startswith("__start ->"):
            edge_lines[i] = f"  __start -> {initial_node_id}{initial_opts};"
            break

    lines.extend(node_lines)
    lines.extend(edge_lines)
    lines.append("}")
    return "\n".join(lines)


def generate_mermaid_graph(sm_info: "StateMachineInfo", direction: str = "TB") -> str:
    """Generates a Mermaid graph representation of the state machine."""
    lines = ["stateDiagram-v2", f"    direction {direction}"]
    edge_lines = []
    processed_states = set()

    def add_mermaid_elements(states: list[StateInfo]) -> None:
        nonlocal edge_lines
        for state_info in states:
            state_name = _get_state_name(state_info.underlying_state)
            if state_name in processed_states:
                continue
            processed_states.add(state_name)

            origin_name = state_name  # Use clean name for mermaid

            if state_info.substates:
                lines.append(f'    state "{origin_name}" {{')
                # Initial transition within substate
                if state_info.initial_transition_target:
                    target_name = _get_state_name(state_info.initial_transition_target)
                    lines.append(f"        [*] --> {target_name}")
                add_mermaid_elements(state_info.substates)
                lines.append("    }")
            # else: # Simple states are implicitly defined by transitions

            # Transitions from this state
            for trans in state_info.fixed_transitions:
                trigger_name = _get_trigger_name(trans.trigger.underlying_trigger)
                dest_name = _get_state_name(trans.destination_state)
                guards_str = _format_guards(
                    trans.guard_conditions
                )  # Mermaid doesn't support guards well in labels
                edge_lines.append(
                    f"    {origin_name} --> {dest_name} : {trigger_name}{guards_str}"
                )

            # Ignored (Self-loop)
            for ignored in state_info.ignored_triggers:
                trigger_name = _get_trigger_name(ignored.trigger.underlying_trigger)
                guards_str = _format_guards(ignored.guard_conditions)
                edge_lines.append(
                    f"    {origin_name} --> {origin_name} : {trigger_name}{guards_str} (ignored)"
                )

            # Dynamic (Self-loop with description)
            for dyn in state_info.dynamic_transitions:
                trigger_name = _get_trigger_name(dyn.trigger.underlying_trigger)
                guards_str = _format_guards(dyn.guard_conditions)
                selector_desc = dyn.destination_state_selector_description.description
                edge_lines.append(
                    f"    {origin_name} --> {origin_name} : {trigger_name}{guards_str} -> ({selector_desc})"
                )

    # Initial transition for the whole machine
    initial_state_name = _get_state_name(sm_info.initial_state)
    lines.append(f"    [*] --> {initial_state_name}")

    # Process all states
    add_mermaid_elements(sm_info.states)

    lines.extend(edge_lines)
    return "\n".join(lines)


def visualize_graph(
    sm: "StateMachine[StateT, TriggerT]",
    filename: str = "state_machine.gv",
    format: str = "png",
    view: bool = True,
) -> None:
    """
    Generates and optionally views a graph using Graphviz.
    Requires the 'graphviz' optional dependency and executable.
    """
    try:
        import graphviz  # type: ignore
    except ImportError:
        print(
            "Optional dependency 'graphviz' not found. Install with 'pip install stateless-py[graphing]'"
        )
        return

    sm_info = sm.get_info()
    dot_graph = generate_dot_graph(sm_info)

    try:
        graph = graphviz.Source(dot_graph, filename=filename, format=format)
        graph.render(view=view, cleanup=True)
        print(f"Graph saved to {filename}.{format}")
    except graphviz.backend.execute.ExecutableNotFound:
        print(
            "Graphviz executable not found. Please install Graphviz (https://graphviz.org/download/) and ensure it's in your PATH."
        )
    except Exception as e:
        print(f"Error rendering graph: {e}")
