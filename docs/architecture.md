# Architecture

The diagram below shows major modules and interactions.

```mermaid
graph TD
    subgraph "Configuration & Transition Modules"
        CFG["State Configuration"]:::config
        TRANS["Transition Manager"]:::config
    end

    subgraph "Core Engine"
        CORE["State Machine Engine"]:::core
    end

    subgraph "Processing Components"
        ACT["Action Executor"]:::processing
        FIRE["Firing Modes"]:::processing
        GUARD["Guard Evaluation"]:::processing
    end

    subgraph "Visualization & Introspection"
        GRAPH["Graph Generator"]:::viz
        INTROSPECT["Introspection & Reflection"]:::viz
    end

    ERROR["Error Handling"]:::error

    CFG --> CORE
    TRANS --> CORE
    CORE --> ACT
    CORE --> FIRE
    CORE --> GUARD
    CORE --> GRAPH
    CORE --> INTROSPECT
    CORE --> ERROR
    GUARD --> ERROR

    classDef config fill:#ADD8E6,stroke:#000,stroke-width:2px;
    classDef core fill:#90EE90,stroke:#000,stroke-width:2px;
    classDef processing fill:#FFDAB9,stroke:#000,stroke-width:2px;
    classDef viz fill:#D8BFD8,stroke:#000,stroke-width:2px;
    classDef error fill:#FFB6C1,stroke:#000,stroke-width:2px;
```

## Module Roles

- `state_machine.py`: orchestration engine and firing logic
- `state_configuration.py`: fluent API for machine configuration
- `state_representation.py`: internal per-state behavior store
- `trigger_behaviour.py`: behavior implementations (fixed, ignored, reentry, internal, dynamic)
- `actions.py`: action wrappers/factories for sync/async execution
- `guards.py`: guard evaluation logic
- `reflection.py`: introspection schema models
- `graph.py`: DOT/Mermaid generation and Graphviz render helper
