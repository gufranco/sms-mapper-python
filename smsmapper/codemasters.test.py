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


def codemasters(ram: int = 0) -> smsmapper.Board:
    return smsmapper.Cartridge(numbered(0x40000), board="codemasters", ram=ram)


class PowerOnTest(unittest.TestCase):
    def test_frames_0_1_and_2_show_banks_0_1_and_0(self) -> None:
        # Arrange
        board = codemasters()

        # Act
        shown = [bank_at(board, address) for address in (0x0000, 0x4000, 0x8000)]

        # Assert
        self.assertEqual(shown, [0, 1, 0])


class RegisterTest(unittest.TestCase):
    def test_a_write_to_0000_selects_frame_0_first_1k_included(self) -> None:
        # Arrange
        board = codemasters()

        # Act
        board.write(0x0000, 3)

        # Assert
        self.assertEqual(bank_at(board, 0x0000), 3)

    def test_a_write_to_4000_selects_frame_1(self) -> None:
        # Arrange
        board = codemasters()

        # Act
        board.write(0x4000, 6)

        # Assert
        self.assertEqual(bank_at(board, 0x4000), 6)

    def test_a_write_to_8000_selects_frame_2(self) -> None:
        # Arrange
        board = codemasters()

        # Act
        board.write(0x8000, 9)

        # Assert
        self.assertEqual(bank_at(board, 0x8000), 9)

    def test_only_the_exact_register_address_is_decoded(self) -> None:
        # Arrange
        board = codemasters()

        # Act
        board.write(0x8001, 9)

        # Assert
        self.assertEqual(board.banks, (0, 1, 0))

    def test_sega_s_registers_reach_nothing(self) -> None:
        # Arrange
        board = codemasters()

        # Act
        board.write(0xFFFF, 9)

        # Assert
        self.assertEqual(board.banks, (0, 1, 0))


class RamTest(unittest.TestCase):
    def test_bit_7_written_to_4000_puts_ram_at_a000(self) -> None:
        # Arrange
        board = codemasters(ram=0x2000)
        board.write(0x4000, 0x80)

        # Act
        board.write(0xA010, 0x3C)

        # Assert
        self.assertEqual((board.read(0xA010), board.ram[0x10]), (0x3C, 0x3C))

    def test_the_ram_leaves_8000_to_9fff_on_the_rom(self) -> None:
        # Arrange
        board = codemasters(ram=0x2000)
        board.write(0x8000, 4)

        # Act
        board.write(0x4000, 0x80)

        # Assert
        self.assertEqual(bank_at(board, 0x9FFF), 4)

    def test_turning_the_ram_on_keeps_frame_1_where_it_was(self) -> None:
        # Arrange
        board = codemasters(ram=0x2000)
        board.write(0x4000, 5)

        # Act
        board.write(0x4000, 0x80)

        # Assert
        self.assertEqual(bank_at(board, 0x4000), 5)

    def test_bit_7_clear_takes_the_ram_away_and_selects_frame_1(self) -> None:
        # Arrange
        board = codemasters(ram=0x2000)
        board.write(0x4000, 0x80)

        # Act
        board.write(0x4000, 0x02)

        # Assert
        self.assertEqual((bank_at(board, 0x4000), bank_at(board, 0xA000)), (2, 0))

    def test_without_ram_bit_7_leaves_a000_on_the_rom(self) -> None:
        # Arrange
        board = codemasters()
        board.write(0x4000, 0x80)

        # Act
        board.write(0xA000, 0x11)

        # Assert
        self.assertEqual(bank_at(board, 0xA000), 0)

    def test_a_write_to_a000_with_the_ram_off_stores_nothing(self) -> None:
        # Arrange
        board = codemasters(ram=0x2000)

        # Act
        board.write(0xA000, 0x11)

        # Assert
        self.assertEqual(board.ram[0], 0)


if __name__ == "__main__":
    unittest.main()
