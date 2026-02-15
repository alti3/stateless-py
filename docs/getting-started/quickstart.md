# Quickstart

## 1. Define States and Triggers

```python
from enum import Enum, auto

class OrderState(Enum):
    DRAFT = auto()
    SUBMITTED = auto()
    APPROVED = auto()

class OrderTrigger(Enum):
    SUBMIT = auto()
    APPROVE = auto()
```

## 2. Configure the State Machine

```python
from stateless import StateMachine

sm = StateMachine[OrderState, OrderTrigger](OrderState.DRAFT)

sm.configure(OrderState.DRAFT).permit(OrderTrigger.SUBMIT, OrderState.SUBMITTED)
sm.configure(OrderState.SUBMITTED).permit(OrderTrigger.APPROVE, OrderState.APPROVED)
```

## 3. Fire Triggers

```python
sm.fire(OrderTrigger.SUBMIT)
assert sm.state == OrderState.SUBMITTED

sm.fire(OrderTrigger.APPROVE)
assert sm.state == OrderState.APPROVED
```

## 4. Add a Guard

```python
is_eligible = False

def can_approve() -> bool:
    return is_eligible

sm = StateMachine[OrderState, OrderTrigger](OrderState.SUBMITTED)
sm.configure(OrderState.SUBMITTED).permit_if(
    OrderTrigger.APPROVE,
    OrderState.APPROVED,
    can_approve,
    "Order must be eligible",
)
```

If `can_approve()` is `False`, `fire(...)` raises `InvalidTransitionError`.

## 5. Use Async Guards or Actions

```python
import asyncio

async def can_approve_async() -> bool:
    await asyncio.sleep(0.01)
    return True

sm = StateMachine[OrderState, OrderTrigger](OrderState.SUBMITTED)
sm.configure(OrderState.SUBMITTED).permit_if(
    OrderTrigger.APPROVE,
    OrderState.APPROVED,
    can_approve_async,
)

await sm.fire_async(OrderTrigger.APPROVE)
```

Use `fire_async(...)` when any involved guard/action/selector is async.
