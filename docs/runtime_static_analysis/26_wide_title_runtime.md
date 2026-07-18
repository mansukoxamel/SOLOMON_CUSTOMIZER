# 26/26 Wide Title runtime 6502静的解析

解析日: 2026-07-19
対象: `magatu_skc/core/title_screen.py`、原作JP title/ending描画経路
一次資料: 現行Python実装、コメント付き原作ASM、`docs/wide_title_trampoline_design.html`、正式ROM/RAM管理簿

## 結論

Wide Title runtimeは、PRG0 bootstrapが14Bのbank-switch trampolineをRAM `$072C-$0739`へcopyし、PRG1 `$80C0`のLEN-stream decoderへ切り替える。decoderはnametable stream、64B attribute table、20 main-slot character tableを処理し、RAM側からPRG0へ戻る。title exit、idle demo、endingは専用helperへ分離されている。

bootstrap、RAM trampoline、LEN decoder、attribute writer、20-slot writer、title clear、idle-demo cleanup、ending専用rendererを命令単位で追跡した。6502本体に確定した制御フロー・stackバグは見つからない。確定問題は2件、方針不一致は1件である。

1. `RESERVED_SPANS`が実際の全書込箇所を登録していない。title start/idle hook、4 attribute抑止site、4 stream pointer byte、bank1 switch byteが機械重複検査から漏れる。
2. `apply_wide_title_idle_demo_cleanup()`とlegacy migrationは、全preflightを一括完了する前に入力ROMを段階的に直接更新する。後段の署名・容量検証で例外になると部分適用が残り得る。
3. `$03C0-$03CD`を使う旧wide-title ROMを検出して自動移行する`migrate_wide_title_trampoline_ram()`は、現在の救済・移行禁止方針と一致しない。

ROM/RAM配置は変更していない。修正も行っていない。

## runtime全体配置

| file | CPU | size | 内容 |
|---:|---:|---:|---|
| `0x4CD1-0x4CD3` | `$CCC1-$CCC3` | 3B | title block A callを`JSR $E919`へ |
| `0x4D9B-0x4D9D` | `$CD8B-$CD8D` | 3B | title block B callを`JSR $E919`へ |
| `0x6929-0x697F` | `$E919-$E96F` | 87B | bootstrap 28B、title clear 7B、ending helper 52B |
| `0x6871-0x6879` | `$E861-$E869` | 9B | idle-demo clear stub |
| `0x80D0-0x87FF` | PRG1 `$80C0-$87EF` | 1840B capacity | LEN decoder、attribute、20-slot table、block A/B stream |
| `0x9090-0x927F` | PRG1 `$9080-$926F` | 496B capacity | ending-only stock decoder、attribute tail、stream |
| `0x3719-0x371B` | `$B709-$B70B` | 3B | ending draw callを`JSR $E93C`へ |
| RAM `$072C-$0733` | - | 8B | PRG1切替＋decoder JMP |
| RAM `$0734-$0739` | - | 6B | PRG0復帰＋RTS |

PRG0 helper 87Bは隙間なく、bootstrap `$E919-$E934`、clear `$E935-$E93B`、ending helper `$E93C-$E96F`である。RAM 14Bは正式RAM管理簿と一致し、title character slot 20の末端`$0722`とは9B離れている。

## bootstrapとRAM bank-switch

`$E919`はX=13から0まで、直後の14B templateをRAM `$072C-$0739`へ逆順copyし、`JMP $072C`する。

```asm
$072C  LDA #$13
$072E  STA $BB86
$0731  JMP $80C0
$0734  LDA #$03
$0736  STA $BB86
$0739  RTS
```

`$13`はPRG1＋CHR3、`$03`はPRG0＋CHR3を選ぶ。switch address `$BB86`はbank0 file `0x3B96`とbank1 file `0xBB96`をともに`$FF`にし、bus conflict時もAを保持する。bank切替後も次命令はRAMからfetchされるため、PRG1 decoderへ安全に移れる。

呼出元はJSR `$E919`であり、bootstrapはJMPでRAMへ、RAM_INはJMPでdecoderへ、decoder末尾はJMP `$0734`、RAM_OUTだけがRTSする。追加のJSR frameはなく、元callerのframeを1回だけ消費する。

## LEN-stream decoder

stream形式はsegmentごとに`[PPU hi][PPU lo][LEN][tile...]`、終端`$FF`である。zero page `$00/$01`がstream pointer、`$02/$03`がPPU low/highである。

各segmentはpointerからheaderを読み、pointerを3進め、`$2002`を読んでlatchをresetし、`$2006`へhigh/low、`$2000`へRAM mirror `$0300`を再設定する。その後X=LEN回、`($00),Y`からtileを読み`$2007`へ書く。run終了後Yをpointerへ加算し、次segmentへ戻る。

- header skipの`ADC #3`前はCLC。
- low pointer加算とrun length加算はいずれもBCC/INCでhigh carryを伝播する。
- X=0のsegmentはencode側が生成しない契約である。
- 終端は`LDX $2002`でPPU latchをresetしてから後続attribute writerへfall-throughする。
- branch offsetはassemblerがlabelから生成し、現在のcode size内に収まる。

decoder coreは元のRTSを持たず、attribute writer、title OAM writerを順に通ってRAM_OUTへJMPする。

## 64B attribute writer

attribute writerは`$2002`を読み、PPU `$2BC0`を設定し、内蔵64B tableをY=0～63で`$2007`へ転送する。`INY / CPY #$40 / BNE`は64回で終了する。

tableは16×15の2×2 tile block paletteを64Bへpackし、最下段offscreen部分を既定`$F0`で保持する。writer後は20-slot helperへ絶対JMPするためstackを増減しない。原作側4箇所のattribute書込命令は3NOPへ変え、後からこの64B tableを上書きしない。

## 20 main-slot character writer

title character tableは20 entry×6Bで、各entryはactive、Y、X、tile1、tile2、attribute相当を持つ。helperはslotごとにLDXでtable offsetを選び、main slot 1～20のfield `+0,+7,+10,+17,+18,+19`へ絶対STAする。

各slotの6 loadは`table_cpu+field,X`で同じentryを参照し、destinationは`$057F + slot*20`である。slot 1から20まで重複せず、slot20の最終fieldは`$0722`でRAM trampoline `$072C`に達しない。最後はJMP `$0734`でbank0復帰する。

hidden entryはY=`$F8`で非表示にする。title exitではPRG0 `$E935`が原作title clear `$CC18`と全main-slot clear `$CB5A`を順にJSRし、RTSする。

## idle-demo cleanup

原作timeout `$CB9E`の5Bを`JSR $E861 / NOP / NOP`へ変える。stubはtitle clear helper `$E935`をJSRしてから、原作の`LDA #$18 / JSR $8D5F`を再実行しRTSする。

手動START経路だけでなくtimeout demo経路でもwide nametableとtitle-only spriteを消す目的であり、原作action値と呼出順を維持する。stubのJSR/RTSは均衡する。

## ending専用renderer

ending `$B709`は`JSR $E93C`へ向ける。helperはPPU待ち、原作palette/NMI-off準備、ending stream pointer設定、14B RAM template copyを行い、`JSR $072C`でPRG1へ入る。

PRG1 `$9080`はstock `$CC4F` decoderのcloneで、DONEの`RTS`だけをending attribute tailへのJMPへ変更する。tailは原作`$CD8E-$CDF2`相当のPPU attribute書込を行い、RAM_OUT `$0734`へJMPする。RAM_OUTのRTSでhelper内JSR frameへ戻り、helperは`JMP $965F`で原作NMI-on復帰へtail-callする。

title編集用LEN streamとending用stock streamを分離しているため、title block Bの編集がending背景へ混入しない。ending reserve上限は書込前に検査される。

## register、flag、stack

- bootstrapはA/Xを破壊し、Yを触らない。title描画callerは作業register保存を要求しない。
- decoderはA/X/Y、`$00-$03`を作業に使う。NMI-off窓内でPPU registerを直接扱う。
- title routeはcaller JSR 1回に対してRAM_OUT RTS 1回。
- ending routeは`JSR $E93C`とhelper内`JSR $072C`があり、RAM_OUT RTSが内側frameを戻し、`JMP $965F`先のRTSが外側frameを戻す原作tail-call構造である。
- title clearとidle stubのJSR/RTSも各1対である。
- processor flagを保存する入口ではなく、各原作後続は描画/初期化結果を使うためflag保存契約はない。

## 正規化preflightとtransaction

`normalize_title_to_wide()`はJP66、複数stock署名、caller B列、bank0/bank1 `$BB86`、PRG1空き、Room Flags帯非交差、stream decode量、予約容量を検査する。書込は一度`out = bytearray(rom)`へ行い、round-trip decodeが元gridと一致した後だけ`rom[:] = out`する。この主正規化経路はtransactionalである。

一方、save-time `apply_wide_title_idle_demo_cleanup()`は入力`rom_data`へ次を順次直接適用する。

```text
title OAM clear
idle-demo cleanup
4 attribute write suppression
ending draw separation
```

前段を書いた後に後段の署名不一致やending容量超過が起きると、例外までに書いた変更を戻さない。`migrate_wide_title_trampoline_ram()`も、bootstrap/stock restoreを書いた後で2 call siteを順番に検査する内部routineを直接使うため、後側callの不一致時に部分更新が残り得る。

修正時は全preflightを先に完了するか、copyへ全変更を適用して成功時だけ原本へ反映する必要がある。

## `RESERVED_SPANS`の登録漏れ

現行登録はPRG0 helper 87B、2 boot call、idle stub、ending call、PRG1 title capacity、PRG1 ending capacityである。実際に書き換える次の範囲は登録されていない。

| file/CPU | size | 実書込 |
|---|---:|---|
| `0x4BC3` / `$CBB3` | 3B | title start clear hook |
| `0x4BAE` / `$CB9E` | 5B | idle-demo timeout hook |
| `0x4CE8`,`0x4DCE`,`0x4DE6`,`0x4DF9` | 各3B | legacy attribute write NOP |
| `$CCBA,$CCBE,$CD84,$CD88` | 各1B | block A/B stream pointer |
| `0xBB96` / PRG1 `$BB86` | 1B | bus-conflict-safe switch byte `$FF` |

正式ROM管理簿にはこれらの多くが個別使用行として載るが、`tools/check_rom_consistency.py`のmodule予約重複検査にはtitle_screenのspanとして入らない。特にPRG1 `0xBB96`は独立1Bであり、別moduleが同位置を予約してもtitle runtimeとの重複を機械的に検出できない。

## 方針不一致: legacy RAM migration

`migrate_wide_title_trampoline_ram()`は旧bootstrap署名を検出し、block gridと重なるRAM `$03C0-$03CD`から現行`$072C-$0739`へ自動移行する。これは過去の内部ROMを現行形式へ変換する明示的migrationであり、現在の「古いROM・途中生成ROMの救済・移行を追加しない」方針と一致しない。

今回は削除していない。修正段階では、現行新規ROM生成に必要かを切り分け、救済禁止を維持するならmigration callと旧署名受入を除く必要がある。

## 判定

- PRG0 bootstrapと14B RAM copy: 正常
- bank1/PRG0切替とstack収支: 正常
- LEN-stream decoder pointer/carry/loop: 正常
- 64B attribute writer: 正常
- 20-slot title character writerとRAM境界: 正常
- title exitとidle-demo cleanup 6502本体: 正常
- ending専用rendererと原作復帰: 正常
- `normalize_title_to_wide()`の事前検証とtransaction: 正常
- save-time cleanup/migrationの失敗時原子性: 異常。部分適用の可能性
- ROM予約の機械登録: 不完全
- legacy `$03C0` migration: 現行方針と不一致

## 修正優先度

1. 高: cleanup/migrationをcopy-on-success化し、失敗時に入力ROMを一切変更しない。
2. 高: 全実書込範囲を`RESERVED_SPANS`へ登録し、正式管理簿と共通ROM整合性検査を一致させる。
3. 中: 救済禁止方針に従いlegacy `$03C0` migrationと旧署名受入を整理する。

ROM生成は行っていない。Python生成命令列、原作ASM、branch、配置定数、正式管理簿を静的に照合した。
