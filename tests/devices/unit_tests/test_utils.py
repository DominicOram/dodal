from unittest.mock import MagicMock

import pytest
from ophyd import Signal
from ophyd.signal import DEFAULT_WRITE_TIMEOUT, InternalSignalError
from ophyd.status import Status
from ophyd.utils import UnknownStatusFailure

from dodal.devices.utils import (
    chain_statuses,
    run_functions_without_blocking,
    set_then_restore,
)
from dodal.log import LOGGER


def get_bad_status():
    status = Status()
    status.set_exception(Exception)
    return status


def get_good_status():
    status = Status()
    status.set_finished()
    return status


def test_run_functions_without_blocking_errors_on_invalid_func():
    def bad_func():
        return 5

    with pytest.raises(ValueError):
        run_functions_without_blocking([bad_func], 5)


def test_full_status_gives_error_if_intermediate_status_fails():
    full_status = run_functions_without_blocking([get_bad_status], 5)
    error = full_status.exception()
    assert error is not None


def test_check_call_back_error_gives_correct_error():
    LOGGER.error = MagicMock()
    run_functions_without_blocking([get_bad_status])

    run_functions_without_blocking([get_good_status])
    LOGGER.error.assert_called_once()


def test_wrap_function_callback():
    dummy_func = MagicMock(return_value=Status)
    run_functions_without_blocking([lambda: get_good_status(), dummy_func])
    dummy_func.assert_called_once


@pytest.fixture
def signal_a() -> Signal:
    return Signal(name="signal_a", value=0.0)


@pytest.fixture
def signal_b() -> Signal:
    return Signal(name="signal_b", value=1.0)


def test_set_then_restore(signal_a: Signal, signal_b: Signal) -> None:
    with set_then_restore({signal_a: 1.0, signal_b: 2.0}) as cache:
        assert cache == {signal_a: 0.0, signal_b: 1.0}
        assert signal_a.get() == 1.0
        assert signal_b.get() == 2.0

    assert signal_a.get() == 0.0
    assert signal_b.get() == 1.0


def test_set_then_restore_restores_on_error(signal_a: Signal, signal_b: Signal) -> None:
    with pytest.raises(Exception):
        with set_then_restore({signal_a: 1.0, signal_b: 2.0}):
            raise Exception("oh dear!")

    assert signal_a.get() == 0.0
    assert signal_b.get() == 1.0


@pytest.mark.parametrize("chain_length", [0, 1, 2])
def test_chain_statuses(chain_length: int) -> None:
    chain = list(map(lambda _: Status(done=False), range(chain_length)))
    super_status = chain_statuses(chain)
    for status in chain:
        assert not super_status.done
        status.set_finished()
        status.wait(timeout=0.1)
    super_status.wait(timeout=0.1)
    assert super_status.done and super_status.success


def test_chain_statuses_failure() -> None:
    status_1 = Status(done=False)
    status_2 = Status(done=False)
    super_status = chain_statuses([status_1, status_2])
    assert not super_status.done
    status_1.set_exception(Exception("there has been an error"))
    with pytest.raises(Exception):
        super_status.wait(timeout=0.1)
    assert super_status.done and not super_status.success
