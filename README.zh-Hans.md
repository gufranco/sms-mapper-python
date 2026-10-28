# SMS Mapper

世嘉 SG-1000 Mark III、两款 Master System 和 Game Gear 上，处理器与其余一切之间的电路板，用 Python 实现：内存映射及其插槽启用、世嘉的分页和 11 种第三方电路板、端口译码和控制器端口，并以世嘉的 Mark III 参考手册为准进行检验。

[English](README.md) | [日本語](README.ja.md) | 简体中文 | [繁體中文（香港）](README.zh-HK.md)

[![CI](https://github.com/gufranco/sms-mapper-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/sms-mapper-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/sms-mapper-python)](https://github.com/gufranco/sms-mapper-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**2,608** 个不同的 Master System 和 Game Gear 映像各启动 **600** 帧，在带寄存器的电路板上的 **813** 个零售映像中属性失败为 **0**，在手册和固定的源码中定位到 **24** 处引文，**12** 种电路板，**845** 个测试，**100%** 语句和分支覆盖率，除标准库外无依赖

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

这个 256K 的虚构映像，每个字节都存着自己所在的 16K 存储体编号。写入 FFFF 为第 2 帧选择存储体 5，而 FFFC 中的存储体偏移 01 按照手册中 4 兆位 ROM 的图示，把每一帧向后移动 8 个存储体：第 2 帧落在存储体 13。偏移改回 00 并置位第 3 位后，第 2 帧就是卡带的 RAM。对 FFFC 到 FFFF 的每次写入也会落入系统 RAM，而系统 RAM 在 DFFC 处重复出现。按下按钮 1 会清除端口 DC 的第 4 位，端口 3F 把两条 TH 线设为输出并拉低，端口 DD 在第 6 和第 7 位读回它们。

## 安装

| 要求   | 版本                 |
| :----- | :------------------- |
| Python | 3.12 或更新          |
| git    | 任意，用于获取子模块 |

```bash
git clone --recurse-submodules https://github.com/gufranco/sms-mapper-python.git
cd sms-mapper-python
python3 smsmapper/doctor.py
```

这个包只导入标准库。子模块是 `zilog-z80-python`，只有普查和测试卡带用到它。从 download-zip 链接得到的源码压缩包不含子模块：在那里普查及其测试会报告无法运行的原因，其余一切照常工作。

doctor 检查机器和签出的代码，最后输出一行结果。提交错误报告时，请贴上它的完整输出。

```
  10 checks, nothing to report
```

发布遵循 [Semantic Versioning](https://semver.org/)，由 semantic-release 根据提交历史生成。每次发布都有标签，并列在[发布页面](https://github.com/gufranco/sms-mapper-python/releases)上。

## 接口

`smsmapper.Cartridge(image, board="sega", ram=0)` 在下列电路板之一上构建一个卡带。`image` 是转储文件中保存的卡带字节，`ram` 是卡带 RAM 的字节数：0、8192、16384 或 32768。`smsmapper.Console(model=None, cartridge=None, bios=None, card=None, region=None, handheld_mode=True)` 把它连同启动 ROM 和卡片插进主机。任何插槽都可以空着，启动 ROM 和卡片同样用 `Cartridge` 构建。

| 型号       | 别名                                     | 卡片插槽 | 复位按钮 | 端口 0 到 6 |
| :--------- | :--------------------------------------- | :------- | :------- | :---------- |
| `mark-iii` | `mark3`、`markiii`、`sg-1000 mark iii`   | 有       | 无       | 无          |
| `sms`      | `master system`、`sms1`、`master-system` | 有       | 有       | 无          |
| `sms2`     | `master system ii`、`master-system-ii`   | 无       | 无       | 无          |
| `gg`       | `game gear`、`game-gear`、`gamegear`     | 无       | 无       | 有          |

`region` 为 `japan`、`usa` 或 `europe`，省略时取型号自己的地区：Mark III 为 `japan`，其余为 `usa`。日本主机把 TH 和 TR 的每个输出都读回为 0，软件借此区分地区；Game Gear 在端口 0 报告地区。`handheld_mode=False` 让 Game Gear 进入 Master System 模式，此时端口 0 到 6 消失，START 成为暂停按钮。

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

### 调用

| 调用                        | 作用                                                                                                  |
| :-------------------------- | :---------------------------------------------------------------------------------------------------- |
| `read(address)`             | 从处理器的 64K 读取 1 字节，经过插槽启用、电路板的分页和系统 RAM                                      |
| `write(address, value)`     | 向处理器的 64K 写入 1 字节。它到达所选插槽的电路板，并像分页寄存器写入那样，从 C000h 起也到达系统 RAM |
| `read_port(port)`           | 从电路板应答的端口读取 1 字节：端口 DC 和 DD，以及 Game Gear 的端口 0 到 6。无人应答之处为 FFh        |
| `write_port(port, value)`   | 向电路板接收的端口写入 1 字节：3E、3F 和 Game Gear 的端口。无人接收的写入被丢弃                       |
| `press(button, player=1)`   | 按住一个按钮：`up`、`down`、`left`、`right`、`1`、`2`，以及主机的 `pause`、`reset` 和 `start`         |
| `release(button, player=1)` | 松开它                                                                                                |

到达视频部件或声音发生器的端口会抛出 `NotOnBoardError`，因为它们由 `sega-vdp-python` 应答，而不是由电路板应答。`smsmapper.ports.decode(model, port, direction)` 说明任一端口到达什么。

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

### 状态

| 属性                     | 含义                                                                                           |
| :----------------------- | :--------------------------------------------------------------------------------------------- |
| `nmi`                    | 暂停按钮保持处理器的不可屏蔽中断线时为真，Game Gear 在 Master System 模式下按住 START 时也为真 |
| `latches`                | TH 线由低变高的次数，每次都请视频部件锁存其计数器                                              |
| `memory.control`         | 端口 3E 的最后一个值：插槽启用，低电平有效                                                     |
| `memory.ram`             | 8K 的系统 RAM                                                                                  |
| `memory.cartridge`       | 卡带，即 `Cartridge` 构建的电路板。`card`、`bios` 和 `expansion` 是其他插槽                    |
| `controllers.io_control` | 主机保存的端口 3F 的最后一个值                                                                 |
| `model`                  | `Model` 记录                                                                                   |

`Cartridge` 构建的电路板具有：处理器 64K 上的 `read(address)` 和 `write(address, value)`，说明写入该处是否到达其寄存器的 `decodes(address)`，指出每个窗口显示哪个存储体的 `banks`，以及 `ram`、`image`、`pages`、`name` 和 `reset()`。93C46 电路板还有 `eeprom.words`，即它的 64 个 16 位字。

### 模块内容

| 名称                           | 内容                                           |
| :----------------------------- | :--------------------------------------------- |
| `smsmapper.BOARDS`             | 按名称列出每种电路板，并说明它是什么           |
| `smsmapper.MODELS`             | 以规范名称为键的 4 条 `Model` 记录             |
| `smsmapper.Board`              | 每种电路板的基础                               |
| `smsmapper.UnknownBoardError`  | 电路板名称不在包中时抛出。消息列出可接受的名称 |
| `smsmapper.UnknownModelError`  | 主机名称不在包中时抛出                         |
| `smsmapper.UnknownRegionError` | 地区不是 `japan`、`usa` 或 `europe` 时抛出     |
| `smsmapper.EmptyImageError`    | 映像中没有任何内容时抛出                       |
| `smsmapper.RamSizeError`       | 卡带 RAM 的大小没有任何电路板使用时抛出        |
| `smsmapper.SlotError`          | 把卡片交给没有卡片插槽的主机时抛出             |
| `smsmapper.NotOnBoardError`    | 端口由视频部件或声音发生器应答时抛出           |
| `smsmapper.__version__`        | 已安装的版本                                   |

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

### 模块

| 模块                    | 内容                                                        |
| :---------------------- | :---------------------------------------------------------- |
| `smsmapper.sega`        | 世嘉的分页、存储体偏移和卡带 RAM                            |
| `smsmapper.codemasters` | Codemasters 的分页及其 8K RAM                               |
| `smsmapper.korean`      | Korean、无分页、188 合 1、Janggun、Zemina 和 Nemesis 电路板 |
| `smsmapper.multicart`   | 4 PAK、Hi-Com 和 Seo Jin 合卡                               |
| `smsmapper.eeprom`      | 93C46 EEPROM 及搭载它的世嘉电路板                           |
| `smsmapper.memory`      | 处理器的 64K：插槽、端口 3E 的启用和系统 RAM                |
| `smsmapper.ports`       | 按主机区分，每个端口到达哪个设备                            |
| `smsmapper.controllers` | 端口 DC 和 DD，以及端口 3F 的方向和电平                     |
| `smsmapper.console`     | 以上全部，再加上 Game Gear 的端口和主机的按钮               |
| `smsmapper.models`      | 4 款主机                                                    |

## 世嘉的分页

手册在内存顶部列出 4 个寄存器。FFFD、FFFE 和 FFFF 选择三个帧各自显示的 16K 存储体，FFFC 保存其余内容：

| FFFC 的位 | 手册所说                | 本包的做法                                      |
| :-------- | :---------------------- | :---------------------------------------------- |
| 0 和 1    | 存储体编号偏移          | 按 4 兆位 ROM 的图示，每级为每一帧加 8 个存储体 |
| 2         | 外部 RAM 的存储体编号   | 选择第 2 帧显示卡带 RAM 的哪 16K                |
| 3         | 第 2 帧中的 ROM 或 RAM  | 卡带有 RAM 时，把它放在第 2 帧                  |
| 4         | 带问号的 RAM 写保护开关 | 不做任何事                                      |
| 7         | 开发板的写保护          | 不做任何事                                      |

最初的 1K 永不移动，所以复位和中断向量始终在那里。对 FFFC 到 FFFF 的每次写入也写进系统 RAM，因此软件从那里读回寄存器的值。

关于偏移，有两个实现与手册不一致，[`conformance/divergences.json`](conformance/divergences.json) 记录了二者：MAME 忽略它，Genesis Plus GX 朝相反方向偏移。普查统计哪些映像设置了偏移。

## 普查

```bash
python3 -m conformance.census "external/Master EverDrive" "external/EverDrive GG" --frames 600 --jobs 12
```

普查把 Master System 和 Game Gear 卡带库中的每个映像，放在 MAME 软件列表为其指定的电路板上，在 `zilog-z80-python` 处理器后面启动，并统计到达电路板寄存器的每次写入。`.sms` 映像运行在 Master System 上，`.gg` 映像运行在 Game Gear 上。只被欧洲合集收录的映像运行在欧洲版主机上，其 50 Hz 的一帧为 313 行；其余映像运行在 262 行的美国版主机上。有些欧洲卡带在开机时测量一帧的长度，在 60 Hz 主机上会停住，因此只在 50 Hz 下分页。视频部件是一个替身，只计行数、发出帧中断和行中断并应答计数器，因为普查关心的是分页，而不是画面。它接受目录、ZIP 压缩包和单个映像，按摘要把每个不同的映像只计一次，打印摘要，写出 [`conformance/corpus.json`](conformance/corpus.json)，并在某项性质被破坏时以 1 退出。

运行由两项性质把关：模型在任何映像上都不抛出异常，以及位于有寄存器的电路板上、大于 48K 的每个零售映像，在帧数上限内写入其中某个寄存器。不分页的卡带无法显示前 48K 之后的内容，所以保持沉默的零售映像意味着本包把电路板弄错了。[`conformance/boards.json`](conformance/boards.json) 按 MAME 软件列表的记录，以整个文件的 SHA-1 列出建在其他电路板上的映像。Master Gear 转接器和 X-Terminator 作弊设备没有建模，因此这些映像在世嘉的分页上运行并单独计数。

| 上一次运行的结果                                 | 数量                  |
| :----------------------------------------------- | :-------------------- |
| 两个卡带库中的条目                               | 17,329                |
| 不同的映像                                       | 2,608                 |
| 带寄存器的电路板上的零售映像，参与把关           | 813                   |
| 在欧洲版主机上运行，每帧 313 行                  | 233                   |
| `4pak` 上的映像，以及其中写过寄存器的数量        | 1 个中的 1 个         |
| `codemasters` 上的映像，以及其中写过寄存器的数量 | 21 个中的 21 个       |
| `eeprom` 上的映像，以及其中写过寄存器的数量      | 7 个中的 7 个         |
| `hicom` 上的映像，以及其中写过寄存器的数量       | 9 个中的 3 个         |
| `janggun` 上的映像，以及其中写过寄存器的数量     | 1 个中的 1 个         |
| `korean` 上的映像，以及其中写过寄存器的数量      | 6 个中的 4 个         |
| `korean_nb` 上的映像，以及其中写过寄存器的数量   | 5 个中的 0 个         |
| `nemesis` 上的映像，以及其中写过寄存器的数量     | 1 个中的 1 个         |
| `sega` 上的映像，以及其中写过寄存器的数量        | 2,549 个中的 2,293 个 |
| `zemina` 上的映像，以及其中写过寄存器的数量      | 8 个中的 8 个         |
| 设置过 FFFC 的存储体偏移                         | 21                    |
| 通过 FFFC 第 3 位启用卡带 RAM                    | 185                   |
| 通过 FFFC 第 2 位选择第二个 RAM 存储体           | 20                    |
| 选择过超出映像末尾的存储体                       | 294                   |
| 从未写过电路板寄存器                             | 269                   |
| 在本包未建模的电路板上                           | 0                     |

[`conformance/corpus.json`](conformance/corpus.json) 只保存这些计数，不含任何卡带的内容，因此测试套件在没有卡带库的机器上也能检查它们。

## 测试卡带

```bash
python3 -m conformance.testroms "/path/to/5 Tools & Service Test Carts.zip"
```

[`conformance/testroms.json`](conformance/testroms.json) 按 SHA-256 列出检验这块电路板的每个测试卡带、每次运行所按的控制器操作脚本，以及它打印的内容。每个都在普查的测试装置上运行，屏幕内容从替身的视频内存中读出。

| 卡带                                           | 运行环境                         | 记录的内容                                                                       |
| :--------------------------------------------- | :------------------------------- | :------------------------------------------------------------------------------- |
| Test Suite 0.32，sverx 制作                    | Master System，海外版和日本版    | 其 System Info 页面根据端口 3F 和 3E 回答 JPN? 为 No 和 Yes，MediaEnable? 为 Yes |
| SMS Paging PFR Detect 2.00，Eric R. Quinn 制作 | 带 32K 卡带 RAM 的 Master System | 最初的 1K 固定，三个帧的其余部分可分页，两个备份页都存在，测试完成               |

Test Suite 的 Model 和 VDP? 两行是视频部件的替身作答，而不是本包，所以记录保留它们只为看到变化。

## 是否正确

世嘉印刷的事实中，凡是测试能触及的，都以代码为准加以检验。[`conformance/hardware.json`](conformance/hardware.json) 保存每条事实及其原句和页码，[`conformance/hardware.test.py`](conformance/hardware.test.py) 据此驱动本包。`python3 -m conformance.quotes` 在手册中找到每个被引用的句子，并在固定版本的 MAME 和 Genesis Plus GX 签出中找到每行被引用的代码。

手册没有印出的每个值都在同一文件的 `notStated` 下，标为未经验证，并写明来源和能够定论的测量。[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) 列出它们。各来源相互矛盾之处在 [`conformance/divergences.json`](conformance/divergences.json) 中。

## 参与开发

| 需要                           | 位置                                                                  |
| :----------------------------- | :-------------------------------------------------------------------- |
| 所有关卡及其运行顺序           | [CONTRIBUTING.md](CONTRIBUTING.md)                                    |
| 面向编码代理的同样内容         | [AGENTS.md](AGENTS.md)                                                |
| 本仓库与家族其他成员共享的标准 | [FAMILY.md](FAMILY.md)                                                |
| 错误报告                       | [GitHub Issues](https://github.com/gufranco/sms-mapper-python/issues) |
| 安全报告                       | [SECURITY.md](SECURITY.md)                                            |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 mypy==1.14.1
python3 smsmapper/console.test.py
```

每个模块旁边都有以它命名的测试文件，各自都能像上面那样单独运行。覆盖率是硬性关卡，语句和分支均为 100%。

## 参考资料

- _Software Reference Manual for the SEGA Mark III Console_，世嘉，未注明日期，重新打字的副本。45 页，184,840 字节，SHA-256 `166f09331ba9df055f7a352f10c6a7843911470bc72d9347eda4a0de86e8cfce`。它不可再分发，不在本仓库中。`python3 -m conformance.documents` 从 https://segaretro.org/images/d/d6/SoftwareReferenceManualForSegaMarkIIIEU.pdf 下载它，并拒绝任何其他文件。
- MAME 的 `src/devices/bus/sega8/rom.cpp`、`src/devices/machine/eepromser.cpp`、`hash/sms.xml` 和 `hash/gamegear.xml`，提交 `94fc55c9692b180dcb608e2e222e48315db5017a`，https://github.com/mamedev/mame ，用于每种第三方电路板以及每个映像所在的电路板。只取事实，不取代码。
- Genesis Plus GX 的 `core/io_ctrl.c`、`core/system.c` 和 `core/cart_hw/sms_cart.c`，提交 `a5834b3df455c49bb97bfaa328c20845831f576b`，https://github.com/ekeeke/Genesis-Plus-GX ，用于手册没有描述的主机。只取事实，不取代码。

## 引用

[CITATION.cff](CITATION.cff) 在每次发布时由写入包版本的脚本更新。

## 许可证

MIT。见 [LICENSE](LICENSE)。
