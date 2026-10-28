import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import smsmapper  # noqa: E402

UNIT = 0x2000


def numbered(size: int) -> bytes:
    return bytes((offset // UNIT) & 0xFF for offset in range(size))


def master_system(region: str | None = None) -> smsmapper.Console:
    return smsmapper.Console("sms", cartridge=smsmapper.Cartridge(numbered(0x40000)), region=region)


class MemoryTest(unittest.TestCase):
    def test_reads_and_writes_reach_the_cartridge_through_the_map(self) -> None:
        # Arrange
        console = master_system()

        # Act
        console.write(0xFFFF, 5)

        # Assert
        self.assertEqual((console.read(0x8000), console.read(0xFFFF)), (10, 5))

    def test_port_3e_moves_the_slot_enables(self) -> None:
        # Arrange
        console = master_system()

        # Act
        console.write_port(0x3E, 0xF8)

        # Assert
        self.assertEqual(console.read(0x0000), 0xFF)

    def test_a_card_on_a_console_without_a_card_slot_is_refused(self) -> None:
        # Arrange
        def attempt() -> object:
            return smsmapper.Console("sms2", card=smsmapper.Cartridge(bytes(0x8000)))

        # Act
        with self.assertRaises(smsmapper.SlotError) as raised:
            attempt()

        # Assert
        self.assertIn("sms2", str(raised.exception))

    def test_a_card_goes_in_the_slot_of_a_console_that_has_one(self) -> None:
        # Arrange
        card = smsmapper.Cartridge(bytes([0x33]) * 0x8000)
        console = smsmapper.Console("mark-iii", card=card)

        # Act
        console.write_port(0x3E, 0xC8)

        # Assert
        self.assertEqual(console.read(0x0000), 0x33)


class RegionTest(unittest.TestCase):
    def test_with_no_region_given_a_console_takes_its_model_s(self) -> None:
        # Arrange
        models = ("mark-iii", "sms")

        # Act
        regions = [smsmapper.Console(model).region for model in models]

        # Assert
        self.assertEqual(regions, ["japan", "usa"])


class ControllerPortTest(unittest.TestCase):
    def test_a_pressed_button_reads_low_on_port_dc(self) -> None:
        # Arrange
        console = master_system()

        # Act
        console.press("1")

        # Assert
        self.assertEqual(console.read_port(0xDC), 0xEF)

    def test_player_2_s_left_reads_low_on_port_dd(self) -> None:
        # Arrange
        console = master_system()
        console.press("left", 2)
        console.press("right", 2)

        # Act
        console.release("right", 2)

        # Assert
        self.assertEqual(console.read_port(0xDD), 0xFE)

    def test_port_3f_drives_th_and_tr(self) -> None:
        # Arrange
        console = master_system()

        # Act
        console.write_port(0x3F, 0x55)

        # Assert
        self.assertEqual(console.read_port(0xDD) & 0xC0, 0x00)

    def test_a_japanese_console_reads_its_outputs_as_0(self) -> None:
        # Arrange
        console = master_system(region="japan")

        # Act
        console.write_port(0x3F, 0xF5)

        # Assert
        self.assertEqual(console.read_port(0xDD) & 0xC0, 0x00)

    def test_with_the_joysticks_off_both_ports_read_ff(self) -> None:
        # Arrange
        console = master_system()
        console.press("up")

        # Act
        console.write_port(0x3E, 0xAC)

        # Assert
        self.assertEqual(console.read_port(0xDC), 0xFF)

    def test_th_rising_asks_the_video_part_for_a_latch(self) -> None:
        # Arrange
        console = master_system()
        console.write_port(0x3F, 0x00)

        # Act
        console.write_port(0x3F, 0x80)

        # Assert
        self.assertEqual(console.latches, 1)


class PortOwnershipTest(unittest.TestCase):
    def test_a_read_of_a_video_port_is_not_the_board_s_to_answer(self) -> None:
        # Arrange
        console = master_system()

        # Act
        with self.assertRaises(smsmapper.NotOnBoardError) as raised:
            console.read_port(0xBF)

        # Assert
        self.assertIn("vdp control", str(raised.exception))

    def test_a_write_to_the_sound_port_is_not_the_board_s_to_take(self) -> None:
        # Arrange
        console = master_system()

        # Act
        with self.assertRaises(smsmapper.NotOnBoardError) as raised:
            console.write_port(0x7F, 0x9F)

        # Assert
        self.assertIn("sound", str(raised.exception))

    def test_a_port_nothing_answers_reads_ff_and_drops_writes(self) -> None:
        # Arrange
        console = master_system()
        console.write_port(0xDC, 0x00)

        # Act
        seen = console.read_port(0x3E)

        # Assert
        self.assertEqual((seen, console.read_port(0xDC)), (0xFF, 0xFF))


class ButtonTest(unittest.TestCase):
    def test_pause_holds_the_non_maskable_line_while_pressed(self) -> None:
        # Arrange
        console = master_system()
        console.press("pause")

        # Act
        held = console.nmi

        # Assert
        self.assertTrue(held)

    def test_releasing_pause_lets_it_go(self) -> None:
        # Arrange
        console = master_system()
        console.press("pause")

        # Act
        console.release("pause")

        # Assert
        self.assertFalse(console.nmi)

    def test_reset_reads_low_on_bit_4_of_port_dd(self) -> None:
        # Arrange
        console = master_system()

        # Act
        console.press("reset")

        # Assert
        self.assertEqual(console.read_port(0xDD), 0xEF)


class GameGearTest(unittest.TestCase):
    def test_port_0_names_the_region_and_start_clears_bit_7(self) -> None:
        # Arrange
        regions = ("japan", "usa", "europe")
        consoles = [smsmapper.Console("gg", region=region) for region in regions]
        consoles[0].press("start")

        # Act
        seen = [console.read_port(0x00) for console in consoles]

        # Assert
        self.assertEqual(seen, [0x00, 0xC0, 0xE0])

    def test_start_on_a_game_gear_in_its_own_mode_raises_no_nmi(self) -> None:
        # Arrange
        console = smsmapper.Console("gg")

        # Act
        console.press("start")

        # Assert
        self.assertFalse(console.nmi)

    def test_in_master_system_mode_start_is_pause_and_port_0_is_gone(self) -> None:
        # Arrange
        console = smsmapper.Console("gg", handheld_mode=False)
        console.press("start")

        # Act
        seen = console.read_port(0x00)

        # Assert
        self.assertEqual((console.nmi, seen), (True, 0xFF))

    def test_the_registers_power_on_at_the_values_genesis_plus_gx_uses(self) -> None:
        # Arrange
        console = smsmapper.Console("gg")

        # Act
        seen = [console.read_port(port) for port in range(1, 7)]

        # Assert
        self.assertEqual(seen, [0x7F, 0xFF, 0x00, 0xFF, 0x00, 0xFF])

    def test_port_1_reads_through_port_2_s_direction_bits(self) -> None:
        # Arrange
        console = smsmapper.Console("gg")
        console.write_port(0x02, 0x0F)

        # Act
        console.write_port(0x01, 0xA5)

        # Assert
        self.assertEqual(console.read_port(0x01), 0xAF)

    def test_port_5_keeps_bits_3_to_7_and_ports_0_and_4_take_no_write(self) -> None:
        # Arrange
        console = smsmapper.Console("gg")
        console.write_port(0x00, 0x00)
        console.write_port(0x04, 0x00)

        # Act
        console.write_port(0x05, 0xFF)

        # Assert
        seen = (console.read_port(0x05), console.read_port(0x00), console.read_port(0x04))
        self.assertEqual(seen, (0xF8, 0xC0, 0xFF))

    def test_ports_3_and_6_keep_what_is_written_and_6_reads_ff(self) -> None:
        # Arrange
        console = smsmapper.Console("gg")
        console.write_port(0x06, 0x12)

        # Act
        console.write_port(0x03, 0x34)

        # Assert
        self.assertEqual((console.read_port(0x03), console.read_port(0x06)), (0x34, 0xFF))

    def test_an_unknown_region_is_refused(self) -> None:
        # Arrange
        def attempt() -> object:
            return smsmapper.Console("gg", region="brazil")

        # Act
        with self.assertRaises(smsmapper.UnknownRegionError) as raised:
            attempt()

        # Assert
        self.assertIn("brazil", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
