import json
import sys
from pathlib import Path
from typing import Any

CORPUS = Path(__file__).resolve().parent / "corpus.json"

COUNTS = ("gated", "silent", "wrapped", "unmodelled", "pal")

TABLES = ("control", "memoryControl", "ioControl", "handheldPorts")


def broken(held: dict[str, Any]) -> list[str]:
    return [name for name, count in held["properties"].items() if count]


def inconsistent(held: dict[str, Any]) -> list[str]:
    images = held["images"]
    boards = held["boards"]
    problems = []
    held_by_boards = sum(counts[0] for counts in boards.values())
    if held_by_boards != images:
        problems.append(f"boards hold {held_by_boards} of {images} images")
    problems += [
        f"board {name} pages {paging} of its {total} images"
        for name, (total, paging) in boards.items()
        if paging > total
    ]
    problems += [
        f"{name} is {held[name]} of {images} images" for name in COUNTS if held[name] > images
    ]
    problems += [
        f"{table} {key} is {count} of {images} images"
        for table in TABLES
        for key, count in held[table].items()
        if count > images
    ]
    return problems


def main(where: Path = CORPUS) -> int:
    held = json.loads(where.read_text())
    print(
        f"{held['images']} images, {held['gated']} retail on a board with registers, {held['frames']} frames each"
    )
    for name, count in held["properties"].items():
        print(f"  {'ok  ' if not count else '   !'}  {name}: {count} broken")
    problems = inconsistent(held)
    for problem in problems:
        print(f"     !  {problem}")
    return 1 if broken(held) or problems else 0


if __name__ == "__main__":
    sys.exit(main())
