from __future__ import annotations

import hashlib
import importlib.machinery
import json
import platform
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, override

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable, Sequence


def installed_version(where: Path | None = None) -> str:
    found = re.search(
        r"""VERSION\s*[:=][^"']*["']([^"']+)["']""",
        (where or Path(__file__).resolve().parent / "version.py").read_text(),
    )
    return found.group(1) if found else "unknown"


VERSION = installed_version()

ROOT = Path(__file__).resolve().parent.parent


def reachable(root: Path = ROOT, path: list[str] | None = None) -> bool:
    where = sys.path if path is None else path
    if str(root) in where:
        return False
    where.insert(0, str(root))
    return True


reachable()

CORPUS = ROOT / "conformance" / "corpus.json"

DOCUMENTS = ROOT / "conformance" / "documents.json"

HELD_DOCUMENTS = ROOT / "docs"

HARNESS_MODULE = "z80"

PROCESSOR = ROOT / "zilog-z80-python"


def look_in(where: Path) -> Callable[[str], Any]:
    return lambda name: importlib.machinery.PathFinder.find_spec(name, [str(where)])


IN_SUBMODULE = look_in(PROCESSOR)


OLDEST_PYTHON = (3, 12)

UNIT = 0x2000

CHECK_IMAGE = 0x40000

CHECK_BANK = 3

CHECK_BYTE = 0x5A

RAM_ADDRESS = 0xC123

MIRROR_ADDRESS = 0xE123

CHECKS = (
    "python",
    "package",
    "boards",
    "paging",
    "mirroring",
    "ports",
    "manual",
    "corpus",
    "harness",
    "library",
)


class Finding:
    __slots__ = ("advice", "detail", "name", "ok")

    def __init__(self, name: str, ok: bool, detail: str, advice: str | None = None) -> None:
        self.name = name
        self.ok = ok
        self.detail = detail
        self.advice = advice

    @property
    def line(self) -> str:
        return f"  {'ok  ' if self.ok else '   !'}  {self.name}: {self.detail}"

    @property
    def report(self) -> str:
        if self.ok or not self.advice:
            return self.line
        return f"{self.line}\n         {self.advice}"

    @override
    def __repr__(self) -> str:
        return f"<Finding {self.name} {'ok' if self.ok else 'not ok'}>"


def _threw(name: str, error: BaseException, advice: str | None = None) -> Finding:
    return Finding(name, False, f"{type(error).__name__}: {error}", advice)


def check_python() -> Finding:
    running = sys.version_info[:2]
    return Finding(
        "python",
        running >= OLDEST_PYTHON,
        f"{platform.python_version()}",
        f"this package needs {OLDEST_PYTHON[0]}.{OLDEST_PYTHON[1]} or newer",
    )


def _load() -> Any:
    import smsmapper

    return smsmapper


def check_package(load: Callable[[], Any] = _load) -> Finding:
    try:
        loaded = load()
    except Exception as error:
        return _threw("package", error, "the package did not import from this directory")
    return Finding("package", True, f"smsmapper {loaded.__version__} imported from {ROOT}")


def _numbered(size: int) -> bytes:
    return bytes((offset // UNIT) & 0xFF for offset in range(size))


def check_boards(load: Callable[[], Any] = _load) -> Finding:
    try:
        package = load()
        names = sorted(package.BOARDS)
        built = [package.Cartridge(_numbered(CHECK_IMAGE), board=name).name for name in names]
    except Exception as error:
        return _threw("boards", error)
    return Finding(
        "boards",
        built == names and bool(names),
        f"built {len(built)} boards: {', '.join(built)}",
        "a board in the catalogue did not build as itself",
    )


def check_paging(load: Callable[[], Any] = _load) -> Finding:
    try:
        package = load()
        console = package.Console("sms", cartridge=package.Cartridge(_numbered(CHECK_IMAGE)))
        console.write(0xFFFF, CHECK_BANK)
        shown = console.read(0x8000) // 2
    except Exception as error:
        return _threw("paging", error)
    return Finding(
        "paging",
        shown == CHECK_BANK,
        f"frame 2 showed bank {shown} after FFFF was written {CHECK_BANK}",
        "a write to Sega's frame 2 register did not move frame 2",
    )


def check_mirroring(load: Callable[[], Any] = _load) -> Finding:
    try:
        package = load()
        console = package.Console("sms", cartridge=package.Cartridge(_numbered(CHECK_IMAGE)))
        console.write(RAM_ADDRESS, CHECK_BYTE)
        shown = console.read(MIRROR_ADDRESS)
    except Exception as error:
        return _threw("mirroring", error)
    return Finding(
        "mirroring",
        shown == CHECK_BYTE,
        f"a byte written at C123h read back as {shown:02X}h at E123h",
        "the system RAM did not answer at both places the manual names",
    )


def check_ports(load: Callable[[], Any] = _load) -> Finding:
    try:
        decode = load().ports.decode
        found = (decode("sms", 0x3E, "write"), decode("sms", 0xBF, "write"))
    except Exception as error:
        return _threw("ports", error)
    return Finding(
        "ports",
        found == ("memory control", "vdp control"),
        f"port 3Eh reached the {found[0]} and port BFh the {found[1]}",
        "the port decode no longer follows A7, A6 and A0",
    )


def check_manual(manifest: Path = DOCUMENTS, held: Path = HELD_DOCUMENTS) -> Finding:
    try:
        entry = json.loads(manifest.read_text())["documents"][0]
        where = held / str(entry["file"])
        if not where.is_file():
            return Finding(
                "manual",
                True,
                f"not here: {where}; the quote check will report checking none",
                None,
            )
        agrees = hashlib.sha256(where.read_bytes()).hexdigest() == entry["sha256"]
    except Exception as error:
        return _threw("manual", error)
    return Finding(
        "manual",
        agrees,
        f"{where.name} is the pinned scan" if agrees else f"{where.name} is a different file",
        "fetch it again with python3 -m conformance.documents",
    )


def check_corpus(path: Path | str = CORPUS) -> Finding:
    where = Path(path)
    if not where.is_file():
        return Finding("corpus", False, f"not here: {where}", "run the census to build one")
    try:
        held = json.loads(where.read_text())
        examined = int(held["images"])
    except Exception as error:
        return _threw("corpus", error, f"{where} did not parse")
    return Finding(
        "corpus",
        examined > 0,
        f"{examined} images behind it",
        "a census that examined no image writes an empty corpus, so check what it walked",
    )


def check_harness(find: Callable[[str], Any] = IN_SUBMODULE) -> Finding:
    try:
        found = find(HARNESS_MODULE)
    except Exception as error:
        return _threw("harness", error)
    if found is None:
        return Finding(
            "harness",
            True,
            "zilog-z80-python is not checked out; only the census needs it, so the "
            "package and the suite run without it",
        )
    return Finding("harness", True, f"zilog-z80-python found at {found.origin}")


def check_library() -> Finding:
    return Finding(
        "library",
        True,
        "the census takes the library to walk as an argument, so there is nothing to be set wrongly",
    )


def examine(corpus: Path | str = CORPUS) -> list[Finding]:
    return [
        check_python(),
        check_package(),
        check_boards(),
        check_paging(),
        check_mirroring(),
        check_ports(),
        check_manual(),
        check_corpus(corpus),
        check_harness(),
        check_library(),
    ]


def report(found: Sequence[Finding]) -> list[str]:
    from smsmapper import environment

    unwell = [one for one in found if not one.ok]
    lines = [
        f"smsmapper {VERSION} on {platform.python_version()}, {platform.system()}",
        "",
    ]
    lines.append("  the machine")
    lines.extend(environment.lines(ROOT))
    lines.append("")
    lines.append("  this package")
    lines.extend(one.report for one in found)
    lines.append("")
    if unwell:
        lines.append(f"  {len(unwell)} of {len(found)} checks did not pass")
    else:
        lines.append(f"  {len(found)} checks, nothing to report")
    return lines


def main(
    argv: Sequence[str] = (),
    examine: Callable[..., list[Finding]] = examine,
    say: Callable[[str], None] = print,
) -> int:
    found = examine()
    for line in report(found):
        say(line)
    return 1 if any(not one.ok for one in found) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
