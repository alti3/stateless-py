# Stateless-py Examples Overview

This document provides a brief overview of the features demonstrated in each example file.

1.  **`01_simple_phone_call.py`**
    *   Basic state machine setup (`StateMachine`).
    *   Defining states and triggers using `Enum`.
    *   Configuring transitions (`configure`, `permit`).
    *   Firing triggers (`fire`).
    *   Entry and Exit actions (`on_entry`, `on_exit`).
    *   Parameterized triggers and actions (passing arguments to `fire`).
    *   Checking permitted triggers (`get_permitted_triggers`).

2.  **`02_bug_tracker.py`**
    *   More complex state transitions.
    *   Parameterized triggers (`fire` with arguments).
    *   Entry actions specific to a trigger (`on_entry_from`).
    *   Re-entry transitions (`permit_reentry`).
    *   Ignoring triggers (`ignore`).
    *   Checking if a trigger can be fired (`can_fire`).

3.  **`03_async_actions.py`**
    *   Using `async def` for entry/exit actions.
    *   Firing triggers asynchronously (`fire_async`).
    *   Handling potential concurrent trigger firing with async queues.

4.  **`04_ignore_reentry.py`**
    *   Demonstrates `ignore` for triggers that shouldn't cause a transition in the current state.
    *   Demonstrates `permit_reentry` for triggers that should cause exit/entry actions within the same state.

5.  **`05_on_off.py`**
    *   A minimal example showing the most basic setup and transitions (like the README example).

6.  **`06_alarm_asyncio.py`**
    *   A more comprehensive `asyncio` example.
    *   Combines async actions (`on_entry_from`, `on_exit`) with `asyncio.sleep` and `asyncio.create_task`.
    *   Uses `fire_async` extensively.
    *   Demonstrates state transitions driven by timed events.

7.  **`07_json_serialization.py`**
    *   Saving and loading state machine state using JSON.
    *   Defining custom JSON encoders/decoders for state and trigger types (Enums).
    *   Restoring the state machine to a previously saved state (`load_state`).

8.  **`08_advanced_features.py`**
    *   Guard clauses for transitions (`permit_if`).
    *   Superstates and Substates (`substate_of`).
    *   Activation/Deactivation actions for superstate scopes (`on_activate`, `on_deactivate`).
    *   Internal transitions (actions within a state without exit/entry) (`internal_transition`).
    *   Initial transitions for superstates (`initial_transition`).
    *   Using a base `Enum` type hint for state machines with mixed Enum state types. 