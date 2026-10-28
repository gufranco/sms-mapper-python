import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from smsmapper import controllers  # noqa: E402


def export() -> controllers.Controllers:
    return controllers.Controllers(0xFF, japan=False, reset_button=True)


class ReleasedTest(unittest.TestCase):
    def test_with_nothing_pressed_both_ports_read_all_ones(self) -> None:
        # Arrange
        pads = export()

        # Act
        seen = (pads.read_a(), pads.read_b())

        # Assert
        self.assertEqual(seen, (0xFF, 0xFF))


class ManualBitsTest(unittest.TestCase):
    def test_each_button_clears_the_bit_the_manual_gives_it(self) -> None:
        # Arrange
        table = {
            (1, "up"): ("a", 0),
            (1, "down"): ("a", 1),
            (1, "left"): ("a", 2),
            (1, "right"): ("a", 3),
            (1, "1"): ("a", 4),
            (1, "2"): ("a", 5),
            (2, "up"): ("a", 6),
            (2, "down"): ("a", 7),
            (2, "left"): ("b", 0),
            (2, "right"): ("b", 1),
            (2, "1"): ("b", 2),
            (2, "2"): ("b", 3),
        }

        # Act
        found = {key: cleared(*key) for key in table}

        # Assert
        self.assertEqual(found, table)

    def test_the_reset_button_clears_bit_4_of_port_b(self) -> None:
        # Arrange
        pads = export()

        # Act
        pads.press("reset")

        # Assert
        self.assertEqual(pads.read_b(), 0xEF)

    def test_a_console_without_a_reset_button_never_clears_it(self) -> None:
        # Arrange
        pads = controllers.Controllers(0xFF, japan=False, reset_button=False)

        # Act
        pads.press("reset")

        # Assert
        self.assertEqual(pads.read_b(), 0xFF)

    def test_releasing_a_button_sets_its_bit_again(self) -> None:
        # Arrange
        pads = export()
        pads.press("up", 1)

        # Act
        pads.release("up", 1)

        # Assert
        self.assertEqual(pads.read_a(), 0xFF)


def cleared(player: int, button: str) -> tuple[str, int]:
    pads = export()
    pads.press(button, player)
    found = [
        (port, (0xFF ^ value).bit_length() - 1)
        for port, value in (("a", pads.read_a()), ("b", pads.read_b()))
        if value != 0xFF
    ]
    return found[0]


class IoControlTest(unittest.TestCase):
    def test_th_and_tr_set_as_outputs_read_back_the_levels_written(self) -> None:
        # Arrange
        pads = export()

        # Act
        pads.write_control(0b0101_0000)

        # Assert
        self.assertEqual((pads.read_a() & 0x20, pads.read_b() & 0xC8), (0x20, 0x08))

    def test_port_a_th_follows_bit_5_and_port_b_th_bit_7(self) -> None:
        # Arrange
        pads = export()

        # Act
        pads.write_control(0b1010_0000)

        # Assert
        self.assertEqual(pads.read_b() & 0xC0, 0xC0)

    def test_lines_left_as_inputs_read_the_controller(self) -> None:
        # Arrange
        pads = export()
        pads.press("2", 1)

        # Act
        pads.write_control(0b0000_1111)

        # Assert
        self.assertEqual(pads.read_a(), 0xDF)

    def test_a_japanese_console_reads_every_output_as_0(self) -> None:
        # Arrange
        pads = controllers.Controllers(0xFF, japan=True, reset_button=False)

        # Act
        pads.write_control(0xF0)

        # Assert
        self.assertEqual((pads.read_a() & 0x20, pads.read_b() & 0xC8), (0x00, 0x00))


class LatchTest(unittest.TestCase):
    def test_th_rising_on_either_port_asks_for_a_counter_latch(self) -> None:
        # Arrange
        pads = export()
        pads.write_control(0x00)
        pads.write_control(0x20)
        pads.write_control(0x00)

        # Act
        pads.write_control(0x80)

        # Assert
        self.assertEqual(pads.latches, 2)

    def test_th_staying_high_asks_for_nothing_more(self) -> None:
        # Arrange
        pads = export()

        # Act
        pads.write_control(0xA0)

        # Assert
        self.assertEqual(pads.latches, 0)


if __name__ == "__main__":
    unittest.main()
