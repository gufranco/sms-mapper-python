from __future__ import annotations

from smsmapper.boards import Board

RAM_SIZE = 0x2000

RAM_START = 0xC000

OPEN_BUS = 0xFF

CARTRIDGE_START = 0xA8

BIOS_START = 0xE0

RAM_OFF = 0x10

CARTRIDGE_OFF = 0x40

CARD_OFF = 0x20

EXPANSION_OFF = 0x80

BIOS_OFF = 0x08


class Memory:
    __slots__ = ("bios", "card", "cartridge", "control", "expansion", "ram")

    def __init__(
        self,
        cartridge: Board | None = None,
        bios: Board | None = None,
        card: Board | None = None,
        expansion: Board | None = None,
    ) -> None:
        self.cartridge = cartridge
        self.bios = bios
        self.card = card
        self.expansion = expansion
        self.ram = bytearray(RAM_SIZE)
        self.control = CARTRIDGE_START if bios is None else BIOS_START

    def slots(self) -> tuple[tuple[int, Board | None], ...]:
        return (
            (CARTRIDGE_OFF, self.cartridge),
            (CARD_OFF, self.card),
            (EXPANSION_OFF, self.expansion),
            (BIOS_OFF, self.bios),
        )

    def selected(self) -> Board | None:
        for off, board in self.slots():
            if not self.control & off:
                return board
        return None

    def ram_on(self) -> bool:
        return not self.control & RAM_OFF

    def read(self, address: int) -> int:
        if address >= RAM_START:
            return self.ram[address % RAM_SIZE] if self.ram_on() else OPEN_BUS
        board = self.selected()
        return OPEN_BUS if board is None else board.read(address)

    def write(self, address: int, value: int) -> None:
        if address >= RAM_START and self.ram_on():
            self.ram[address % RAM_SIZE] = value
        board = self.selected()
        if board is not None:
            board.write(address, value)
