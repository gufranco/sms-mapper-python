# Working in this repository

Read [FAMILY.md](FAMILY.md) first. It is the standard every member of this
family carries, byte for byte, and it decides most questions before they are
asked. What follows is only what is true of this member. [README.md](README.md)
is the document written for a person.

## What this project is, in one paragraph

A model of the board between the Z80 and everything else on the Sega Mark III,
both Master Systems and the Game Gear: the memory map with its slot enables
from port 3E, the 8K of system RAM and its mirror, Sega's paging with the bank
shift and the cartridge RAM, eleven third-party paging boards including the
93C46 EEPROM board, the port decode, the controller ports with port 3F, the Game
Gear's ports 0 to 6, and the pause button on the processor's non-maskable line.
What the manual prints comes from Sega's Mark III reference manual. What it
does not comes from Genesis Plus GX for the later consoles and from MAME for
the third-party boards, marked unverified. What real software asks of the board
comes from a census over the Master System and Game Gear libraries.

## The interface a caller drives

- `smsmapper.Cartridge(image, board="sega", ram=0)` builds a cartridge on one of
  the boards `smsmapper.BOARDS` names. `ram` is 0, 8K, 16K or 32K.
- `smsmapper.Console(model, cartridge=..., bios=..., card=..., region=...,
handheld_mode=...)` puts cartridges in a console. `model` is `mark-iii`,
  `sms`, `sms2` or `gg`.
- `read`, `write`, `read_port` and `write_port` are the processor's side.
  A port that reaches the video part or the sound generator raises
  `NotOnBoardError`, because `sega-vdp-python` answers those.
- `press` and `release` hold the pads' buttons and the console's `pause`,
  `reset` and `start`. `nmi` is the non-maskable line and `latches` counts the
  TH rises that ask the video part to latch its counters.

Everything the package raises lives in
[`smsmapper/errors.py`](smsmapper/errors.py) and nowhere else.

This is a board, not a clocked part. It runs no program and has no clock of its
own: every access answers at once, with no wait state added.

## The authority ladder

1. **[`conformance/hardware.json`](conformance/hardware.json) facts**, quoted
   from Sega's Mark III reference manual and matched against its text layer by
   [`conformance/quotes.py`](conformance/quotes.py).
2. **The cartridge libraries**, through
   [`conformance/census.py`](conformance/census.py), for which registers real
   software writes.
3. **Genesis Plus GX** for the Master System's and Game Gear's port behaviour,
   and **MAME** for every third-party board, each under `notStated` with
   `verified: false`. Their quoted lines are matched against the pinned
   checkouts in `external/`.

[`conformance/divergences.json`](conformance/divergences.json) records every
place two sources part, including the bank shift, where the manual, MAME and
Genesis Plus GX give three different answers.

## What is settled and what is not

**Settled: everything the manual prints and a test can reach.** Each fact in
[`conformance/hardware.json`](conformance/hardware.json) names, under `heldBy`,
the test in [`conformance/hardware.test.py`](conformance/hardware.test.py) that
holds it.

**Not settled: 18 things**, every entry under `notStated` and three questions
only the divergences carry, each in [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) with what
would close it. Do not close one by argument.

## The bank shift follows the manual

FFFC bits 0 and 1 shift every bank number by eight per step. The manual's
figure for the 4 Mbit ROM and its note say so: bank shift 00 with bank 09
reaches what bank shift 01 with bank 1 does. MAME implements no shift, and
Genesis Plus GX shifts the other way and only for frames written after the
shift changes. This package applies the shift to every frame at once, as an
adder in front of the bank lines would.

**If you are about to change the shift, read the census first.** Its
`SHIFTED` observation names every image that sets it, and none of them may
start paging into the wrong bank.

## Files kept in `external/`

Everything this member reads and may not ship sits in `external/`, which git
ignores and Dropbox is told to leave alone, per FAMILY.md's "Where the files a
member reads are kept". [`artifacts.manifest.json`](artifacts.manifest.json)
names every file by size, CRC32, MD5, SHA-1 and SHA-256, and every checkout by
its repository and commit:

- `external/Master EverDrive/`, 110 archives from the Master EverDrive pack of
  2022-05-04, which the census walks whole. One of them,
  `5 Tools & Service Test Carts.zip`, holds the test cartridges.
- `external/EverDrive GG/`, 75 archives from the EverDrive GG pack of
  2020-12-21, which the census walks whole.
- `external/mame/`, a sparse checkout of MAME at the pinned commit, for the
  quoted lines of the third-party boards.
- `external/Genesis-Plus-GX/`, a checkout of Genesis Plus GX at the pinned
  commit, for the quoted lines about the consoles.

```bash
python3 -m conformance.external
python3 -m conformance.external --describe external/<file>
```

The first says which are here, verified, missing or wrong. The second prints
the manifest entry for a file being added. A file added to `external/` gets an
entry in the same change, and a census over a library that is not in the
manifest is not a result anyone else can reproduce.

## The census board is not the console

[`conformance/harness.py`](conformance/harness.py) puts this package's
`Console` behind the processor with a stand-in for the video part. The
stand-in counts lines, raises the frame flag at line 192 and the line flag from
register 10, answers the V counter with the 192-line table and keeps nothing
else: no pixels, no sprites, no access windows. A Master System whose region
is `europe` gets the 313-line PAL frame and its V counter, and the census
gives an image that console when the European set is the only set that lists
it. Back to the Future Part III times a frame at power-on and stops for good
on a 262-line console, so on the American one it never pages. It is not `sega-vdp-python`,
and a cartridge that waits on a sprite collision or a VRAM read will stall on
it. What the census asks about is paging, which happens long before a game
needs either.

A Master System run starts where the export boot program hands over: the
stack at DFF0h and RAM C000h holding A8h, as `sega-vdp-python`'s census board
does. A Game Gear run starts from its reset values.

## Test cartridges

[`conformance/testroms.json`](conformance/testroms.json) lists every test
cartridge that exercises this board, by SHA-256, as FAMILY.md's fifth
requirement asks. Each comes from the Master EverDrive set's
`5 Tools & Service Test Carts.zip`, kept at `external/Master EverDrive/` as
[`artifacts.manifest.json`](artifacts.manifest.json) records.

```bash
python3 -m conformance.testroms [--write] <zip, folder or image ...>
```

With no argument it reads the folders and zips named in `TEST_CARTRIDGES`,
and with that unset, the zip kept under `external/`. With none present it says
so and exits 2, and CI turns that into a notice.
[`conformance/testroms.test.py`](conformance/testroms.test.py) replays the
recorded verdicts with no image present.

## Every gate, in the order to run them

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 --with types-setuptools==84.0.0.20260812 mypy==1.14.1
pnpm install --frozen-lockfile && pnpm run format:check
uvx yamllint==1.38.0 --strict .
cov=(uvx --python 3.12 --from coverage==7.6.10 --with setuptools==84.0.0 coverage)
"${cov[@]}" erase
for f in $(find smsmapper conformance -name '*.test.py' | sort); do
  "${cov[@]}" run -a "$f" || echo "FAILED $f"
done
"${cov[@]}" report
```

Then the ones outside the coverage step:

```bash
python3 -m conformance.corpus
python3 -m conformance.speed
python3 -m conformance.documents --check
python3 -m conformance.quotes
```

And, with the libraries present, the three that read them:

```bash
python3 -m conformance.external
python3 -m conformance.census "external/Master EverDrive" "external/EverDrive GG" --frames 600 --jobs 12
python3 -m conformance.testroms
```

Everything under [`conformance/`](conformance) runs as a module. Run as a
script, its own directory goes on the import path and a file there shadows any
standard library module of the same name.

## Conventions that are not negotiable

| Thing                       | Rule                                                                                                                                              |
| :-------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------ |
| Language                    | Python only                                                                                                                                       |
| Comments                    | None in source or in build files, and a docstring counts as one. Names, small functions, constants and types carry what a comment would have said |
| Test layout                 | `<module>.test.py` beside the module it covers                                                                                                    |
| Test shape                  | Arrange, act, assert, each opened by its bare marker                                                                                              |
| Coverage                    | 100% statements and branches, enforced                                                                                                            |
| Types                       | `mypy` at strict, plus every optional error class                                                                                                 |
| Package manager for tooling | pnpm, never npm                                                                                                                                   |
| Commits                     | Conventional Commits, subject at most 50 characters                                                                                               |
| Documents                   | Read, quoted and pinned by digest. Never committed                                                                                                |
| Cartridges                  | Never committed, in any form, for any reason                                                                                                      |

The linter's ignores in [`pyproject.toml`](pyproject.toml) carry no comments, so
their reasons live here:

- `N818`: some exceptions are signals rather than failures. The standard
  library names those without the suffix too.
- `N999` and `PLR2004` in tests: a test file is named after its module with a
  dot, and its literals are the expected values.
- `T201` in `conformance/`, the doctor and `environment.py`: printing is their
  output.
- `BLE001` in the doctor, `environment.py` and the census: a check that throws
  has to become a line in the report rather than end the run. One image that
  raises must not throw away the census's results for every other image.
- The `z80.*` override: the processor is typed and checked in its own
  repository against its own gate.
- `external/` in the linter's and coverage's exclusions: it holds checkouts of
  other projects, never this one's code.

The formatter's ignores in [`.prettierignore`](.prettierignore) carry no
comments either, so their reasons live here:

- `pnpm-lock.yaml` and `package-lock.json`: the package manager writes them, in
  its own layout, on every install.
- `node_modules/`, `.venv/`, `venv/`, `build/`, `dist/` and `*.egg-info/`:
  installed or built, never written by hand.
- `.coverage`, `coverage.json`, `htmlcov/` and the tool caches: the output of a
  run, never committed.
- `docs/`, `specs/`, `.work/`, `.claude/` and `external/`: local working
  material, never committed.
- [`zilog-z80-python`](zilog-z80-python): a submodule. It is a member that
  formats and checks itself, and the commit pinned here is not this
  repository's to change.

## Layout

```
smsmapper/
  boards.py       what every board is built on: the image, its pages and its RAM
  cartridge.py    every board by name, and Cartridge, which builds one
  sega.py         Sega's paging, the bank shift and the cartridge RAM
  codemasters.py  Codemasters' paging and its 8K of RAM
  korean.py       the Korean, no-bank, 188-in-1, Janggun, Zemina and Nemesis boards
  multicart.py    the 4 PAK, Hi-Com and Seo Jin multicarts
  eeprom.py       the 93C46 EEPROM and the Sega board that carries it
  memory.py       the processor's 64K: slots, port 3E and the system RAM
  ports.py        which device a port reaches, per console
  controllers.py  ports DC and DD, and port 3F
  console.py      all of it together, with the Game Gear's ports and the buttons
  models.py       the four consoles
  errors.py       everything this package raises
  doctor.py       what the machine and the package look like, for a report
  environment.py  what the doctor reads about the machine
  version.py      rewritten by the release job and by nothing else
conformance/
  census.py         boots every image in a library you own and counts its paging
  harness.py        the processor, this package and a stand-in for the video part
  boards.json       which images need a board other than Sega's paging, from MAME's lists
  corpus.json       the census counts, holding nothing from any cartridge
  corpus.py         replays them
  testroms.json     every test cartridge that exercises the board, and what each run printed
  testroms.py       runs the ones you hold on the census harness and reads their screens
  external.py       which of the files in external/ are here, verified, missing or wrong
  bench.py          the record, shared by the record's tests
  documents.json    the manual, by digest
  documents.py      brings it down and refuses any other file
  hardware.json     Sega's manual, fact by fact, and every value it does not print
  divergences.json  every place two sources part
  manual.py         the manual's text, flattened to letters and digits
  quotes.py         every quote the records carry, found in the manual or the pinned source
  links.py          the weekly check that every cited address still answers
  speed.py          the throughput floor
  source.py         the check that no documentation string remains
  family_*.test.py  the family standard, held as tests, one topic a file
  family_member.py  what this member answers to them
  family_shared.py  what more than one of them reads
zilog-z80-python/   the processor the census drives, a pinned submodule
external/           the libraries and the reference checkouts, never committed
artifacts.manifest.json  every file and checkout in external/, by digest or commit
```

## Things that will bite you

**A write reaches only the slot that is switched on.** Turn the cartridge off
through port 3E and a write to FFFF lands in RAM but not in the cartridge's
register. That is Genesis Plus GX's reading, recorded as unverified.

**The first 1K is not fixed on every board.** Sega's paging and the boards
built on it keep it; Codemasters', Zemina's, Janggun's and the multicarts' do
not.

**Bank numbers wrap by the image's own page count.** A 128K image selecting
bank 9 shows bank 1, and the census counts the retail images that rely on that.

**`sms` and `gg` decode the same ports above 06h.** Ports 0 to 6 belong to the
Game Gear only in its own mode; in Master System mode they decode as a Master
System's.

## Before calling anything finished

[`FAMILY.md`](FAMILY.md) carries a checklist under "What a new repository has to
have before it is a member". Every line on it was a defect found in one of these
repositories and fixed in all of them. Read it before adding a surface, and read
it again before saying a change is done.

**A check nobody has seen fail is not known to work.** Drive it, once,
deliberately, against input that should fail it.

**Silence and success produce the same output.** A census that walked no file
says so, and exits non-zero.

## What a change is expected to leave behind

A gate that would have caught the bug. A change to a board, the memory map or a
port also runs the census over a real library. The tests check what the manual
says, and the census checks what software that ran on the board still does.
