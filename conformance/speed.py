import statistics
import sys
import time
from collections.abc import Sequence

import smsmapper

MEASURED_HERE = 1_580_000

HEADROOM = 10

FLOOR_STEP = 10_000

FLOOR = MEASURED_HERE // HEADROOM // FLOOR_STEP * FLOOR_STEP

ACCESSES = 228 * 262 // 4

REPEATS = 5

IMAGE = 0x80000

PAGE_EVERY = 0x100

ADDRESS_SPACE = 0x10000

STRIDE = 0x0137

RAM_ON = 0x08


def busy_console() -> smsmapper.Console:
    image = bytes(offset & 0xFF for offset in range(IMAGE))
    cartridge = smsmapper.Cartridge(image, ram=0x8000)
    console = smsmapper.Console("sms", cartridge=cartridge)
    console.write(0xFFFC, RAM_ON)
    return console


class Timed:
    __slots__ = ("calls", "seconds", "what")

    def __init__(self, what: str, calls: int, seconds: Sequence[float]) -> None:
        self.what = what
        self.calls = calls
        self.seconds = list(seconds)

    def median(self) -> float:
        return statistics.median(self.seconds)

    def rate(self) -> float:
        taken = self.median()
        return self.calls / taken if taken > 0 else 0.0

    def beats(self, floor: int) -> bool:
        return self.rate() >= floor


def one_frame(console: smsmapper.Console, calls: int) -> None:
    address = 0
    for call in range(calls):
        if call % PAGE_EVERY == 0:
            console.write(0xFFFF, call // PAGE_EVERY)
        console.read(address)
        address = (address + STRIDE) % ADDRESS_SPACE


def measure(calls: int = ACCESSES, repeats: int = REPEATS) -> Timed:
    seconds = []
    for _ in range(repeats):
        console = busy_console()
        started = time.perf_counter()
        one_frame(console, calls)
        seconds.append(time.perf_counter() - started)
    return Timed("memory accesses through a paging console", calls, seconds)


def lines_for(found: Timed, floor: int = FLOOR) -> list[str]:
    runtime = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    lines = [
        f"  {found.what}: {found.rate():,.0f} per second"
        f" (median of {len(found.seconds)}) on Python {runtime}",
        f"  floor: {floor:,} per second",
    ]
    if not found.beats(floor):
        lines.append(f"  below the floor: {found.rate():,.0f} is under {floor:,}")
    return lines


def main(calls: int = ACCESSES, repeats: int = REPEATS, floor: int = FLOOR) -> int:
    found = measure(calls, repeats)
    for line in lines_for(found, floor):
        print(line)
    return 0 if found.beats(floor) else 1


if __name__ == "__main__":
    raise SystemExit(main())
