# 20/26 StageExt loader 6502静的解析

解析日: 2026-07-19
対象: `magatu_skc/core/stage_ext.py`、`panel_monster_stage_variant.py`、`fire2_item_runtime.py`、`solomon_seal_block.py`、`m66_expander.py`、`saver.py`
一次資料: 現行Python実装、現行mapper66検証ROM、正式ROM/RAM管理簿

## 結論

StageExtは、16B headerと64 room×8B entryをPRG1へ保持し、mapper66 room loadの末尾で現在roomの設定をRAMへ展開する基盤である。現行保存ROMではStageExt単体91B loaderではなく、同じ副作用を維持したPanel Variant版85Bと、その前段のSpecial Item helper 140Bが実効経路になる。

table pointer、全64 room、loader chain、bank内CPU/file対応、A/X/Y、Carry、zero-page、stack、全RAM consumerを追跡した。6502本体の確定バグは見つからなかった。確定したPython読込み検証バグ1件は修正した。

- `read_runtime_room_flags()`はMAGICだけを検査し、formatとentry sizeを検査しない。非対応headerでもruntime flagを先に読み、level load時の特殊item復元へ使ってしまう。

通常のアプリが生成したformat 2のmapper66 ROMではtable、実効loader、gameplay flag helper、Special Item前段の全byteが現行定数と一致し、roomごとのcacheは正しく構築される。header検証を共通化し、runtime flag readerもformatとentry sizeを検査するよう修正した。ROM/RAM配置と6502 byte列は変更していない。

## StageExt table形式

tableはfile `0x8800-0x8A0F`の528Bである。PRG1 CPU空間ではheaderが`$87F0-$87FF`、room entryが`$8800-$89FF`になる。

headerは次の16Bである。

```text
MGSTGEXT 02 08 40 00 FF FF FF FF
```

format=2、entry size=8、room count=64である。各entryは次の構造を持つ。

| byte | 内容 | runtime copy先 |
|---:|---|---:|
| 0 | StageExt flags | bit4→`$077A bit7`、bit5/6→`$0770 bit5/4` |
| 1 | fire reset value | 現行6502 loaderでは未使用 |
| 2 | 鍵持ち初期敵slot | `$072B` |
| 3 | 落下死妖精化初期敵slot | `$077E` |
| 4 | announcement id | 現行開始画面runtimeは別tableを使用 |
| 5 | announcement flags | 現行開始画面runtimeは別tableを使用 |
| 6 | Room Flags cache | `$0778` |
| 7 | 特殊扉cell | `$077C` |

未指定entryはflags=0、key/fairy slot=`$FF`、他=0である。最初のentryはfile `0x8810`、最後は`0x8A08-0x8A0F`に収まり、直後`0x8A10`からloader slotが始まる。

## loader入口と最終chain

mapper66 l_a2 loaderのfile `0x80C4`、CPU `$80B4`にある元の`RTS / 00 / 00`を`JMP $8A00`へ置換する。現行save順は次である。

1. `stage_ext.apply_runtime_loader()`がStageExt単体slotを書く。
2. Panel Variant writerが同じ96B slotを、StageExt副作用を含む85B版へ置換する。
3. Special Item writerがslot先頭3Bを`JMP $9270`へ置換し、前段helperの末尾へPanel版85Bを連結する。

実効経路は次になる。

```text
l_a2 loader tail $80B4
  -> JMP $8A00
  -> JMP $9270                 Special Item 140B helper
  -> StageExt/Panel 85B body
  -> JMP $8A66                 gameplay flag helper 22B
  -> JMP $8FDB                 Transparent Seal suppress helper
  -> RTS                       l_a2呼出元へ復帰
```

全段がJMPでtail-chainされ、最後のRTSだけが元のl_a2呼出frameを消費する。追加のJSR/RTS不均衡はない。

## 初期化されるruntime RAM

StageExt/Panel bodyはroomごとに次を初期化する。

| RAM | 初期値/入力 | 用途 |
|---:|---:|---|
| `$072A` | `$FF` | 鍵持ち敵の実行slot未bind |
| `$077F` | `$FF` | 妖精化敵の実行slot未bind |
| `$0723` | 0 | drop tile+1 |
| `$0724` | 0 | drop active |
| `$0729` | 0 | 初期敵count |
| `$077A` | 0後、entry bit4をbit7へ | Final Stage Redirect |
| `$077D` | 0後、別64B tableからroom値 | Seal block state |
| `$072B` | entry byte2 | 鍵持ち初期敵slot |
| `$077E` | entry byte3 | 妖精化初期敵slot |
| `$0778` | entry byte6 | Room Flags |
| `$077C` | entry byte7 | 特殊扉cell |
| `$0770` | entry bit5/6から再構築 | Warp Mirror / Enemy Clear Key Open |

前roomの発火済みlatchやbind結果を持ち越さない。`$0770`はbit5をそのまま残し、bit6を2回LSRしてbit4へ移し、ORして書くため、Warp Mirror cooldown bit6とEnemy Clear発火済みbit7もroom開始時にclearされる。

## room×8 pointer計算

Xには`$0428`の0-based room番号を保持する。pointer `$00/$01`は次で作る。

```asm
LDA $0428       ; Panel版はXからTXA
ASL A
ASL A
ASL A
STA $00
LDA #$88
ADC #$00
STA $01
```

3回目のASL後のCarryは元room番号bit5である。room 0～31は`$8800-$88F8`、room 32～63はhigh byteが1増えて`$8900-$89F8`となる。64 room全てについて計算値と`$8800 + room*8`が一致した。

ADC前にCLCを置かないのは意図的で、ASLのCarryをhigh byteへ渡すためである。room番号はXに残り、後段のSeal table `$8E9B,X`とTransparent Seal helperの4 table参照に使われる。

## register、flag、zero-page契約

- Aは初期化値、entry値、flag変換に使い、呼出元への保存契約はない。
- Xは現在room番号として最後のTransparent Seal helperまで維持する。
- Yはentry offset 0/2/3/6/7とSpecial Item copyに使用し、保存契約はない。
- `$00/$01`はStageExt entry pointerであり、後段gameplay helperも同じpointerを使用する。
- room×8計算のCarryはpointer high byteへ意図的に伝播する。
- gameplay helperのLSR後Carryは使用せず、最後はTransparent Seal helperの比較結果等で上書きされる。
- loader body自身はstackを操作せず、JMP chain末尾のRTSで元の呼出へ戻る。

## StageExt単体版と実効Panel版の差

StageExt単体91B版はentry byte0/2/3/6/7、Seal値をコピーし、直接`$8FDB`へ進む。Panel版85Bは同じ値をコピーするが、entry byte6の直後にbyte7を`INY`で読み、末尾を`JMP $8A66`へ変える。

`$8A66` helperがentry byte0からWarp MirrorとEnemy Clear Key Openを`$0770`へ展開した後、`$8FDB`へ進む。従って現行の最終保存ROMではStageExt単体版の副作用は全て保たれ、gameplay flagだけが追加される。

Special Item helperはStageExt/Panel bodyより前に16B item cellを`$0740-$074F`へコピーし、`$0771`をclearし、必要なら`$0772/$0773`からfire rangeを復元する。その後はPanel bodyを直列実行するためStageExt cacheを省略しない。

## 確定したバグ

### [解消] runtime room flags readerだけheader検証が不足する

`read_table()`はMAGICに加えてformatが1または2、entry sizeが8であることを検査する。一方、`read_runtime_room_flags()`は次だけで読み始める。

```python
if not raw.startswith(MAGIC):
    return [0] * count
```

format、entry size、room countを検査しない。`m66.load_all_levels_m66()`は通常table読込みより先にこの関数を呼び、bit5が立つroomのvisible/cracked in-block item復元へ結果を使用する。

そのため、MAGICだけ同じでformatが非対応、またはentry sizeが8でないtableでも、固定8B間隔のbyte6を現行runtime flagとして解釈し、item属性やblock状態を変更し得る。その後`read_table()`がFalseを返しても、先に行ったlevel変換は戻らない。

通常のアプリ生成ROMはformat 2・entry size 8なので発生しない。`_supported_table_format()`へheader validationを共通化し、通常table readerとruntime flag readerが同じ条件でformat 1/2・entry size 8だけを受理するよう修正した。

## Python writerの正常事項

`apply_runtime_loader()`は、hookを原形または現行形に限定し、96B slotを空き、StageExt版、Panel版、Special Item→Panel版のいずれかに限定してから書く。必要長はslot終端`0x8A70`まで検査する。検証完了後に失敗し得る処理はなく、通常入力では部分適用を残さない。

`patch_table()`はtable終端`0x8A10`まで長さを確認し、528Bを一括で置換する。同じ内容なら書かない。format 1読込み時はfairy fieldを非対応として無効化し、format 2で現在の全fieldを読む。

## ROM/RAM配置

| file | PRG1 CPU | size | 内容 |
|---:|---:|---:|---|
| `0x80C4-0x80C6` | `$80B4-$80B6` | 3B | l_a2 tail hook |
| `0x8800-0x8A0F` | `$87F0-$89FF` | 528B | header + 64×8B StageExt table |
| `0x8A10-0x8A6F` | `$8A00-$8A5F` | 96B | StageExt/Panel loader slot |
| `0x8A76-0x8A8B` | `$8A66-$8A7B` | 22B | gameplay flag helper |
| `0x8EAB-0x8EEA` | `$8E9B-$8EDA` | 64B | Seal block-state table |
| `0x8FEB-0x900B` | `$8FDB-$8FFB` | 33B | Transparent Seal suppress helper |
| `0x9280-0x930B` | `$9270-$92FB` | 140B | Special Item前段+Panel loader |

StageExt自身の専用RAM予約は`$077C-$077D`の2Bである。他のcopy先は各consumer runtimeの正式予約であり、管理簿上も所有が分かれている。

## 正常と確認した事項

- 16B headerと64×8B entryの境界
- file offsetとPRG1 CPU addressの対応
- room 0～63のpointer low/high計算
- entry byte0/2/3/6/7と各RAMの対応
- room開始時のcache、latch、target slot初期化
- StageExt版、Panel版、Special Item版の副作用同値性
- X=room番号のSeal helperまでの維持
- zero-page `$00/$01`の連続利用
- JMP tail-chainと最終RTSのstack均衡
- 現行ROM byte列、`RESERVED_SPANS`、正式ROM/RAM管理簿の一致
- format 1/2の受理と未知format・不正entry sizeの拒否

## 未実施

- ROM生成
- emulatorでの動的実行
- ROM/RAM管理簿の変更
