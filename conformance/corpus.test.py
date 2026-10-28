import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from conformance import census, corpus  # noqa: E402

HELD: dict[str, Any] = json.loads((ROOT / "conformance" / "corpus.json").read_text())


def sound() -> dict[str, Any]:
    return {
        "listings": 3,
        "images": 2,
        "gated": 1,
        "frames": 600,
        "properties": dict.fromkeys(census.PROPERTIES, 0),
        "boards": {"codemasters": [1, 1], "sega": [1, 0]},
        "control": dict.fromkeys(census.CONTROL_BITS, 0),
        "wrapped": 1,
        "silent": 1,
        "unmodelled": 0,
        "pal": 1,
        "memoryControl": {"A8": 2},
        "ioControl": {"F5": 1},
        "handheldPorts": {},
    }


def run_main(held: dict[str, Any]) -> tuple[int, str]:
    where = Path(tempfile.mkdtemp()) / "corpus.json"
    where.write_text(json.dumps(held))
    said = io.StringIO()
    with contextlib.redirect_stdout(said):
        code = corpus.main(where)
    return code, said.getvalue()


class ReplayTest(unittest.TestCase):
    def test_the_corpus_here_breaks_no_property(self) -> None:
        # Arrange
        held = HELD

        # Act
        broken = corpus.broken(held)

        # Assert
        self.assertEqual(broken, [])

    def test_and_holds_together(self) -> None:
        # Arrange
        held = HELD

        # Act
        problems = corpus.inconsistent(held)

        # Assert
        self.assertEqual(problems, [])

    def test_and_names_every_property_the_census_gates_on(self) -> None:
        # Arrange
        gated = list(census.PROPERTIES)

        # Act
        named = list(HELD["properties"])

        # Assert
        self.assertEqual(named, gated)


class CheckTest(unittest.TestCase):
    def test_a_sound_corpus_passes(self) -> None:
        # Arrange
        held = sound()

        # Act
        code, said = run_main(held)

        # Assert
        self.assertEqual((code, "2 images" in said), (0, True))

    def test_a_broken_property_fails_and_is_named(self) -> None:
        # Arrange
        held = {**sound(), "properties": {**sound()["properties"], census.PAGES: 1}}

        # Act
        code, said = run_main(held)

        # Assert
        self.assertEqual((code, f"{census.PAGES}: 1 broken" in said), (1, True))

    def test_boards_that_do_not_add_up_to_the_images_are_reported(self) -> None:
        # Arrange
        held = {**sound(), "boards": {"sega": [1, 0]}}

        # Act
        problems = corpus.inconsistent(held)

        # Assert
        self.assertEqual(problems, ["boards hold 1 of 2 images"])

    def test_a_board_paging_more_images_than_it_holds_is_reported(self) -> None:
        # Arrange
        held = {**sound(), "boards": {"sega": [2, 3]}}

        # Act
        problems = corpus.inconsistent(held)

        # Assert
        self.assertEqual(problems, ["board sega pages 3 of its 2 images"])

    def test_any_count_above_the_image_count_is_reported(self) -> None:
        # Arrange
        held = {
            **sound(),
            "gated": 3,
            "silent": 3,
            "wrapped": 3,
            "unmodelled": 3,
            "pal": 3,
            "control": {**sound()["control"], "ram": 3},
            "ioControl": {"F5": 3},
        }

        # Act
        problems = corpus.inconsistent(held)

        # Assert
        expected = [
            "gated is 3 of 2 images",
            "silent is 3 of 2 images",
            "wrapped is 3 of 2 images",
            "unmodelled is 3 of 2 images",
            "pal is 3 of 2 images",
            "control ram is 3 of 2 images",
            "ioControl F5 is 3 of 2 images",
        ]
        self.assertEqual(problems, expected)

    def test_an_inconsistent_corpus_fails_the_run(self) -> None:
        # Arrange
        held = {**sound(), "silent": 3}

        # Act
        code, said = run_main(held)

        # Assert
        self.assertEqual((code, "silent is 3 of 2 images" in said), (1, True))


if __name__ == "__main__":
    unittest.main()
