from __future__ import annotations

from typing import override

from smsmapper.boards import BANK, UNIT, Board

REGISTERS = (0x0000, 0x4000, 0x8000)

RAM_SELECT = 0x80

RAM_BASE = 0x07

RAM_UNIT = 5

POWER_ON = (0, 1, 0)

FRAME_1 = 1


class Codemasters(Board):
    __slots__ = ("ram_base", "ram_on", "registers")

    name = "codemasters"

    summary = (
        "Codemasters' paging: writes to 0000, 4000 and 8000 select the frames, 8K of RAM at A000"
    )

    @override
    def reset(self) -> None:
        self.registers = list(POWER_ON)
        self.ram_on = False
        self.ram_base = 0

    def ram_shown(self, address: int) -> bool:
        return self.ram_on and bool(self.ram) and address // UNIT == RAM_UNIT

    def ram_offset(self, address: int) -> int:
        return (self.ram_base * UNIT + (address & (UNIT - 1))) % len(self.ram)

    @override
    def read(self, address: int) -> int:
        if self.ram_shown(address):
            return self.ram[self.ram_offset(address)]
        return self.in_bank(self.banks[address // BANK], address)

    @override
    def write(self, address: int, value: int) -> None:
        if address in REGISTERS:
            self.select(REGISTERS.index(address), value)
        if self.ram_shown(address):
            self.ram[self.ram_offset(address)] = value

    def select(self, frame: int, value: int) -> None:
        if frame == FRAME_1 and value & RAM_SELECT:
            self.ram_on = True
            self.ram_base = value & RAM_BASE
            return
        if frame == FRAME_1:
            self.ram_on = False
        self.registers[frame] = value

    @override
    def decodes(self, address: int) -> bool:
        return address in REGISTERS

    @property
    @override
    def banks(self) -> tuple[int, ...]:
        return tuple(value % self.pages for value in self.registers)
