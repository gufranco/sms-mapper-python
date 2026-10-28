from __future__ import annotations

from smsmapper.errors import UnknownModelError

ALL_INPUTS = 0xFF

TH_DRIVEN_HIGH = 0xF5

DEFAULT = "sms"


class Model:
    __slots__ = (
        "aliases",
        "card_slot",
        "handheld",
        "io_control",
        "name",
        "region",
        "reset_button",
        "summary",
    )

    def __init__(
        self,
        name: str,
        summary: str,
        aliases: tuple[str, ...],
        features: tuple[bool, bool, bool],
        io_control: int,
        region: str = "usa",
    ) -> None:
        self.name = name
        self.summary = summary
        self.aliases = aliases
        self.card_slot, self.handheld, self.reset_button = features
        self.io_control = io_control
        self.region = region


MODELS: dict[str, Model] = {
    model.name: model
    for model in (
        Model(
            "mark-iii",
            "The SG-1000 Mark III, Japan, 1985",
            ("mark3", "markiii", "sg-1000 mark iii"),
            (True, False, False),
            TH_DRIVEN_HIGH,
            "japan",
        ),
        Model(
            "sms",
            "The first Master System, with the card slot and the reset button",
            ("master system", "sms1", "master-system"),
            (True, False, True),
            ALL_INPUTS,
        ),
        Model(
            "sms2",
            "The Master System II, without the card slot or the reset button",
            ("master system ii", "master-system-ii"),
            (False, False, False),
            ALL_INPUTS,
        ),
        Model(
            "gg",
            "The Game Gear, with its own ports 0 to 6",
            ("game gear", "game-gear", "gamegear"),
            (False, True, False),
            ALL_INPUTS,
        ),
    )
}


def lookup(name: str | None) -> Model:
    wanted = (name or DEFAULT).strip().lower()
    for model in MODELS.values():
        if wanted == model.name or wanted in model.aliases:
            return model
    raise UnknownModelError(f"no console is called {name!r}; the consoles are {sorted(MODELS)}")
