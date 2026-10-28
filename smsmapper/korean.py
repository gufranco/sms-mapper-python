from __future__ import annotations

from typing import override

from smsmapper.boards import BANK, FIXED, UNIT, Board

POWER_ON = (0, 1, 2)

KOREAN_REGISTER = 0xA000

FRAME_2 = 2

WINDOW = 0x4000

WINDOW_DECODE = 0x6000

WINDOW_SELECT = 0x2000

WINDOW_COMPLEMENT = 0x1F

UNITS = 6

JANGGUN_REGISTERS = (0x4000, 0x6000, 0x8000, 0xA000)

JANGGUN_FIRST_SLOT = 2

JANGGUN_CONTROL = 0xFFFD

REVERSED = 0x80

BANK_MASK = 0x3F

ZEMINA_REGISTERS = 4

ZEMINA_SLOTS = (4, 5, 2, 3)


def reversed_bits(value: int) -> int:
    return int(f"{value:08b}"[::-1], 2)


class Korean(Board):
    __slots__ = ("registers",)

    name = "korean"

    summary = "A Korean board that selects the bank for 8000 to BFFF with a write to A000"

    @override
    def reset(self) -> None:
        self.registers = [value % self.pages for value in POWER_ON]

    @override
    def read(self, address: int) -> int:
        if address < FIXED:
            return self.rom(address)
        return self.in_bank(self.registers[address // BANK], address)

    @override
    def write(self, address: int, value: int) -> None:
        if address == KOREAN_REGISTER:
            self.registers[FRAME_2] = value % self.pages

    @override
    def decodes(self, address: int) -> bool:
        return address == KOREAN_REGISTER

    @property
    @override
    def banks(self) -> tuple[int, ...]:
        return tuple(self.registers)


class KoreanNoBank(Korean):
    __slots__ = ()

    name = "korean_nb"

    summary = "A Korean board with no paging at all: banks 0, 1 and 2 stay where they power on"

    @override
    def write(self, address: int, value: int) -> None:
        return None

    @override
    def decodes(self, address: int) -> bool:
        return False


class Korean188(Board):
    __slots__ = ("register",)

    name = "korean_188in1"

    summary = "The Korean 188-in-1 board: the first 16K fixed, a 32K window from an 8K bank at 4000"

    @override
    def reset(self) -> None:
        self.register = 0

    def window(self) -> int:
        return (self.register ^ WINDOW_COMPLEMENT) % (self.pages * 2)

    @override
    def read(self, address: int) -> int:
        if address < WINDOW:
            return self.rom(address)
        return self.rom(self.window() * UNIT + address - WINDOW)

    @override
    def write(self, address: int, value: int) -> None:
        if address & WINDOW_DECODE == WINDOW_SELECT:
            self.register = value

    @override
    def decodes(self, address: int) -> bool:
        return address & WINDOW_DECODE == WINDOW_SELECT

    @property
    @override
    def banks(self) -> tuple[int, ...]:
        return (0, self.window())


class Janggun(Board):
    __slots__ = ("slots",)

    name = "janggun"

    summary = (
        "Daiou's board for Janggun-ui Adeul: 8K banks, and banks with bit 7 set read bit-reversed"
    )

    @override
    def reset(self) -> None:
        self.slots = list(range(UNITS))

    @override
    def read(self, address: int) -> int:
        selected = self.slots[address // UNIT]
        byte = self.in_unit(selected & BANK_MASK, address)
        return reversed_bits(byte) if selected & REVERSED else byte

    @override
    def write(self, address: int, value: int) -> None:
        if address in JANGGUN_REGISTERS:
            self.slots[JANGGUN_FIRST_SLOT + JANGGUN_REGISTERS.index(address)] = value
        elif address >= JANGGUN_CONTROL:
            first = (address - JANGGUN_CONTROL) * 2
            self.slots[first : first + 2] = [(value % self.pages) * 2 + half for half in (0, 1)]

    @override
    def decodes(self, address: int) -> bool:
        return address in JANGGUN_REGISTERS or address >= JANGGUN_CONTROL

    @property
    @override
    def banks(self) -> tuple[int, ...]:
        return tuple(self.slots)


class Zemina(Board):
    __slots__ = ("slots",)

    name = "zemina"

    summary = "Zemina's board: six 8K banks, selected by writes to 0000 to 0003"

    def units(self) -> int:
        return self.pages * 2

    @override
    def reset(self) -> None:
        self.slots = [slot % self.units() for slot in range(UNITS)]

    @override
    def read(self, address: int) -> int:
        return self.in_unit(self.slots[address // UNIT], address)

    @override
    def write(self, address: int, value: int) -> None:
        if address < ZEMINA_REGISTERS:
            self.slots[ZEMINA_SLOTS[address]] = value % self.units()

    @override
    def decodes(self, address: int) -> bool:
        return address < ZEMINA_REGISTERS

    @property
    @override
    def banks(self) -> tuple[int, ...]:
        return tuple(self.slots)


class Nemesis(Zemina):
    __slots__ = ()

    name = "nemesis"

    summary = "Zemina's board as Nemesis uses it, starting with the last 8K bank at 0000"

    @override
    def reset(self) -> None:
        super().reset()
        self.slots[0] = self.units() - 1
