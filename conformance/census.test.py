import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from typing import Any, override

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from conformance import census, harness  # noqa: E402

LOOP = bytes([0x18, 0xFE])

PAGES = bytes([0x3E, 0x05, 0x32, 0xFF, 0xFF]) + LOOP

PAL_ONLY = (
    bytes([0xDB, 0xBF, 0xDB, 0xBF, 0xA7, 0xF2, 0x02, 0x00, 0x01, 0x96, 0x0A])
    + bytes([0x0B, 0x79, 0xB0, 0xC2, 0x0B, 0x00, 0xDB, 0xBF, 0xA7, 0xFA, 0x1C, 0x00])
    + PAGES
)


def image(code: bytes, size: int = 0x40000, mark: int = 0) -> bytes:
    return code + bytes(size - len(code) - 1) + bytes([mark])


def a_library(files: dict[str, dict[str, bytes]]) -> Path:
    where = Path(tempfile.mkdtemp())
    for archive, members in files.items():
        with zipfile.ZipFile(where / archive, "w") as bundle:
            for name, body in members.items():
                bundle.writestr(f"folder/{name}", body)
    return where


def a_board_list(rom: bytes, board: str) -> Path:
    where = Path(tempfile.mkdtemp()) / "boards.json"
    sha1 = hashlib.sha1(rom, usedforsecurity=False).hexdigest()
    where.write_text(json.dumps({"boards": [{"sha1": sha1, "board": board}]}))
    return where


def taken(paths: list[Path], listed: Path | None = None) -> dict[str, Any]:
    return dict(census.take(paths, frames=2, jobs=1, listed=listed))


def run_main(argv: list[str], into: Path) -> tuple[int, str]:
    said = io.StringIO()
    with contextlib.redirect_stdout(said):
        code = census.main(argv, into)
    return code, said.getvalue()


class WalkTest(unittest.TestCase):
    def test_images_are_read_out_of_archives_and_loose_files_alike(self) -> None:
        # Arrange
        where = a_library({"1 US - A-Z.zip": {"A.sms": b"a", "notes.txt": b"x"}})
        (where / "B.gg").write_bytes(b"b")
        (where / "C.txt").write_bytes(b"c")

        # Act
        found = sorted((name, rom) for _, name, rom in census.images_in(where))

        # Assert
        self.assertEqual(found, [("A.sms", b"a"), ("B.gg", b"b")])

    def test_an_archive_or_an_image_can_be_named_directly(self) -> None:
        # Arrange
        where = a_library({"set.zip": {"A.sms": b"a"}})
        (where / "B.gg").write_bytes(b"b")
        (where / "C.txt").write_bytes(b"c")

        # Act
        found = [
            [name for _, name, _ in census.images_in(where / one)]
            for one in ("set.zip", "B.gg", "C.txt")
        ]

        # Assert
        self.assertEqual(found, [["A.sms"], ["B.gg"], []])

    def test_retail_means_a_regional_set_and_no_prototype_or_demo_tag(self) -> None:
        # Arrange
        asked = [
            ("1 US - A-Z.zip", "Game (USA).sms"),
            ("2 Europe - A-Z.zip", "Game (Europe) (Proto).sms"),
            ("4 Hacks.zip", "Game (Hack).sms"),
        ]

        # Act
        found = [census.gated(collection, name) for collection, name in asked]

        # Assert
        self.assertEqual(found, [True, False, False])

    def test_the_board_list_is_read_by_whole_file_sha1(self) -> None:
        # Arrange
        rom = image(LOOP, 0x8000, 7)
        listed = a_board_list(rom, "codemasters")

        # Act
        found = census.board_of(rom, census.boards(listed))

        # Assert
        self.assertEqual(found, "codemasters")


class ExamineTest(unittest.TestCase):
    def test_an_image_that_pages_reports_its_writes(self) -> None:
        # Arrange
        job = (image(PAGES), 2, census.CONSOLE, "sega", "usa")

        # Act
        found = census.examine(job)

        # Assert
        self.assertEqual((found["writes"], found["raised"], found["board"]), (1, None, "sega"))

    def test_a_game_gear_image_runs_on_the_game_gear(self) -> None:
        # Arrange
        job = (image(bytes([0xDB, 0x00]) + LOOP, 0x8000), 2, census.HANDHELD, "sega", "usa")

        # Act
        found = census.examine(job)

        # Assert
        self.assertEqual(found["handheldPorts"], [0])

    def test_an_image_that_throws_reports_what_it_threw_and_where(self) -> None:
        # Arrange
        class Broken(harness.Run):
            __slots__ = ()

            @override
            def run_frames(self, count: int) -> None:
                raise ValueError("bad opcode")

        job = (image(LOOP), 2, census.CONSOLE, "sega", "usa")

        # Act
        found = census.examine(job, Broken)

        # Assert
        self.assertEqual(found["raised"], "ValueError: bad opcode at frame 0")

    def test_a_board_this_package_does_not_model_runs_on_sega_s(self) -> None:
        # Arrange
        job = (image(PAGES), 2, census.CONSOLE, "mgear", "usa")

        # Act
        found = census.examine(job)

        # Assert
        self.assertEqual((found["board"], found["writes"]), ("sega", 1))


class RegionTest(unittest.TestCase):
    def test_an_image_only_the_european_set_lists_runs_on_a_pal_console(self) -> None:
        # Arrange
        where = a_library({"2 Europe - A-Z.zip": {"Late (Europe).sms": image(PAL_ONLY)}})

        # Act
        found = taken([where])

        # Assert
        self.assertEqual((found["properties"][census.PAGES], found["pal"]), (0, 1))

    def test_an_image_another_set_also_lists_runs_on_an_ntsc_console(self) -> None:
        # Arrange
        rom = image(PAL_ONLY)
        where = a_library(
            {"2 Europe - A-Z.zip": {"Late (Europe).sms": rom}, "1 US - A-Z.zip": {"Late.sms": rom}}
        )

        # Act
        found = taken([where])

        # Assert
        self.assertEqual((found["properties"][census.PAGES], found["pal"]), (1, 0))


class PropertyTest(unittest.TestCase):
    def test_a_retail_image_over_48k_that_never_pages_breaks_the_property(self) -> None:
        # Arrange
        where = a_library({"1 US - A-Z.zip": {"Big (USA).sms": image(LOOP)}})

        # Act
        found = taken([where])

        # Assert
        held = (found["properties"][census.PAGES], found["culprits"][census.PAGES])
        self.assertEqual(held, (1, ["Big (USA).sms"]))

    def test_a_small_image_that_never_pages_breaks_nothing(self) -> None:
        # Arrange
        where = a_library({"1 US - A-Z.zip": {"Small (USA).sms": image(LOOP, 0xC000)}})

        # Act
        found = taken([where])

        # Assert
        self.assertEqual((found["properties"][census.PAGES], found["silent"]), (0, 1))

    def test_a_hack_that_never_pages_breaks_nothing(self) -> None:
        # Arrange
        where = a_library({"4 Hacks.zip": {"Big (Hack).sms": image(LOOP)}})

        # Act
        found = taken([where])

        # Assert
        self.assertEqual((found["properties"][census.PAGES], found["gated"]), (0, 0))

    def test_a_board_with_no_registers_is_never_asked_to_page(self) -> None:
        # Arrange
        rom = image(LOOP, mark=3)
        where = a_library({"1 US - A-Z.zip": {"Big (USA).sms": rom}})

        # Act
        found = taken([where], a_board_list(rom, "korean_nb"))

        # Assert
        self.assertEqual((found["properties"][census.PAGES], found["gated"]), (0, 0))

    def test_an_image_that_throws_breaks_the_other_property(self) -> None:
        # Arrange
        class Broken(harness.Run):
            __slots__ = ()

            @override
            def run_frames(self, count: int) -> None:
                raise ValueError("bad opcode")

        where = a_library({"4 Homebrew.zip": {"Bad.sms": image(LOOP)}})

        # Act
        found = dict(census.take([where], frames=2, jobs=1, build=Broken))

        # Assert
        held = (
            found["properties"][census.RAISES_NOTHING],
            found["culprits"][census.RAISES_NOTHING],
        )
        self.assertEqual(held, (1, ["Bad.sms: ValueError: bad opcode at frame 0"]))


class TallyTest(unittest.TestCase):
    def test_each_distinct_image_is_counted_once_and_retail_if_any_copy_is(self) -> None:
        # Arrange
        rom = image(PAGES)
        where = a_library({"1 US - A-Z.zip": {"A (USA).sms": rom}, "4 Hacks.zip": {"A.sms": rom}})

        # Act
        found = taken([where])

        # Assert
        self.assertEqual((found["listings"], found["images"], found["gated"]), (2, 1, 1))

    def test_the_boards_count_their_images_and_the_ones_that_paged(self) -> None:
        # Arrange
        rom = image(bytes([0x3E, 0x04, 0x32, 0x00, 0x80]) + LOOP, mark=9)
        where = a_library({"1 US - A-Z.zip": {"A (USA).sms": rom, "B (USA).sms": image(PAGES)}})

        # Act
        found = taken([where], a_board_list(rom, "codemasters"))

        # Assert
        self.assertEqual(found["boards"], {"codemasters": [1, 1], "sega": [1, 1]})

    def test_fffc_bits_wrapped_banks_and_port_settings_are_counted_by_image(self) -> None:
        # Arrange
        paging = bytes([0x3E, 0x8B, 0x32, 0xFC, 0xFF, 0x3E, 0x30, 0x32, 0xFF, 0xFF])
        code = paging + bytes([0x3E, 0xA8, 0xD3, 0x3E, 0x3E, 0xF5, 0xD3, 0x3F])
        where = a_library({"4 Homebrew.zip": {"A.sms": image(code + LOOP)}})

        # Act
        found = taken([where])

        # Assert
        held = (found["control"], found["wrapped"], found["memoryControl"], found["ioControl"])
        expected = (
            {"bank shift": 1, "ram bank": 0, "ram": 1, "bit 4": 0, "bit 7": 1},
            1,
            {"A8": 1},
            {"F5": 1},
        )
        self.assertEqual(held, expected)

    def test_unmodelled_boards_are_counted_apart(self) -> None:
        # Arrange
        rom = image(PAGES, mark=4)
        where = a_library({"1 US - A-Z.zip": {"A (USA).sms": rom}})

        # Act
        found = taken([where], a_board_list(rom, "xterminator"))

        # Assert
        self.assertEqual(
            (found["unmodelled"], found["culprits"][census.UNMODELLED]),
            (1, ["A (USA).sms: xterminator"]),
        )

    def test_more_than_one_job_gives_the_same_answer(self) -> None:
        # Arrange
        where = a_library(
            {"1 US - A-Z.zip": {"A (USA).sms": image(PAGES), "B (USA).sms": image(LOOP, 0x8000)}}
        )

        # Act
        found = dict(census.take([where], frames=2, jobs=2))

        # Assert
        self.assertEqual(
            {key: found[key] for key in ("images", "silent")}, {"images": 2, "silent": 1}
        )


class MainTest(unittest.TestCase):
    def test_no_path_prints_the_usage_and_exits_2(self) -> None:
        # Arrange
        into = Path(tempfile.mkdtemp()) / "corpus.json"

        # Act
        code, said = run_main([], into)

        # Assert
        self.assertEqual((code, census.USAGE in said), (2, True))

    def test_a_flag_with_no_value_prints_the_usage(self) -> None:
        # Arrange
        into = Path(tempfile.mkdtemp()) / "corpus.json"

        # Act
        code, _ = run_main(["somewhere", "--frames"], into)

        # Assert
        self.assertEqual(code, 2)

    def test_an_absent_path_is_named_and_a_census_of_nothing_fails(self) -> None:
        # Arrange
        into = Path(tempfile.mkdtemp()) / "corpus.json"

        # Act
        code, said = run_main(["/nowhere/at/all", "--jobs", "1"], into)

        # Assert
        self.assertEqual((code, "absent: /nowhere/at/all" in said, into.exists()), (1, True, False))

    def test_a_clean_run_writes_the_corpus_and_exits_0(self) -> None:
        # Arrange
        where = a_library({"1 US - A-Z.zip": {"A (USA).sms": image(PAGES)}})
        into = Path(tempfile.mkdtemp()) / "corpus.json"

        # Act
        code, said = run_main([str(where), "--frames", "2", "--jobs", "1"], into)

        # Assert
        written = json.loads(into.read_text())
        self.assertEqual(
            (code, written["images"], "culprits" in written, "1 distinct" in said),
            (0, 1, False, True),
        )

    def test_a_broken_property_exits_1_and_names_the_image(self) -> None:
        # Arrange
        where = a_library({"1 US - A-Z.zip": {"Big (USA).sms": image(LOOP)}})
        into = Path(tempfile.mkdtemp()) / "corpus.json"

        # Act
        code, said = run_main([str(where), "--frames", "2", "--jobs", "1"], into)

        # Assert
        self.assertEqual((code, "Big (USA).sms" in said), (1, True))


if __name__ == "__main__":
    unittest.main()
