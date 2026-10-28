from __future__ import annotations

from typing import override

from smsmapper.boards import BANK, FIXED, Board

FOUR_PAK_REGISTERS = (0x3FFE, 0x7FFF, 0xBFFF)

GAME_BASE = 0x30

FRAMES = 3

HICOM_REGISTER = 0xFFFF

HICOM_WINDOW = 0x8000

FIRST_BANK = 0x3FFF

SEOJIN_GAME = 0xFFF0

SEOJIN_FRAMES = 0xFFFD

SEOJIN_INVERT = 0x80

GAME_MASK = 0x0F

POWER_ON = (0, 1, 2)


class FourPak(Board):
    __slots__ = ("registers",)

    name = "4pak"

    summary = "HES's 4 PAK All Action: 3FFE, 7FFF and BFFF select the frames, 3FFE also the game"

    @override
    def reset(self) -> None:
        self.registers = [0] * FRAMES

    @override
    def read(self, address: int) -> int:
        return self.in_bank(self.banks[address // BANK], address)

    @override
    def write(self, address: int, value: int) -> None:
        if address in FOUR_PAK_REGISTERS:
            self.registers[FOUR_PAK_REGISTERS.index(address)] = value

    @override
    def decodes(self, address: int) -> bool:
        return address in FOUR_PAK_REGISTERS

    @property
    @override
    def banks(self) -> tuple[int, ...]:
        game, middle, offset = self.registers
        return (game % self.pages, middle % self.pages, ((game & GAME_BASE) + offset) % self.pages)


class HiCom(Board):
    __slots__ = ("register",)

    name = "hicom"

    summary = (
        "Hi-Com's multicarts: FFFF selects a 32K bank at 0000, 8000 to BFFF shows the first 16K"
    )

    @override
    def reset(self) -> None:
        self.register = 0

    @override
    def read(self, address: int) -> int:
        if address >= HICOM_WINDOW:
            return self.rom(address & FIRST_BANK)
        return self.rom(self.banks[0] * HICOM_WINDOW + address)

    @override
    def write(self, address: int, value: int) -> None:
        if address == HICOM_REGISTER:
            self.register = value

    @override
    def decodes(self, address: int) -> bool:
        return address == HICOM_REGISTER

    @property
    @override
    def banks(self) -> tuple[int, ...]:
        return (self.register % (self.pages * 2),)


class Seojin(Board):
    __slots__ = ("game", "registers")

    name = "seojin"

    summary = "Seo Jin's multicarts: FFF0 selects a 32K game, FFFD to FFFF the frames within it"

    @override
    def reset(self) -> None:
        self.game = 0
        self.registers = list(POWER_ON)

    @override
    def read(self, address: int) -> int:
        if address < FIXED:
            return self.rom((self.game & GAME_MASK) * 2 * BANK + address) ^ SEOJIN_INVERT
        return self.in_bank(self.banks[address // BANK], address) ^ SEOJIN_INVERT

    @override
    def write(self, address: int, value: int) -> None:
        if address == SEOJIN_GAME:
            self.game = value
        elif address >= SEOJIN_FRAMES:
            self.registers[address - SEOJIN_FRAMES] = value

    @override
    def decodes(self, address: int) -> bool:
        return address == SEOJIN_GAME or address >= SEOJIN_FRAMES

    @property
    @override
    def banks(self) -> tuple[int, ...]:
        base = (self.game & GAME_MASK) << 1
        return tuple((base | value) % self.pages for value in self.registers)
