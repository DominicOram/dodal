import pytest
from dodal.devices.areadetector.adsim import AdSimDetector
from dodal.beamlines.adsim import det

from tempfile import TemporaryDirectory
import os


@pytest.fixture
def data_directory() -> TemporaryDirectory:
    data_dir = TemporaryDirectory()
    os.makedirs(data_dir.name, exist_ok=True)
    assert os.path.exists(data_dir.name)
    return data_dir


@pytest.fixture
def adsim(data_directory: TemporaryDirectory) -> AdSimDetector:
    assert os.environ["EPICS_CA_SERVER_PORT"] == "6064"
    assert os.environ["EPICS_CA_REPEATER_PORT"] == "6065"

    adsim = det()

    adsim.hdf.reg_root = "/"
    # adsim.hdf.read_path_template = data_directory.name
    adsim.hdf.write_path_template = data_directory.name
    # adsim.hdf.read_path_template = "tmpdata"

    adsim.wait_for_connection()
    return adsim


@pytest.mark.adsim
def test_stage_and_unstage(adsim: AdSimDetector) -> None:
    adsim.stage()
    adsim.unstage()


@pytest.mark.adsim
def test_hdf_armed(adsim: AdSimDetector) -> None:
    adsim.stage()
    assert adsim.hdf.array_counter.get() == 0
    assert adsim.hdf.capture.get()
    adsim.unstage()
    assert not adsim.hdf.capture.get()


from bluesky import RunEngine
from bluesky.plans import count
from databroker import Broker

from databroker import catalog, temp


@pytest.mark.adsim
def test_acquire_data(adsim: AdSimDetector) -> None:
    broker = temp()
    RE = RunEngine()
    RE(count([adsim], num=5), broker.v1.insert)
    images = broker.get_images(broker[-1], "adsim_image")
    # Shape of sim detector in default startup state
    assert images.shape == (5, 100, 960, 1280)
