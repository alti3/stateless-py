# Transition Model

`Transition[StateT, TriggerT]` describes a single transition event.

## Properties

```python
source
destination
trigger
parameters
is_reentry
```

## Constructor

```python
Transition(source, destination, trigger, parameters=())
```

## InitialTransition

`InitialTransition` extends `Transition` and is used internally when entering configured initial substates.

## Usage

Transition objects are passed to callbacks/actions to provide contextual data about the current transition.
