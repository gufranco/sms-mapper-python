# Open questions

What this project does not know for certain, and what it would take to find out.

Everything here is a place where being faithful is still a claim rather than a measurement. The only Sega document is the Mark III reference manual, a retyped copy that describes the Mark III and none of the consoles after it. Below it sit Genesis Plus GX for the later consoles and MAME for the third-party boards, which are leads rather than authorities, and the cartridge libraries, which say which registers software writes but not what the board does with a write nobody makes.

Every entry is also in [`conformance/hardware.json`](conformance/hardware.json) under `notStated`, or in [`conformance/divergences.json`](conformance/divergences.json), so a program can read what a person reads here.

## What would settle almost all of them

A Master System of each revision, a Japanese one, a Game Gear and a cartridge whose code runs from RAM and writes what it reads to save memory. Such a cartridge can switch slots off, write the paging registers, drive port 3F and read everything back, which settles the bank shift, the slot enables, the open bus and the region lines at once. A Game Gear and an EverDrive GG are available; no Master System is.

## What the manual does not print

### Where a board's frames start with no boot program to set them

**This package does.** Sega's board and the boards modelled on it start at banks 0, 1 and 2, whatever ran before.

**Why it is open.** The manual says the system ROM writes those values, which leaves a console with no boot program, such as the Game Gear, undecided.

**Where the value came from.** MAME src/devices/bus/sega8/rom.cpp at 94fc55c9692b180dcb608e2e222e48315db5017a, late_bank_setup; Genesis Plus GX agrees.

**What would settle it.** Read FFFD to FFFF's effect on a Game Gear with a cartridge whose first instructions read a byte from each frame before writing any register.

### How many bits of a frame register select a bank

**This package does.** Every bit of a frame register selects, taken modulo the image's 16K page count.

**Why it is open.** The manual's figure shows three zero bits above a five bit page number, and its page 21 shows a three bit one. Images over 512K exist in the library and page past both.

**Where the value came from.** MAME rom.cpp write_mapper and Genesis Plus GX sms_cart.c mapper_16k_w, which both take the whole byte modulo the page count.

**What would settle it.** Write 20h to FFFF on a 512K Sega cartridge and read 8000h against bank 0.

### When the bank shift takes effect

**This package does.** The bank shift applies to every frame at once, including banks selected before it changed.

**Why it is open.** The manual's figure shows the mapping but not when the shift takes effect.

**Where the value came from.** No implementation agrees: MAME has no shift, and Genesis Plus GX applies it only to a frame written after it changes.

**What would settle it.** On a 4 Mbit Sega cartridge, select bank 1 in frame 2, then write 01h to FFFC, and read 8000h.

### What answers when two slots are switched on together

**This package does.** With several slots enabled at once, the cartridge answers, then the card, then the expansion slot, then the boot ROM.

**Why it is open.** The manual names each enable but not what two enabled slots do together.

**Where the value came from.** Genesis Plus GX sms_cart.c sms_cart_switch at a5834b3d, which picks the cartridge over the boot ROM and models no card or expansion slot.

**What would settle it.** Enable the cartridge and the boot ROM together on a Master System and read 0000h.

### What the bus reads when nothing drives it

**This package does.** FFh, for memory no slot answers, RAM switched off, ports nothing answers and controller ports switched off.

**Why it is open.** The manual does not say what the bus reads when nothing drives it.

**Where the value came from.** Genesis Plus GX sms_cart.c, which fills unmapped memory with FFh.

**What would settle it.** Switch every slot off from code running in RAM and read 0000h, then read port 3Eh.

### Whether a switched-off cartridge still sees writes

**This package does.** A write below C000h, or to a paging register, reaches only the slot whose enable is on.

**Why it is open.** The manual says the register sits in the cartridge but not whether a disabled cartridge still sees the bus.

**Where the value came from.** Genesis Plus GX, which routes writes through the mapper of the active slot only.

**What would settle it.** With the cartridge switched off, write FFFFh from RAM, switch it back on and read 8000h.

### What port 3E holds at power on

**This package does.** Port 3E holds E0h with a boot program present and A8h without one.

**Why it is open.** The manual names the map at power on but not the value of port 3E's latch, and a console without a boot program starts where one hands over.

**Where the value came from.** Genesis Plus GX io_ctrl.c io_reset.

**What would settle it.** On a console booting a cartridge without its boot program, read RAM C000h, where the export boot programs store the value they last wrote.

### What a TH or TR line set as an output reads back

**This package does.** A TH or TR line set as an output reads back the level port 3F drives; port 3F starts with every line an input, F5h on the Mark III.

**Why it is open.** The manual gives port 3F's bits for the gun and the trackball but not what an output reads back.

**Where the value came from.** Genesis Plus GX io_ctrl.c io_z80_read and io_reset.

**What would settle it.** Write 55h and AAh to port 3F on an export Master System and read ports DC and DD after each.

### How a Japanese console reads its own outputs

**This package does.** A Japanese console reads every TH and TR output as 0, which is how software tells the regions apart.

**Why it is open.** No Sega document describes the export consoles, so none says how they differ.

**Where the value came from.** Genesis Plus GX io_ctrl.c io_z80_write.

**What would settle it.** Write F5h to port 3F on a Japanese Master System and read port DD.

### What makes the video part latch its counters when software drives TH

**This package does.** A TH level going from low to high on either port asks the video part to latch its counters.

**Why it is open.** The manual describes the gun latching the beam position, not what latches it when software drives TH itself.

**Where the value came from.** Genesis Plus GX io_ctrl.c io_z80_write.

**What would settle it.** Drive TH low then high from port 3F mid-line and read ports 7E and 7F.

### What the Game Gear's ports 0 to 6 hold and do

**This package does.** Port 0 holds START in bit 7 and the region in bits 6 and 5; ports 1 to 5 the link port at 00, FF, 00, FF and 00; port 1 reads through port 2's direction bits; port 5 keeps bits 3 to 7; port 6 reads FFh.

**Why it is open.** No Sega document for the Game Gear is known to be public.

**Where the value came from.** Genesis Plus GX io_ctrl.c io_reset, io_gg_read and io_gg_write.

**What would settle it.** Read ports 0 to 6 on a Game Gear of each region straight after power on.

### What START does in each of the Game Gear's modes

**This package does.** START raises no NMI in the Game Gear's own mode and acts as pause in Master System mode.

**Why it is open.** No Sega document for the Game Gear is known to be public.

**Where the value came from.** Genesis Plus GX system.c, which skips the pause NMI in Game Gear mode.

**What would settle it.** Press START on a Game Gear running a Master System cartridge with an NMI handler that counts.

### Whether the board adds a wait state anywhere

**This package does.** The board inserts no wait state on any memory or port access.

**Why it is open.** The manual says nothing of access timing on the board.

**Where the value came from.** Neither MAME nor Genesis Plus GX inserts any on these consoles.

**What would settle it.** A logic analyser on WAIT of a running Master System and Game Gear.

### What a read past the end of an image shows

**This package does.** A read past the end of an image wraps to its start.

**Why it is open.** A cartridge's ROM decodes only the address lines it has, so smaller images repeat, but the manual does not say so and odd sizes such as 48K are not powers of two.

**Where the value came from.** MAME rom.cpp, whose own comment marks mirroring of sizes that are not powers of two as not done; this package wraps by the image length.

**What would settle it.** Read a 48K Sega cartridge at bank 3.

### Whether each third-party board pages as MAME says

**This package does.** Codemasters, 4 PAK, Zemina, Nemesis, Janggun, Hi-Com, Korean, Korean 188-in-1, Korean no-bank, Seo Jin and the 93C46 EEPROM board, register by register as smsmapper models them.

**Why it is open.** No maker of a third-party board published its design.

**Where the value came from.** MAME src/devices/bus/sega8/rom.cpp and src/devices/machine/eepromser.cpp at 94fc55c9692b180dcb608e2e222e48315db5017a, BSD-3-Clause; facts only, no code is taken.

**What would settle it.** Each board's census row: the images MAME lists on it boot and write its registers. A board without a row has nothing in the library exercising it.

## Where the sources part

### Which way the bank shift moves a bank number

**This package does.** Adds eight banks per step, as the manual's figure and its note say.

**Why it is open.** Genesis Plus GX takes eight banks away per step, and MAME implements no shift at all.

**Where the value came from.** The manual, pages 39 and 40.

**What would settle it.** On a 4 Mbit Sega cartridge write 01h to FFFC and 01h to FFFF, and compare 8000h with banks 9 and 25.

### Whether port 3E bit 4 switches the system RAM off

**This package does.** Switches it off: C000h to FFFFh read FFh and drop writes.

**Why it is open.** The manual names the bit; Genesis Plus GX ignores it.

**Where the value came from.** The manual, page 19.

**What would settle it.** Set bit 4 of port 3E from code in ROM and read C000h.

### What FFFC bit 4 does

**This package does.** Nothing.

**Why it is open.** The manual calls it a RAM write protect switch with a question mark, and Genesis Plus GX maps the cartridge RAM over C000h with it.

**Where the value came from.** The manual, page 39, and Genesis Plus GX sms_cart.c.

**What would settle it.** Set FFFC bit 4 on a Sega cartridge with RAM and read C000h against both RAMs.
