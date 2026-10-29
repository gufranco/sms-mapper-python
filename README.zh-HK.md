# SMS Mapper

世嘉 SG-1000 Mark III、兩款 Master System 和 Game Gear 上，處理器與其餘一切之間的電路板，以 Python 實現：記憶體映射及其插槽啟用、世嘉的分頁和 11 種第三方電路板、端口解碼和控制器端口，並以世嘉的 Mark III 參考手冊為準加以檢驗。

[English](README.md) | [日本語](README.ja.md) | [简体中文](README.zh-Hans.md) | 繁體中文（香港）

[![ci](https://img.shields.io/github/actions/workflow/status/gufranco/sms-mapper-python/ci.yml?branch=main&style=flat-square&label=ci)](https://github.com/gufranco/sms-mapper-python/actions/workflows/ci.yml)
[![release](https://img.shields.io/github/v/release/gufranco/sms-mapper-python?style=flat-square&label=release)](https://github.com/gufranco/sms-mapper-python/releases/latest)
[![coverage](https://img.shields.io/badge/coverage-100%25-brightgreen?style=flat-square)](https://github.com/gufranco/sms-mapper-python/actions/workflows/ci.yml)
[![openssf scorecard](https://img.shields.io/ossf-scorecard/github.com/gufranco/sms-mapper-python?style=flat-square&label=openssf%20scorecard)](https://scorecard.dev/viewer/?uri=github.com/gufranco/sms-mapper-python)
[![license](https://img.shields.io/github/license/gufranco/sms-mapper-python?style=flat-square&label=license)](LICENSE)

**2,608** 個不同的 Master System 和 Game Gear 映像檔各啟動 **600** 幀，在帶暫存器的電路板上的 **813** 個零售映像檔中屬性失敗為 **0**，在手冊和固定的原始碼中找到 **24** 處引文，**12** 種電路板，**845** 個測試，**100%** 語句和分支覆蓋率，除標準庫外沒有依賴套件

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

這個 256K 的虛構映像檔，每個位元組都存着自己所在的 16K 記憶庫編號。寫入 FFFF 為第 2 幀選擇記憶庫 5，而 FFFC 中的記憶庫偏移 01 按照手冊中 4 兆位元 ROM 的圖示，把每一幀向後移動 8 個記憶庫：第 2 幀落在記憶庫 13。偏移改回 00 並設定第 3 位元後，第 2 幀就是卡帶的 RAM。對 FFFC 到 FFFF 的每次寫入也會落入系統 RAM，而系統 RAM 在 DFFC 處重複出現。按下按鈕 1 會清除端口 DC 的第 4 位元，端口 3F 把兩條 TH 線設為輸出並拉低，端口 DD 在第 6 和第 7 位元讀回它們。

## 安裝

| 要求   | 版本                     |
| :----- | :----------------------- |
| Python | 3.12 或更新              |
| git    | 任何版本，用於取得子模組 |

```bash
git clone --recurse-submodules https://github.com/gufranco/sms-mapper-python.git
cd sms-mapper-python
python3 smsmapper/doctor.py
```

這個套件只匯入標準庫。子模組是 `zilog-z80-python`，只有普查和測試卡帶會用到它。從 download-zip 連結取得的原始碼封存不含子模組：在那裏普查及其測試會報告無法執行的原因，其餘一切照常運作。

doctor 檢查機器和簽出的程式碼，最後輸出一行結果。提交錯誤報告時，請貼上它的完整輸出。

```
  10 checks, nothing to report
```

發佈遵循 [Semantic Versioning](https://semver.org/)，由 semantic-release 根據提交歷史產生。每次發佈都有標籤，並列在[發佈頁面](https://github.com/gufranco/sms-mapper-python/releases)上。

## 介面

`smsmapper.Cartridge(image, board="sega", ram=0)` 在下列電路板之一上建立一個卡帶。`image` 是傾印檔保存的卡帶位元組，`ram` 是卡帶 RAM 的位元組數：0、8192、16384 或 32768。`smsmapper.Console(model=None, cartridge=None, bios=None, card=None, region=None, handheld_mode=True)` 把它連同啟動 ROM 和卡片插進主機。任何插槽都可以留空，啟動 ROM 和卡片同樣以 `Cartridge` 建立。

| 型號       | 別名                                     | 卡片插槽 | 重設按鈕 | 端口 0 到 6 |
| :--------- | :--------------------------------------- | :------- | :------- | :---------- |
| `mark-iii` | `mark3`、`markiii`、`sg-1000 mark iii`   | 有       | 無       | 無          |
| `sms`      | `master system`、`sms1`、`master-system` | 有       | 有       | 無          |
| `sms2`     | `master system ii`、`master-system-ii`   | 無       | 無       | 無          |
| `gg`       | `game gear`、`game-gear`、`gamegear`     | 無       | 無       | 有          |

`region` 為 `japan`、`usa` 或 `europe`，省略時取型號自己的地區：Mark III 為 `japan`，其餘為 `usa`。日本主機把 TH 和 TR 的每個輸出都讀回為 0，軟件藉此分辨地區；Game Gear 在端口 0 報告地區。`handheld_mode=False` 令 Game Gear 進入 Master System 模式，此時端口 0 到 6 消失，START 成為暫停按鈕。

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

### 呼叫

| 呼叫                        | 作用                                                                                                      |
| :-------------------------- | :-------------------------------------------------------------------------------------------------------- |
| `read(address)`             | 從處理器的 64K 讀取 1 個位元組，經過插槽啟用、電路板的分頁和系統 RAM                                      |
| `write(address, value)`     | 向處理器的 64K 寫入 1 個位元組。它到達所選插槽的電路板，並像分頁暫存器寫入那樣，從 C000h 起也到達系統 RAM |
| `read_port(port)`           | 從電路板應答的端口讀取 1 個位元組：端口 DC 和 DD，以及 Game Gear 的端口 0 到 6。無人應答之處為 FFh        |
| `write_port(port, value)`   | 向電路板接收的端口寫入 1 個位元組：3E、3F 和 Game Gear 的端口。無人接收的寫入會被捨棄                     |
| `press(button, player=1)`   | 按住一個按鈕：`up`、`down`、`left`、`right`、`1`、`2`，以及主機的 `pause`、`reset` 和 `start`             |
| `release(button, player=1)` | 放開它                                                                                                    |

到達視訊部件或聲音產生器的端口會拋出 `NotOnBoardError`，因為它們由 `sega-vdp-python` 應答，而不是由電路板應答。`smsmapper.ports.decode(model, port, direction)` 說明任何端口到達甚麼。

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

### 狀態

| 屬性                     | 含義                                                                                           |
| :----------------------- | :--------------------------------------------------------------------------------------------- |
| `nmi`                    | 暫停按鈕保持處理器的不可遮罩中斷線時為真，Game Gear 在 Master System 模式下按住 START 時亦為真 |
| `latches`                | TH 線由低變高的次數，每次都請視訊部件鎖存其計數器                                              |
| `memory.control`         | 端口 3E 的最後一個值：插槽啟用，低電平有效                                                     |
| `memory.ram`             | 8K 的系統 RAM                                                                                  |
| `memory.cartridge`       | 卡帶，即 `Cartridge` 建立的電路板。`card`、`bios` 和 `expansion` 是其他插槽                    |
| `controllers.io_control` | 主機保存的端口 3F 的最後一個值                                                                 |
| `model`                  | `Model` 記錄                                                                                   |

`Cartridge` 建立的電路板具有：處理器 64K 上的 `read(address)` 和 `write(address, value)`，說明寫入該處是否到達其暫存器的 `decodes(address)`，指出每個視窗顯示哪個記憶庫的 `banks`，以及 `ram`、`image`、`pages`、`name` 和 `reset()`。93C46 電路板還有 `eeprom.words`，即它的 64 個 16 位元字。

### 模組內容

| 名稱                           | 內容                                             |
| :----------------------------- | :----------------------------------------------- |
| `smsmapper.BOARDS`             | 按名稱列出每種電路板，並說明它是甚麼             |
| `smsmapper.MODELS`             | 以標準名稱為鍵的 4 條 `Model` 記錄               |
| `smsmapper.Board`              | 每種電路板的基礎                                 |
| `smsmapper.UnknownBoardError`  | 電路板名稱不在套件中時拋出。訊息列出可接受的名稱 |
| `smsmapper.UnknownModelError`  | 主機名稱不在套件中時拋出                         |
| `smsmapper.UnknownRegionError` | 地區不是 `japan`、`usa` 或 `europe` 時拋出       |
| `smsmapper.EmptyImageError`    | 映像檔中沒有任何內容時拋出                       |
| `smsmapper.RamSizeError`       | 卡帶 RAM 的大小沒有任何電路板採用時拋出          |
| `smsmapper.SlotError`          | 把卡片交給沒有卡片插槽的主機時拋出               |
| `smsmapper.NotOnBoardError`    | 端口由視訊部件或聲音產生器應答時拋出             |
| `smsmapper.__version__`        | 已安裝的版本                                     |

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

### 模組

| 模組                    | 內容                                                        |
| :---------------------- | :---------------------------------------------------------- |
| `smsmapper.sega`        | 世嘉的分頁、記憶庫偏移和卡帶 RAM                            |
| `smsmapper.codemasters` | Codemasters 的分頁及其 8K RAM                               |
| `smsmapper.korean`      | Korean、無分頁、188 合 1、Janggun、Zemina 和 Nemesis 電路板 |
| `smsmapper.multicart`   | 4 PAK、Hi-Com 和 Seo Jin 合卡                               |
| `smsmapper.eeprom`      | 93C46 EEPROM 及搭載它的世嘉電路板                           |
| `smsmapper.memory`      | 處理器的 64K：插槽、端口 3E 的啟用和系統 RAM                |
| `smsmapper.ports`       | 按主機區分，每個端口到達哪個裝置                            |
| `smsmapper.controllers` | 端口 DC 和 DD，以及端口 3F 的方向和電平                     |
| `smsmapper.console`     | 以上全部，再加上 Game Gear 的端口和主機的按鈕               |
| `smsmapper.models`      | 4 款主機                                                    |

## 世嘉的分頁

手冊在記憶體頂部列出 4 個暫存器。FFFD、FFFE 和 FFFF 選擇三個幀各自顯示的 16K 記憶庫，FFFC 保存其餘內容：

| FFFC 的位元 | 手冊所說                  | 本套件的做法                                      |
| :---------- | :------------------------ | :------------------------------------------------ |
| 0 和 1      | 記憶庫編號偏移            | 按 4 兆位元 ROM 的圖示，每級為每一幀加 8 個記憶庫 |
| 2           | 外部 RAM 的記憶庫編號     | 選擇第 2 幀顯示卡帶 RAM 的哪 16K                  |
| 3           | 第 2 幀中的 ROM 或 RAM    | 卡帶有 RAM 時，把它放在第 2 幀                    |
| 4           | 附問號的 RAM 寫入保護開關 | 不做任何事                                        |
| 7           | 開發板的寫入保護          | 不做任何事                                        |

最初的 1K 永不移動，所以重設和中斷向量始終在那裏。對 FFFC 到 FFFF 的每次寫入亦會寫進系統 RAM，因此軟件從那裏讀回暫存器的值。

關於偏移，有兩個實現與手冊不一致，[`conformance/divergences.json`](conformance/divergences.json) 記錄了兩者：MAME 忽略它，Genesis Plus GX 朝相反方向偏移。普查統計哪些映像檔設定了偏移。

## 普查

```bash
python3 -m conformance.census "external/Master EverDrive" "external/EverDrive GG" --frames 600 --jobs 12
```

普查把 Master System 和 Game Gear 卡帶庫中的每個映像檔，放在 MAME 軟件清單為其指定的電路板上，在 `zilog-z80-python` 處理器後面啟動，並統計到達電路板暫存器的每次寫入。`.sms` 映像檔在 Master System 上執行，`.gg` 映像檔在 Game Gear 上執行。只被歐洲合集收錄的映像檔在歐洲版主機上執行，其 50 Hz 的一幀為 313 行；其餘映像檔在 262 行的美國版主機上執行。有些歐洲卡帶在開機時量度一幀的長度，在 60 Hz 主機上會停住，因此只在 50 Hz 下分頁。視訊部件是一個替身，只計行數、發出幀中斷和行中斷並應答計數器，因為普查關心的是分頁，而不是畫面。它接受目錄、ZIP 封存和單一映像檔，按摘要把每個不同的映像檔只計一次，列印摘要，寫出 [`conformance/corpus.json`](conformance/corpus.json)，並在某項性質被破壞時以 1 結束。

執行由兩項性質把關：模型在任何映像檔上都不拋出例外，以及位於有暫存器的電路板上、大於 48K 的每個零售映像檔，在幀數上限內寫入其中某個暫存器。不分頁的卡帶無法顯示前 48K 之後的內容，所以保持沉默的零售映像檔意味着本套件把電路板弄錯了。[`conformance/boards.json`](conformance/boards.json) 按 MAME 軟件清單的記錄，以整個檔案的 SHA-1 列出建於其他電路板上的映像檔。Master Gear 轉接器和 X-Terminator 作弊裝置沒有建模，因此這些映像檔在世嘉的分頁上執行並另行計算。

| 上次執行的結果                                     | 數量                  |
| :------------------------------------------------- | :-------------------- |
| 兩個卡帶庫中的項目                                 | 17,329                |
| 不同的映像檔                                       | 2,608                 |
| 帶暫存器的電路板上的零售映像檔，參與把關           | 813                   |
| 在歐洲版主機上執行，每幀 313 行                    | 233                   |
| `4pak` 上的映像檔，以及其中寫過暫存器的數量        | 1 個中的 1 個         |
| `codemasters` 上的映像檔，以及其中寫過暫存器的數量 | 21 個中的 21 個       |
| `eeprom` 上的映像檔，以及其中寫過暫存器的數量      | 7 個中的 7 個         |
| `hicom` 上的映像檔，以及其中寫過暫存器的數量       | 9 個中的 3 個         |
| `janggun` 上的映像檔，以及其中寫過暫存器的數量     | 1 個中的 1 個         |
| `korean` 上的映像檔，以及其中寫過暫存器的數量      | 6 個中的 4 個         |
| `korean_nb` 上的映像檔，以及其中寫過暫存器的數量   | 5 個中的 0 個         |
| `nemesis` 上的映像檔，以及其中寫過暫存器的數量     | 1 個中的 1 個         |
| `sega` 上的映像檔，以及其中寫過暫存器的數量        | 2,549 個中的 2,293 個 |
| `zemina` 上的映像檔，以及其中寫過暫存器的數量      | 8 個中的 8 個         |
| 設定過 FFFC 的記憶庫偏移                           | 21                    |
| 透過 FFFC 第 3 位元啟用卡帶 RAM                    | 185                   |
| 透過 FFFC 第 2 位元選擇第二個 RAM 記憶庫           | 20                    |
| 選擇過超出映像檔末端的記憶庫                       | 294                   |
| 從未寫過電路板暫存器                               | 269                   |
| 在本套件未建模的電路板上                           | 0                     |

[`conformance/corpus.json`](conformance/corpus.json) 只保存這些計數，不含任何卡帶的內容，因此測試套件在沒有卡帶庫的機器上也能檢查它們。

## 測試卡帶

```bash
python3 -m conformance.testroms "/path/to/5 Tools & Service Test Carts.zip"
```

[`conformance/testroms.json`](conformance/testroms.json) 按 SHA-256 列出檢驗這塊電路板的每個測試卡帶、每次執行所按的控制器操作腳本，以及它列印的內容。每個都在普查的測試裝置上執行，畫面內容從替身的視訊記憶體中讀出。

| 卡帶                                           | 執行環境                           | 記錄的內容                                                                       |
| :--------------------------------------------- | :--------------------------------- | :------------------------------------------------------------------------------- |
| Test Suite 0.32，sverx 製作                    | Master System，海外版和日本版      | 其 System Info 頁面根據端口 3F 和 3E 回答 JPN? 為 No 和 Yes，MediaEnable? 為 Yes |
| SMS Paging PFR Detect 2.00，Eric R. Quinn 製作 | 配備 32K 卡帶 RAM 的 Master System | 最初的 1K 固定，三個幀的其餘部分可分頁，兩個備份頁都存在，測試完成               |

Test Suite 的 Model 和 VDP? 兩行是視訊部件的替身作答，而不是本套件，所以記錄保留它們只為看到變化。

## 是否正確

世嘉印刷的事實中，凡是測試能觸及的，都以程式碼為準加以檢驗。[`conformance/hardware.json`](conformance/hardware.json) 保存每條事實及其原句和頁碼，[`conformance/hardware.test.py`](conformance/hardware.test.py) 據此驅動本套件。`python3 -m conformance.quotes` 在手冊中找到每個被引用的句子，並在固定版本的 MAME 和 Genesis Plus GX 簽出中找到每行被引用的程式碼。

手冊沒有印出的每個值都在同一檔案的 `notStated` 下，標為未經驗證，並寫明來源和能夠定論的測量。[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) 列出它們。各來源互相矛盾之處在 [`conformance/divergences.json`](conformance/divergences.json) 中。

## 參與開發

| 需要                             | 位置                                                                  |
| :------------------------------- | :-------------------------------------------------------------------- |
| 所有關卡及其執行次序             | [CONTRIBUTING.md](CONTRIBUTING.md)                                    |
| 面向編碼代理的同樣內容           | [AGENTS.md](AGENTS.md)                                                |
| 本儲存庫與家族其他成員共用的標準 | [FAMILY.md](FAMILY.md)                                                |
| 錯誤報告                         | [GitHub Issues](https://github.com/gufranco/sms-mapper-python/issues) |
| 安全報告                         | [SECURITY.md](SECURITY.md)                                            |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 mypy==1.14.1
python3 smsmapper/console.test.py
```

每個模組旁邊都有以它命名的測試檔，各自都能像上面那樣單獨執行。覆蓋率是硬性關卡，語句和分支均為 100%。

## 參考資料

- _Software Reference Manual for the SEGA Mark III Console_，世嘉，未註明日期，重新打字的副本。45 頁，184,840 位元組，SHA-256 `166f09331ba9df055f7a352f10c6a7843911470bc72d9347eda4a0de86e8cfce`。它不可再分發，不在本儲存庫中。`python3 -m conformance.documents` 從 https://segaretro.org/images/d/d6/SoftwareReferenceManualForSegaMarkIIIEU.pdf 下載它，並拒絕任何其他檔案。
- MAME 的 `src/devices/bus/sega8/rom.cpp`、`src/devices/machine/eepromser.cpp`、`hash/sms.xml` 和 `hash/gamegear.xml`，提交 `94fc55c9692b180dcb608e2e222e48315db5017a`，https://github.com/mamedev/mame ，用於每種第三方電路板以及每個映像檔所在的電路板。只取事實，不取程式碼。
- Genesis Plus GX 的 `core/io_ctrl.c`、`core/system.c` 和 `core/cart_hw/sms_cart.c`，提交 `a5834b3df455c49bb97bfaa328c20845831f576b`，https://github.com/ekeeke/Genesis-Plus-GX ，用於手冊沒有描述的主機。只取事實，不取程式碼。

## 引用

[CITATION.cff](CITATION.cff) 在每次發佈時由寫入套件版本的腳本更新。

## 授權

MIT。見 [LICENSE](LICENSE)。
