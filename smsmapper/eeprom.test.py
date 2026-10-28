import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import smsmapper  # noqa: E402

LINES = 0x8000

SELECT = 0x04

CLOCK = 0x02

ENABLE = 0x08

RESET = 0x80

UNIT = 0x2000


def numbered(size: int) -> bytes:
    return bytes((offset // UNIT) & 0xFF for offset in range(size))


def built() -> smsmapper.eeprom.SegaEeprom:
    board = smsmapper.Cartridge(numbered(0x20000), board="eeprom")
    assert isinstance(board, smsmapper.eeprom.SegaEeprom)
    return board


def enabled() -> smsmapper.eeprom.SegaEeprom:
    board = built()
    board.write(0xFFFC, ENABLE)
    return board


def clock_in(board: smsmapper.Board, bits: str) -> None:
    for bit in bits:
        board.write(LINES, SELECT | int(bit))
        board.write(LINES, SELECT | CLOCK | int(bit))


def command(board: smsmapper.Board, bits: str) -> None:
    board.write(LINES, 0)
    board.write(LINES, SELECT)
    clock_in(board, "1" + bits)


def data_out(board: smsmapper.Board) -> int:
    return board.read(LINES) & 1


def clock_out(board: smsmapper.Board, count: int) -> list[int]:
    seen = []
    for _ in range(count):
        board.write(LINES, SELECT)
        board.write(LINES, SELECT | CLOCK)
        seen.append(data_out(board))
    return seen


def read_word(board: smsmapper.Board, address: int) -> int:
    command(board, f"10{address:06b}")
    return int("".join(map(str, clock_out(board, 16))), 2)


def write_word(board: smsmapper.Board, address: int, value: int) -> None:
    command(board, f"01{address:06b}{value:016b}")
    board.write(LINES, 0)


def unlock(board: smsmapper.Board) -> None:
    command(board, "00110000")
    board.write(LINES, 0)


class EnableTest(unittest.TestCase):
    def test_with_the_eeprom_off_8000_reads_the_rom(self) -> None:
        # Arrange
        board = built()

        # Act
        shown = board.read(LINES)

        # Assert
        self.assertEqual(shown, 4)

    def test_with_it_on_8000_reads_the_lines_with_bit_1_set(self) -> None:
        # Arrange
        board = enabled()

        # Act
        board.write(LINES, 0xF0)

        # Assert
        self.assertEqual(board.read(LINES), 0xF3)

    def test_with_it_off_a_write_to_8000_reaches_no_line(self) -> None:
        # Arrange
        board = built()
        board.write(LINES, 0xF0)

        # Act
        board.write(0xFFFC, ENABLE)

        # Assert
        self.assertEqual(board.read(LINES), 0x03)

    def test_it_pages_through_sega_s_registers(self) -> None:
        # Arrange
        board = enabled()

        # Act
        board.write(0xFFFE, 5)

        # Assert
        self.assertEqual((board.banks, board.read(0x4000)), ((0, 5, 2), 10))

    def test_the_first_1k_stays_put(self) -> None:
        # Arrange
        board = enabled()

        # Act
        board.write(0xFFFD, 3)

        # Assert
        self.assertEqual((board.read(0x03FF), board.read(0x0400)), (0, 6))


class ReadTest(unittest.TestCase):
    def test_an_erased_word_reads_all_ones_after_a_dummy_zero(self) -> None:
        # Arrange
        board = enabled()
        command(board, "10000101")

        # Act
        dummy = data_out(board)

        # Assert
        self.assertEqual((dummy, clock_out(board, 16)), (0, [1] * 16))

    def test_the_contents_given_are_read_back_high_byte_first(self) -> None:
        # Arrange
        board = enabled()
        board.eeprom.words[9] = 0x1234

        # Act
        found = read_word(board, 9)

        # Assert
        self.assertEqual(found, 0x1234)

    def test_clocking_past_the_word_shifts_out_its_trailing_zeros_then_ones(self) -> None:
        # Arrange
        board = enabled()
        command(board, "10000000")
        clock_out(board, 16)

        # Act
        after = clock_out(board, 17)

        # Assert
        self.assertEqual(after, [0] * 16 + [1])

    def test_outside_a_read_the_line_idles_high(self) -> None:
        # Arrange
        board = enabled()

        # Act
        idle = data_out(board)

        # Assert
        self.assertEqual(idle, 1)


class WriteTest(unittest.TestCase):
    def test_a_write_at_power_on_is_refused(self) -> None:
        # Arrange
        board = enabled()

        # Act
        write_word(board, 3, 0xBEEF)

        # Assert
        self.assertEqual(board.eeprom.words[3], 0xFFFF)

    def test_after_ewen_a_write_lands(self) -> None:
        # Arrange
        board = enabled()
        unlock(board)

        # Act
        write_word(board, 3, 0xBEEF)

        # Assert
        self.assertEqual(read_word(board, 3), 0xBEEF)

    def test_ewds_locks_it_again(self) -> None:
        # Arrange
        board = enabled()
        unlock(board)
        command(board, "00000000")

        # Act
        write_word(board, 3, 0xBEEF)

        # Assert
        self.assertEqual(board.eeprom.words[3], 0xFFFF)

    def test_erase_sets_one_word_to_all_ones(self) -> None:
        # Arrange
        board = enabled()
        board.eeprom.words[7] = 0
        unlock(board)

        # Act
        command(board, "11000111")

        # Assert
        self.assertEqual(board.eeprom.words[7], 0xFFFF)

    def test_erase_all_sets_every_word_to_all_ones(self) -> None:
        # Arrange
        board = enabled()
        board.eeprom.words[:] = [0] * 64
        unlock(board)

        # Act
        command(board, "00100000")

        # Assert
        self.assertEqual(set(board.eeprom.words), {0xFFFF})

    def test_write_all_ands_its_value_into_every_word(self) -> None:
        # Arrange
        board = enabled()
        board.eeprom.words[1] = 0x0FF0
        unlock(board)

        # Act
        command(board, "00010000" + f"{0xFF00:016b}")

        # Assert
        self.assertEqual(board.eeprom.words[:2], [0xFF00, 0x0F00])

    def test_while_locked_erase_and_both_all_commands_change_nothing(self) -> None:
        # Arrange
        board = enabled()
        board.eeprom.words[:] = [0x1111] * 64
        command(board, "11000000")
        command(board, "00100000")

        # Act
        command(board, "00010000" + "0" * 16)

        # Assert
        self.assertEqual(set(board.eeprom.words), {0x1111})


class FramingTest(unittest.TestCase):
    def test_a_start_bit_of_zero_is_waited_through(self) -> None:
        # Arrange
        board = enabled()
        board.eeprom.words[2] = 0xA5A5
        board.write(LINES, SELECT)
        clock_in(board, "00")

        # Act
        clock_in(board, "110000010")

        # Assert
        self.assertEqual(int("".join(map(str, clock_out(board, 16))), 2), 0xA5A5)

    def test_dropping_select_in_the_middle_abandons_the_command(self) -> None:
        # Arrange
        board = enabled()
        unlock(board)
        command(board, "01000011" + "0" * 8)
        board.write(LINES, 0)

        # Act
        clock_in(board, "0" * 8)

        # Assert
        self.assertEqual(board.eeprom.words[3], 0xFFFF)

    def test_a_clock_raised_with_select_in_one_write_is_not_a_start_bit(self) -> None:
        # Arrange
        board = enabled()
        board.eeprom.words[1] = 0
        board.write(LINES, 0x01)
        board.write(LINES, SELECT | CLOCK | 0x01)
        clock_in(board, "110000001")

        # Act
        seen = clock_out(board, 16)

        # Assert
        self.assertEqual(seen, [0] * 16)

    def test_dropping_select_ends_a_read(self) -> None:
        # Arrange
        board = enabled()
        board.eeprom.words[0] = 0
        command(board, "10000000")
        clock_out(board, 1)

        # Act
        board.write(LINES, 0)

        # Assert
        self.assertEqual(data_out(board), 1)

    def test_bit_7_of_fffc_resets_it_and_locks_it(self) -> None:
        # Arrange
        board = enabled()
        unlock(board)
        board.write(0xFFFC, RESET | ENABLE)

        # Act
        write_word(board, 4, 0)

        # Assert
        self.assertEqual(board.eeprom.words[4], 0xFFFF)

    def test_a_board_reset_keeps_the_contents(self) -> None:
        # Arrange
        board = enabled()
        board.eeprom.words[5] = 0x0101

        # Act
        board.reset()

        # Assert
        self.assertEqual((board.eeprom.words[5], board.read(LINES)), (0x0101, 4))


if __name__ == "__main__":
    unittest.main()
