import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import smsmapper  # noqa: E402
from conformance.bench import FACTS, hexadecimal, numbered  # noqa: E402
from smsmapper import ports  # noqa: E402

ENABLE_BITS = {"bios": 0x08, "ram": 0x10, "card": 0x20, "cartridge": 0x40, "expansion": 0x80}


def mark_iii(
    cartridge: smsmapper.Board | None = None,
    bios: smsmapper.Board | None = None,
    card: smsmapper.Board | None = None,
) -> smsmapper.Console:
    return smsmapper.Console("mark-iii", cartridge=cartridge, bios=bios, card=card)


class MemoryMapTest(unittest.TestCase):
    def test_at_power_on_the_boot_rom_is_at_0000_and_ram_at_c000(self) -> None:
        # Arrange
        fact = FACTS["powerOnMap"]["value"]
        bios = smsmapper.Cartridge(bytes([0x31]) * fact["size"])
        console = mark_iii(bios=bios, cartridge=smsmapper.Cartridge(bytes(0x8000)))
        console.write(hexadecimal(fact["ram"]), 0x5A)

        # Act
        seen = (console.read(hexadecimal(fact["rom"])), console.read(hexadecimal(fact["ram"])))

        # Assert
        self.assertEqual(seen, (0x31, 0x5A))

    def test_the_ram_answers_at_both_places_the_manual_names(self) -> None:
        # Arrange
        places = [hexadecimal(span.split("-")[0]) for span in FACTS["ramMirror"]["value"]]
        console = mark_iii(cartridge=smsmapper.Cartridge(bytes(0x8000)))

        # Act
        console.write(places[0] + 0x123, 0x77)

        # Assert
        self.assertEqual([console.read(place + 0x123) for place in places], [0x77, 0x77])

    def test_each_enable_bit_of_port_3e_turns_its_slot_off_when_set(self) -> None:
        # Arrange
        named = FACTS["memoryEnables"]["value"]
        bits = {name: 1 << int(bit) for bit, name in named.items() if bit.isdigit()}
        slots = {"bios": 0x11, "card": 0x22, "cartridge": 0x33}
        console = mark_iii(
            **{name: smsmapper.Cartridge(bytes([v]) * 0x8000) for name, v in slots.items()}
        )
        everything_off = 0xFF & ~bits["ram"]

        # Act
        seen = {name: read_with(console, everything_off & ~bits[name]) for name in slots}

        # Assert
        self.assertEqual((seen, bits), (slots, {**ENABLE_BITS, "joysticks": 0x04}))


class PagingTest(unittest.TestCase):
    def test_a_write_to_a_paging_register_is_duplicated_in_ram(self) -> None:
        # Arrange
        register = hexadecimal(FACTS["bankRegisterEcho"]["value"])
        console = mark_iii(cartridge=smsmapper.Cartridge(numbered(0x40000)))

        # Act
        console.write(register, 6)

        # Assert
        self.assertEqual((console.read(register), console.read(0x8000) // 2), (6, 6))

    def test_fffd_to_ffff_select_frames_0_to_2(self) -> None:
        # Arrange
        frames = FACTS["frameRegisters"]["value"]
        board = smsmapper.Cartridge(numbered(0x40000))

        # Act
        for register, frame in frames.items():
            board.write(hexadecimal(register), 4 + frame)

        # Assert
        self.assertEqual(board.banks, (4, 5, 6))

    def test_a_board_starts_with_the_values_the_system_rom_sets(self) -> None:
        # Arrange
        values = FACTS["powerOnRegisters"]["value"]

        # Act
        board = smsmapper.Cartridge(numbered(0x40000))

        # Assert
        expected = tuple(values[register] for register in ("FFFD", "FFFE", "FFFF"))
        self.assertEqual((board.banks, values["FFFC"]), (expected, 0))

    def test_fffc_bit_3_swaps_frame_2_for_ram_and_bit_2_picks_its_bank(self) -> None:
        # Arrange
        bits = {meaning: 1 << int(bit) for bit, meaning in FACTS["frameTwoRam"]["value"].items()}
        board = smsmapper.Cartridge(numbered(0x40000), ram=0x8000)
        board.write(0xFFFC, bits["RAM in frame 2"])
        board.write(0x8000, 0x11)
        board.write(0xFFFC, bits["RAM in frame 2"] | bits["RAM bank"])

        # Act
        board.write(0x8000, 0x22)

        # Assert
        self.assertEqual((board.ram[0], board.ram[0x4000]), (0x11, 0x22))

    def test_the_bank_shift_adds_eight_banks_per_step(self) -> None:
        # Arrange
        shift = FACTS["bankShift"]["value"]
        board = smsmapper.Cartridge(numbered(0x80000))
        board.write(0xFFFF, 1)

        # Act
        board.write(0xFFFC, 1 << shift["bits"][0])

        # Assert
        self.assertEqual(board.banks[2], 1 + shift["adds"])

    def test_the_first_1k_never_moves(self) -> None:
        # Arrange
        size = FACTS["fixedFirstKilobyte"]["value"]
        board = smsmapper.Cartridge(numbered(0x40000))

        # Act
        board.write(0xFFFD, 9)

        # Assert
        self.assertEqual((board.read(size - 1), board.read(size) // 2), (0, 9))


class PortTest(unittest.TestCase):
    def test_the_eight_ports_reach_what_the_manual_names(self) -> None:
        # Arrange
        listed = FACTS["ports"]["value"]
        ways = {"in": ports.READ, "out": ports.WRITE}

        # Act
        found = {
            port: {way: ports.decode("mark-iii", int(port, 16), ways[way]) for way in names}
            for port, names in listed.items()
        }

        # Assert
        self.assertEqual(found, listed)

    def test_each_controller_line_reads_on_the_bit_the_manual_gives(self) -> None:
        # Arrange
        table = FACTS["controllerBits"]["value"]
        console = smsmapper.Console("sms", cartridge=smsmapper.Cartridge(bytes(0x8000)))

        # Act
        seen = {
            port: [line_bit(console, port, line) for line in lines] for port, lines in table.items()
        }

        # Assert
        self.assertEqual(seen, {port: list(range(len(lines))) for port, lines in table.items()})

    def test_port_3f_bits_1_and_3_make_th_an_output_driven_by_bits_5_and_7(self) -> None:
        # Arrange
        lines = FACTS["strobeLines"]["value"]
        console = smsmapper.Console("sms", cartridge=smsmapper.Cartridge(bytes(0x8000)))
        inputs = 0x0F & ~sum(1 << bit for bit in lines["directions"])

        # Act
        console.write_port(0x3F, inputs)

        # Assert
        self.assertEqual(console.read_port(0xDD) & 0xC0, 0x00)


def read_with(console: smsmapper.Console, enables: int) -> int:
    console.write_port(0x3E, enables)
    return console.read(0x0000)


BUTTONS = {"up": "up", "down": "down", "left": "left", "right": "right", "SW1": "1", "SW2": "2"}


def line_bit(console: smsmapper.Console, port: str, line: str) -> int:
    name, button = line.split("-") if "-" in line else ("", "RESET")
    player = 2 if name == "P2" or (port == "DD" and button == "SW2") else 1
    pressed = "reset" if button.startswith("RESET") else BUTTONS[button]
    console.press(pressed, player)
    value = console.read_port(int(port, 16))
    console.release(pressed, player)
    return (0xFF ^ value).bit_length() - 1


if __name__ == "__main__":
    unittest.main()
