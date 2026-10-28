from __future__ import annotations

from typing import override

from smsmapper.boards import BANK, FIXED, Board

CONTROL = 0xFFFC

SHIFT_MASK = 0x03

SHIFT_STEP = 8

RAM_BANK = 0x04

RAM_ON = 0x08

POWER_ON = (0, 0, 1, 2)

FRAME_2 = 2


class Sega(Board):
    __slots__ = ("registers",)

    name = "sega"

    summary = "Sega's paging: three 16K frames from FFFD to FFFF, cartridge RAM from FFFC"

    @override
    def reset(self) -> None:
        self.registers = list(POWER_ON)

    def physical(self, value: int) -> int:
        return (value + SHIFT_STEP * (self.registers[0] & SHIFT_MASK)) % self.pages

    def ram_shown(self) -> bool:
        return bool(self.ram) and bool(self.registers[0] & RAM_ON)

    def ram_offset(self, address: int) -> int:
        half = BANK if self.registers[0] & RAM_BANK else 0
        return (half + (address & (BANK - 1))) % len(self.ram)

    @override
    def read(self, address: int) -> int:
        frame = address // BANK
        if frame == FRAME_2 and self.ram_shown():
            return self.ram[self.ram_offset(address)]
        if address < FIXED:
            return self.rom(address)
        return self.in_bank(self.banks[frame], address)

    @override
    def write(self, address: int, value: int) -> None:
        if address >= CONTROL:
            self.registers[address - CONTROL] = value
        elif address // BANK == FRAME_2 and self.ram_shown():
            self.ram[self.ram_offset(address)] = value

    @override
    def decodes(self, address: int) -> bool:
        return address >= CONTROL

    @property
    @override
    def banks(self) -> tuple[int, ...]:
        return tuple(self.physical(value) for value in self.registers[1:])
