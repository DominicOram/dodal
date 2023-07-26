from dodal.beamlines.beamline_utils import device_instantiation
from dodal.devices.areadetector import AdAravisDetector
from dodal.utils import BeamlinePrefix

PREFIX: str = BeamlinePrefix("p38").beamline_prefix


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
