from typing import Dict, Iterator

import dodal.devices.athena.panda.tables as tables

from bluesky.protocols import Descriptor, Flyable, PartialEvent
from ophyd.v2.core import AsyncStatus, wait_for_value


class FlyingPanda(Flyable):
    def __init__(self, panda):
        self.dev = panda
        self._frames = []

    @property
    def name(self) -> str:
        return self.dev.name

    async def set_frames(self, frames):
        table = tables.build_table(*zip(*frames))
        await self.dev.seq[1].tables.set(table)

    @AsyncStatus.wrap
    async def kickoff(self) -> None:
        await self.dev.seq[1].enable.set("ONE")
        await wait_for_value(self.dev.seq[1].active, "1", 5)

    @AsyncStatus.wrap
    async def complete(self) -> None:
        await wait_for_value(self.dev.seq[1].active, "0", 20)
        await self.dev.seq[1].enable.set("ZERO")

    def collect(self) -> Iterator[PartialEvent]:
        yield from iter([])

    def describe_collect(self) -> Dict[str, Dict[str, Descriptor]]:
        return {}