from ophyd import Component as Cpt
from ophyd import DetectorBase, EpicsSignal
from ophyd.areadetector.base import ADComponent as Cpt
from ophyd.areadetector.detectors import DetectorBase

from dodal.devices.utils import set_then_restore

from .adutils import Hdf5Writer, SingleTriggerV33, SynchronisedAdDriverBase


class AdSimDetector(SingleTriggerV33, DetectorBase):
    cam: SynchronisedAdDriverBase = Cpt(
        SynchronisedAdDriverBase, suffix="CAM:", lazy=True
    )
    hdf: Hdf5Writer = Cpt(
        Hdf5Writer,
        suffix="HDF5:",
        root="",
        write_path_template="",
        lazy=True,
    )

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.hdf.kind = "normal"

        self.stage_sigs = {
            # Get stage to wire up the plugins
            self.hdf.nd_array_port: self.cam.port_name.get(),
            # Reset array counter on stage
            self.cam.array_counter: 0,
            # Set image mode to multiple on stage so we have the option, can still
            # set num_images to 1
            self.cam.image_mode: "Multiple",
            # For now, this Ophyd device does not support hardware
            # triggered scanning, disable on stage
            self.cam.trigger_mode: "Internal",
            **self.stage_sigs,  # type: ignore
        }

        # Settings to apply when priming plugins during pre-stage
        self._priming_settings = {
            self.hdf.enable: 1,
            self.hdf.nd_array_port: self.cam.port_name.get(),
            self.cam.array_callbacks: 1,
            self.cam.image_mode: "Single",
            self.cam.trigger_mode: "Off",
            # Take the quickest possible frame
            self.cam.acquire_time: 6.3e-05,
            self.cam.acquire_period: 0.003,
        }

        # Signals that control driver and hdf writer should be put_complete to
        # avoid race conditions during priming
        for signal in set(self.stage_sigs.keys()).union(
            set(self._priming_settings.keys())
        ):
            if isinstance(signal, EpicsSignal):
                signal.put_complete = True
        self.cam.acquire.put_complete = True

    def stage(self, *args, **kwargs):
        # We have to manually set the acquire period bcause the EPICS driver
        # doesn't do it for us. If acquire time is a staged signal, we use the
        # stage value to calculate the acquire period, otherwise we perform
        # a caget and use the current acquire time.
        if self.cam.acquire_time in self.stage_sigs:
            acquire_time = self.stage_sigs[self.cam.acquire_time]
        else:
            acquire_time = self.cam.acquire_time.get()
        self.stage_sigs[self.cam.acquire_period] = acquire_time

        # Ensure plugins are primed
        self._minimal_frame(timeout=10.0)

        # Now calling the super method should set the acquire period
        super(AdSimDetector, self).stage(*args, **kwargs)

    def _minimal_frame(self, timeout: float) -> None:
        """
        Take a single frame and pipe it through all enabled plugins
        """

        self.cam.acquire.set(0).wait(timeout=timeout)
        with set_then_restore(self._priming_settings):
            # Acquire a frame
            self.cam.acquire.set(1).wait(timeout=timeout)
