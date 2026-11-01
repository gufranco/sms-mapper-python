from __future__ import annotations

from smsmapper import models

READ = "read"

WRITE = "write"

MEMORY_CONTROL = "memory control"

IO_CONTROL = "i/o control"

V_COUNTER = "v counter"

H_COUNTER = "h counter"

SOUND = "sound"

VDP_DATA = "vdp data"

VDP_CONTROL = "vdp control"

PORT_A = "port a"

PORT_B = "port b"

NOTHING = "nothing"

HANDHELD = "game gear port "

HANDHELD_PORTS = 7

MASTER_SYSTEM_MODE = "game gear in master system mode"

CONTROL_SPAN = 0x40

FULLY_DECODED = (0x3E, 0x3F)

LOW_BYTE = 0xFF

DECODED = 0xC1

DECODE: dict[tuple[int, str], str] = {
    (0x00, WRITE): MEMORY_CONTROL,
    (0x01, WRITE): IO_CONTROL,
    (0x40, READ): V_COUNTER,
    (0x41, READ): H_COUNTER,
    (0x40, WRITE): SOUND,
    (0x41, WRITE): SOUND,
    (0x80, READ): VDP_DATA,
    (0x80, WRITE): VDP_DATA,
    (0x81, READ): VDP_CONTROL,
    (0x81, WRITE): VDP_CONTROL,
    (0xC0, READ): PORT_A,
    (0xC1, READ): PORT_B,
}


def decode(model: str, port: int, direction: str) -> str:
    number = port & LOW_BYTE
    if model == MASTER_SYSTEM_MODE or models.lookup(model).handheld:
        return _handheld(model, number, direction)
    return _decoded(number, direction)


def _handheld(model: str, number: int, direction: str) -> str:
    if number < HANDHELD_PORTS and model != MASTER_SYSTEM_MODE:
        return f"{HANDHELD}{number}"
    if number < CONTROL_SPAN and number not in FULLY_DECODED:
        return NOTHING
    return _decoded(number, direction)


def _decoded(number: int, direction: str) -> str:
    return DECODE.get((number & DECODED, direction), NOTHING)
