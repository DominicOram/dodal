import pytest
from bluesky import plan_stubs as bps
from bluesky.run_engine import RunEngine
from ophyd.sim import make_fake_device

from dodal.devices.i24.dual_backlight import DualBacklight


@pytest.fixture
def fake_backlight() -> DualBacklight:
    FakeBacklight = make_fake_device(DualBacklight)
    fake_backlight: DualBacklight = FakeBacklight(name="backlight")

    fake_backlight.pos1.zrst.set("Out")
    fake_backlight.pos1.onst.set("In")
    fake_backlight.pos1.twst.set("LoadCheck")
    fake_backlight.pos1.thst.set("OAV2")
    fake_backlight.pos1.frst.set("Diode")
    return fake_backlight


def test_dual_backlight_can_be_written_and_read_from(fake_backlight: DualBacklight):
    fake_backlight.led2.sim_put("OFF")
    assert fake_backlight.led2.get() == "OFF"


def test_backlight_position(fake_backlight: DualBacklight):
    fake_backlight.pos1.pos_level.sim_put(fake_backlight.IN)
    assert fake_backlight.pos1.pos_level.get() == "In"


def test_when_led1_out_it_switches_off(fake_backlight: DualBacklight):
    RE = RunEngine()
    RE(bps.abs_set(fake_backlight, fake_backlight.OUT))
    assert fake_backlight.led1.get() == "OFF"


def test_when_led1_not_out_it_switches_on(fake_backlight: DualBacklight):
    RE = RunEngine()
    RE(bps.abs_set(fake_backlight, "OAV2"))
    assert fake_backlight.led1.get() == "ON"


def test_allowed_positions(fake_backlight: DualBacklight):
    p = fake_backlight.pos1.allowed_backlight_positions
    assert type(p) is list
    assert len(p) == 5
