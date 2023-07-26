import sys
from unittest.mock import patch

with patch.dict("os.environ", {"BEAMLINE": "p38"}, clear=True):
    from dodal.beamlines import beamline_utils, p38
    from dodal.utils import make_all_devices


def test_device_creation():
    devices = make_all_devices(p38, fake_with_ophyd_sim=True)
    assert len(devices) > 0
    for device_name in devices.keys():
        assert device_name in beamline_utils.ACTIVE_DEVICES
    assert len(beamline_utils.ACTIVE_DEVICES) == len(devices)


def teardown_module():
    beamline_utils.BL = "p38"
    for module in list(sys.modules):
        if module.endswith("beamline_utils"):
            del sys.modules[module]
