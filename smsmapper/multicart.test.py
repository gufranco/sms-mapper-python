import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import smsmapper  # noqa: E402

UNIT = 0x2000


def numbered(size: int) -> bytes:
    return bytes((offset // UNIT) & 0xFF for offset in range(size))


def bank_at(board: smsmapper.Board, address: int) -> int:
    return board.read(address) // 2


def built(name: str, size: int = 0x80000) -> smsmapper.Board:
    return smsmapper.Cartridge(numbered(size), board=name)


class FourPakTest(unittest.TestCase):
    def test_every_frame_powers_on_at_bank_0(self) -> None:
        # Arrange
        board = built("4pak")

        # Act
        shown = [bank_at(board, address) for address in (0x0000, 0x4000, 0x8000)]

        # Assert
        self.assertEqual(shown, [0, 0, 0])

    def test_3ffe_selects_frame_0_and_the_game_frame_2_belongs_to(self) -> None:
        # Arrange
        board = built("4pak")
        board.write(0xBFFF, 2)

        # Act
        board.write(0x3FFE, 0x13)

        # Assert
        self.assertEqual(board.banks, (0x13, 0, 0x12))

    def test_7fff_selects_frame_1(self) -> None:
        # Arrange
        board = built("4pak")

        # Act
        board.write(0x7FFF, 5)

        # Assert
        self.assertEqual(bank_at(board, 0x4000), 5)

    def test_bfff_adds_to_the_game_base_for_frame_2(self) -> None:
        # Arrange
        board = built("4pak")
        board.write(0x3FFE, 0x20)

        # Act
        board.write(0xBFFF, 3)

        # Assert
        self.assertEqual(bank_at(board, 0x8000), 0x23 % 32)

    def test_other_addresses_reach_nothing(self) -> None:
        # Arrange
        board = built("4pak")

        # Act
        board.write(0xFFFF, 5)

        # Assert
        self.assertEqual(board.banks, (0, 0, 0))


class HiComTest(unittest.TestCase):
    def test_ffff_selects_the_32k_bank_at_0000(self) -> None:
        # Arrange
        board = built("hicom")

        # Act
        board.write(0xFFFF, 3)

        # Assert
        self.assertEqual([bank_at(board, 0x0000), bank_at(board, 0x4000)], [6, 7])

    def test_8000_to_bfff_always_shows_the_first_16k(self) -> None:
        # Arrange
        board = built("hicom")

        # Act
        board.write(0xFFFF, 3)

        # Assert
        self.assertEqual(bank_at(board, 0x8000), 0)

    def test_fffe_reaches_nothing(self) -> None:
        # Arrange
        board = built("hicom")

        # Act
        board.write(0xFFFE, 3)

        # Assert
        self.assertEqual(board.banks, (0,))


class SeojinTest(unittest.TestCase):
    def test_every_byte_reads_with_bit_7_inverted(self) -> None:
        # Arrange
        board = built("seojin")

        # Act
        shown = [board.read(address) for address in (0x0000, 0x4000, 0x8000)]

        # Assert
        self.assertEqual(shown, [0x80, 0x82, 0x84])

    def test_fff0_selects_the_32k_game_every_frame_is_offset_into(self) -> None:
        # Arrange
        board = built("seojin")

        # Act
        board.write(0xFFF0, 3)

        # Assert
        self.assertEqual([board.read(0x0000) ^ 0x80, board.banks], [12, (6, 7, 6)])

    def test_the_frame_registers_are_ored_into_the_game_base(self) -> None:
        # Arrange
        board = built("seojin")
        board.write(0xFFF0, 3)

        # Act
        board.write(0xFFFF, 1)

        # Assert
        self.assertEqual(board.banks, (6, 7, 7))

    def test_fffc_reaches_nothing(self) -> None:
        # Arrange
        board = built("seojin")

        # Act
        board.write(0xFFFC, 1)

        # Assert
        self.assertEqual(board.banks, (0, 1, 2))


if __name__ == "__main__":
    unittest.main()
