from pathlib import Path
from dodal.utils import BeamlinePrefix
from dodal.devices.athena.panda import FlyingPanda

from ophyd.v2.core import DeviceCollector
from ophyd_epics_devices.panda import PandA
from ophyd_epics_devices.areadetector import (
    ADDriver,
    HDFStreamerDet,
    NDFileHDF,
    TmpDirectoryProvider,
)


BEAMLINE = "p38"
PREFIX: str = BeamlinePrefix(f"{BEAMLINE}").beamline_prefix


def d11(name: str = "D11") -> HDFStreamerDet:
    ## Ophyd V1 setup
    # det = AdAravisDetector(name=name, prefix=f"{PREFIX}-DI-DCAM-03:")
    # det.hdf.reg_root = "/dls/p38/data/2023/cm33874-3"
    # det.hdf.write_path_template = "%Y"

    d11_dir = TmpDirectoryProvider()
    d11_dir._directory = Path(f"/dls/{BEAMLINE}/data/2023/cm33874-3/D11")

    with DeviceCollector():
        d11_drv = ADDriver(f"{PREFIX}-DI-DCAM-03:DET:")
        d11_hdf = NDFileHDF(f"{PREFIX}-DI-DCAM-03:HDF5:")
        det = HDFStreamerDet(d11_drv, d11_hdf, d11_dir)
    return det


def d12(name: str = "D12") -> HDFStreamerDet:
    ## Ophyd V1 setup
    # det = AdAravisDetector(name=name, prefix=f"{PREFIX}-DI-DCAM-04:")
    # det.hdf.reg_root = "/dls/p38/data/2023/cm33874-3"
    # det.hdf.write_path_template = "%Y"

    d12_dir = TmpDirectoryProvider()
    d12_dir._directory = Path(f"/dls/{BEAMLINE}/data/2023/cm33873/D12")

    with DeviceCollector():
        d12_drv = ADDriver(f"{PREFIX}-DI-DCAM-04:DET:")
        d12_hdf = NDFileHDF(f"{PREFIX}-DI-DCAM-04:HDF5:")
        det = HDFStreamerDet(d12_drv, d12_hdf, d12_dir)
    return det


def panda(name: str = "PANDA") -> PandA:
    with DeviceCollector():
        pbox = PandA("BL38P-PANDA")
    return pbox


def fl_panda(name: str = "FL_PANDA", pnd: PandA = None) -> FlyingPanda:
    pbox = FlyingPanda(pnd)
    return pbox