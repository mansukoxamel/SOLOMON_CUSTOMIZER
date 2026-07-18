# 21/26 Solomon Seal Block runtime 6502静的解析

解析日: 2026-07-19
対象: `magatu_skc/core/solomon_seal_block.py`、`solomon_seal_stage.py`、`stage_ext.py`、`room_flags.py`、`m66.py`、原作Solomon's Seal配置`$BB7A-$BB9E`
一次資料: コメント付き原作ASM、日本版原作ROM、現行mapper66検証ROM、正式ROM/RAM管理簿

## 結論

Solomon Seal Blockは、原作が常に隠しitem値`$60`で配置する8個のSolomon's Sealを、room編集内容に応じて茶ブロック内`$A0`、白ブロック内`$E0`、透明breakable block内へ拡張するruntimeである。

PRG0書込みhelper 11B、PRG1取得済み抑止helper 33B、room別5 table、StageExt loaderとの順序、全8 Seal bit/座標/mask対応を追跡した。6502本体の確定バグは見つからなかった。配置・writer上の確定問題は2件である。

1. 管理簿と`RESERVED_SPANS`はfile `0x900C-0x900E`の3Bだけを使用中とするが、writerは`0x900C-0x9018`の13Bを検査・書込みする。空きとされる後続10Bを他runtimeが実際には使用できない。
2. `_verify()`が旧31B helperと旧13B tail配置を明示的に受け入れる互換分岐を残しており、現在の救済禁止方針と一致しない。

通常のアプリ生成mapper66 ROMでは、Seal書込み値、取得済み抑止、mask解除、stack・register・flag契約は成立する。ROM/RAM配置は変更していない。修正も行っていない。

## 原作Seal配置処理

原作`SUB_BB7A`はAでSeal bit `$01-$80`を受け取る。`$7A`の取得済みbitとANDし、未取得時だけbit位置をXへ変換して`$BB96,X`からgrid座標をYへ読む。

```asm
$BB8D: LDY $BB96,X
$BB90: LDA #$60
$BB92: STA $0304,Y
$BB95: RTS
```

`$60`はitem `$20`にhidden bit `$40`を加えた値である。座標表は`89 97 2D 54 6B B7 1D 1E`で、8 Seal bitと固定対応する。Seal出現stageは別の特殊処理dispatchが決め、編集後もbitと座標slotの対応は変わらない。

呼出scriptのうち5本は`JMP $BB7A`でtail callし、3本は`JSR $BB7A`後に直ちにLDAまたはJMPを実行する。従って元のLDAが作るN/Z flagを呼出側branchへ引き渡す契約はない。

## PRG0 block-state helper `$EFF5`

hookは元の5Bを同じ長さで次へ置換する。

```asm
$BB90: LDA #$60
$BB92: JSR $EFF5
```

11B helperは次である。

```asm
LDA $077D
BNE override
LDA #$60
override:
STA $0304,Y
RTS
```

StageExt loaderがroom別64B table `$8E9B,X`から`$077D`へ0、`$A0`、`$E0`のいずれかをコピーする。0なら原作`$60`、茶なら`$A0`、breakable whiteなら`$E0`を書き込む。

Yは原作`$BB96,X`の座標のまま保持される。X、stack深度も変わらない。override時はAとNが原作と異なるが、上記の全呼出scriptはreturn flagを使わないため成立する。

## 編集データからroom別値を作る条件

`build_table()`は現在のSeal stageと固定座標を組み合わせ、64B tableを作る。

| editor cell | `$077D` | Seal配置値 |
|---|---:|---:|
| 通常/対象外 | `$00` | `$60` hidden Seal |
| 茶block | `$A0` | `$A0` brown in-block Seal |
| breakable white block | `$E0` | `$E0` white in-block Seal |

白blockでも`breakable_white_cells`に含まれないsolid whiteはoverride対象にならない。これは原作hidden Sealへ戻す明示条件である。

Seal stageを移動した場合、`solomon_seal_stage.current_stages()`が各bitの特殊処理script位置を再検出し、同じslotの座標を移動先roomへ割り当てる。8 stageは重複不可かつ昇順で、各Seal bitの順序を維持する。

## 透明breakable Sealの保存時合成

透明breakable blockは`$077D`の1B値だけでは表現できない。`levels_for_save()`はeditorのLevelを変更せず、保存用shallow copyに次を一時追加する。

1. Seal座標にある既存itemを保存用copyから除く。
2. 通常item `$20`を同じ座標へ追加する。
3. その座標をvisible-in-block item maskへ追加する。
4. 元の`invisible_breakable_cells`は維持する。

mapper66 writerはroomごとの24B maskをPRG1 side tableへ保存する。Room Flags scannerは初期描画後にmask bitを消費し、Seal cellをin-block状態へ変換する。

## 透明Seal用4 table

各tableは64 room×1Bである。

| PRG1 CPU | 値 |
|---:|---|
| `$8EDB,X` | grid位置byte。対象なしは`$FF` |
| `$8F1B,X` | Seal取得bit `$01-$80`。対象なしは0 |
| `$8F5B,X` | 24B maskのbyte index。対象なしは`$FF` |
| `$8F9B,X` | 対象bitだけ0のAND mask。対象なしは`$FF` |

grid位置は`((y+1)<<4)|x`で、`$0304,Y`の原作位置表現と一致する。mask indexは`(y*16+x)>>3`、clear maskは`~(1<<((y*16+x)&7))`である。m66 writerも同じLSB-first形式を使う。

8個の既定座標について、mask byte indexとbit maskを機械計算し、m66の24B mask形式と一致することを確認した。

## 取得済み透明Seal抑止 `$8FDB`

33B helperはmapper66 room loader、StageExt/Panel/gameplay flag chainの最後に実行される。この時点でXは現在room、gridと`$0750-$076F` side dataはRAMへ展開済みである。

処理は次である。

1. `$8EDB,X`が`$FF`ならRTS。
2. roomのSeal bitを`$7A`とANDし、未取得ならRTS。
3. 取得済みなら対象grid cellへ`$50`を戻す。
4. `$0750 + mask index`へclear maskをANDし、Seal用visible mask bitを消す。
5. RTSでmapper66 loader呼出元へ戻る。

`$50`は後段のRoom Flags特殊cell scannerで`$90`へ変換され、itemを持たない透明breakable blockになる。mask bitも先に消してあるため、取得済みSealを再び`$C0+item`へ変換しない。

2本のBEQはどちらも33B末尾RTSへ着地する。Yは最初にgrid位置、次にmask indexへ変わるが呼出元に保存契約はない。Xはroom番号のまま、stack操作は末尾RTSだけである。

## 確定した問題

### [P2] 3B使用領域のwriter footprintが13Bある

現行tail helper本体は次の3Bだけである。

```asm
$8FFC: JMP $8FDB
```

`RESERVED_SPANS`と正式ROM管理簿もfile `0x900C-0x900E`の3Bだけを予約し、`0x900F-0x9018`の10Bを空きとしている。この整理自体は「実処理だけを予約する」方針に合う。

しかし実装は`TRANSPARENT_SEAL_PANEL_TAIL_HELPER_SLOT`を13Bで作り、後ろ10Bを0で埋める。`_verify()`は13B全体を既定slot、旧配置、または全`00/EA`に限定し、`apply()`も13B全体を書き直す。

従って別runtimeが管理簿上の空き10Bを使うと、Solomon Seal writerは競合として保存を拒否する。予約表では空きだがwriter契約では空きでない確定不一致である。現行tailは3Bだけを検査・書込みし、paddingをwriter対象から外すのが配置を変えない最小方針になる。

### [P3] 旧runtime受入れが救済禁止方針と不一致

`_verify()`は `_OLD_TRANSPARENT_SEAL_SUPPRESS_HELPER_BMI` と、2Bずれた旧tailの重なりを明示判定して受け入れる。受入れ後は現行byte列へ上書きするため、通常の新規ROM動作には影響しない。

ただし現在のプロジェクト方針は、正式版前の古い実験ROM・途中生成ROMを救う互換判定を持たないことである。この2分岐は目的が旧配置救済そのもので、現行方針と一致しない。機能修正とは分けて削除対象を判断すべきである。

## Python writerの正常事項

必要長はPRG0 helper、PRG1 table群、tail slotの最大終端`0x9019`まで検査する。`$BB90` hook、PRG0 helper、PRG1 suppress helper、tailを事前検証してからtableとcodeを書くため、通常の未知code競合では部分適用しない。

Seal block tableと4透明tableは現在のlevel内容から毎回全64Bを再構築する。未使用roomには0または`$FF`を明示し、前回room設定を残さない。

## ROM/RAM配置

| file | CPU | size | 内容 |
|---:|---:|---:|---|
| `0x3BA0-0x3BA4` | `$BB90-$BB94` | 5B | Seal write hook |
| `0x7005-0x700F` | `$EFF5-$EFFF` | 11B | block-state helper |
| `0x8EAB-0x8EEA` | PRG1 `$8E9B-$8EDA` | 64B | block-state table |
| `0x8EEB-0x8F2A` | PRG1 `$8EDB-$8F1A` | 64B | transparent grid cell table |
| `0x8F2B-0x8F6A` | PRG1 `$8F1B-$8F5A` | 64B | Seal bit table |
| `0x8F6B-0x8FAA` | PRG1 `$8F5B-$8F9A` | 64B | mask index table |
| `0x8FAB-0x8FEA` | PRG1 `$8F9B-$8FDA` | 64B | mask clear table |
| `0x8FEB-0x900B` | PRG1 `$8FDB-$8FFB` | 33B | acquired-Seal suppress helper |
| `0x900C-0x900E` | PRG1 `$8FFC-$8FFE` | 3B | tail JMP |

専用RAMは`$077D`の1Bである。取得bit `$7A`、visible mask `$0750-$0767`、room番号Xは原作または他runtimeの既存契約を読み、追加予約しない。

現行mapper66検証ROMではhook、11B helper、33B helper、3B tailとpaddingがPython定数に一致した。全table範囲、正式ROM/RAM管理簿、`RESERVED_SPANS`の位置も照合した。

## 正常と確認した事項

- 原作8 Seal bit、特殊処理stage、座標slotの対応
- `$60/$A0/$E0`のblock-state書込み
- Y座標、X、stack、呼出元flag契約
- 透明Seal保存用Level copyがeditor本体を変更しないこと
- 4 tableのroom、Seal bit、grid位置、mask byte/bit対応
- 取得済み・未取得・対象なしの全branch
- StageExt/Panel/Special Item loaderとの実行順
- `$50 -> $90`変換前のmask解除
- 現行ROM code byte列と正式ROM/RAM管理簿の位置

## 未実施

- ROM生成
- emulatorでの動的実行
- 修正実装
- ROM/RAM管理簿の変更
