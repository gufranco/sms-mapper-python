import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import smsmapper  # noqa: E402

THIRD_PARTY = (
    "4pak",
    "codemasters",
    "eeprom",
    "hicom",
    "janggun",
    "korean",
    "korean_188in1",
    "korean_nb",
    "nemesis",
    "seojin",
    "zemina",
)


class RegistryTest(unittest.TestCase):
    def test_it_names_sega_s_board_and_every_third_party_one_mame_lists(self) -> None:
        # Arrange
        expected = sorted(("sega", *THIRD_PARTY))

        # Act
        named = sorted(smsmapper.BOARDS)

        # Assert
        self.assertEqual(named, expected)

    def test_every_board_says_what_it_is(self) -> None:
        # Arrange
        boards = smsmapper.BOARDS

        # Act
        blank = [name for name, summary in boards.items() if not summary.strip()]

        # Assert
        self.assertEqual(blank, [])

    def test_a_cartridge_is_built_on_the_board_it_names(self) -> None:
        # Arrange
        image = bytes(0x8000)

        # Act
        built = [smsmapper.Cartridge(image, board=name).name for name in smsmapper.BOARDS]

        # Assert
        self.assertEqual(built, list(smsmapper.BOARDS))

    def test_sega_s_board_is_the_default(self) -> None:
        # Arrange
        image = bytes(0x8000)

        # Act
        built = smsmapper.Cartridge(image)

        # Assert
        self.assertEqual(built.name, "sega")


class ImageTest(unittest.TestCase):
    def test_the_page_count_rounds_a_partial_16k_bank_up(self) -> None:
        # Arrange
        image = bytes(0xC000 + 1)

        # Act
        board = smsmapper.Cartridge(image)

        # Assert
        self.assertEqual(board.pages, 4)

    def test_the_image_is_kept_as_given(self) -> None:
        # Arrange
        image = bytes(range(256)) * 64

        # Act
        board = smsmapper.Cartridge(image)

        # Assert
        self.assertEqual(board.image, image)


class RamSizeTest(unittest.TestCase):
    def test_every_size_a_board_carries_is_accepted(self) -> None:
        # Arrange
        sizes = (0, 0x2000, 0x4000, 0x8000)

        # Act
        built = [len(smsmapper.Cartridge(bytes(0x8000), ram=size).ram) for size in sizes]

        # Assert
        self.assertEqual(built, list(sizes))

    def test_a_negative_size_is_refused(self) -> None:
        # Arrange
        def attempt() -> object:
            return smsmapper.Cartridge(bytes(0x8000), ram=-1)

        # Act
        with self.assertRaises(smsmapper.RamSizeError) as raised:
            attempt()

        # Assert
        self.assertIn("-1", str(raised.exception))


class DecodeTest(unittest.TestCase):
    def test_each_board_names_the_addresses_its_registers_sit_at(self) -> None:
        # Arrange
        probes = (0x0000, 0x0003, 0x2000, 0x3FFE, 0x4000, 0x6000, 0x7FFF, 0x8000, 0xA000)
        tops = (0xBFFF, 0xFFF0, 0xFFFC, 0xFFFD, 0xFFFF)
        expected = {
            "sega": [0xFFFC, 0xFFFD, 0xFFFF],
            "codemasters": [0x0000, 0x4000, 0x8000],
            "4pak": [0x3FFE, 0x7FFF, 0xBFFF],
            "eeprom": [0x8000, 0xFFFC, 0xFFFD, 0xFFFF],
            "hicom": [0xFFFF],
            "janggun": [0x4000, 0x6000, 0x8000, 0xA000, 0xFFFD, 0xFFFF],
            "korean": [0xA000],
            "korean_188in1": [0x2000, 0x3FFE, 0xA000, 0xBFFF],
            "korean_nb": [],
            "nemesis": [0x0000, 0x0003],
            "seojin": [0xFFF0, 0xFFFD, 0xFFFF],
            "zemina": [0x0000, 0x0003],
        }

        # Act
        found = {
            name: [
                a
                for a in (*probes, *tops)
                if smsmapper.Cartridge(bytes(0x8000), board=name).decodes(a)
            ]
            for name in smsmapper.BOARDS
        }

        # Assert
        self.assertEqual(found, expected)


if __name__ == "__main__":
    unittest.main()
