# Reflection Models

Introspection models are defined in `stateless.reflection` using Pydantic.

## Core Models

- `InvocationInfo`
- `GuardInfo`
- `ActionInfo`
- `TriggerInfo`
- `TransitionInfo`
- `DynamicTransitionInfo`
- `InternalTransitionInfo`
- `IgnoredTransitionInfo`
- `StateInfo`
- `StateMachineInfo`

## How They Are Produced

`StateMachine.get_info()` walks configured states and builds model instances for every configured action/transition relationship.

## Useful Fields

- `InvocationInfo.is_async`: determine async handlers
- `TriggerInfo.parameter_types`: populated by `set_trigger_parameters(...)`
- `StateInfo.substates` + `StateInfo.superstate_value`: inspect hierarchy
- `StateInfo.initial_transition_target`: inspect configured initial substate
