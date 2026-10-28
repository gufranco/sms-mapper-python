import collections
import functools
import hashlib
import json
import sys
import zipfile
from collections.abc import Iterator, Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import smsmapper
from conformance import harness

CONSOLE = ".sms"

HANDHELD = ".gg"

SUFFIXES = (CONSOLE, HANDHELD)

MODELS = {CONSOLE: "sms", HANDHELD: "gg"}

EUROPEAN_SET = "Europe - A-Z"

GATED_SETS = ("US - A-Z", EUROPEAN_SET, "Japan - A-Z")

NTSC_REGION = "usa"

NOT_GAMES = ("[BIOS]", "(Beta", "(Proto", "(Demo", "(Sample")

FRAMES = 600

JOBS = 10

LARGEST_UNPAGED = 0xC000

ADDRESS_SPACE = 0x10000

BOARDS = Path(__file__).resolve().parent / "boards.json"

CORPUS = Path(__file__).resolve().parent / "corpus.json"

CORPUS_INDENT = 2

DEFAULT_BOARD = "sega"

RAISES_NOTHING = "the model raises on no image"

PAGES = "every retail image over 48K writes a register of its board within the frame bound"

PROPERTIES = (RAISES_NOTHING, PAGES)

WRAPPED = "images that select a bank past the end of the image"

SHIFTED = "images that set FFFC's bank shift"

UNMODELLED = "images on a board this package does not model, run on Sega's paging"

OBSERVED = (WRAPPED, SHIFTED, UNMODELLED)

CONTROL_BITS = {"bank shift": 0x03, "ram bank": 0x04, "ram": 0x08, "bit 4": 0x10, "bit 7": 0x80}

USAGE = "usage: python3 -m conformance.census <path> [path ...] [--frames N] [--jobs N]"

Image = tuple[str, str, bytes]

Distinct = tuple[bool, bytes, str, str | None, str]


def boards(where: Path = BOARDS) -> dict[str, str]:
    held = json.loads(where.read_text())["boards"]
    return {str(one["sha1"]): str(one["board"]) for one in held}


def _members(where: Path) -> Iterator[Image]:
    with zipfile.ZipFile(where) as bundle:
        for entry in bundle.infolist():
            if not entry.is_dir() and Path(entry.filename).suffix.lower() in SUFFIXES:
                yield where.name, Path(entry.filename).name, bundle.read(entry)


def images_in(where: Path) -> Iterator[Image]:
    if where.is_dir():
        for path in sorted(where.rglob("*")):
            yield from images_in(path)
        return
    if where.suffix.lower() == ".zip":
        yield from _members(where)
    elif where.suffix.lower() in SUFFIXES:
        yield where.parent.name, where.name, where.read_bytes()


def board_of(rom: bytes, listed: Mapping[str, str]) -> str | None:
    return listed.get(hashlib.sha1(rom, usedforsecurity=False).hexdigest())


def gated(collection: str, name: str) -> bool:
    retail = any(one in collection for one in GATED_SETS)
    shipped = not any(tag in name for tag in NOT_GAMES)
    return retail and shipped


def sets_of(collection: str) -> set[str]:
    return {one for one in GATED_SETS if one in collection}


def region_of(sets: set[str]) -> str:
    return harness.PAL_REGION if sets == {EUROPEAN_SET} else NTSC_REGION


def modelled(board: str) -> bool:
    return board in smsmapper.BOARDS


@functools.cache
def has_registers(board: str) -> bool:
    built = smsmapper.Cartridge(bytes(LARGEST_UNPAGED), board=board)
    return any(built.decodes(address) for address in range(ADDRESS_SPACE))


def _seen(run: harness.Run, raised: str | None) -> dict[str, Any]:
    seen = run.seen
    return {
        "board": run.board.name,
        "writes": sum(seen.writes.values()),
        "wrapped": seen.wrapped > 0,
        "control": seen.control_bits,
        "memoryControl": sorted(seen.memory_control),
        "ioControl": sorted(seen.io_control),
        "handheldPorts": sorted(seen.handheld_ports),
        "raised": raised,
    }


def examine(
    job: tuple[bytes, int, str, str, str], build: type[harness.Run] = harness.Run
) -> dict[str, Any]:
    rom, frames, suffix, board, region = job
    chosen = board if modelled(board) else DEFAULT_BOARD
    run = build(rom, board=chosen, model=MODELS[suffix], region=region)
    try:
        run.run_frames(frames)
    except Exception as error:
        return _seen(run, f"{type(error).__name__}: {error} at frame {run.frames}")
    return _seen(run, None)


def _distinct(paths: list[Path], listed: Mapping[str, str]) -> tuple[int, list[Distinct]]:
    count = 0
    seen: dict[str, Distinct] = {}
    sets: dict[str, set[str]] = {}
    for where in paths:
        for collection, name, rom in images_in(where):
            count += 1
            digest = hashlib.sha256(rom).hexdigest()
            held = seen.get(digest)
            retail = bool(held and held[0]) or gated(collection, name)
            found = sets.setdefault(digest, set())
            found |= sets_of(collection)
            seen[digest] = (retail, rom, name, board_of(rom, listed), region_of(found))
    return count, [seen[digest] for digest in sorted(seen)]


def _suffix(name: str) -> str:
    return HANDHELD if name.lower().endswith(HANDHELD) else CONSOLE


def _results(
    images: list[Distinct], frames: int, jobs: int, build: type[harness.Run]
) -> list[dict[str, Any]]:
    work = [
        (rom, frames, _suffix(name), board or DEFAULT_BOARD, region)
        for _, rom, name, board, region in images
    ]
    if jobs <= 1:
        return [examine(one, build) for one in work]
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        return list(pool.map(examine, work))


def asked_to_page(image: Distinct) -> bool:
    retail, _, _, board, _ = image
    chosen = board or DEFAULT_BOARD
    return retail and modelled(chosen) and has_registers(chosen)


def _counts(values: Sequence[Sequence[int]]) -> dict[str, int]:
    counted: collections.Counter[str] = collections.Counter()
    for held in values:
        counted.update(f"{value:02X}" for value in held)
    return dict(sorted(counted.items()))


def tally(images: Sequence[Distinct], results: Sequence[dict[str, Any]]) -> dict[str, Any]:
    broken = dict.fromkeys(PROPERTIES, 0)
    per_board: dict[str, list[int]] = {}
    for image, found in zip(images, results, strict=True):
        counts = per_board.setdefault(found["board"], [0, 0])
        counts[0] += 1
        counts[1] += found["writes"] > 0
        broken[RAISES_NOTHING] += found["raised"] is not None
        broken[PAGES] += needs_paging(image) and not found["writes"]
    return {
        "properties": broken,
        "boards": dict(sorted(per_board.items())),
        "control": {
            name: sum(1 for found in results if found["control"] & bits)
            for name, bits in CONTROL_BITS.items()
        },
        "wrapped": sum(1 for found in results if found["wrapped"]),
        "silent": sum(1 for found in results if not found["writes"]),
        "unmodelled": sum(1 for _, _, _, board, _ in images if board and not modelled(board)),
        "pal": sum(1 for image in images if image[4] == harness.PAL_REGION),
        "memoryControl": _counts([found["memoryControl"] for found in results]),
        "ioControl": _counts([found["ioControl"] for found in results]),
        "handheldPorts": _counts([found["handheldPorts"] for found in results]),
    }


def needs_paging(image: Distinct) -> bool:
    return asked_to_page(image) and len(image[1]) > LARGEST_UNPAGED


def culprits(images: Sequence[Distinct], results: Sequence[dict[str, Any]]) -> dict[str, list[str]]:
    named: dict[str, list[str]] = {name: [] for name in (*PROPERTIES, *OBSERVED)}
    for image, found in zip(images, results, strict=True):
        name, board = image[2], image[3]
        if found["raised"] is not None:
            named[RAISES_NOTHING].append(f"{name}: {found['raised']}")
        if needs_paging(image) and not found["writes"]:
            named[PAGES].append(name)
        if found["wrapped"]:
            named[WRAPPED].append(name)
        if found["control"] & CONTROL_BITS["bank shift"]:
            named[SHIFTED].append(name)
        if board and not modelled(board):
            named[UNMODELLED].append(f"{name}: {board}")
    return named


def take(
    paths: list[Path],
    frames: int = FRAMES,
    jobs: int = JOBS,
    listed: Path | None = None,
    build: type[harness.Run] = harness.Run,
) -> Mapping[str, Any]:
    count, images = _distinct(paths, boards(BOARDS if listed is None else listed))
    results = _results(images, frames, jobs, build)
    return {
        "listings": count,
        "images": len(images),
        "gated": sum(1 for image in images if asked_to_page(image)),
        "frames": frames,
        **tally(images, results),
        "culprits": culprits(images, results),
    }


def _options(argv: list[str]) -> tuple[list[Path], int, int] | None:
    paths: list[Path] = []
    frames, jobs = FRAMES, JOBS
    rest = list(argv)
    while rest:
        item = rest.pop(0)
        if item in ("--frames", "--jobs"):
            if not rest:
                return None
            value = int(rest.pop(0))
            frames, jobs = (value, jobs) if item == "--frames" else (frames, value)
        else:
            paths.append(Path(item))
    return (paths, frames, jobs) if paths else None


def report(taken: Mapping[str, Any]) -> list[str]:
    named = taken["culprits"]
    lines = [
        f"{taken['listings']} listings, {taken['images']} distinct images, "
        f"{taken['gated']} retail on a board with registers, {taken['frames']} frames each"
    ]
    for name, count in taken["properties"].items():
        lines.append(f"  {'ok  ' if not count else '   !'}  {name}: {count} broken")
        lines.extend(f"         {one}" for one in named[name])
    for name in OBSERVED:
        lines.append(f"  observed  {name}: {len(named[name])} images")
        lines.extend(f"         {one}" for one in named[name])
    return lines


def main(argv: list[str], into: Path = CORPUS) -> int:
    chosen = _options(argv)
    if chosen is None:
        print(USAGE)
        return 2
    paths, frames, jobs = chosen
    for one in paths:
        if not one.exists():
            print(f"absent: {one}")
    taken = take([one for one in paths if one.exists()], frames, jobs)
    for line in report(taken):
        print(line)
    if taken["images"]:
        kept = {key: value for key, value in taken.items() if key != "culprits"}
        into.write_text(json.dumps(kept, indent=CORPUS_INDENT) + "\n")
    failed = any(taken["properties"].values()) or not taken["images"]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
