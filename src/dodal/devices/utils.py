import functools
import operator
import time
from contextlib import contextmanager
from functools import partial
from typing import (
    Any,
    Callable,
    Iterable,
    Mapping,
    Optional,
    Protocol,
    runtime_checkable,
)

from bluesky.protocols import Movable
from ophyd import Component, EpicsSignal
from ophyd.status import AndStatus, Status, StatusBase

from dodal.log import LOGGER


def epics_signal_put_wait(pv_name: str, wait: float = 1.0) -> EpicsSignal:
    """Creates a `Component` around an `EpicsSignal` that waits for a callback on a put.

    Args:
        pv_name (str): The name of the PV for the `EpicsSignal`
        wait (str, optional): The timeout to wait for a callback. Defaults to 1.0.

    Returns:
        EpicsSignal: An EpicsSignal that will wait for a callback.
    """
    return Component(EpicsSignal, pv_name, put_complete=True, write_timeout=wait)


def run_functions_without_blocking(
    functions_to_chain: list[Callable[[], StatusBase]],
    timeout: float = 60.0,
) -> Status:
    """Creates and initiates an asynchronous chaining of functions which return a status.

    Usage:
    This function can be used to take a series of status-returning functions and run them all sequentially and in the background by making use of callbacks. It also ensures exceptions on each returned status are propagated

    Args:
    functions_to_chain( list(function - > StatusBase) ): A list of functions which each return a status object

    Returns:
    Status: A status object which is marked as complete once all of the Status objects returned by the
    unwrapped functions have completed.
    """

    # The returned status - marked as finished at the end of the callback chain. If any
    # intermediate statuses have an exception, the full_status will timeout.
    full_status = Status(timeout=timeout)

    def closing_func():
        full_status.set_finished()

    # Wrap each function by first checking the previous status and attaching a callback to the next
    # function in the chain
    def wrap_func(old_status, current_func: Callable[[], StatusBase], next_func):
        check_callback_error(old_status)
        status = current_func()

        if not isinstance(status, StatusBase):
            LOGGER.error(
                f"wrap_func attempted to wrap {current_func} when it does not return a Status"
            )
            raise ValueError(f"{current_func} does not return a Status")

        status.add_callback(next_func)

    def check_callback_error(status: Status):
        error = status.exception()
        if error is not None:
            full_status.set_exception(error)
            # So full_status can also be checked for any errors
            LOGGER.error(f"Status {status} has failed with error {error}")

    # Each wrapped function needs to attach its callback to the subsequent wrapped function, therefore
    # wrapped_funcs list needs to be created in reverse order

    wrapped_funcs = list()
    wrapped_funcs.append(
        partial(
            wrap_func,
            current_func=functions_to_chain[-1],
            next_func=closing_func,
        )
    )

    # Wrap each function in reverse
    for num, func in enumerate(list(reversed(functions_to_chain))[1:-1]):
        wrapped_funcs.append(
            partial(
                wrap_func,
                current_func=func,
                next_func=wrapped_funcs[-1],
            )
        )

    starting_status = Status(done=True, success=True)

    # Initiate the chain of functions
    wrap_func(starting_status, functions_to_chain[0], wrapped_funcs[-1])
    return full_status


@runtime_checkable
class MovableAndGettable(Movable, Protocol):
    def get(self) -> Any:
        ...


@contextmanager
def set_then_restore(
    demands: Mapping[MovableAndGettable, Any],
    timeout: Optional[float] = 10.0,
):
    """
    Set a collection of signals. Restore values upon exit of context manager.

    Example:
        with set_then_restore({a: 1, b: 2}):
            # Do things with a and b

        # a and b will be restored to their original values here

    Args:
        demands: Dictionary of signals and the values to set them to for the duration
            of the context.
        timeout: Timeout to apply when . Defaults to 10.0.

    Yields:
        cache: Dictionary of signals to restore values
    """
    cache = {signal: signal.get() for signal in demands.keys()}
    try:
        all_set_operations = [signal.set(value) for signal, value in demands.items()]
        status = chain_statuses(all_set_operations)
        status.wait(timeout=timeout)
        yield cache
    finally:
        chain_statuses(
            (signal.set(original_value) for signal, original_value in cache.items())
        ).wait(timeout=timeout)


def chain_statuses(statuses: Iterable[Status]) -> Status:
    """
    Creates a status that ands together a series of statuses.
    The returned status succeeds when all input statuses succeed and fails when
    any one input status fails.

    Args:
        statuses: Iterable of statuses to and together.

    Returns:
        Status: A wrapping status
    """

    # Strange timing going on in Ophyd library, Status is not done on creation
    # despite constructor
    initial = Status(done=True, success=True)
    initial.wait(timeout=0.1)

    def reducer(a: Status, b: Status) -> Status:
        return AndStatus(a, b)

    return functools.reduce(reducer, list(statuses), initial)
