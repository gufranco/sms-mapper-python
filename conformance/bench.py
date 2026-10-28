import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

HELD: dict[str, Any] = json.loads((ROOT / "conformance" / "hardware.json").read_text())

FACTS: dict[str, Any] = HELD["facts"]

UNSTATED: dict[str, Any] = HELD["notStated"]

UNIT = 0x2000


def numbered(size: int) -> bytes:
    return bytes((offset // UNIT) & 0xFF for offset in range(size))


def hexadecimal(text: str) -> int:
    return int(text, 16)
