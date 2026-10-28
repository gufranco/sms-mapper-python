import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import smsmapper  # noqa: E402


class BaseTest(unittest.TestCase):
    def test_a_bare_board_keeps_the_image_and_holds_no_registers(self) -> None:
        # Arrange
        image = bytes(range(256)) * 4

        # Act
        board = smsmapper.Board(image)

        # Assert
        self.assertEqual((board.image, board.pages, len(board.ram)), (image, 1, 0))

    def test_a_bare_board_answers_no_read(self) -> None:
        # Arrange
        board = smsmapper.Board(bytes(0x4000))

        # Act
        with self.assertRaises(NotImplementedError) as raised:
            board.read(0)

        # Assert
        self.assertIsInstance(raised.exception, NotImplementedError)

    def test_a_bare_board_takes_no_write(self) -> None:
        # Arrange
        board = smsmapper.Board(bytes(0x4000))

        # Act
        with self.assertRaises(NotImplementedError) as raised:
            board.write(0xFFFF, 1)

        # Assert
        self.assertIsInstance(raised.exception, NotImplementedError)

    def test_a_bare_board_names_no_banks(self) -> None:
        # Arrange
        board = smsmapper.Board(bytes(0x4000))

        # Act
        with self.assertRaises(NotImplementedError) as raised:
            _ = board.banks

        # Assert
        self.assertIsInstance(raised.exception, NotImplementedError)


class BareDecodeTest(unittest.TestCase):
    def test_a_bare_board_names_no_register(self) -> None:
        # Arrange
        board = smsmapper.Board(bytes(0x4000))

        # Act
        with self.assertRaises(NotImplementedError) as raised:
            board.decodes(0xFFFF)

        # Assert
        self.assertIsInstance(raised.exception, NotImplementedError)


if __name__ == "__main__":
    unittest.main()
