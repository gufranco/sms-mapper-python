from __future__ import annotations

from typing import ClassVar

from smsmapper.errors import EmptyImageError, RamSizeError

BANK = 0x4000

UNIT = 0x2000

FIXED = 0x0400

RAM_SIZES = (0, 0x2000, 0x4000, 0x8000)


class Board:
    __slots__ = ("image", "pages", "ram")

    name: ClassVar[str] = ""

    summary: ClassVar[str] = ""

    def __init__(self, image: bytes, ram: int = 0) -> None:
        if not image:
            raise EmptyImageError("the image is empty, so no board can show anything")
        if ram not in RAM_SIZES:
            raise RamSizeError(f"no board carries {ram} bytes of RAM; it takes one of {RAM_SIZES}")
        self.image = bytes(image)
        self.pages = -(-len(self.image) // BANK)
        self.ram = bytearray(ram)
        self.reset()

    def reset(self) -> None:
        return None

    def rom(self, offset: int) -> int:
        return self.image[offset % len(self.image)]

    def in_bank(self, bank: int, address: int) -> int:
        return self.rom(bank * BANK + (address & (BANK - 1)))

    def in_unit(self, unit: int, address: int) -> int:
        return self.rom(unit * UNIT + (address & (UNIT - 1)))

    def read(self, address: int) -> int:
        raise NotImplementedError

    def write(self, address: int, value: int) -> None:
        raise NotImplementedError

    def decodes(self, address: int) -> bool:
        raise NotImplementedError

    @property
    def banks(self) -> tuple[int, ...]:
        raise NotImplementedError
