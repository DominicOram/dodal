from dodal.beamlines.beamline_utils import BL, device_instantiation
from dodal.beamlines.beamline_utils import set_beamline as set_utils_beamline
from dodal.devices.areadetector import AdAravisDetector
from dodal.log import set_beamline
from dodal.utils import BeamlinePrefix, get_beamline_name

PREFIX: str = BeamlinePrefix("p38").beamline_prefix

BL = get_beamline_name("p38")
set_beamline(BL)
set_utils_beamline(BL)


def d11(
    wait_for_connection: bool = True,
    fake_with_ophyd_sim: bool = False,
) -> AdAravisDetector:
    return device_instantiation(
        device=AdAravisDetector,
        name="D11",
        prefix=f"{PREFIX}-DI-DCAM-03:",
        wait=wait_for_connection,
        fake=fake_with_ophyd_sim,
    )


def d12(
    wait_for_connection: bool = True,
    fake_with_ophyd_sim: bool = False,
) -> AdAravisDetector:
    return device_instantiation(
        device=AdAravisDetector,
        name="D12",
        prefix=f"{PREFIX}-DI-DCAM-04:",
        wait=wait_for_connection,
        fake=fake_with_ophyd_sim,
    )
