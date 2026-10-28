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


class PowerOnTest(unittest.TestCase):
    def test_the_three_frames_show_banks_0_1_and_2(self) -> None:
        # Arrange
        board = smsmapper.Cartridge(numbered(0x40000))

        # Act
        shown = [bank_at(board, address) for address in (0x0400, 0x4000, 0x8000)]

        # Assert
        self.assertEqual(shown, [0, 1, 2])

    def test_a_32k_image_wraps_frame_2_onto_its_first_bank(self) -> None:
        # Arrange
        board = smsmapper.Cartridge(numbered(0x8000))

        # Act
        shown = bank_at(board, 0x8000)

        # Assert
        self.assertEqual(shown, 0)

    def test_an_8k_image_repeats_through_every_frame(self) -> None:
        # Arrange
        board = smsmapper.Cartridge(bytes(range(256)) * 32)

        # Act
        shown = [board.read(address) for address in (0x0001, 0x2001, 0x4001, 0xA001)]

        # Assert
        self.assertEqual(shown, [1, 1, 1, 1])


class FrameRegisterTest(unittest.TestCase):
    def test_a_write_to_ffff_selects_the_bank_frame_2_shows(self) -> None:
        # Arrange
        board = smsmapper.Cartridge(numbered(0x40000))

        # Act
        board.write(0xFFFF, 5)

        # Assert
        self.assertEqual(bank_at(board, 0x8000), 5)

    def test_fffd_and_fffe_select_frames_0_and_1(self) -> None:
        # Arrange
        board = smsmapper.Cartridge(numbered(0x40000))
        board.write(0xFFFD, 7)

        # Act
        board.write(0xFFFE, 6)

        # Assert
        self.assertEqual([bank_at(board, 0x0400), bank_at(board, 0x4000)], [7, 6])

    def test_the_first_1k_stays_on_the_first_1k_of_the_image(self) -> None:
        # Arrange
        board = smsmapper.Cartridge(numbered(0x40000))

        # Act
        board.write(0xFFFD, 8)

        # Assert
        self.assertEqual([bank_at(board, 0x03FF), bank_at(board, 0x0400)], [0, 8])

    def test_a_bank_past_the_end_wraps_by_the_page_count(self) -> None:
        # Arrange
        board = smsmapper.Cartridge(numbered(0x20000))

        # Act
        board.write(0xFFFF, 9)

        # Assert
        self.assertEqual(bank_at(board, 0x8000), 1)

    def test_writes_below_fffc_reach_no_register(self) -> None:
        # Arrange
        board = smsmapper.Cartridge(numbered(0x40000))
        board.write(0xFFFB, 9)

        # Act
        board.write(0x8000, 9)

        # Assert
        self.assertEqual(board.banks, (0, 1, 2))


class BankShiftTest(unittest.TestCase):
    def test_shift_01_with_bank_1_reaches_what_shift_00_with_bank_9_does(self) -> None:
        # Arrange
        board = smsmapper.Cartridge(numbered(0x80000))
        board.write(0xFFFC, 0x01)

        # Act
        board.write(0xFFFF, 1)

        # Assert
        self.assertEqual(bank_at(board, 0x8000), 9)

    def test_shift_11_moves_bank_8_back_to_the_first_bank(self) -> None:
        # Arrange
        board = smsmapper.Cartridge(numbered(0x80000))
        board.write(0xFFFC, 0x03)

        # Act
        board.write(0xFFFE, 8)

        # Assert
        self.assertEqual(bank_at(board, 0x4000), 0)

    def test_the_shift_also_moves_banks_selected_before_it(self) -> None:
        # Arrange
        board = smsmapper.Cartridge(numbered(0x80000))

        # Act
        board.write(0xFFFC, 0x02)

        # Assert
        self.assertEqual(board.banks, (16, 17, 18))


class CartridgeRamTest(unittest.TestCase):
    def test_bit_3_of_fffc_puts_ram_in_frame_2(self) -> None:
        # Arrange
        board = smsmapper.Cartridge(numbered(0x40000), ram=0x4000)
        board.write(0xFFFC, 0x08)

        # Act
        board.write(0x8123, 0x5A)

        # Assert
        self.assertEqual(board.read(0x8123), 0x5A)

    def test_clearing_bit_3_brings_the_rom_back(self) -> None:
        # Arrange
        board = smsmapper.Cartridge(numbered(0x40000), ram=0x4000)
        board.write(0xFFFC, 0x08)
        board.write(0x8000, 0x5A)

        # Act
        board.write(0xFFFC, 0x00)

        # Assert
        self.assertEqual(bank_at(board, 0x8000), 2)

    def test_bit_2_picks_the_second_16k_of_a_32k_ram(self) -> None:
        # Arrange
        board = smsmapper.Cartridge(numbered(0x40000), ram=0x8000)
        board.write(0xFFFC, 0x08)
        board.write(0x8000, 0x11)
        board.write(0xFFFC, 0x0C)

        # Act
        board.write(0x8000, 0x22)

        # Assert
        held = (board.read(0x8000), board.ram[0x0000], board.ram[0x4000])
        self.assertEqual(held, (0x22, 0x11, 0x22))

    def test_an_8k_ram_repeats_through_frame_2(self) -> None:
        # Arrange
        board = smsmapper.Cartridge(numbered(0x40000), ram=0x2000)
        board.write(0xFFFC, 0x08)

        # Act
        board.write(0x8001, 0x77)

        # Assert
        self.assertEqual(board.read(0xA001), 0x77)

    def test_bit_3_on_a_board_without_ram_leaves_the_rom_in_place(self) -> None:
        # Arrange
        board = smsmapper.Cartridge(numbered(0x40000))

        # Act
        board.write(0xFFFC, 0x08)

        # Assert
        self.assertEqual(bank_at(board, 0x8000), 2)

    def test_a_write_to_frame_2_with_ram_off_changes_nothing(self) -> None:
        # Arrange
        board = smsmapper.Cartridge(numbered(0x40000), ram=0x4000)

        # Act
        board.write(0x8000, 0x99)

        # Assert
        self.assertEqual((bank_at(board, 0x8000), board.ram[0]), (2, 0))


class ResetTest(unittest.TestCase):
    def test_reset_puts_the_registers_back_and_keeps_the_ram(self) -> None:
        # Arrange
        board = smsmapper.Cartridge(numbered(0x40000), ram=0x4000)
        board.write(0xFFFC, 0x09)
        board.write(0x8000, 0x42)
        board.write(0xFFFF, 7)

        # Act
        board.reset()

        # Assert
        held = (board.banks, bank_at(board, 0x8000), board.ram[0])
        self.assertEqual(held, ((0, 1, 2), 2, 0x42))


if __name__ == "__main__":
    unittest.main()
