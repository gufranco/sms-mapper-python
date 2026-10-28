# SMS Mapper

Sega の SG-1000 Mark III、2 機種のマスターシステム、ゲームギアで、プロセッサとそれ以外のすべての間にあるボードを Python で実装したものです。メモリマップとスロットの有効化、Sega のページングと 11 種類のサードパーティ製ボード、ポートのデコード、コントローラポートを、Sega の Mark III リファレンスマニュアルに照らして検証しています。

[English](README.md) | 日本語 | [简体中文](README.zh-Hans.md) | [繁體中文（香港）](README.zh-HK.md)

[![CI](https://github.com/gufranco/sms-mapper-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/sms-mapper-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/sms-mapper-python)](https://github.com/gufranco/sms-mapper-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

異なるマスターシステムとゲームギアのイメージ **2,608** 本をそれぞれ **600** フレーム起動、レジスタのあるボードに載った市販の **813** 本で性質の不合格 **0** 件、マニュアルと固定したソースで所在を確認した引用 **24** 件、ボード **12** 種、テスト **845** 件、ステートメントとブランチのカバレッジ **100%**、標準ライブラリ以外への依存関係なし

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

この 256K の架空のイメージは、各バイトに自分の 16K バンク番号を持っています。FFFF への書き込みでフレーム 2 にバンク 5 を選び、FFFC のバンクシフト 01 で、マニュアルの 4 メガビット ROM の図のとおりすべてのフレームが 8 バンク先へ移るので、フレーム 2 はバンク 13 になります。シフトを 00 に戻してビット 3 を立てると、フレーム 2 はカートリッジの RAM になります。FFFC から FFFF への書き込みはすべてシステム RAM にも入り、システム RAM は DFFC にも現れます。ボタン 1 を押すとポート DC のビット 4 が下がり、ポート 3F は 2 本の TH ラインを出力として Low にし、それをポート DD がビット 6 と 7 で読み返します。

## インストール

| 要件   | バージョン                         |
| :----- | :--------------------------------- |
| Python | 3.12 以降                          |
| git    | サブモジュールの取得に、どれでも可 |

```bash
git clone --recurse-submodules https://github.com/gufranco/sms-mapper-python.git
cd sms-mapper-python
python3 smsmapper/doctor.py
```

パッケージは標準ライブラリ以外を何も import しません。サブモジュールは `zilog-z80-python` で、使うのは全数調査とテストカートリッジだけです。download-zip リンクから得たソースアーカイブにはサブモジュールがなく、そこでは全数調査とそのテストが動かない理由を報告し、それ以外はすべて動きます。

doctor はマシンとチェックアウトを調べ、最後に 1 行を出力します。バグ報告には出力全体を貼り付けてください。

```
  10 checks, nothing to report
```

リリースは [Semantic Versioning](https://semver.org/) に従い、semantic-release がコミット履歴から切り出します。すべてのリリースにはタグが付き、[リリースページ](https://github.com/gufranco/sms-mapper-python/releases) に載ります。

## インターフェース

`smsmapper.Cartridge(image, board="sega", ram=0)` は、下のボードのどれかに載ったカートリッジを作ります。`image` はダンプが保持するとおりのカートリッジのバイト列、`ram` はバイト単位のカートリッジ RAM で、0、8192、16384、32768 のいずれかです。`smsmapper.Console(model=None, cartridge=None, bios=None, card=None, region=None, handheld_mode=True)` はそれをブート ROM とカードとともに本体に挿します。どのスロットも空でかまわず、ブート ROM とカードも `Cartridge` で作ります。

| モデル     | 別名                                     | カードスロット | リセットボタン | ポート 0 から 6 |
| :--------- | :--------------------------------------- | :------------- | :------------- | :-------------- |
| `mark-iii` | `mark3`、`markiii`、`sg-1000 mark iii`   | あり           | なし           | なし            |
| `sms`      | `master system`、`sms1`、`master-system` | あり           | あり           | なし            |
| `sms2`     | `master system ii`、`master-system-ii`   | なし           | なし           | なし            |
| `gg`       | `game gear`、`game-gear`、`gamegear`     | なし           | なし           | あり            |

`region` は `japan`、`usa`、`europe` のいずれかで、省略するとモデル自身の地域、つまり Mark III では `japan`、それ以外では `usa` になります。日本の本体は TH と TR の出力をすべて 0 として読み返し、ソフトウェアはそれで地域を見分けます。ゲームギアはポート 0 で地域を報告します。`handheld_mode=False` にするとゲームギアはマスターシステムモードになり、ポート 0 から 6 が消え、START がポーズボタンになります。

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

### 呼び出し

| 呼び出し                    | 効果                                                                                                                                        |
| :-------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------ |
| `read(address)`             | プロセッサの 64K から 1 バイト。スロットの有効化、ボードのページング、システム RAM を経由します                                             |
| `write(address, value)`     | プロセッサの 64K へ 1 バイト。選ばれたスロットのボードに届き、C000h 以上ではページングレジスタへの書き込みと同じくシステム RAM にも届きます |
| `read_port(port)`           | ボードが応答するポートから 1 バイト。ポート DC と DD、ゲームギアのポート 0 から 6 です。何も応答しないところは FFh                          |
| `write_port(port, value)`   | ボードが受け取るポートへ 1 バイト。3E、3F、ゲームギアのポートです。誰も受け取らない書き込みは捨てられます                                   |
| `press(button, player=1)`   | ボタンを押したままにします。`up`、`down`、`left`、`right`、`1`、`2`、本体の `pause`、`reset`、`start` です                                  |
| `release(button, player=1)` | 離します                                                                                                                                    |

ビデオパートかサウンドジェネレータに届くポートは `NotOnBoardError` を送出します。それらはボードではなく `sega-vdp-python` が応答するからです。`smsmapper.ports.decode(model, port, direction)` は、どのポートが何に届くかを答えます。

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

### 状態

| 属性                     | 意味                                                                                                                                  |
| :----------------------- | :------------------------------------------------------------------------------------------------------------------------------------ |
| `nmi`                    | ポーズボタンがプロセッサのノンマスカブルラインを保持している間、またはマスターシステムモードのゲームギアで START が押されている間は真 |
| `latches`                | TH ラインが Low から High になった回数。そのたびにビデオパートにカウンタのラッチを求めます                                            |
| `memory.control`         | ポート 3E の最後の値。スロットの有効化で、アクティブ Low です                                                                         |
| `memory.ram`             | 8K のシステム RAM                                                                                                                     |
| `memory.cartridge`       | カートリッジ、つまり `Cartridge` が作ったボード。`card`、`bios`、`expansion` がほかのスロットです                                     |
| `controllers.io_control` | 本体が保持しているとおりのポート 3F の最後の値                                                                                        |
| `model`                  | `Model` レコード                                                                                                                      |

`Cartridge` が作るボードには、プロセッサの 64K に対する `read(address)` と `write(address, value)`、そこへの書き込みがレジスタに届くかを答える `decodes(address)`、各ウィンドウが見せるバンクを名指す `banks`、`ram`、`image`、`pages`、`name`、`reset()` があります。93C46 のボードには、64 個の 16 ビットワードである `eeprom.words` もあります。

### モジュールの内容

| 名前                           | 内容                                                                         |
| :----------------------------- | :--------------------------------------------------------------------------- |
| `smsmapper.BOARDS`             | すべてのボードを名前で引き、それが何であるかを添えたもの                     |
| `smsmapper.MODELS`             | 正式名をキーとする 4 つの `Model` レコード                                   |
| `smsmapper.Board`              | すべてのボードの土台                                                         |
| `smsmapper.UnknownBoardError`  | パッケージにないボード名で送出されます。メッセージに受け付ける名前を並べます |
| `smsmapper.UnknownModelError`  | パッケージにない本体名で送出されます                                         |
| `smsmapper.UnknownRegionError` | `japan`、`usa`、`europe` 以外の地域で送出されます                            |
| `smsmapper.EmptyImageError`    | 中身のないイメージで送出されます                                             |
| `smsmapper.RamSizeError`       | どのボードも積んでいない大きさのカートリッジ RAM で送出されます              |
| `smsmapper.SlotError`          | カードスロットのない本体にカードを渡すと送出されます                         |
| `smsmapper.NotOnBoardError`    | ビデオパートかサウンドジェネレータが応答するポートで送出されます             |
| `smsmapper.__version__`        | インストールされているバージョン                                             |

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

### モジュール

| モジュール              | 内容                                                              |
| :---------------------- | :---------------------------------------------------------------- |
| `smsmapper.sega`        | Sega のページング、バンクシフト、カートリッジ RAM                 |
| `smsmapper.codemasters` | Codemasters のページングと 8K の RAM                              |
| `smsmapper.korean`      | Korean、ノーバンク、188-in-1、Janggun、Zemina、Nemesis の各ボード |
| `smsmapper.multicart`   | 4 PAK、Hi-Com、Seo Jin のマルチカート                             |
| `smsmapper.eeprom`      | 93C46 EEPROM と、それを積む Sega のボード                         |
| `smsmapper.memory`      | プロセッサの 64K。スロット、ポート 3E の有効化、システム RAM      |
| `smsmapper.ports`       | 本体ごとに、どのポートがどのデバイスに届くか                      |
| `smsmapper.controllers` | ポート DC と DD、ポート 3F の方向とレベル                         |
| `smsmapper.console`     | そのすべてに、ゲームギアのポートと本体のボタンを加えたもの        |
| `smsmapper.models`      | 4 つの本体                                                        |

## Sega のページング

マニュアルはメモリの最上位に 4 つのレジスタを載せています。FFFD、FFFE、FFFF は 3 つのフレームそれぞれが見せる 16K バンクを選び、FFFC が残りを持ちます。

| FFFC のビット | マニュアルの記述                      | このパッケージの動作                                                      |
| :------------ | :------------------------------------ | :------------------------------------------------------------------------ |
| 0 と 1        | バンク番号シフト                      | 4 メガビット ROM の図のとおり、すべてのフレームに 1 段ごとに 8 バンク足す |
| 2             | 外部 RAM のバンク番号                 | フレーム 2 がカートリッジ RAM のどちらの 16K を見せるかを選ぶ             |
| 3             | フレーム 2 の ROM と RAM の切り替え   | カートリッジに RAM があれば、フレーム 2 をその RAM にする                 |
| 4             | 疑問符つきの RAM 書き込み保護スイッチ | 何もしない                                                                |
| 7             | 開発ボードの書き込み保護              | 何もしない                                                                |

最初の 1K は動かないので、リセットと割り込みのベクタは常にそこにあります。FFFC から FFFF への書き込みはどれもシステム RAM にも書かれるので、ソフトウェアはレジスタの値をそこから読み返します。

シフトについては 2 つの実装がマニュアルと食い違い、[`conformance/divergences.json`](conformance/divergences.json) が両方を記録しています。MAME はシフトを無視し、Genesis Plus GX は逆向きにずらします。全数調査はどのイメージがシフトを設定するかを数えます。

## 全数調査

```bash
python3 -m conformance.census "external/Master EverDrive" "external/EverDrive GG" --frames 600 --jobs 12
```

全数調査は、マスターシステムとゲームギアのライブラリにあるすべてのイメージを、MAME のソフトウェアリストが指定するボードに載せ、`zilog-z80-python` プロセッサの後ろで起動し、ボードのレジスタに届いた書き込みをすべて数えます。`.sms` イメージはマスターシステムで、`.gg` イメージはゲームギアで動きます。ヨーロッパのセットだけに載っているイメージはヨーロッパ版の本体で動き、その 50 Hz のフレームは 313 ラインです。それ以外のイメージは 262 ラインのアメリカ版の本体で動きます。ヨーロッパのカートリッジには電源投入時にフレームの長さを測り、60 Hz の本体では止まるものがあり、それらは 50 Hz でしかページングしません。ビデオパートは代役で、ラインを数え、フレーム割り込みとライン割り込みを上げ、カウンタに答えるだけです。全数調査が問うのは画像ではなくページングだからです。ディレクトリ、ZIP アーカイブ、単体のイメージを受け付け、異なるイメージをダイジェストで 1 回ずつ数え、要約を出力し、[`conformance/corpus.json`](conformance/corpus.json) を書き出し、性質が破れると 1 で終了します。

実行を判定する性質は 2 つです。どのイメージでもモデルが例外を送出しないこと、そしてレジスタを持つボード上の 48K を超える市販イメージが、フレームの上限内にそのレジスタのどれかに書き込むことです。ページングしないカートリッジは最初の 48K より先を見せられないので、黙ったままの市販イメージはこのパッケージがボードを間違えていることを意味します。[`conformance/boards.json`](conformance/boards.json) は、MAME のソフトウェアリストの記録に従い、別のボードで作られたイメージをファイル全体の SHA-1 で挙げています。Master Gear アダプタと X-Terminator チートデバイスはモデル化していないので、それらのイメージは Sega のページングで動かし、別に数えます。

| 直近の実行の結果                                             | 件数                |
| :----------------------------------------------------------- | :------------------ |
| 2 つのライブラリにある項目                                   | 17,329              |
| 異なるイメージ                                               | 2,608               |
| レジスタのあるボードに載った市販イメージ。判定の対象です     | 813                 |
| ヨーロッパ版の本体で動かしたもの。1 フレーム 313 ライン      | 233                 |
| `4pak` のイメージと、そのうちレジスタに書き込んだもの        | 1 本中 1 本         |
| `codemasters` のイメージと、そのうちレジスタに書き込んだもの | 21 本中 21 本       |
| `eeprom` のイメージと、そのうちレジスタに書き込んだもの      | 7 本中 7 本         |
| `hicom` のイメージと、そのうちレジスタに書き込んだもの       | 9 本中 3 本         |
| `janggun` のイメージと、そのうちレジスタに書き込んだもの     | 1 本中 1 本         |
| `korean` のイメージと、そのうちレジスタに書き込んだもの      | 6 本中 4 本         |
| `korean_nb` のイメージと、そのうちレジスタに書き込んだもの   | 5 本中 0 本         |
| `nemesis` のイメージと、そのうちレジスタに書き込んだもの     | 1 本中 1 本         |
| `sega` のイメージと、そのうちレジスタに書き込んだもの        | 2,549 本中 2,293 本 |
| `zemina` のイメージと、そのうちレジスタに書き込んだもの      | 8 本中 8 本         |
| FFFC のバンクシフトを設定したもの                            | 21                  |
| FFFC のビット 3 でカートリッジ RAM を有効にしたもの          | 185                 |
| FFFC のビット 2 で 2 つ目の RAM バンクを選んだもの           | 20                  |
| イメージの末尾より先のバンクを選んだもの                     | 294                 |
| ボードのレジスタに一度も書き込まなかったもの                 | 269                 |
| このパッケージがモデル化していないボードのもの               | 0                   |

[`conformance/corpus.json`](conformance/corpus.json) はこれらの件数だけを持ち、どのカートリッジの中身も持たないので、ライブラリのないマシンでもテストスイートがそれを確かめます。

## テストカートリッジ

```bash
python3 -m conformance.testroms "/path/to/5 Tools & Service Test Carts.zip"
```

[`conformance/testroms.json`](conformance/testroms.json) は、このボードを試すすべてのテストカートリッジを SHA-256 で挙げ、各実行で押すコントローラ操作の台本と、表示された内容を記録しています。どれも全数調査のハーネスで動かし、画面は代役のビデオメモリから読み取ります。

| カートリッジ                                 | 実行した環境                                    | 記録の内容                                                                                         |
| :------------------------------------------- | :---------------------------------------------- | :------------------------------------------------------------------------------------------------- |
| Test Suite 0.32、sverx 作                    | マスターシステム、海外版と日本版                | System Info ページが、ポート 3F と 3E から JPN? に No と Yes、MediaEnable? に Yes と答える         |
| SMS Paging PFR Detect 2.00、Eric R. Quinn 作 | 32K のカートリッジ RAM を積んだマスターシステム | 最初の 1K は固定、3 つのフレームの残りはページング可能、2 つのバックアップページがあり、テスト完了 |

Test Suite の Model と VDP? の行は、このパッケージではなくビデオパートの代役が答えたものなので、記録は変化を見るためだけにそれを残しています。

## 正しいかどうか

Sega が印刷した事実のうちテストで到達できるものは、すべてコードに照らして保たれています。[`conformance/hardware.json`](conformance/hardware.json) は各事実をその文とページとともに持ち、[`conformance/hardware.test.py`](conformance/hardware.test.py) がそれに照らしてパッケージを動かします。`python3 -m conformance.quotes` は引用された文をすべてマニュアルの中で、引用されたコードの行をすべて固定した MAME と Genesis Plus GX のチェックアウトの中で見つけます。

マニュアルが印刷していない値はすべて同じファイルの `notStated` にあり、未検証と記され、出所と、それを決着させる測定が書かれています。[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) がそれを並べます。情報源が食い違う箇所は [`conformance/divergences.json`](conformance/divergences.json) にあります。

## 開発に参加する

| 必要なもの                               | 場所                                                                  |
| :--------------------------------------- | :-------------------------------------------------------------------- |
| すべてのゲートとその実行順               | [CONTRIBUTING.md](CONTRIBUTING.md)                                    |
| 同じ内容をコーディングエージェント向けに | [AGENTS.md](AGENTS.md)                                                |
| このリポジトリがファミリーと共有する標準 | [FAMILY.md](FAMILY.md)                                                |
| バグ報告                                 | [GitHub Issues](https://github.com/gufranco/sms-mapper-python/issues) |
| セキュリティ報告                         | [SECURITY.md](SECURITY.md)                                            |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 mypy==1.14.1
python3 smsmapper/console.test.py
```

各モジュールには、その名を持つテストファイルが隣にあり、上のようにそれぞれ単独で動きます。カバレッジはステートメントとブランチの 100% が必須のゲートです。

## 参考文献

- _Software Reference Manual for the SEGA Mark III Console_、Sega、日付なし、打ち直しの写し。45 ページ、184,840 バイト、SHA-256 `166f09331ba9df055f7a352f10c6a7843911470bc72d9347eda4a0de86e8cfce`。再配布できないので、このリポジトリには入っていません。`python3 -m conformance.documents` が https://segaretro.org/images/d/d6/SoftwareReferenceManualForSegaMarkIIIEU.pdf からダウンロードし、ほかのファイルは拒否します。
- MAME の `src/devices/bus/sega8/rom.cpp`、`src/devices/machine/eepromser.cpp`、`hash/sms.xml`、`hash/gamegear.xml`、コミット `94fc55c9692b180dcb608e2e222e48315db5017a`、https://github.com/mamedev/mame 。すべてのサードパーティ製ボードと、各イメージが載るボードのために。事実のみで、コードは取り込んでいません。
- Genesis Plus GX の `core/io_ctrl.c`、`core/system.c`、`core/cart_hw/sms_cart.c`、コミット `a5834b3df455c49bb97bfaa328c20845831f576b`、https://github.com/ekeeke/Genesis-Plus-GX 。マニュアルが扱わない本体のために。事実のみで、コードは取り込んでいません。

## 引用

[CITATION.cff](CITATION.cff) は、パッケージのバージョンを刻むスクリプトがリリースごとに更新します。

## ライセンス

MIT。[LICENSE](LICENSE) を参照してください。
