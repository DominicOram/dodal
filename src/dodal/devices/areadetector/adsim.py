from ophyd import Component as Cpt
from ophyd.areadetector.base import ADComponent as Cpt
from ophyd.areadetector.detectors import DetectorBase

from .adutils import (
    Hdf5Writer,
    PluginWiring,
    SingleTriggerV33,
    SynchronisedAdDriverBase,
)


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

    def __init__(self, *args, wiring: PluginWiring, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.plugin_wiring = wiring
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

        priming_settings = {
            self.hdf.enable: 1,
            self.hdf.nd_array_port: self.cam.port_name.get(),
            self.cam.array_callbacks: 1,
            self.cam.image_mode: "Single",
            self.cam.trigger_mode: "Internal",
            # Take the quickest possible frame
            self.cam.acquire_time: 0.0,
            self.cam.acquire_period: 0.0,
        }

        # Backup state and ensure we are not acquiring
        reset_to = {signal: signal.get() for signal in priming_settings.keys()}
        self.cam.acquire.set(0).wait(timeout=timeout)

        try:
            # Apply all settings for acquisition
            for signal, value in priming_settings.items():
                # Ensure that .wait really will wait until the PV is set including its RBV
                signal.set(value).wait(timeout=timeout)

            # Acquire a frame
            self.cam.acquire.set(1).wait(timeout=timeout)
        finally:
            # Revert settings to previous values
            for signal, value in reversed(reset_to.items()):
                signal.set(value).wait(timeout=timeout)
