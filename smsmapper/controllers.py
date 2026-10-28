from __future__ import annotations

PAD_BUTTONS = ("up", "down", "left", "right", "1", "2")

RESET = "reset"

ALL_HIGH = 0xFF

PORT_A_BITS = {
    (1, "up"): 0,
    (1, "down"): 1,
    (1, "left"): 2,
    (1, "right"): 3,
    (1, "1"): 4,
    (1, "2"): 5,
    (2, "up"): 6,
    (2, "down"): 7,
}

PORT_B_BITS = {
    (2, "left"): 0,
    (2, "right"): 1,
    (2, "1"): 2,
    (2, "2"): 3,
}

RESET_BIT = 4

A_TR_INPUT = 0x01

A_TH_INPUT = 0x02

B_TR_INPUT = 0x04

B_TH_INPUT = 0x08

A_TR_LEVEL = 0x10

A_TH_LEVEL = 0x20

B_TR_LEVEL = 0x40

B_TH_LEVEL = 0x80

TH_LEVELS = A_TH_LEVEL | B_TH_LEVEL

DIRECTIONS = 0x0F

A_TR_BIT = 5

B_TR_BIT = 3

A_TH_BIT = 6

B_TH_BIT = 7

CONSOLE = 0


class Controllers:
    __slots__ = ("io_control", "japan", "latches", "pressed", "reset_button")

    def __init__(self, io_control: int, japan: bool, reset_button: bool) -> None:
        self.io_control = io_control
        self.japan = japan
        self.reset_button = reset_button
        self.pressed: set[tuple[int, str]] = set()
        self.latches = 0

    def press(self, button: str, player: int = 1) -> None:
        self.pressed.add(self.key(button, player))

    def release(self, button: str, player: int = 1) -> None:
        self.pressed.discard(self.key(button, player))

    @staticmethod
    def key(button: str, player: int) -> tuple[int, str]:
        return (CONSOLE, button) if button == RESET else (player, button)

    def write_control(self, value: int) -> None:
        rising = value & ~self.io_control & TH_LEVELS
        if rising:
            self.latches += 1
        self.io_control = value & DIRECTIONS if self.japan else value

    def lines(self, table: dict[tuple[int, str], int]) -> int:
        held = ALL_HIGH
        for key, bit in table.items():
            if key in self.pressed:
                held &= ~(1 << bit)
        return held

    def driven(self, held: int, direction: int, level: int, bit: int) -> int:
        if self.io_control & direction:
            return held
        shown = 1 << bit if self.io_control & level else 0
        return (held & ~(1 << bit)) | shown

    def read_a(self) -> int:
        return self.driven(self.lines(PORT_A_BITS), A_TR_INPUT, A_TR_LEVEL, A_TR_BIT)

    def read_b(self) -> int:
        held = self.lines(PORT_B_BITS)
        if self.reset_button and (CONSOLE, RESET) in self.pressed:
            held &= ~(1 << RESET_BIT)
        held = self.driven(held, B_TR_INPUT, B_TR_LEVEL, B_TR_BIT)
        held = self.driven(held, A_TH_INPUT, A_TH_LEVEL, A_TH_BIT)
        return self.driven(held, B_TH_INPUT, B_TH_LEVEL, B_TH_BIT)
