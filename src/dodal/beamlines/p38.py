from dodal.devices.areadetector import AdAravisDetector
from dodal.utils import BeamlinePrefix

PREFIX: str = BeamlinePrefix("p38").beamline_prefix


def d11(name: str = "D11") -> AdAravisDetector:
    det = AdAravisDetector(name=name, prefix=f"{PREFIX}-DI-DCAM-03:")
    det.hdf.reg_root = "/dls/p38/data/2023/cm33874-3"
    det.hdf.write_path_template = "%Y"
    return det


def d12(name: str = "D12") -> AdAravisDetector:
    det = AdAravisDetector(name=name, prefix=f"{PREFIX}-DI-DCAM-04:")
    det.hdf.reg_root = "/dls/p38/data/2023/cm33874-3"
    det.hdf.write_path_template = "%Y"
    return det
