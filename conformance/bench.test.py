import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from conformance import bench  # noqa: E402


class RecordTest(unittest.TestCase):
    def test_the_facts_and_the_unstated_values_come_from_one_record(self) -> None:
        # Arrange
        held = bench.HELD

        # Act
        parts = (bench.FACTS is held["facts"], bench.UNSTATED is held["notStated"])

        # Assert
        self.assertEqual(parts, (True, True))


class HelperTest(unittest.TestCase):
    def test_a_numbered_image_holds_each_8k_unit_s_own_number(self) -> None:
        # Arrange
        size = 0x8000

        # Act
        image = bench.numbered(size)

        # Assert
        self.assertEqual([image[offset] for offset in range(0, size, 0x2000)], [0, 1, 2, 3])

    def test_a_hexadecimal_address_is_read_as_a_number(self) -> None:
        # Arrange
        text = "FFFC"

        # Act
        found = bench.hexadecimal(text)

        # Assert
        self.assertEqual(found, 0xFFFC)


if __name__ == "__main__":
    unittest.main()
