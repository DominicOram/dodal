from pyfiglet import Figlet
from collections import deque, namedtuple
from itertools import cycle
import numpy as np

from ophyd_epics_devices.panda import SeqTable
from ophyd.v2.core import observe_value


Frame = namedtuple(
    "Frame",
    (
        "repeats",
        "trigger",
        "position",
        "time1",
        "outa1",
        "outb1",
        "outc1",
        "outd1",
        "oute1",
        "outf1",
        "time2",
        "outa2",
        "outb2",
        "outc2",
        "outd2",
        "oute2",
        "outf2",
    ),
)


def frames(text):
    """Convert the given text into 6x6 block format"""
    lines = Figlet(font="clr6x6", width=10 * len(text)).renderText(text).splitlines()
    return zip(*[[0 if c == " " else 1 for c in line] for line in lines][::-1])


def table_frames(frames, width, posn=600, step=6):
    """Convert stream of individual columns into windowed chunks"""
    buffer = deque((r for _, r in zip(range(width), frames)), maxlen=width)
    for frame in frames:
        yield from as_table_frame(buffer, posn, step)
        buffer.append(frame)


def frame(
    *,
    repeats=1,
    trigger="Immediate",
    position=0,
    time1=0,
    outa1=0,
    outb1=0,
    outc1=0,
    outd1=0,
    oute1=0,
    outf1=0,
    time2=0,
    outa2=0,
    outb2=0,
    outc2=0,
    outd2=0,
    oute2=0,
    outf2=0
) -> Frame:
    """Create frame optionally overriding default values"""
    return Frame(
        repeats,
        trigger,
        position,
        time1,
        outa1,
        outb1,
        outc1,
        outd1,
        oute1,
        outf1,
        time2,
        outa2,
        outb2,
        outc2,
        outd2,
        oute2,
        outf2,
    )


def as_table_frame(buffer, posn=600, step=6):
    """Convert a set of frame data into frames with positions and triggers"""
    yield frame(trigger="POSA>=POSITION", position=posn)
    for a, b, c, d, e, f, *_ in buffer:
        yield frame(
            trigger="POSA<=POSITION",
            position=posn,
            outa2=a,
            outb2=b,
            outc2=c,
            outd2=d,
            oute2=e,
            outf2=f,
        )
        posn -= step
        if posn <= 0:
            break
    yield frame(trigger="POSA<=POSITION", position=max(0, posn))


def table_chunks(frames, length):
    """Split stream of frames into groups that can be set as sequence tables"""
    buffer = [iter(frames)] * length
    for chunk in zip(*buffer):
        yield list(chunk) + [frame(repeats=0)]


def seq_tables(tables):
    for table in tables:
        yield build_table(*zip(*table))


def build_table(
    repeats,
    trigger,
    position,
    time1,
    outa1,
    outb1,
    outc1,
    outd1,
    oute1,
    outf1,
    time2,
    outa2,
    outb2,
    outc2,
    outd2,
    oute2,
    outf2,
):
    table = SeqTable()
    table["REPEATS"] = np.array(repeats, dtype=np.uint16)
    table["POSITION"] = np.array(position, dtype=np.int32)
    table["TRIGGER"] = np.array(trigger)
    table["TIME1"] = np.array(time1, np.uint32)
    table["OUTA1"] = np.array(outa1, np.uint8)
    table["OUTB1"] = np.array(outb1, np.uint8)
    table["OUTC1"] = np.array(outc1, np.uint8)
    table["OUTD1"] = np.array(outd1, np.uint8)
    table["OUTE1"] = np.array(oute1, np.uint8)
    table["OUTF1"] = np.array(outf1, np.uint8)
    table["TIME2"] = np.array(time2, np.uint32)
    table["OUTA2"] = np.array(outa2, np.uint8)
    table["OUTB2"] = np.array(outb2, np.uint8)
    table["OUTC2"] = np.array(outc2, np.uint8)
    table["OUTD2"] = np.array(outd2, np.uint8)
    table["OUTE2"] = np.array(oute2, np.uint8)
    table["OUTF2"] = np.array(outf2, np.uint8)
    return table


async def display(pnd, text, limit=50, posn=600, step=6, window=30, chunk=100):
    src = seq_tables(
        table_chunks(table_frames(cycle(frames(text)), window, posn, step), chunk)
    )
    await pnd.seq1.table.set(next(src))
    await pnd.seq1.enable.set("ONE")
    async for ready in observe_value(pnd.seq1.can_write_next):
        if ready == 1:
            print("New table time")
            active = await pnd.seq1.bita.get_value()
            if (
                limit == 0 or active == "ONE"
            ):  # intentionally == to allow -1 to be infinite
                print("Limit reached: " + active)
                await pnd.seq1.table.set(build_table([1], ["Immediate"], *([[0]] * 15)))
                await pnd.seq1.enable.set("ZERO")
                break
            await pnd.seq1.table.set(next(src))

            limit -= 1


def test_frames():
    exp = [
        (0, 0, 0, 0, 0, 0),
        (0, 0, 1, 1, 0, 0),
        (0, 1, 0, 0, 1, 0),
        (0, 1, 0, 0, 1, 0),
        (0, 0, 1, 0, 1, 0),
        (0, 1, 1, 1, 1, 0),
        (0, 0, 0, 0, 0, 0),
        (0, 0, 0, 0, 0, 0),
        (0, 1, 1, 1, 1, 1),
        (0, 1, 0, 0, 1, 0),
        (0, 1, 0, 0, 1, 0),
        (0, 1, 0, 0, 1, 0),
        (0, 0, 1, 1, 0, 0),
        (0, 0, 0, 0, 0, 0),
        (0, 0, 0, 0, 0, 0),
        (0, 0, 1, 1, 0, 0),
        (0, 1, 0, 0, 1, 0),
        (0, 1, 0, 0, 1, 0),
        (0, 1, 0, 0, 1, 0),
        (0, 0, 0, 0, 0, 0),
        (0, 0, 0, 0, 0, 0),
    ]
    act = list(frames("abc"))
    assert exp == act


def test_table_frames():
    tf = table_frames(frames("abcd"), 12)
    full = list(tf)
    print(full[1])
    print(full[14])
    for i in range(12):
        left = full[i + 1]
        right = full[i + 14]
        assert left.outa2 == right.outa2
        assert left.outb2 == right.outb2
        assert left.outc2 == right.outc2
        assert left.outd2 == right.outd2
        assert left.oute2 == right.oute2
        assert left.outf2 == right.outf2


def test_table_chunks():
    tc = table_chunks(range(100), 12)
    first = next(tc)
    assert len(first) == 13
