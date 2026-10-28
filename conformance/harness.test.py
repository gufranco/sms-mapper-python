import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from conformance import harness  # noqa: E402

LOOP = bytes([0x18, 0xFE])


def program(code: bytes, size: int = 0x8000) -> bytes:
    return code + bytes(size - len(code))


def paging(*writes: tuple[int, int]) -> bytes:
    code = b"".join(
        bytes([0x3E, value, 0x32, address & 0xFF, address >> 8]) for address, value in writes
    )
    return code + LOOP


class VideoTest(unittest.TestCase):
    def test_a_frame_takes_262_lines_of_228_states(self) -> None:
        # Arrange
        video = harness.Video()

        # Act
        ended = [video.advance(228 * 262 - 1), video.advance(1)]

        # Assert
        self.assertEqual(ended, [False, True])

    def test_the_frame_flag_rises_at_line_192_and_a_status_read_clears_it(self) -> None:
        # Arrange
        video = harness.Video()
        video.advance(228 * 192)

        # Act
        status = [video.read(harness.STATUS), video.read(harness.STATUS)]

        # Assert
        self.assertEqual([one & 0x80 for one in status], [0x80, 0x00])

    def test_the_frame_interrupt_asks_only_when_register_1_enables_it(self) -> None:
        # Arrange
        video = harness.Video()
        video.advance(228 * 192)
        asked_before = video.irq

        # Act
        for byte in (0x20, 0x81):
            video.write(harness.CONTROL, byte)

        # Assert
        self.assertEqual((asked_before, video.irq), (False, True))

    def test_the_line_counter_asks_when_register_0_enables_it(self) -> None:
        # Arrange
        video = harness.Video()
        for byte in (0x10, 0x80, 0x00, 0x8A):
            video.write(harness.CONTROL, byte)

        # Act
        video.advance(228 * 2)

        # Assert
        self.assertEqual(video.irq, True)

    def test_a_line_reload_of_2_asks_again_on_every_third_line(self) -> None:
        # Arrange
        video = harness.Video()
        for byte in (0x10, 0x80, 0x02, 0x8A):
            video.write(harness.CONTROL, byte)
        video.advance(228)
        video.read(harness.STATUS)

        # Act
        asked = []
        for _ in range(3):
            video.advance(228)
            asked.append(video.irq)

        # Assert
        self.assertEqual(asked, [False, False, True])

    def test_a_data_port_access_breaks_the_control_pair(self) -> None:
        # Arrange
        video = harness.Video()
        video.write(harness.CONTROL, 0x20)
        video.write(harness.DATA, 0x00)

        # Act
        video.write(harness.CONTROL, 0x81)

        # Assert
        self.assertEqual(video.registers[1], 0x00)

    def test_the_v_counter_jumps_back_after_line_da(self) -> None:
        # Arrange
        video = harness.Video()

        # Act
        seen = []
        for line in (0x00, 0xDA, 0xDB, 0x105):
            video.advance(228 * line - video.states)
            seen.append(video.read(harness.V_COUNTER))

        # Assert
        self.assertEqual(seen, [0x00, 0xDA, 0xD5, 0xFF])

    def test_a_pal_frame_takes_313_lines(self) -> None:
        # Arrange
        video = harness.Video(pal=True)

        # Act
        ended = [video.advance(228 * 313 - 1), video.advance(1)]

        # Assert
        self.assertEqual(ended, [False, True])

    def test_the_pal_v_counter_jumps_back_after_line_f2(self) -> None:
        # Arrange
        video = harness.Video(pal=True)

        # Act
        seen = []
        for line in (0x00, 0xF2, 0xF3, 312):
            video.advance(228 * line - video.states)
            seen.append(video.read(harness.V_COUNTER))

        # Assert
        self.assertEqual(seen, [0x00, 0xF2, 0xBA, 0xFF])

    def test_the_h_counter_and_the_data_port_read_0(self) -> None:
        # Arrange
        video = harness.Video()

        # Act
        seen = (video.read(harness.H_COUNTER), video.read(harness.DATA))

        # Assert
        self.assertEqual(seen, (0, 0))


class VideoMemoryTest(unittest.TestCase):
    def test_a_write_address_and_data_writes_land_in_video_memory(self) -> None:
        # Arrange
        video = harness.Video()
        video.write(harness.CONTROL, 0x00)
        video.write(harness.CONTROL, 0x78)

        # Act
        for value in (0x41, 0x01):
            video.write(harness.DATA, value)

        # Assert
        self.assertEqual(bytes(video.vram[0x3800:0x3802]), bytes([0x41, 0x01]))

    def test_a_read_address_fills_the_buffer_the_next_read_returns(self) -> None:
        # Arrange
        video = harness.Video()
        video.vram[0x0123] = 0x5A
        video.write(harness.CONTROL, 0x23)
        video.write(harness.CONTROL, 0x01)

        # Act
        seen = video.read(harness.DATA)

        # Assert
        self.assertEqual(seen, 0x5A)

    def test_a_colour_write_moves_the_address_without_touching_video_memory(self) -> None:
        # Arrange
        video = harness.Video()
        video.write(harness.CONTROL, 0x00)
        video.write(harness.CONTROL, 0xC0)

        # Act
        video.write(harness.DATA, 0x3F)

        # Assert
        self.assertEqual((video.vram[0], video.address), (0, 1))

    def test_the_screen_reads_the_name_table_as_text_at_an_offset(self) -> None:
        # Arrange
        video = harness.Video()
        video.registers[2] = 0xFF
        for column, letter in enumerate("OK"):
            video.vram[0x3800 + column * 2] = ord(letter) - 0x20

        # Act
        rows = harness.screen(video, -0x20)

        # Assert
        self.assertEqual((len(rows), rows[0][:2]), (24, "OK"))

    def test_a_tile_outside_printable_text_reads_as_a_space(self) -> None:
        # Arrange
        video = harness.Video()
        video.registers[2] = 0xFF
        video.vram[0x3801] = 0x01

        # Act
        rows = harness.screen(video, 0)

        # Assert
        self.assertEqual(rows[0][0], " ")


class RunTest(unittest.TestCase):
    def test_it_says_why_it_cannot_run_without_the_processor(self) -> None:
        # Arrange
        where = Path("/nowhere")

        # Act
        said = harness.why_not(where)

        # Assert
        self.assertIn("git submodule update", str(said))

    def test_with_the_processor_there_nothing_stops_it(self) -> None:
        # Arrange
        where = harness.PROCESSOR

        # Act
        said = harness.why_not(where)

        # Assert
        self.assertIsNone(said)

    def test_a_write_to_a_register_of_the_board_is_counted_where_it_landed(self) -> None:
        # Arrange
        run = harness.Run(program(paging((0xFFFF, 5), (0xFFFE, 4)), 0x40000))

        # Act
        run.run_frames(1)

        # Assert
        self.assertEqual(
            (dict(run.seen.writes), run.seen.banks), ({0xFFFF: 1, 0xFFFE: 1}, {0, 1, 4, 5})
        )

    def test_a_write_selecting_past_the_end_of_the_image_is_counted(self) -> None:
        # Arrange
        run = harness.Run(program(paging((0xFFFF, 0x21)), 0x40000))

        # Act
        run.run_frames(1)

        # Assert
        self.assertEqual(run.seen.wrapped, 1)

    def test_fffc_bits_are_gathered(self) -> None:
        # Arrange
        run = harness.Run(program(paging((0xFFFC, 0x08), (0xFFFC, 0x11))))

        # Act
        run.run_frames(1)

        # Assert
        self.assertEqual(run.seen.control_bits, 0x19)

    def test_a_write_outside_the_board_s_registers_is_not_counted(self) -> None:
        # Arrange
        run = harness.Run(program(paging((0xC000, 1))))

        # Act
        run.run_frames(1)

        # Assert
        self.assertEqual(dict(run.seen.writes), {})

    def test_the_slot_and_controller_port_settings_are_counted(self) -> None:
        # Arrange
        code = bytes([0x3E, 0xA8, 0xD3, 0x3E, 0x3E, 0xF5, 0xD3, 0x3F, 0xDB, 0xDD]) + LOOP
        run = harness.Run(program(code))

        # Act
        run.run_frames(1)

        # Assert
        self.assertEqual(
            (dict(run.seen.memory_control), dict(run.seen.io_control)), ({0xA8: 1}, {0xF5: 1})
        )

    def test_the_video_and_sound_ports_reach_the_stand_in(self) -> None:
        # Arrange
        code = bytes([0x3E, 0x9F, 0xD3, 0x7F, 0xDB, 0xBF, 0xDB, 0x7E, 0xD3, 0xBE]) + LOOP
        run = harness.Run(program(code))

        # Act
        run.run_frames(1)

        # Assert
        self.assertEqual(run.seen.sound, 1)

    def test_a_game_gear_image_reaches_its_own_ports(self) -> None:
        # Arrange
        code = bytes([0xDB, 0x00, 0xD3, 0x06]) + LOOP
        run = harness.Run(program(code), model="gg")

        # Act
        run.run_frames(1)

        # Assert
        self.assertEqual(sorted(run.seen.handheld_ports), [0, 6])

    def test_a_master_system_starts_where_the_export_boot_program_hands_over(self) -> None:
        # Arrange
        image = program(LOOP)

        # Act
        run = harness.Run(image)

        # Assert
        self.assertEqual((run.cpu.registers.sp, run.console.read(0xC000)), (0xDFF0, 0xA8))

    def test_a_game_gear_starts_from_its_reset_values(self) -> None:
        # Arrange
        image = program(LOOP)

        # Act
        run = harness.Run(image, model="gg")

        # Assert
        self.assertEqual(run.console.read(0xC000), 0x00)

    def test_a_run_takes_the_console_s_region(self) -> None:
        # Arrange
        image = program(LOOP)

        # Act
        run = harness.Run(image, region="japan")

        # Assert
        self.assertEqual(run.console.region, "japan")

    def test_a_european_master_system_runs_pal_frames_and_a_game_gear_never_does(self) -> None:
        # Arrange
        image = program(LOOP)

        # Act
        found = [
            harness.Run(image, model=model, region=region).video.lines
            for model, region in (("sms", "europe"), ("sms", "usa"), ("gg", "europe"))
        ]

        # Assert
        self.assertEqual(found, [313, 262, 262])

    def test_frames_are_counted_as_the_video_ends_them(self) -> None:
        # Arrange
        run = harness.Run(program(LOOP))

        # Act
        run.run_frames(3)

        # Assert
        self.assertEqual(run.frames, 3)

    def test_an_image_on_another_board_runs_on_it(self) -> None:
        # Arrange
        run = harness.Run(program(paging((0x8000, 6)), 0x40000), board="codemasters")

        # Act
        run.run_frames(1)

        # Assert
        self.assertEqual((dict(run.seen.writes), run.board.banks), ({0x8000: 1}, (0, 1, 6)))

    def test_the_frame_interrupt_reaches_the_processor(self) -> None:
        # Arrange
        image = bytearray(
            program(
                bytes([0x3E, 0x20, 0xD3, 0xBF, 0x3E, 0x81, 0xD3, 0xBF, 0xED, 0x56, 0xFB]) + LOOP
            )
        )
        image[0x38:0x3A] = bytes([0x18, 0xFE])
        run = harness.Run(bytes(image))

        # Act
        run.run_frames(1)

        # Assert
        self.assertEqual(run.cpu.registers.pc, 0x38)


if __name__ == "__main__":
    unittest.main()
