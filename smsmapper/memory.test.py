import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import smsmapper  # noqa: E402
from smsmapper import memory  # noqa: E402

UNIT = 0x2000


def filled(value: int, size: int = 0x8000) -> smsmapper.Board:
    return smsmapper.Cartridge(bytes([value]) * size)


def numbered(size: int) -> bytes:
    return bytes((offset // UNIT) & 0xFF for offset in range(size))


class PowerOnTest(unittest.TestCase):
    def test_with_no_bios_the_cartridge_ram_and_joysticks_are_on(self) -> None:
        # Arrange
        cartridge = filled(0x11)

        # Act
        bus = memory.Memory(cartridge=cartridge)

        # Assert
        self.assertEqual((bus.control, bus.read(0x0000)), (0xA8, 0x11))

    def test_with_a_bios_the_bios_ram_and_joysticks_are_on(self) -> None:
        # Arrange
        bios = filled(0x22, 0x2000)

        # Act
        bus = memory.Memory(cartridge=filled(0x11), bios=bios)

        # Assert
        self.assertEqual((bus.control, bus.read(0x0000)), (0xE0, 0x22))


class EnableTest(unittest.TestCase):
    def test_bit_6_clear_selects_the_cartridge(self) -> None:
        # Arrange
        bus = memory.Memory(cartridge=filled(0x11), bios=filled(0x22, 0x2000))

        # Act
        bus.control = 0xA8

        # Assert
        self.assertEqual(bus.read(0x4000), 0x11)

    def test_bit_5_clear_selects_the_card(self) -> None:
        # Arrange
        bus = memory.Memory(cartridge=filled(0x11), card=filled(0x33))

        # Act
        bus.control = 0xC8

        # Assert
        self.assertEqual(bus.read(0x4000), 0x33)

    def test_bit_7_clear_selects_the_expansion_slot(self) -> None:
        # Arrange
        bus = memory.Memory(cartridge=filled(0x11), expansion=filled(0x44))

        # Act
        bus.control = 0x68

        # Assert
        self.assertEqual(bus.read(0x4000), 0x44)

    def test_with_every_rom_off_the_bus_reads_ff(self) -> None:
        # Arrange
        bus = memory.Memory(cartridge=filled(0x11), bios=filled(0x22, 0x2000))

        # Act
        bus.control = 0xF8

        # Assert
        self.assertEqual(bus.read(0x8000), 0xFF)

    def test_an_enabled_slot_holding_nothing_reads_ff(self) -> None:
        # Arrange
        bus = memory.Memory()

        # Act
        shown = bus.read(0x0000)

        # Assert
        self.assertEqual(shown, 0xFF)

    def test_the_cartridge_wins_over_the_bios_when_both_are_on(self) -> None:
        # Arrange
        bus = memory.Memory(cartridge=filled(0x11), bios=filled(0x22, 0x2000))

        # Act
        bus.control = 0xA0

        # Assert
        self.assertEqual(bus.read(0x0000), 0x11)

    def test_a_write_reaches_only_the_selected_slot(self) -> None:
        # Arrange
        cartridge = smsmapper.Cartridge(numbered(0x40000))
        bios = smsmapper.Cartridge(numbered(0x40000))
        bus = memory.Memory(cartridge=cartridge, bios=bios)

        # Act
        bus.write(0xFFFF, 5)

        # Assert
        self.assertEqual((bios.banks[2], cartridge.banks[2]), (5, 2))

    def test_with_every_rom_off_a_write_reaches_no_slot(self) -> None:
        # Arrange
        cartridge = smsmapper.Cartridge(numbered(0x40000))
        bus = memory.Memory(cartridge=cartridge)
        bus.control = 0xF8

        # Act
        bus.write(0xFFFF, 5)

        # Assert
        self.assertEqual(cartridge.banks[2], 2)


class RamTest(unittest.TestCase):
    def test_8k_of_ram_sits_at_c000_and_again_at_e000(self) -> None:
        # Arrange
        bus = memory.Memory(cartridge=filled(0x11))

        # Act
        bus.write(0xC123, 0x5A)

        # Assert
        self.assertEqual((bus.read(0xC123), bus.read(0xE123)), (0x5A, 0x5A))

    def test_a_paging_register_write_also_lands_in_ram(self) -> None:
        # Arrange
        cartridge = smsmapper.Cartridge(numbered(0x40000))
        bus = memory.Memory(cartridge=cartridge)

        # Act
        bus.write(0xFFFF, 6)

        # Assert
        self.assertEqual((bus.read(0xDFFF), cartridge.banks[2]), (6, 6))

    def test_bit_4_set_turns_the_ram_off(self) -> None:
        # Arrange
        bus = memory.Memory(cartridge=filled(0x11))
        bus.write(0xC000, 0x5A)
        bus.control = 0xB8

        # Act
        bus.write(0xC000, 0x77)

        # Assert
        self.assertEqual((bus.read(0xC000), bus.ram[0]), (0xFF, 0x5A))

    def test_with_the_ram_off_a_register_write_still_reaches_the_cartridge(self) -> None:
        # Arrange
        cartridge = smsmapper.Cartridge(numbered(0x40000))
        bus = memory.Memory(cartridge=cartridge)
        bus.control = 0xB8

        # Act
        bus.write(0xFFFF, 3)

        # Assert
        self.assertEqual(cartridge.banks[2], 3)


if __name__ == "__main__":
    unittest.main()
