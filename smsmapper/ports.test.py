import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from smsmapper import ports  # noqa: E402


class ManualPortsTest(unittest.TestCase):
    def test_the_eight_ports_the_manual_lists_reach_their_devices(self) -> None:
        # Arrange
        listed = {
            (0x3E, ports.WRITE): ports.MEMORY_CONTROL,
            (0x3F, ports.WRITE): ports.IO_CONTROL,
            (0x7E, ports.READ): ports.V_COUNTER,
            (0x7F, ports.READ): ports.H_COUNTER,
            (0x7F, ports.WRITE): ports.SOUND,
            (0xBE, ports.READ): ports.VDP_DATA,
            (0xBF, ports.WRITE): ports.VDP_CONTROL,
            (0xDC, ports.READ): ports.PORT_A,
            (0xDD, ports.READ): ports.PORT_B,
        }

        # Act
        found = {key: ports.decode("sms", *key) for key in listed}

        # Assert
        self.assertEqual(found, listed)


class MirrorTest(unittest.TestCase):
    def test_only_a7_a6_and_a0_decide_the_device(self) -> None:
        # Arrange
        pairs = [(0x00, 0x3E), (0x41, 0x7F), (0x80, 0xBE), (0xC1, 0xDD), (0xFF, 0xDD)]

        # Act
        found = [
            ports.decode("sms", one, ports.READ) == ports.decode("sms", two, ports.READ)
            for one, two in pairs
        ]

        # Assert
        self.assertEqual(found, [True] * len(pairs))

    def test_the_upper_address_byte_is_ignored(self) -> None:
        # Arrange
        port = 0x12BF

        # Act
        found = ports.decode("sms", port, ports.WRITE)

        # Assert
        self.assertEqual(found, ports.VDP_CONTROL)

    def test_the_control_ports_answer_no_read_and_the_controller_ports_no_write(self) -> None:
        # Arrange
        asked = [(0x3E, ports.READ), (0x3F, ports.READ), (0xDC, ports.WRITE), (0xDD, ports.WRITE)]

        # Act
        found = [ports.decode("sms", port, direction) for port, direction in asked]

        # Assert
        self.assertEqual(found, [ports.NOTHING] * 4)

    def test_the_counters_and_the_sound_share_40_to_7f_by_direction(self) -> None:
        # Arrange
        asked = [(0x40, ports.READ), (0x41, ports.READ), (0x40, ports.WRITE), (0x41, ports.WRITE)]

        # Act
        found = [ports.decode("sms", port, direction) for port, direction in asked]

        # Assert
        self.assertEqual(found, [ports.V_COUNTER, ports.H_COUNTER, ports.SOUND, ports.SOUND])

    def test_the_vdp_ports_answer_both_ways(self) -> None:
        # Arrange
        asked = [(0x80, ports.WRITE), (0x81, ports.READ)]

        # Act
        found = [ports.decode("sms", port, direction) for port, direction in asked]

        # Assert
        self.assertEqual(found, [ports.VDP_DATA, ports.VDP_CONTROL])


class GameGearTest(unittest.TestCase):
    def test_ports_0_to_6_reach_the_game_gear_s_own_registers(self) -> None:
        # Arrange
        numbers = range(7)

        # Act
        found = [ports.decode("gg", number, ports.READ) for number in numbers]

        # Assert
        self.assertEqual(found, [f"{ports.HANDHELD}{number}" for number in numbers])

    def test_port_7_falls_back_to_the_master_system_decode(self) -> None:
        # Arrange
        port = 0x07

        # Act
        found = ports.decode("gg", port, ports.WRITE)

        # Assert
        self.assertEqual(found, ports.IO_CONTROL)

    def test_a_master_system_has_no_port_6(self) -> None:
        # Arrange
        port = 0x06

        # Act
        found = ports.decode("sms2", port, ports.WRITE)

        # Assert
        self.assertEqual(found, ports.MEMORY_CONTROL)


if __name__ == "__main__":
    unittest.main()
