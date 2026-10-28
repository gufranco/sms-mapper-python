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
    if models.lookup(model).handheld and number < HANDHELD_PORTS:
        return f"{HANDHELD}{number}"
    return DECODE.get((number & DECODED, direction), NOTHING)
