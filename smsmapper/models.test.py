import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import smsmapper  # noqa: E402
from smsmapper import models  # noqa: E402


class CatalogueTest(unittest.TestCase):
    def test_it_holds_the_mark_iii_both_master_systems_and_the_game_gear(self) -> None:
        # Arrange
        expected = ["gg", "mark-iii", "sms", "sms2"]

        # Act
        named = sorted(smsmapper.MODELS)

        # Assert
        self.assertEqual(named, expected)

    def test_every_alias_finds_its_model(self) -> None:
        # Arrange
        pairs = [
            (alias, model.name) for model in smsmapper.MODELS.values() for alias in model.aliases
        ]

        # Act
        found = [(alias, models.lookup(alias).name) for alias, _ in pairs]

        # Assert
        self.assertEqual(found, pairs)

    def test_a_name_is_found_whatever_its_case(self) -> None:
        # Arrange
        asked = "Game Gear"

        # Act
        found = models.lookup(asked)

        # Assert
        self.assertEqual(found.name, "gg")

    def test_no_name_means_the_master_system(self) -> None:
        # Arrange
        asked = None

        # Act
        found = models.lookup(asked)

        # Assert
        self.assertEqual(found.name, "sms")

    def test_an_unknown_name_is_refused_with_the_names_there_are(self) -> None:
        # Arrange
        asked = "mega-drive"

        # Act
        with self.assertRaises(smsmapper.UnknownModelError) as raised:
            models.lookup(asked)

        # Assert
        self.assertIn("sms2", str(raised.exception))


class WhatDiffersTest(unittest.TestCase):
    def test_the_mark_iii_was_sold_in_japan_and_the_rest_default_to_the_usa(self) -> None:
        # Arrange
        catalogue = smsmapper.MODELS

        # Act
        regions = {name: model.region for name, model in catalogue.items()}

        # Assert
        self.assertEqual(regions, {"mark-iii": "japan", "sms": "usa", "sms2": "usa", "gg": "usa"})

    def test_only_the_first_master_system_and_the_mark_iii_carry_a_card_slot(self) -> None:
        # Arrange
        catalogue = smsmapper.MODELS

        # Act
        carded = sorted(name for name, model in catalogue.items() if model.card_slot)

        # Assert
        self.assertEqual(carded, ["mark-iii", "sms"])

    def test_only_the_game_gear_answers_ports_0_to_6(self) -> None:
        # Arrange
        catalogue = smsmapper.MODELS

        # Act
        handheld = [name for name, model in catalogue.items() if model.handheld]

        # Assert
        self.assertEqual(handheld, ["gg"])

    def test_only_the_first_master_system_has_a_reset_button(self) -> None:
        # Arrange
        catalogue = smsmapper.MODELS

        # Act
        with_reset = [name for name, model in catalogue.items() if model.reset_button]

        # Assert
        self.assertEqual(with_reset, ["sms"])

    def test_the_mark_iii_starts_with_th_driven_high_and_the_rest_with_every_line_an_input(
        self,
    ) -> None:
        # Arrange
        catalogue = smsmapper.MODELS

        # Act
        starts = {name: model.io_control for name, model in catalogue.items()}

        # Assert
        self.assertEqual(starts, {"mark-iii": 0xF5, "sms": 0xFF, "sms2": 0xFF, "gg": 0xFF})


if __name__ == "__main__":
    unittest.main()
