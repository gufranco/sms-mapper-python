import collections
import sys
from pathlib import Path
from typing import Any

import smsmapper
from smsmapper import ports

ROOT = Path(__file__).resolve().parent.parent

PROCESSOR = ROOT / "zilog-z80-python"

SEED = 0x5235

STATES_PER_LINE = 228

LINES = 262

FRAME_LINE = 192

LAST_COUNTED_LINE = 0xDA

COUNTER_JUMP = 6

PAL_LINES = 313

PAL_LAST_COUNTED_LINE = 0xF2

PAL_COUNTER_JUMP = 0x39

PAL_REGION = "europe"

STATUS = "status"

CONTROL = "control"

DATA = "data"

V_COUNTER = "v counter"

H_COUNTER = "h counter"

FRAME_FLAG = 0x80

LINE_FLAG = 0x40

FRAME_ENABLE = 0x20

LINE_ENABLE = 0x10

REGISTER_CODE = 2

LINE_RELOAD = 10

REGISTER_COUNT = 16

VRAM_SIZE = 0x4000

READ_CODE = 0

COLOUR_CODE = 3

HIGH_ADDRESS = 0x3F

COLUMNS = 32

ROWS = 24

TABLE_BITS = 0x0E

TABLE_SHIFT = 10

INDEX_HIGH = 0x01

PRINTABLE = range(0x20, 0x7F)

HANDOFF_STACK = 0xDFF0

HANDOFF_MEMORY_CONTROL = 0xA8

RAM_START = 0xC000

CARTRIDGE_RAM = {"sega": 0x8000, "codemasters": 0x2000}

SEGA_CONTROL = 0xFFFC

SEGA_FRAMES = 0xFFFD

SEGA_LIKE = ("sega", "eeprom")

VIDEO_READS = {
    ports.VDP_CONTROL: STATUS,
    ports.VDP_DATA: DATA,
    ports.V_COUNTER: V_COUNTER,
    ports.H_COUNTER: H_COUNTER,
}

VIDEO_WRITES = {ports.VDP_CONTROL: CONTROL, ports.VDP_DATA: DATA}


def why_not(where: Path = PROCESSOR) -> str | None:
    if (where / "z80" / "__init__.py").is_file():
        return None
    return (
        f"the census drives zilog-z80-python from {where}, which is not checked out."
        " Run git submodule update --init --recursive"
    )


def _processor() -> Any:
    if str(PROCESSOR) not in sys.path:
        sys.path.append(str(PROCESSOR))
    import z80

    return z80


class Video:
    __slots__ = (
        "address",
        "buffer",
        "code",
        "counter",
        "first",
        "flags",
        "jump",
        "last_counted",
        "latched",
        "lines",
        "registers",
        "states",
        "vram",
    )

    def __init__(self, pal: bool = False) -> None:
        self.lines = PAL_LINES if pal else LINES
        self.last_counted = PAL_LAST_COUNTED_LINE if pal else LAST_COUNTED_LINE
        self.jump = PAL_COUNTER_JUMP if pal else COUNTER_JUMP
        self.registers = [0] * REGISTER_COUNT
        self.vram = bytearray(VRAM_SIZE)
        self.states = 0
        self.flags = 0
        self.counter = 0
        self.latched = False
        self.first = 0
        self.address = 0
        self.code = 0
        self.buffer = 0

    @property
    def line(self) -> int:
        return (self.states // STATES_PER_LINE) % self.lines

    @property
    def irq(self) -> bool:
        frame = self.flags & FRAME_FLAG and self.registers[1] & FRAME_ENABLE
        line = self.flags & LINE_FLAG and self.registers[0] & LINE_ENABLE
        return bool(frame or line)

    def advance(self, states: int) -> bool:
        before = self.states // STATES_PER_LINE
        self.states += states
        for line in range(before + 1, self.states // STATES_PER_LINE + 1):
            self.line_begins(line % self.lines)
        return before // self.lines != (self.states // STATES_PER_LINE) // self.lines

    def line_begins(self, line: int) -> None:
        if line == FRAME_LINE:
            self.flags |= FRAME_FLAG
        if line > FRAME_LINE:
            self.counter = self.registers[LINE_RELOAD]
            return
        self.counter -= 1
        if self.counter < 0:
            self.counter = self.registers[LINE_RELOAD]
            self.flags |= LINE_FLAG

    def read(self, target: str) -> int:
        if target == STATUS:
            held, self.flags, self.latched = self.flags, 0, False
            return held
        if target == V_COUNTER:
            line = self.line
            return line if line <= self.last_counted else line - self.jump
        if target == H_COUNTER:
            return 0
        self.latched = False
        held = self.buffer
        self.fetch()
        return held

    def fetch(self) -> None:
        self.buffer = self.vram[self.address]
        self.address = (self.address + 1) % VRAM_SIZE

    def write(self, target: str, value: int) -> None:
        if target != CONTROL:
            self.latched = False
            if self.code != COLOUR_CODE:
                self.vram[self.address] = value
            self.address = (self.address + 1) % VRAM_SIZE
            return
        if not self.latched:
            self.first, self.latched = value, True
            return
        self.latched = False
        self.code = value >> 6
        self.address = ((value & HIGH_ADDRESS) << 8) | self.first
        if self.code == REGISTER_CODE:
            self.registers[value & (REGISTER_COUNT - 1)] = self.first
        elif self.code == READ_CODE:
            self.fetch()


def _character(code: int) -> str:
    return chr(code) if code in PRINTABLE else " "


def screen(video: Video, offset: int) -> list[str]:
    base = (video.registers[2] & TABLE_BITS) << TABLE_SHIFT
    rows = []
    for row in range(ROWS):
        cells = []
        for column in range(COLUMNS):
            at = base + (row * COLUMNS + column) * 2
            tile = video.vram[at] | (video.vram[at + 1] & INDEX_HIGH) << 8
            cells.append(_character(tile - offset))
        rows.append("".join(cells))
    return rows


class Seen:
    __slots__ = (
        "banks",
        "control_bits",
        "handheld_ports",
        "io_control",
        "memory_control",
        "sound",
        "wrapped",
        "writes",
    )

    def __init__(self) -> None:
        self.writes: collections.Counter[int] = collections.Counter()
        self.banks: set[int] = set()
        self.wrapped = 0
        self.control_bits = 0
        self.memory_control: collections.Counter[int] = collections.Counter()
        self.io_control: collections.Counter[int] = collections.Counter()
        self.sound = 0
        self.handheld_ports: set[int] = set()


class Ports:
    __slots__ = ("run",)

    def __init__(self, run: "Run") -> None:
        self.run = run

    def read(self, address: int) -> int:
        return self.run.read_port(address)

    def write(self, address: int, value: int) -> None:
        self.run.write_port(address, value)


class Run:
    __slots__ = ("board", "console", "cpu", "frames", "seen", "video")

    def __init__(
        self, image: bytes, board: str = "sega", model: str = "sms", region: str = "usa"
    ) -> None:
        z80 = _processor()
        cartridge = smsmapper.Cartridge(image, board=board, ram=CARTRIDGE_RAM.get(board, 0))
        self.board = cartridge
        self.console = smsmapper.Console(model, cartridge=cartridge, region=region)
        self.video = Video(pal=region == PAL_REGION and not self.console.model.handheld)
        self.seen = Seen()
        self.frames = 0
        self.cpu = z80.Cpu("z80", self, ports=Ports(self), seed=SEED)
        self.cpu.reset()
        if not self.console.model.handheld:
            self.cpu.registers.sp = HANDOFF_STACK
            self.console.write(RAM_START, HANDOFF_MEMORY_CONTROL)

    def read8(self, address: int) -> int:
        return self.console.read(address)

    def write8(self, address: int, value: int) -> None:
        self.console.write(address, value)
        if self.board.decodes(address):
            self.noticed(address, value)

    def noticed(self, address: int, value: int) -> None:
        seen = self.seen
        seen.writes[address] += 1
        seen.banks.update(self.board.banks)
        if self.board.name not in SEGA_LIKE:
            return
        if address == SEGA_CONTROL:
            seen.control_bits |= value
        elif address >= SEGA_FRAMES and value >= self.board.pages:
            seen.wrapped += 1

    def read_port(self, address: int) -> int:
        target = ports.decode(self.console.decoding(), address, ports.READ)
        if target in VIDEO_READS:
            return self.video.read(VIDEO_READS[target])
        self.handheld(target)
        return self.console.read_port(address)

    def write_port(self, address: int, value: int) -> None:
        target = ports.decode(self.console.decoding(), address, ports.WRITE)
        if target in VIDEO_WRITES:
            self.video.write(VIDEO_WRITES[target], value)
            return
        if target == ports.SOUND:
            self.seen.sound += 1
            return
        self.handheld(target)
        if target == ports.MEMORY_CONTROL:
            self.seen.memory_control[value] += 1
        elif target == ports.IO_CONTROL:
            self.seen.io_control[value] += 1
        self.console.write_port(address, value)

    def handheld(self, target: str) -> None:
        if target.startswith(ports.HANDHELD):
            self.seen.handheld_ports.add(int(target.removeprefix(ports.HANDHELD)))

    def run_frames(self, count: int) -> None:
        target = self.frames + count
        while self.frames < target:
            states = self.cpu.step()
            self.frames += self.video.advance(states)
            self.cpu.irq_line = self.video.irq
            self.cpu.nmi_line = self.console.nmi
