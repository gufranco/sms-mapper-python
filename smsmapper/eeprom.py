from __future__ import annotations

from typing import override

from smsmapper.boards import BANK, FIXED, Board

WORDS = 64

DATA_BITS = 16

ADDRESS_BITS = 6

COMMAND_BITS = 2 + ADDRESS_BITS

ERASED = 0xFFFF

SHIFT_WIDTH = 32

SHIFT_MASK = (1 << SHIFT_WIDTH) - 1

TOP = SHIFT_WIDTH - 1

LINES = 0x8000

CONTROL = 0xFFFC

DATA_IN = 0x01

CLOCK = 0x02

SELECT = 0x04

ENABLE = 0x08

RESET = 0x80

LINE_MASK = 0xFC

ALWAYS_SET = 0x02

POWER_ON = (0, 1, 2)


IDLE = "idle"

START = "start"

COMMAND = "command"

READING = "reading"

DATA = "data"

BUSY = "busy"


class Eeprom93C46:
    __slots__ = (
        "address",
        "clock",
        "count",
        "data_in",
        "gathered",
        "locked",
        "operation",
        "select",
        "shift",
        "state",
        "words",
    )

    def __init__(self) -> None:
        self.words = [ERASED] * WORDS
        self.reset()

    def reset(self) -> None:
        self.state = IDLE
        self.locked = True
        self.select = self.clock = self.data_in = False
        self.gathered = self.count = self.shift = self.address = 0
        self.operation = ""

    def output(self) -> int:
        if self.state == READING:
            return self.shift >> TOP
        return 1

    def lines(self, select: bool, clock: bool, data_in: bool) -> None:
        rising_select = select and not self.select
        rising_clock = clock and not self.clock
        falling_select = self.select and not select
        self.data_in, self.select, self.clock = data_in, select, clock
        if falling_select:
            self.state = IDLE
        elif rising_select and self.state == IDLE:
            self.state = START
        elif rising_clock and not rising_select:
            self.clocked()

    def clocked(self) -> None:
        if self.state == START and self.data_in:
            self.gathered = self.count = 0
            self.state = COMMAND
        elif self.state == COMMAND:
            self.gathered = (self.gathered << 1) | self.data_in
            self.count += 1
            if self.count == COMMAND_BITS:
                self.execute()
        elif self.state == READING:
            self.shift_out()
        elif self.state == DATA:
            self.shift_in()

    def shift_out(self) -> None:
        if self.count == 0:
            self.shift = self.words[self.address] << (SHIFT_WIDTH - DATA_BITS)
        else:
            self.shift = ((self.shift << 1) | 1) & SHIFT_MASK
        self.count += 1

    def shift_in(self) -> None:
        self.shift = (self.shift << 1) | self.data_in
        self.count += 1
        if self.count == DATA_BITS:
            self.finish_write(self.shift & ERASED)

    def execute(self) -> None:
        opcode = self.gathered >> ADDRESS_BITS
        self.address = self.gathered & (WORDS - 1)
        self.count = self.shift = 0
        if opcode == 0:
            self.execute_extended(self.address >> (ADDRESS_BITS - 2))
        elif opcode == 1:
            self.operation, self.state = "write", DATA
        elif opcode == 2:
            self.state = READING
        else:
            self.erase([self.address])

    def execute_extended(self, kind: int) -> None:
        if kind == 0:
            self.locked, self.state = True, IDLE
        elif kind == 1:
            self.operation, self.state = "all", DATA
        elif kind == 2:
            self.erase(range(WORDS))
        else:
            self.locked, self.state = False, IDLE

    def erase(self, addresses: range | list[int]) -> None:
        if self.locked:
            self.state = IDLE
            return
        for address in addresses:
            self.words[address] = ERASED
        self.state = BUSY

    def finish_write(self, value: int) -> None:
        if self.locked:
            self.state = IDLE
            return
        if self.operation == "write":
            self.words[self.address] = value
        else:
            self.words[:] = [word & value for word in self.words]
        self.state = BUSY


class SegaEeprom(Board):
    __slots__ = ("eeprom", "enabled", "lines_held", "registers")

    name = "eeprom"

    summary = "Sega's paging with a 93C46 EEPROM behind 8000, as the Game Gear baseball games carry"

    def __init__(self, image: bytes, ram: int = 0) -> None:
        self.eeprom = Eeprom93C46()
        super().__init__(image, ram)

    @override
    def reset(self) -> None:
        self.registers = [value % self.pages for value in POWER_ON]
        self.enabled = False
        self.lines_held = 0
        self.eeprom.reset()

    @override
    def read(self, address: int) -> int:
        if address == LINES and self.enabled:
            return (self.lines_held & LINE_MASK) | ALWAYS_SET | self.eeprom.output()
        if address < FIXED:
            return self.rom(address)
        return self.in_bank(self.registers[address // BANK], address)

    @override
    def write(self, address: int, value: int) -> None:
        if address == LINES and self.enabled:
            self.lines_held = value
            self.eeprom.lines(bool(value & SELECT), bool(value & CLOCK), bool(value & DATA_IN))
        elif address == CONTROL:
            self.control(value)
        elif address > CONTROL:
            self.registers[address - CONTROL - 1] = value % self.pages

    def control(self, value: int) -> None:
        if value & RESET:
            self.eeprom.reset()
        self.enabled = bool(value & ENABLE)

    @override
    def decodes(self, address: int) -> bool:
        return address == LINES or address >= CONTROL

    @property
    @override
    def banks(self) -> tuple[int, ...]:
        return tuple(self.registers)
