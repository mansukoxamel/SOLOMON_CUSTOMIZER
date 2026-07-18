# 25/26 Gap Fix 6502静的解析

解析日: 2026-07-19
対象: `magatu_skc/core/gap_fix.py`、原作衝突sampler `$86D4-$8788`
一次資料: 現行Python実装、コメント付き原作ASM、`docs/gap_entry_mechanism.html`、正式ROM管理簿

## 結論

Gap Fixは、Danaの4隅衝突maskを`$058A`へ保存する直前の原作3Bをhookし、落下state、左右入力、壁の縁cell、直下の開口cellを確認した時だけ左/右衝突bitを消す136B runtimeである。

全命令、左右経路、grid index、branch、A/X/Y、zero page、stack収支を追跡した。6502本体に確定バグは見つからない。確定した管理上の問題が1件、古い資料の不一致が1件ある。

1. `gap_fix.py`は`RESERVED_SPANS`を定義していない。`tools/check_rom_consistency.py`は、この定義を持つmoduleだけを収集するため、hook 3Bとcave 136Bの両方がROM重複検査から完全に抜ける。
2. コメント付きASMと`docs/i18n_string_inventory.md`の一部は旧配置`$C000`を残している。現行配置は`$E879-$E900`である。

正式ROM管理簿には現行caveが使用中として載り、`room_flags.py`の空き検証もGap Fix spanを明示的に許容している。しかし共通機械検査から漏れる事実は変わらない。ROM/RAM配置は変更していない。修正も行っていない。

## 配置とhook

| file | CPU | size | 内容 |
|---:|---:|---:|---|
| `0x078F-0x0793` | `$877F-$8783` | 5B | 安定署名`A5 0A 6A 6A 6A` |
| `0x0794-0x0796` | `$8784-$8786` | 3B | 原作`LDY #$0B / STA ($08),Y`を`JMP $E879`へ置換 |
| `0x6889-0x6910` | `$E879-$E900` | 136B | Gap Fix runtime本体 |

機能OFFでもcave本体は固定配置し、hookだけを原作3Bへ戻す。save時は現在のhook状態を`is_applied()`で読み、その値を保ったまま`apply()`でcaveを常設するため、保存のたびに設定が勝手に変わる経路はない。

## 原作衝突mask生成

原作`$86D4-$8788`は、entity pointer `$08/$09`からY/X座標を読み、Dana hitboxの上端`Y-13`、下端`Y-1`、左端`X-4`、右端`X+3`を作る。4隅に対応する`$0304,Y`のbit7をcarryへ取り込み、`ROR $0A`でmask化する。

最後の`$877F-$8783`は`$0A`をAへ取り出して3回RORし、原作`$8784-$8786`がY=11、`STA ($08),Y`でentity offset +11、Danaでは`$058A`へ保存する。Gap Fixはこの最終storeだけを置換するため、上流の4隅sample、速度、座標commit、衝突resolverを変更しない。

## runtime入口と落下state gate

入口時Aは原作が保存しようとしていた衝突maskである。最初にPHAし、`$0582`を2回LSRして`AND #$07`する。結果が6または2の時だけ補正を行い、それ以外は共通fallbackでPLAし、原作と同じstoreを行う。

```asm
PHA
LDA $0582
LSR A
LSR A
AND #$07
CMP #$06
BEQ falling
CMP #$02
BNE original_store
```

非対象stateのbranchはruntime末尾の`PLA / LDY #$0B / STA ($08),Y / RTS`へ到達する。Aは完全に元値へ戻り、原作storeと同じ結果になる。

## 左方向経路

補正maskとしてzero page `$0B`へ`$FF`を置き、`$03E4 bit1`が立つ時だけ左経路を実行する。

```text
col = (DanaX - 4) >> 4
row = (DanaY - 13) & $F0
idx = row | col
```

`$0304+idx`が非solidなら何もしない。solidなら`idx+$10`、すなわち同じ列の直下cellを読む。直下もsolidなら通常壁なので何もしない。縁がsolid、直下が非solidの組合せだけ`$0B &= $FE`として左衝突bit0を消す。

`SBC #$04`と`SBC #$0D`の前にはそれぞれSECがあり、X/Y edge計算にcarry混入はない。4回LSR後のX列は0～15、rowは上位nibbleで、ORAにより原作grid index式と一致する。

## 右方向経路

`$03E4 bit0`が立つ時だけ右経路を実行する。

```text
col = (DanaX + 3) >> 4
row = (DanaY - 13) & $F0
idx = row | col
```

X加算前はCLC、Y減算前はSECである。左と同様に縁cellがsolid、直下が非solidの時だけ`$0B &= $FD`として右衝突bit1を消す。左右同時入力なら両経路を順に通り、各方向の開口条件を満たしたbitだけが独立して消える。

## 共通store、register、flag、stack

対象stateでは最後にPLAで元maskを戻し、`AND $0B`を行う。非対象stateはANDを通らず元maskをそのまま保存する。両方とも`LDY #$0B / STA ($08),Y / RTS`で原作callerへ戻る。

- PHAは全終端で必ず1回のPLAと対になる。
- JSRは追加せず、hookがJMPなのでruntime末尾のRTSが原作subroutineのcall frameを消費する。
- Xはruntime内で変更しない。
- Yはgrid index作業後、store直前に必ず`#$0B`へ戻す。
- Aは対象stateでは補正済みmask、非対象stateでは入口時maskでstoreされる。
- `$0B/$0C`は元の衝突sampler自身が使うscratchであり、runtimeも同じ呼出範囲内で再利用する。`$08/$09` entity pointerは変更しない。
- RTS時のprocessor flagは原作store/RTS時と完全一致する契約ではないが、callerは`$058A`の値を利用し、flag保存を要求する呼出規約ではない。

## 通常壁と開口の分離

このruntimeの安全条件は「縁cell solid、直下cell non-solid」の2段判定である。通常壁は直下もsolidなのでmaskを変えない。過去の無条件版で起きたstate振動・soft lockを、この直下条件が防いでいる。

速度`$0587/$0588`、座標`$0589`、grid本体、左右resolverには書き込まない。変更対象はそのframeに`$058A`へ保存するbit0/bit1だけである。既存のMesen/実機確認結果と6502命令列は一致する。

## Python preflightと固定構造

`_verify()`は次を検査する。

- ROM長がcave末尾以上
- `$877F`の5B署名
- hookが原作3Bまたは現行JMP
- caveが現行136Bまたは全00/EA

未知byteは例外で停止し、競合領域へ上書きしない。ON/OFFにかかわらずcave本体を毎回書く方針も固定ROM構造と一致する。古いcaveや旧hookを受け入れる互換分岐はない。

## 確定問題: `RESERVED_SPANS`欠落

`tools/check_rom_consistency.py`の`collect_reserved_spans()`は、AST上でmodule直下に`RESERVED_SPANS`代入があるPython fileだけをimport・収集する。`gap_fix.py`には定義がないため、次の両範囲が検査母集団に入らない。

- hook `0x0794-0x0796`
- cave `0x6889-0x6910`

`room_flags.py`は自身の4096B空き検査で`(_gf.OFF_CAVE, len(_gf.CAVE))`を個別許容しているが、これはGap Fixを共通重複検査へ登録する代わりにはならない。他moduleが将来この範囲を予約しても、正式な機械検査がGap Fixとの重複を報告できない状態である。

修正時は`RESERVED_SPANS = ((OFF_HOOK, len(HOOK)), (OFF_CAVE, len(CAVE)))`相当を登録し、正式管理簿との一致と重複検査を通す必要がある。これは配置移動ではなく既存配置の登録修正だが、実装・台帳・検査を同一コミットで確定するべきである。

## 資料不一致

コメント付きASMの統合経緯と`docs/i18n_string_inventory.md`の一部には旧cave `$C000`が残る。現行Python、正式ROM管理簿、PRG0配置資料はいずれも`$E879-$E900`で一致するため、旧記述が誤りである。今回は解析資料の修正は行っていない。

## 判定

- 原作衝突mask保存hook: 正常
- state 6/2 gate: 正常
- 左edge/opening判定とbit0 clear: 正常
- 右edge/opening判定とbit1 clear: 正常
- 通常壁fallback: 正常
- A/X/Y、zero page、stack収支: 正常
- ON/OFF固定caveとpreflight: 正常
- ROM予約の機械登録: 異常。`RESERVED_SPANS`欠落
- 古い資料のcave address: 不一致

## 修正優先度

1. 中: hook/caveを`RESERVED_SPANS`へ登録し、共通ROM重複検査の対象にする。
2. 低: コメント付きASMと文字列inventoryの旧`$C000`記述を現行`$E879`へ更新する。

6502本体は現状維持が妥当である。
