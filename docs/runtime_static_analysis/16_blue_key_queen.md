# 16/26 Blue Key Queen runtime 6502静的解析

解析日: 2026-07-19
対象: `magatu_skc/core/blue_key_queen_runtime.py`、`saver.py`、原作item dispatcher `$C532-$C5D2`、原作Fairy queue `$9EE1-$9F09`
一次資料: コメント付き原作ASM、日本版原作ROM、現行mapper66検証ROM、正式ROM管理簿、CHANGELOG

## 結論

Blue Key Queenは、原作では無効果の青鍵item `$1A`を取得した時に原作Fairy予約数`$0454`を1増やし、次に空き敵slotへ生成されるFairyだけをFairy Princess `$1D`へ変更する常設runtimeである。敵slotが満杯なら原作queueが予約を保持し、空きができた後に生成する。

31Bの全命令、item dispatcher、17 sub-slot探索、Fairy座標設定、敵初期化、`$87`の全原作access、hook署名、Python適用順を追跡した。単一の青鍵予約、通常Fairyだけの予約、敵slot満杯後のretryは成立する。

確定した6502本体バグはない。成立条件となるレギュレーションは次の1件である。

1. 青鍵item `$1A`は1部屋に1個だけ配置する。Princess予約は`$87 bit1`の1件だけでよく、複数青鍵の順序・個数はruntimeの保証対象にしない。

通常Bell予約が先に溜まっていても、青鍵取得後の次回spawnはPrincessを優先する。厳密な取得順より現行の単純な1bit処理を優先し、この挙動を仕様として維持する。ROM/RAM配置と6502バイト列は変更していない。

## 配置レギュレーション

- 青鍵item `$1A`は1部屋につき1個までとする。
- 青鍵を複数配置したROMのPrincess個数・出現順は保証しない。
- 通常Bellと青鍵の予約が同時に残った場合はPrincessを先に出す。取得順FIFOは実装しない。
- この制約をeditor UIで強制する処理は別作業とし、今回のruntime静的修正には含めない。
- runtime側へ複数青鍵counter、FIFO、新規RAM、救済処理を追加しない。

## 原作のitem取得経路

ゲームplay taskは`$9ED5`で`JSR $C532`を呼び、Dana中心cellのitemを判定する。item `$06-$22`は`$C5B6`から共通取得処理へ入り、SE `$0D`をqueueした後、Aからtable indexを作って`$C5D3`のword tableへdispatchする。

青鍵item `$1A`の原作entryは次である。

```text
$C5FB: B5 C5    .word $C5B5
$C5B5: RTS
```

runtimeはwordだけを`$E056`へ変更する。命令列をhookするのではなく原作tableのhandler pointerを差し替えるため、`$E056`末尾の`RTS`は他の原作item handlerと同じstack契約でdispatcherへ戻る。

共通取得処理はhandlerへ入る前に`$02=#$40`を設定済みであり、handlerが`$02`を触らなくてもitem取得actionは成立する。runtimeはAとcondition flagを変更するが、X/Yを触らない。原作の無効果handlerもレジスタ保存を保証しないため、呼出規約上の問題はない。

## item handler `$E056-$E05F`

10Bの処理は次のとおりである。

```asm
INC $0454       ; Fairy予約数 +1
LDA #$02
ORA $87
STA $87         ; bit1 = Princess pending
RTS
```

`$0454`は原作Bell item `$0F/$18`も`INC`する8bit counterである。Blue Keyも同じqueueへ入るため、敵slotが満杯でも予約数は減らない。

`$87 bit0`は原作のFairy取得演出中flagである。runtimeは`ORA #$02`なのでbit0とbits2-7を保持する。

## 原作Fairy queue `$9EE1-$9F09`

main game loopは敵AI、item取得、mirror処理の後、各loop末尾でFairy queueを処理する。

```text
$0454 == 0 -----------------------------> 次loop
  |
  +-- $B2EAで17 sub-slotを探索
        |
        +-- 空きなし -------------------> 次loop（予約保持）
        +-- 空きあり
              DEC $0454
              sub[0] = $80
              X = spawn slot index
              door cell byte5をpixel座標へ変換
              type = $1C
              $A297で座標設定
              $A2B8で初期化
```

`$B2EA`はslot 0～16を走査し、sub-slot byte0のbit7が0の最初のslotを返す。失敗時はcarry clearで`$9F09`へ分岐するため、queueとPrincess pending bitのどちらも消費しない。

成功時は`DEC $0454`を先に行い、door位置を`$91A3`でpixelへ変換する。したがってBlue Key Queenも原作Fairyと同じ扉位置へ出現する。

## type選択hook `$9EFF`

原作4Bは次である。

```asm
LDA #$1C
STA $07
```

現行hookは`JSR $E060 / NOP`へ置換する。selectorは21Bである。

```text
$87 bit1 == 0
  -> A=$1C / $07=$1C / RTS

$87 bit1 == 1
  -> $87 &= $FD
  -> A=$1D / $07=$1D / RTS
```

正常Fairy経路はtype `$1C`、Princess経路はtype `$1D`を返す。どちらも`$A297`と`$A2B8`の共通初期化へ続く。両typeは原作property table上で同じgroupに属し、type下位bitだけがFairyとFairy Princessの見た目・向きを選ぶ。

selectorはX/Yとcarryを保持する。A、N、Zは原作`LDA #$1C`と同様に最終的に正・非0となる。`BIT $87`によりVは`$87 bit6`へ変わり得るが、後続`$A297/$A2B8`はVを条件分岐へ使わず、実動作へ影響しない。

## `$87`との共存

原作コードで命令として実行される`$87` accessは次である。

| 処理 | 命令 | bit1への影響 |
|---|---|---|
| Fairy演出開始 `$C4B0` | `LDA #1 / ORA $87 / STA $87` | 保持 |
| Fairy演出終了 `$C4CF` | `LSR $87 / ASL $87` | 保持 |
| cleanup `$C885` | `LSR $87 / ASL $87` | 保持 |
| item取得抑制 `$C56C/$C5BB` | `LDA $87 / LSR A` | memoryは変更しない |

`LSR/ASL`の組は元のbits1-7を元位置へ戻し、bit0だけを0にする。従って原作Fairy演出がPrincess pendingを消すことはない。

コメント付きASMの`$CE2A/$D00E`に見える`STX $87`は実行命令ではなくdata decode上の見かけであり、runtimeとの競合にはならない。

## レギュレーション外の入力

### 複数のBlue Key予約

runtimeが保持する状態量は一致していない。

| 状態 | RAM | 表現可能範囲 |
|---|---:|---:|
| 未spawn Fairy総数 | `$0454` | 0～255 |
| 未spawn Princess数 | `$87 bit1` | 0または1 |

敵slotが埋まっていてqueueを消費できない間にBlue Keyを2個取得すると、次になる。

```text
初期状態                  $0454=0, bit1=0
Blue Key 1個目            $0454=1, bit1=1
Blue Key 2個目            $0454=2, bit1=1
空き発生、1体目spawn      $0454=1, bit1=0, type=$1D
次loop、2体目spawn         $0454=0, bit1=0, type=$1C
```

2個目もBlue Key由来であるのに、Princessではなく通常Fairyになる。ただし青鍵は1部屋1個という配置レギュレーションなので、この状態は保証対象外であり、6502本体バグとして扱わない。

通常BellとBlue Keyの混在では取得順を表現しない。Bellを先に取得して`$0454=1`、その後Blue Keyで`$0454=2/bit1=1`にすると、最初のspawnがPrincess、次が通常Fairyとなる。これは現行のPrincess優先仕様である。

取得順FIFOや複数Princess counterは実装しない。青鍵1個という制約では不要であり、RAMとruntimeを増やして現行処理を複雑化しない。

## ROM/RAM配置

| file | CPU | size | 内容 |
|---:|---:|---:|---|
| `0x6066-0x606F` | `$E056-$E05F` | 10B | Blue Key item handler |
| `0x6070-0x6084` | `$E060-$E074` | 21B | Fairy/Princess selector |
| `0x460B-0x460C` | `$C5FB-$C5FC` | 2B | item `$1A` handler word |
| `0x1F0F-0x1F12` | `$9EFF-$9F02` | 4B | Fairy type load hook |

runtime本体は`0x6066-0x6084`の31Bで、直後`0x6085-0x60CB`は71Bの正式な空きである。現行mapper66検証ROMの31BとPython builderはbyte単位で一致した。

専用RAMは新規予約していない。原作`$0454`と原作`$87`の未使用bit1を使う。青鍵1部屋1個のレギュレーションにより、counterや追加RAMは不要である。

## Python書込み側

`apply()`は書込み前に次を全て検証する。

1. ROM sizeがruntime終端まであること。
2. item handler wordが原作`$C5B5`または現行`$E056`であること。
3. Fairy type loadが原作4Bまたは現行hookであること。
4. runtime caveが現行31Bまたは全byte `00/EA`であること。

全検証が終わるまで`rom_data`へ書かないため、未知のhookやcave競合で部分適用を残さない。出力はruntime、item hook、type hookの順だが、事前検証済みなのでatomicity上の問題はない。

旧runtime byte列を特別に認識して移行する救済経路もない。

## 正常と確認した事項

- item `$1A` table indexとword hook位置
- handlerのRTS/stack契約
- item取得共通処理の`$02`設定
- queueが0の経路
- slot成功/失敗とretry時の予約保持
- door cellからpixel座標への変換
- Fairy `$1C`とFairy Princess `$1D`の共通初期化
- `$87 bit0`とのbit分割共存
- selectorのX/Y/carry保持と後続flag利用
- 2つのhook署名、runtime cave競合検査
- 書込み前の一括検証
- `RESERVED_SPANS`、正式ROM管理簿、現行ROM byte列の一致

## 未実施

- ROM生成
- emulatorでの動的実行
- UI側の青鍵1個制約
- RAM/ROM管理簿の変更
