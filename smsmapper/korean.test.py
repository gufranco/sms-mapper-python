import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import smsmapper  # noqa: E402

UNIT = 0x2000


def numbered(size: int) -> bytes:
    return bytes((offset // UNIT) & 0xFF for offset in range(size))


def units(board: smsmapper.Board) -> list[int]:
    return [board.read(address) for address in range(0x0400, 0xC000, UNIT)]


def built(name: str, size: int = 0x40000) -> smsmapper.Board:
    return smsmapper.Cartridge(numbered(size), board=name)


class KoreanTest(unittest.TestCase):
    def test_power_on_shows_banks_0_1_and_2(self) -> None:
        # Arrange
        board = built("korean")

        # Act
        shown = units(board)

        # Assert
        self.assertEqual(shown, [0, 1, 2, 3, 4, 5])

    def test_a_write_to_a000_selects_frame_2(self) -> None:
        # Arrange
        board = built("korean")

        # Act
        board.write(0xA000, 6)

        # Assert
        self.assertEqual(board.banks, (0, 1, 6))

    def test_sega_s_registers_and_other_addresses_reach_nothing(self) -> None:
        # Arrange
        board = built("korean")
        board.write(0xFFFF, 6)

        # Act
        board.write(0xA001, 6)

        # Assert
        self.assertEqual(board.banks, (0, 1, 2))

    def test_the_first_1k_stays_on_the_first_1k(self) -> None:
        # Arrange
        board = built("korean")

        # Act
        shown = board.read(0x03FF)

        # Assert
        self.assertEqual(shown, 0)


class KoreanNoBankTest(unittest.TestCase):
    def test_no_write_moves_a_frame(self) -> None:
        # Arrange
        board = built("korean_nb")
        board.write(0xFFFF, 6)

        # Act
        board.write(0xA000, 6)

        # Assert
        self.assertEqual((units(board), board.banks), ([0, 1, 2, 3, 4, 5], (0, 1, 2)))


class Korean188Test(unittest.TestCase):
    def test_power_on_shows_the_8k_bank_1f_from_4000(self) -> None:
        # Arrange
        board = built("korean_188in1", 0x80000)

        # Act
        shown = units(board)

        # Assert
        self.assertEqual(shown, [0, 1, 0x1F, 0x20, 0x21, 0x22])

    def test_a_write_to_2000_picks_the_8k_bank_by_its_complement(self) -> None:
        # Arrange
        board = built("korean_188in1", 0x80000)

        # Act
        board.write(0x2000, 0x1C)

        # Assert
        self.assertEqual(units(board)[2:], [3, 4, 5, 6])

    def test_a000_to_bfff_reaches_the_same_register(self) -> None:
        # Arrange
        board = built("korean_188in1", 0x80000)

        # Act
        board.write(0xBFFF, 0x1E)

        # Assert
        self.assertEqual(board.banks, (0, 1))

    def test_4000_to_9fff_reach_no_register(self) -> None:
        # Arrange
        board = built("korean_188in1", 0x80000)
        board.write(0x4000, 0)

        # Act
        board.write(0x8000, 0)

        # Assert
        self.assertEqual(board.banks, (0, 0x1F))

    def test_the_8k_bank_wraps_by_twice_the_16k_page_count(self) -> None:
        # Arrange
        board = built("korean_188in1", 0x8000)

        # Act
        shown = units(board)[2]

        # Assert
        self.assertEqual(shown, 3)


class JanggunTest(unittest.TestCase):
    def test_power_on_shows_8k_banks_0_to_5(self) -> None:
        # Arrange
        board = built("janggun")

        # Act
        shown = units(board)

        # Assert
        self.assertEqual(shown, [0, 1, 2, 3, 4, 5])

    def test_writes_to_4000_6000_8000_and_a000_each_select_an_8k_bank(self) -> None:
        # Arrange
        board = built("janggun")
        for address, value in ((0x4000, 9), (0x6000, 10), (0x8000, 11)):
            board.write(address, value)

        # Act
        board.write(0xA000, 12)

        # Assert
        self.assertEqual(units(board), [0, 1, 9, 10, 11, 12])

    def test_a_bank_with_bit_7_set_reads_every_byte_bit_reversed(self) -> None:
        # Arrange
        board = smsmapper.Cartridge(bytes([0x01, 0x80, 0x0F]) + bytes(0x7FFD), board="janggun")

        # Act
        board.write(0x4000, 0x80)

        # Assert
        self.assertEqual([board.read(0x4000 + one) for one in range(3)], [0x80, 0x01, 0xF0])

    def test_bit_6_of_a_bank_number_is_dropped(self) -> None:
        # Arrange
        board = built("janggun", 0x80000)

        # Act
        board.write(0x8000, 0x41)

        # Assert
        self.assertEqual(units(board)[4], 1)

    def test_a_sega_register_selects_a_pair_of_8k_banks(self) -> None:
        # Arrange
        board = built("janggun")

        # Act
        board.write(0xFFFE, 3)

        # Assert
        self.assertEqual(units(board)[2:4], [6, 7])

    def test_fffc_reaches_nothing(self) -> None:
        # Arrange
        board = built("janggun")

        # Act
        board.write(0xFFFC, 3)

        # Assert
        self.assertEqual(board.banks, (0, 1, 2, 3, 4, 5))


class ZeminaTest(unittest.TestCase):
    def test_power_on_shows_8k_banks_0_to_5(self) -> None:
        # Arrange
        board = built("zemina")

        # Act
        shown = units(board)

        # Assert
        self.assertEqual(shown, [0, 1, 2, 3, 4, 5])

    def test_writes_to_0000_to_0003_select_8000_a000_4000_and_6000(self) -> None:
        # Arrange
        board = built("zemina")
        for address, value in ((0x0000, 20), (0x0001, 21), (0x0002, 22)):
            board.write(address, value)

        # Act
        board.write(0x0003, 23)

        # Assert
        self.assertEqual(units(board), [0, 1, 22, 23, 20, 21])

    def test_0004_reaches_no_register(self) -> None:
        # Arrange
        board = built("zemina")

        # Act
        board.write(0x0004, 20)

        # Assert
        self.assertEqual(board.banks, (0, 1, 2, 3, 4, 5))

    def test_a_bank_past_the_end_wraps_by_the_8k_count(self) -> None:
        # Arrange
        board = built("zemina", 0x20000)

        # Act
        board.write(0x0000, 17)

        # Assert
        self.assertEqual(units(board)[4], 1)


class NemesisTest(unittest.TestCase):
    def test_power_on_shows_the_last_8k_bank_at_0000(self) -> None:
        # Arrange
        board = built("nemesis", 0x20000)

        # Act
        shown = board.read(0x0000)

        # Assert
        self.assertEqual(shown, 15)

    def test_it_pages_as_zemina_does(self) -> None:
        # Arrange
        board = built("nemesis", 0x20000)

        # Act
        board.write(0x0002, 7)

        # Assert
        self.assertEqual(board.banks, (15, 1, 7, 3, 4, 5))


if __name__ == "__main__":
    unittest.main()
