# 16/26 Blue Key Queen runtime 6502静的解析

解析日: 2026-07-19
対象: `magatu_skc/core/blue_key_queen_runtime.py`、`saver.py`、原作item dispatcher `$C532-$C5D2`、原作Fairy queue `$9EE1-$9F09`
一次資料: コメント付き原作ASM、日本版原作ROM、現行mapper66検証ROM、正式ROM管理簿、CHANGELOG

## 結論

Blue Key Queenは、原作では無効果の青鍵item `$1A`を取得した時に原作Fairy予約数`$0454`を1増やし、次に空き敵slotへ生成されるFairyだけをFairy Princess `$1D`へ変更する常設runtimeである。敵slotが満杯なら原作queueが予約を保持し、空きができた後に生成する。

31Bの全命令、item dispatcher、17 sub-slot探索、Fairy座標設定、敵初期化、`$87`の全原作access、hook署名、Python適用順を追跡した。単一の青鍵予約、通常Fairyだけの予約、敵slot満杯後のretryは成立する。

確定バグは1件である。

1. Fairy予約数は8bit counterなのにPrincess予約は1bitしかないため、未消費の青鍵予約が2件以上になると2件目以降が通常Fairyへ化ける。通常Bellと混在した時は取得順も保持できない。

ROM/RAM配置は変更していない。修正も行っていない。

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

## 確定したバグ

### [P1] 複数のBlue Key予約を1bitで表せない

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

2個目もBlue Key由来であるのに、Princessではなく通常Fairyになる。青鍵を複数配置できる現行editor上で到達可能な状態であり、6502本体の確定ロジックバグである。

通常BellとBlue Keyの混在でも取得順を表現できない。Bellを先に取得して`$0454=1`、その後Blue Keyで`$0454=2/bit1=1`にすると、最初のspawnがPrincess、次が通常Fairyとなる。予約種別の順番が取得順と逆になる。

正確に直すには、少なくともPrincess未spawn数を別counterで持つか、予約種別をFIFOとして持つ必要がある。Princess counterだけなら「総数のうちPrincessを先に出す」動作で複数青鍵は直るが、Bellとの取得順までは保持できない。修正方式によってRAM使用量と仕様が変わるため、本解析では実装していない。

## ROM/RAM配置

| file | CPU | size | 内容 |
|---:|---:|---:|---|
| `0x6066-0x606F` | `$E056-$E05F` | 10B | Blue Key item handler |
| `0x6070-0x6084` | `$E060-$E074` | 21B | Fairy/Princess selector |
| `0x460B-0x460C` | `$C5FB-$C5FC` | 2B | item `$1A` handler word |
| `0x1F0F-0x1F12` | `$9EFF-$9F02` | 4B | Fairy type load hook |

runtime本体は`0x6066-0x6084`の31Bで、直後`0x6085-0x60CB`は71Bの正式な空きである。現行mapper66検証ROMの31BとPython builderはbyte単位で一致した。

専用RAMは新規予約していない。原作`$0454`と原作`$87`の未使用bit1を使う。ただし確定バグをcounter方式で直す場合は、新たなRAM byteまたは既存共有領域の明示契約が必要になる。

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
- 修正実装
- RAM/ROM管理簿の変更
