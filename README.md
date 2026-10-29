# SMS Mapper

The board between the processor and everything else on the Sega Mark III, both Master Systems and the Game Gear, in Python: the memory map and its slot enables, Sega's paging and eleven third-party boards, the port decode and the controller ports, held to Sega's Mark III reference manual.

English | [日本語](README.ja.md) | [简体中文](README.zh-Hans.md) | [繁體中文（香港）](README.zh-HK.md)

[![ci](https://img.shields.io/github/actions/workflow/status/gufranco/sms-mapper-python/ci.yml?branch=main&style=flat-square&label=ci)](https://github.com/gufranco/sms-mapper-python/actions/workflows/ci.yml)
[![release](https://img.shields.io/github/v/release/gufranco/sms-mapper-python?style=flat-square&label=release)](https://github.com/gufranco/sms-mapper-python/releases/latest)
[![coverage](https://img.shields.io/badge/coverage-100%25-brightgreen?style=flat-square)](https://github.com/gufranco/sms-mapper-python/actions/workflows/ci.yml)
[![openssf scorecard](https://img.shields.io/ossf-scorecard/github.com/gufranco/sms-mapper-python?style=flat-square&label=openssf%20scorecard)](https://scorecard.dev/viewer/?uri=github.com/gufranco/sms-mapper-python)
[![license](https://img.shields.io/github/license/gufranco/sms-mapper-python?style=flat-square&label=license)](LICENSE)

**2,608** distinct Master System and Game Gear images booted for **600** frames each, **0** property failures over the **813** retail ones on a board with registers, **24** quotes located in the manual and the pinned sources, **12** boards, **845** tests, **100%** statement and branch coverage, no dependencies beyond the standard library

```python
import smsmapper

image = bytes(offset // 0x4000 for offset in range(0x40000))
cartridge = smsmapper.Cartridge(image, board="sega", ram=0x2000)
console = smsmapper.Console("sms", cartridge=cartridge)

console.write(0xFFFF, 5)
console.write(0xFFFC, 0x01)
print(console.read(0x8000), cartridge.banks)

console.write(0xFFFC, 0x08)
console.write(0x8000, 0x42)
print(hex(console.read(0x8000)), hex(cartridge.ram[0]), hex(console.read(0xDFFC)))

console.press("1")
console.write_port(0x3F, 0x55)
print(hex(console.read_port(0xDC)), hex(console.read_port(0xDD)))
```

```
13 (8, 9, 13)
0x42 0x42 0x8
0xef 0x3f
```

Each byte of the made-up 256K image holds its own 16K bank number. A write to FFFF selects bank 5 for frame 2, and a bank shift of 01 in FFFC moves every frame eight banks on, as the manual's figure for the 4 Mbit ROM shows: frame 2 lands on bank 13. With the shift back at 00 and bit 3 set, frame 2 is the cartridge's RAM. Every write to FFFC to FFFF also lands in the system RAM, which repeats at DFFC. Pressing button 1 clears bit 4 of port DC, and port 3F drives both TH lines low as outputs, which port DD reads back in bits 6 and 7.

## Install

| Requirement | Version                     |
| :---------- | :-------------------------- |
| Python      | 3.12 or newer               |
| git         | Any, to fetch the submodule |

```bash
git clone --recurse-submodules https://github.com/gufranco/sms-mapper-python.git
cd sms-mapper-python
python3 smsmapper/doctor.py
```

The package imports nothing outside the standard library. The submodule is `zilog-z80-python`, and only the census and the test cartridges use it. A source archive from the download-zip link has no submodule: there the census and its tests report why they cannot run, and everything else works.

The doctor checks the machine and the checkout and ends with one line. Paste its whole output into any bug report.

```
  10 checks, nothing to report
```

Releases follow [Semantic Versioning](https://semver.org/) and are cut from the commit history by semantic-release. Every release is tagged and listed on the [releases page](https://github.com/gufranco/sms-mapper-python/releases).

## The interface

`smsmapper.Cartridge(image, board="sega", ram=0)` builds a cartridge on one of the boards below. `image` is the cartridge's bytes as a dump holds them, and `ram` is its RAM in bytes: 0, 8192, 16384 or 32768. `smsmapper.Console(model=None, cartridge=None, bios=None, card=None, region=None, handheld_mode=True)` puts it, a boot ROM and a card in a console. Any slot may be left empty, and the boot ROM and the card are built with `Cartridge` too.

| Model      | Aliases                                  | Card slot | Reset button | Ports 0 to 6 |
| :--------- | :--------------------------------------- | :-------- | :----------- | :----------- |
| `mark-iii` | `mark3`, `markiii`, `sg-1000 mark iii`   | Yes       | No           | No           |
| `sms`      | `master system`, `sms1`, `master-system` | Yes       | Yes          | No           |
| `sms2`     | `master system ii`, `master-system-ii`   | No        | No           | No           |
| `gg`       | `game gear`, `game-gear`, `gamegear`     | No        | No           | Yes          |

`region` is `japan`, `usa` or `europe`, and left out it is the model's own: `japan` for the Mark III and `usa` for the rest. A Japanese console reads every TH and TR output back as 0, which is how software tells the regions apart, and the Game Gear reports the region in port 0. `handheld_mode=False` puts a Game Gear in Master System mode, where ports 0 to 6 disappear and START is the pause button.

```python
import smsmapper

image = bytes(0x8000)
for console in (
    smsmapper.Console("mark-iii", card=smsmapper.Cartridge(image)),
    smsmapper.Console("sms", cartridge=smsmapper.Cartridge(image), region="japan"),
    smsmapper.Console("sms2", cartridge=smsmapper.Cartridge(image), region="europe"),
    smsmapper.Console("gg", cartridge=smsmapper.Cartridge(image), region="europe"),
):
    print(console.model.name, console.region, hex(console.memory.control))

game_gear = smsmapper.Console("gg", region="japan")
game_gear.press("start")
print(hex(game_gear.read_port(0x00)), game_gear.nmi)
```

```
mark-iii japan 0xa8
sms japan 0xa8
sms2 europe 0xa8
gg europe 0xa8
0x0 False
```

### Calls

| Call                        | Effect                                                                                                                                   |
| :-------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------- |
| `read(address)`             | One byte from the processor's 64K, through the slot enables, the board's paging and the system RAM                                       |
| `write(address, value)`     | One byte to the processor's 64K. It reaches the selected slot's board, and the system RAM from C000h up, as a paging register write does |
| `read_port(port)`           | One byte from a port the board answers: ports DC and DD, and the Game Gear's ports 0 to 6. FFh where nothing answers                     |
| `write_port(port, value)`   | One byte to a port the board takes: 3E, 3F and the Game Gear's ports. A write nothing takes is dropped                                   |
| `press(button, player=1)`   | Holds a button: `up`, `down`, `left`, `right`, `1`, `2`, and the console's `pause`, `reset` and `start`                                  |
| `release(button, player=1)` | Lets it go                                                                                                                               |

A port that reaches the video part or the sound generator raises `NotOnBoardError`, because those answer from `sega-vdp-python`, not from the board. `smsmapper.ports.decode(model, port, direction)` names what any port reaches.

```python
from smsmapper import ports

for port in (0x3E, 0x7F, 0xBE, 0xDD):
    print(
        f"{port:02X}",
        ports.decode("sms", port, ports.READ),
        "/",
        ports.decode("sms", port, ports.WRITE),
    )
```

```
3E nothing / memory control
7F h counter / sound
BE vdp data / vdp data
DD port b / nothing
```

### State

| Attribute                | Meaning                                                                                                            |
| :----------------------- | :----------------------------------------------------------------------------------------------------------------- |
| `nmi`                    | True while the pause button holds the processor's non-maskable line, or START on a Game Gear in Master System mode |
| `latches`                | How many times a TH line has gone from low to high, each of which asks the video part to latch its counters        |
| `memory.control`         | Port 3E's last value: the slot enables, active low                                                                 |
| `memory.ram`             | The 8K of system RAM                                                                                               |
| `memory.cartridge`       | The cartridge, the board `Cartridge` built. `card`, `bios` and `expansion` are the other slots                     |
| `controllers.io_control` | Port 3F's last value, as the console holds it                                                                      |
| `model`                  | The `Model` record                                                                                                 |

A board built by `Cartridge` has `read(address)` and `write(address, value)` for the processor's 64K, `decodes(address)` saying whether a write there reaches one of its registers, `banks` naming the bank each window shows, `ram`, `image`, `pages`, `name` and `reset()`. The 93C46 board also has `eeprom.words`, its 64 sixteen-bit words.

### Module contents

| Name                           | Content                                                                                 |
| :----------------------------- | :-------------------------------------------------------------------------------------- |
| `smsmapper.BOARDS`             | Every board by name, with what it is                                                    |
| `smsmapper.MODELS`             | The four `Model` records, keyed by canonical name                                       |
| `smsmapper.Board`              | What every board is built on                                                            |
| `smsmapper.UnknownBoardError`  | Raised for a board name the package does not have. The message lists the names accepted |
| `smsmapper.UnknownModelError`  | Raised for a console name the package does not have                                     |
| `smsmapper.UnknownRegionError` | Raised for a region other than `japan`, `usa` and `europe`                              |
| `smsmapper.EmptyImageError`    | Raised for an image with nothing in it                                                  |
| `smsmapper.RamSizeError`       | Raised for cartridge RAM of a size no board carries                                     |
| `smsmapper.SlotError`          | Raised for a card given to a console without a card slot                                |
| `smsmapper.NotOnBoardError`    | Raised for a port the video part or the sound generator answers                         |
| `smsmapper.__version__`        | The installed version                                                                   |

```python
import smsmapper

for name, summary in smsmapper.BOARDS.items():
    print(f"{name:14} {summary}")

try:
    smsmapper.Cartridge(bytes(0x8000), board="sega-5000")
except smsmapper.UnknownBoardError as error:
    print(error)
```

```
sega           Sega's paging: three 16K frames from FFFD to FFFF, cartridge RAM from FFFC
codemasters    Codemasters' paging: writes to 0000, 4000 and 8000 select the frames, 8K of RAM at A000
4pak           HES's 4 PAK All Action: 3FFE, 7FFF and BFFF select the frames, 3FFE also the game
eeprom         Sega's paging with a 93C46 EEPROM behind 8000, as the Game Gear baseball games carry
hicom          Hi-Com's multicarts: FFFF selects a 32K bank at 0000, 8000 to BFFF shows the first 16K
janggun        Daiou's board for Janggun-ui Adeul: 8K banks, and banks with bit 7 set read bit-reversed
korean         A Korean board that selects the bank for 8000 to BFFF with a write to A000
korean_188in1  The Korean 188-in-1 board: the first 16K fixed, a 32K window from an 8K bank at 4000
korean_nb      A Korean board with no paging at all: banks 0, 1 and 2 stay where they power on
nemesis        Zemina's board as Nemesis uses it, starting with the last 8K bank at 0000
seojin         Seo Jin's multicarts: FFF0 selects a 32K game, FFFD to FFFF the frames within it
zemina         Zemina's board: six 8K banks, selected by writes to 0000 to 0003
no board is called 'sega-5000'; the boards are ['4pak', 'codemasters', 'eeprom', 'hicom', 'janggun', 'korean', 'korean_188in1', 'korean_nb', 'nemesis', 'sega', 'seojin', 'zemina']
```

### Modules

| Module                  | Holds                                                                    |
| :---------------------- | :----------------------------------------------------------------------- |
| `smsmapper.sega`        | Sega's paging, with the bank shift and the cartridge RAM                 |
| `smsmapper.codemasters` | Codemasters' paging and its 8K of RAM                                    |
| `smsmapper.korean`      | The Korean, Korean no-bank, 188-in-1, Janggun, Zemina and Nemesis boards |
| `smsmapper.multicart`   | The 4 PAK, Hi-Com and Seo Jin multicarts                                 |
| `smsmapper.eeprom`      | The 93C46 EEPROM and the Sega board that carries it                      |
| `smsmapper.memory`      | The processor's 64K: the slots, port 3E's enables and the system RAM     |
| `smsmapper.ports`       | Which device a port reaches, per console                                 |
| `smsmapper.controllers` | Ports DC and DD, and port 3F's directions and levels                     |
| `smsmapper.console`     | All of it together, with the Game Gear's ports and the console's buttons |
| `smsmapper.models`      | The four consoles                                                        |

## Sega's paging

The manual prints four registers at the top of memory. FFFD, FFFE and FFFF select the 16K bank each of the three frames shows, and FFFC holds the rest:

| FFFC bits | What the manual says                           | What this package does                                                        |
| :-------- | :--------------------------------------------- | :---------------------------------------------------------------------------- |
| 0 and 1   | Bank number shift                              | Adds eight banks per step to every frame, as the figure for 4 Mbit ROMs shows |
| 2         | External RAM bank number                       | Picks which 16K of the cartridge RAM frame 2 shows                            |
| 3         | ROM or RAM in frame 2                          | Puts the cartridge RAM in frame 2, when the cartridge has any                 |
| 4         | RAM write protect switch, with a question mark | Nothing                                                                       |
| 7         | A development board's write protect            | Nothing                                                                       |

The first 1K never moves, so the reset and interrupt vectors are always there. Each write to FFFC to FFFF is also written to the system RAM, so software reads its registers back from there.

Two implementations disagree with the manual on the shift, and [`conformance/divergences.json`](conformance/divergences.json) carries both: MAME ignores it, and Genesis Plus GX shifts the other way. The census counts which images set it.

## The census

```bash
python3 -m conformance.census "external/Master EverDrive" "external/EverDrive GG" --frames 600 --jobs 12
```

The census boots every image in a Master System and Game Gear library behind the `zilog-z80-python` processor, on the board MAME's software lists name for it, and counts every write that reaches one of the board's registers. A `.sms` image runs on a Master System and a `.gg` image on a Game Gear. An image that only the European set lists runs on a European console, whose 50 Hz frame is 313 lines; every other image runs on a 262-line American one. Some European cartridges time a frame at power-on and stop on a 60 Hz console, so they page only at 50 Hz. The video part is a stand-in that only counts lines, raises the frame and line interrupts and answers the counters, because what the census asks about is paging, not pictures. It accepts directories, zip archives and single images, counts each distinct image once by digest, prints a summary, writes [`conformance/corpus.json`](conformance/corpus.json), and exits 1 when a property breaks.

Two properties gate the run: the model raises no exception on any image, and every retail image over 48K on a board with registers writes one of them within the frame bound. A cartridge that never pages could not show what lies past its first 48K, so a retail one that stays silent is a board this package has wrong. [`conformance/boards.json`](conformance/boards.json) names, by whole-file SHA-1 as MAME's software lists record them, the images built on another board. The Master Gear adapter and the X-Terminator cheat device are not modelled, so those images run on Sega's paging and are counted apart.

| Result of the last run                                      | Count          |
| :---------------------------------------------------------- | :------------- |
| Listings across both libraries                              | 17,329         |
| Distinct images                                             | 2,608          |
| Retail images on a board with registers, the ones that gate | 813            |
| Run on a European console, 313 lines a frame                | 233            |
| Images on `4pak`, and how many wrote a register             | 1 of 1         |
| Images on `codemasters`, and how many wrote a register      | 21 of 21       |
| Images on `eeprom`, and how many wrote a register           | 7 of 7         |
| Images on `hicom`, and how many wrote a register            | 3 of 9         |
| Images on `janggun`, and how many wrote a register          | 1 of 1         |
| Images on `korean`, and how many wrote a register           | 4 of 6         |
| Images on `korean_nb`, and how many wrote a register        | 0 of 5         |
| Images on `nemesis`, and how many wrote a register          | 1 of 1         |
| Images on `sega`, and how many wrote a register             | 2,293 of 2,549 |
| Images on `zemina`, and how many wrote a register           | 8 of 8         |
| Set FFFC's bank shift                                       | 21             |
| Enabled cartridge RAM through FFFC bit 3                    | 185            |
| Chose the second RAM bank through FFFC bit 2                | 20             |
| Selected a bank past the end of the image                   | 294            |
| Never wrote a board register                                | 269            |
| On a board this package does not model                      | 0              |

[`conformance/corpus.json`](conformance/corpus.json) holds those counts and nothing from any cartridge, so the suite checks them on a machine with no library.

## Test cartridges

```bash
python3 -m conformance.testroms "/path/to/5 Tools & Service Test Carts.zip"
```

[`conformance/testroms.json`](conformance/testroms.json) lists every test cartridge that exercises this board, by SHA-256, the script of controller presses each run takes, and what it printed. Each runs on the census harness, and its screen is read out of the stand-in's video memory.

| Cartridge                                    | Run on                                    | What the record holds                                                                                       |
| :------------------------------------------- | :---------------------------------------- | :---------------------------------------------------------------------------------------------------------- |
| Test Suite 0.32, by sverx                    | A Master System, export and Japan         | Its System Info page answers JPN? No and Yes, and MediaEnable? Yes, from ports 3F and 3E                    |
| SMS Paging PFR Detect 2.00, by Eric R. Quinn | A Master System with 32K of cartridge RAM | The first 1K fixed, the rest of all three frames pageable, both backup pages present, and the test complete |

The Test Suite's Model and VDP? lines are the stand-in for the video part answering, not this package, so the record keeps them only to see them change.

## Is it right

Every fact Sega printed that a test can reach is held to the code. [`conformance/hardware.json`](conformance/hardware.json) carries each fact with its sentence and page, and [`conformance/hardware.test.py`](conformance/hardware.test.py) drives the package against them. `python3 -m conformance.quotes` finds every quoted sentence in the manual, and every quoted line of code in the pinned MAME and Genesis Plus GX checkouts.

Every value the manual does not print sits under `notStated` in the same file, marked unverified, with its source and the measurement that would settle it. [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) lists them. The places where sources part are in [`conformance/divergences.json`](conformance/divergences.json).

## Working on it

| Need                                                            | Where                                                                 |
| :-------------------------------------------------------------- | :-------------------------------------------------------------------- |
| Every gate and the order to run them                            | [CONTRIBUTING.md](CONTRIBUTING.md)                                    |
| The same material for a coding agent                            | [AGENTS.md](AGENTS.md)                                                |
| The standard this repository shares with the rest of the family | [FAMILY.md](FAMILY.md)                                                |
| Bug reports                                                     | [GitHub Issues](https://github.com/gufranco/sms-mapper-python/issues) |
| Security reports                                                | [SECURITY.md](SECURITY.md)                                            |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 mypy==1.14.1
python3 smsmapper/console.test.py
```

Each module has a test file beside it, named after it, and each runs on its own as above. Coverage is a hard gate at 100% statement and branch.

## References

- _Software Reference Manual for the SEGA Mark III Console_, Sega, undated, a retyped copy. 45 pages, 184,840 bytes, SHA-256 `166f09331ba9df055f7a352f10c6a7843911470bc72d9347eda4a0de86e8cfce`. It is not redistributable and is not in this repository. `python3 -m conformance.documents` downloads it from https://segaretro.org/images/d/d6/SoftwareReferenceManualForSegaMarkIIIEU.pdf and refuses any other file.
- MAME, `src/devices/bus/sega8/rom.cpp`, `src/devices/machine/eepromser.cpp`, `hash/sms.xml` and `hash/gamegear.xml` at commit `94fc55c9692b180dcb608e2e222e48315db5017a`, https://github.com/mamedev/mame, for every third-party board and the boards each image is on. Facts only; no code is taken.
- Genesis Plus GX, `core/io_ctrl.c`, `core/system.c` and `core/cart_hw/sms_cart.c` at commit `a5834b3df455c49bb97bfaa328c20845831f576b`, https://github.com/ekeeke/Genesis-Plus-GX, for the consoles the manual does not describe. Facts only; no code is taken.

## Citing this

[CITATION.cff](CITATION.cff) is updated with each release by the script that stamps the package version.

## License

MIT. See [LICENSE](LICENSE).
