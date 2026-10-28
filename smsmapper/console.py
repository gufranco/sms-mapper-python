from __future__ import annotations

from smsmapper import models, ports
from smsmapper.boards import Board
from smsmapper.controllers import Controllers
from smsmapper.errors import NotOnBoardError, SlotError, UnknownRegionError
from smsmapper.memory import Memory

REGION_BITS = {"japan": 0x00, "usa": 0x40, "europe": 0x60}

JAPAN = "japan"

PORT_0_START = 0x80

HANDHELD_POWER_ON = (0x00, 0xFF, 0x00, 0xFF, 0x00, 0xFF)

DIRECTION_MASK = 0x7F

SERIAL_KEEPS = 0xF8

OPEN_BUS = 0xFF

JOYSTICKS_OFF = 0x04

PAUSE = "pause"

START = "start"

CONSOLE_BUTTONS = (PAUSE, START)

HANDHELD_MODE_STAND_IN = "sms2"

READ_ONLY = (0, 4)

WRITE_ONLY = 6

SERIAL = 5

PARALLEL = 1


class Console:
    __slots__ = ("controllers", "handheld_mode", "held", "memory", "model", "region", "registers")

    def __init__(
        self,
        model: str | None = None,
        cartridge: Board | None = None,
        bios: Board | None = None,
        card: Board | None = None,
        region: str | None = None,
        handheld_mode: bool = True,
    ) -> None:
        self.model = models.lookup(model)
        region = region or self.model.region
        if region not in REGION_BITS:
            raise UnknownRegionError(
                f"no region is called {region!r}; they are {sorted(REGION_BITS)}"
            )
        if card is not None and not self.model.card_slot:
            raise SlotError(f"the {self.model.name} has no card slot")
        self.region = region
        self.handheld_mode = handheld_mode
        self.memory = Memory(cartridge=cartridge, bios=bios, card=card)
        self.controllers = Controllers(
            self.model.io_control, japan=region == JAPAN, reset_button=self.model.reset_button
        )
        self.registers = [PORT_0_START | REGION_BITS[region], *HANDHELD_POWER_ON]
        self.held: set[str] = set()

    def read(self, address: int) -> int:
        return self.memory.read(address)

    def write(self, address: int, value: int) -> None:
        self.memory.write(address, value)

    def decoding(self) -> str:
        if self.model.handheld and not self.handheld_mode:
            return HANDHELD_MODE_STAND_IN
        return self.model.name

    def read_port(self, port: int) -> int:
        target = ports.decode(self.decoding(), port, ports.READ)
        if target.startswith(ports.HANDHELD):
            return self.handheld_read(int(target.removeprefix(ports.HANDHELD)))
        if target in (ports.PORT_A, ports.PORT_B):
            return self.controller_port(target)
        if target == ports.NOTHING:
            return OPEN_BUS
        raise NotOnBoardError(
            f"port {port & 0xFF:02X}h reaches the {target}, which is not on the board"
        )

    def write_port(self, port: int, value: int) -> None:
        target = ports.decode(self.decoding(), port, ports.WRITE)
        if target.startswith(ports.HANDHELD):
            self.handheld_write(int(target.removeprefix(ports.HANDHELD)), value)
        elif target == ports.MEMORY_CONTROL:
            self.memory.control = value
        elif target == ports.IO_CONTROL:
            self.controllers.write_control(value)
        elif target != ports.NOTHING:
            raise NotOnBoardError(
                f"port {port & 0xFF:02X}h reaches the {target}, which is not on the board"
            )

    def controller_port(self, target: str) -> int:
        if self.memory.control & JOYSTICKS_OFF:
            return OPEN_BUS
        if target == ports.PORT_A:
            return self.controllers.read_a()
        return self.controllers.read_b()

    def handheld_read(self, number: int) -> int:
        if number == 0:
            return self.registers[0] & ~(PORT_0_START if START in self.held else 0)
        if number == PARALLEL:
            direction = self.registers[2] & DIRECTION_MASK
            return (self.registers[PARALLEL] & ~direction) | direction
        if number == WRITE_ONLY:
            return OPEN_BUS
        return self.registers[number]

    def handheld_write(self, number: int, value: int) -> None:
        if number in READ_ONLY:
            return
        self.registers[number] = value & SERIAL_KEEPS if number == SERIAL else value

    def press(self, button: str, player: int = 1) -> None:
        if button in CONSOLE_BUTTONS:
            self.held.add(button)
        else:
            self.controllers.press(button, player)

    def release(self, button: str, player: int = 1) -> None:
        if button in CONSOLE_BUTTONS:
            self.held.discard(button)
        else:
            self.controllers.release(button, player)

    @property
    def nmi(self) -> bool:
        if self.model.handheld:
            return not self.handheld_mode and START in self.held
        return PAUSE in self.held

    @property
    def latches(self) -> int:
        return self.controllers.latches
