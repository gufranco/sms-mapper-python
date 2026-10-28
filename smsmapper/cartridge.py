from __future__ import annotations

from smsmapper.boards import Board
from smsmapper.codemasters import Codemasters
from smsmapper.eeprom import SegaEeprom
from smsmapper.errors import UnknownBoardError
from smsmapper.korean import Janggun, Korean, Korean188, KoreanNoBank, Nemesis, Zemina
from smsmapper.multicart import FourPak, HiCom, Seojin
from smsmapper.sega import Sega

KINDS: dict[str, type[Board]] = {
    kind.name: kind
    for kind in (
        Sega,
        Codemasters,
        FourPak,
        SegaEeprom,
        HiCom,
        Janggun,
        Korean,
        Korean188,
        KoreanNoBank,
        Nemesis,
        Seojin,
        Zemina,
    )
}

BOARDS: dict[str, str] = {name: kind.summary for name, kind in KINDS.items()}

DEFAULT = Sega.name


def Cartridge(image: bytes, board: str = DEFAULT, ram: int = 0) -> Board:  # noqa: N802
    kind = KINDS.get(board)
    if kind is None:
        raise UnknownBoardError(f"no board is called {board!r}; the boards are {sorted(KINDS)}")
    return kind(image, ram)
