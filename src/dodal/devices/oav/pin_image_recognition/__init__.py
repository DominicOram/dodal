import asyncio
import time
from collections import OrderedDict
from typing import Optional, Tuple, Type, TypeVar

import numpy as np
from bluesky.protocols import Descriptor
from numpy.typing import NDArray
from ophyd.v2.core import Device, Readable, Reading, SimSignalBackend
from ophyd.v2.epics import SignalR, SignalRW, epics_signal_r

from dodal.devices.oav.pin_image_recognition.utils import (
    ARRAY_PROCESSING_FUNCTIONS_MAP,
    MxSampleDetect,
    ScanDirections,
    identity,
)
from dodal.log import LOGGER

T = TypeVar("T")


def _create_soft_signal(datatype: Type[T], name: str) -> SignalRW[T]:
    return SignalRW(
        SimSignalBackend(
            datatype, f"sim://oav_with_pin_tip_detection_soft_params:{name}"
        )
    )


class PinTipDetection(Readable, Device):
    """
    A device which will read a single frame from an on-axis view and use that frame
    to calculate the pin-tip offset (in pixels) of that frame.

    Used for pin tip centring workflow.

    Note that if the tip of the sample is off-screen, this class will return the centre as the "edge"
    of the image. If the entire sample if off-screen (i.e. no suitable edges were detected at all)
    then it will return (None, None).
    """

    def __init__(self, prefix: str, name: str = ""):
        self._prefix: str = prefix
        self._name = name

        self.array_data: SignalR[NDArray[np.uint8]] = epics_signal_r(
            NDArray[np.uint8], f"pva://{prefix}PVA:ARRAY"
        )

        self.oav_width: SignalR[int] = epics_signal_r(
            int, f"{prefix}PVA:ArraySize1_RBV"
        )
        self.oav_height: SignalR[int] = epics_signal_r(
            int, f"{prefix}PVA:ArraySize2_RBV"
        )

        # Soft parameters for pin-tip detection.
        self.timeout: SignalRW[float] = _create_soft_signal(float, "timeout")
        self.preprocess: SignalRW[int] = _create_soft_signal(int, "preprocess")
        self.preprocess_ksize: SignalRW[int] = _create_soft_signal(
            int, "preprocess_ksize"
        )
        self.preprocess_iterations: SignalRW[int] = _create_soft_signal(
            int, "preprocess_iterations"
        )
        self.canny_upper: SignalRW[int] = _create_soft_signal(int, "canny_upper")
        self.canny_lower: SignalRW[int] = _create_soft_signal(int, "canny_lower")
        self.close_ksize: SignalRW[int] = _create_soft_signal(int, "close_ksize")
        self.close_iterations: SignalRW[int] = _create_soft_signal(
            int, "close_iterations"
        )
        self.scan_direction: SignalRW[int] = _create_soft_signal(int, "scan_direction")
        self.min_tip_height: SignalRW[int] = _create_soft_signal(int, "min_tip_height")

        super().__init__(name=name)

    async def _get_tip_position(
        self,
    ) -> Tuple[Tuple[Optional[int], Optional[int]], float]:
        """
        Gets the location of the pin tip.

        Returns tuple of:
            ((tip_x, tip_y), timestamp)
        """

        preprocess_key = await self.preprocess.get_value()
        preprocess_iter = await self.preprocess_iterations.get_value()
        preprocess_ksize = await self.preprocess_ksize.get_value()

        try:
            preprocess_func = ARRAY_PROCESSING_FUNCTIONS_MAP[preprocess_key](
                iter=preprocess_iter, ksize=preprocess_ksize
            )
        except KeyError:
            LOGGER.error("Invalid preprocessing function, using identity")
            preprocess_func = identity()

        sample_detection = MxSampleDetect(
            preprocess=preprocess_func,
            canny_lower=await self.canny_lower.get_value(),
            canny_upper=await self.canny_upper.get_value(),
            close_ksize=await self.close_ksize.get_value(),
            close_iterations=await self.close_iterations.get_value(),
            scan_direction=await self.scan_direction.get_value(),
            min_tip_height=await self.min_tip_height.get_value(),
        )

        array_reading: dict[str, Reading] = await self.array_data.read()
        array_data: NDArray[np.uint8] = array_reading[""]["value"]
        timestamp: float = array_reading[""]["timestamp"]

        height: int = await self.oav_height.get_value()
        width: int = await self.oav_width.get_value()

        num_pixels: int = height * width  # type: ignore
        value_len = array_data.shape[0]

        try:
            if value_len == num_pixels * 3:
                # RGB data
                value = array_data.reshape(height, width, 3)
            elif value_len == num_pixels:
                # Grayscale data
                value = array_data.reshape(height, width)
            else:
                # Something else?
                raise ValueError(
                    "Unexpected data array size: expected {} (grayscale data) or {} (rgb data), got {}",
                    num_pixels,
                    num_pixels * 3,
                    value_len,
                )

            start_time = time.time()
            location = sample_detection.processArray(value)
            end_time = time.time()
            LOGGER.debug(
                "Sample location detection took {}ms".format(
                    (end_time - start_time) * 1000.0
                )
            )
            tip_x = location.tip_x
            tip_y = location.tip_y
        except Exception as e:
            LOGGER.error(f"Failed to detect pin-tip location due to exception: {e}")
            tip_x = None
            tip_y = None

        return (tip_x, tip_y), timestamp

    async def connect(self, sim: bool = False):
        await super().connect(sim)

        # Set defaults for soft parameters
        await self.timeout.set(10.0)
        await self.canny_upper.set(100)
        await self.canny_lower.set(50)
        await self.close_iterations.set(5)
        await self.close_ksize.set(5)
        await self.scan_direction.set(ScanDirections.FORWARD.value)
        await self.min_tip_height.set(5)
        await self.preprocess.set(10)  # Identity function
        await self.preprocess_iterations.set(5)
        await self.preprocess_ksize.set(5)

    async def read(self) -> dict[str, Reading]:
        tip_pos, timestamp = await asyncio.wait_for(
            self._get_tip_position(), timeout=await self.timeout.get_value()
        )

        return OrderedDict(
            [
                (self._name, {"value": tip_pos, "timestamp": timestamp}),
            ]
        )

    async def describe(self) -> dict[str, Descriptor]:
        return OrderedDict(
            [
                (
                    self._name,
                    {
                        "source": f"pva://{self._prefix}PVA:ARRAY",
                        "dtype": "number",
                        "shape": [2],  # Tuple of (x, y) tip position
                    },
                )
            ],
        )
