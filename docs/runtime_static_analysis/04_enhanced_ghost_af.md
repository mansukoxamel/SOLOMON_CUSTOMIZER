# 4/26 強化ゴースト A-F runtime 6502静的解析

解析日: 2026-07-18
対象バージョン: v0.9.40 / commit `5db3d29` 後の作業ツリー
対象: `magatu_skc/core/ghostb0_runtime.py`、共通入口`magatu_skc/core/new_enemy_runtime.py`、Bullet速度依存`magatu_skc/core/panel_monster_stage_variant.py`
一次資料: `解析資料/ROM完全解析/solomon_commented.asm`、日本版原作ROM、現行mapper66 workstate、正式ROM管理簿

## 結論

強化ゴーストruntimeは、敵ID `$B0-$BB`をA-Fの6group、各group右・左の2IDへ割り当てる。原作Ghostの横移動AI `$ABF7`を本体として再利用し、その前後へ独立した移動速度、発射間隔、Bullet速度、発射方向を追加する211Bのruntimeである。

5個のcode chunkはすべて命令境界で末尾まで分解できた。共通入口からsetup、init、毎フレームAI、Bullet生成、animationまでの生きた経路を追跡した結果、確定した実動作バグは見つからなかった。特に、親Ghostが原作壁待ち用に使う`sub[6]`と追加Bulletが一時的に使う`sub[6]`は、同じフレームで競合しない。追加Bullet生成時は原作`$AE76`が親子link bitを直ちにclearするため、原作Ghostの後始末へ誤ってBulletが渡ることもない。

一方、保守上の問題を3件記録する。

1. 高速Bullet marker書込みを別runtimeの固定アドレス`$E59B`へ直接依存し、Ghost writer単体ではその署名を検査しない。
2. 正式版前の救済禁止方針に反する旧`PRE_COMPACT_RUNTIME`受入れが残る。
3. 旧ID配置監査のGhost `$86/$87`節が現行`$B0-$BB`実装と食い違う。

この解析ではruntimeコード、ROM配置、管理簿を変更していない。

## IDとparameterの対応

| group | 右 | 左 | parameter index |
|---|---:|---:|---:|
| A | `$B0` | `$B1` | 0 |
| B | `$B2` | `$B3` | 1 |
| C | `$B4` | `$B5` | 2 |
| D | `$B6` | `$B7` | 3 |
| E | `$B8` | `$B9` | 4 |
| F | `$BA` | `$BB` | 5 |

group indexは`(type & $0E) >> 1`で得る。`$B0-$BB`の偶数・奇数pairを同じindexへ落とし、範囲内で0-5が一度ずつ現れる。

設定表`$ED88-$ED9F`は、構造体を6個並べる方式ではなく、同種parameterを6個ずつ連続させるstructure-of-arraysである。

| offset | size | 内容 | 許容値 |
|---:|---:|---|---|
| `+0` | 6B | body metadata index | `$1A`通常 / `$1E`高速 |
| `+6` | 6B | cooldown初期値 | `$80 | interval`、interval 1-127 |
| `+12` | 6B | Bullet速度marker | `$00/$88/$89/$8A/$8B` |
| `+18` | 6B | 発射方向 | 0後方 / 2上 / 3下 |

body値は生の速度byteではない。setup pointer table `$D9D3,Y`へ渡す偶数indexで、`$1A`は原作Ghost右/左group `$34/$35`相当、`$1E`は原作Ghost別速度group `$3C/$3D`相当を選ぶ。従って原作物理とanimation metadataをまとめて切り替える。

## 原作Ghost AI

原作Neul/Ghost共通入口は`$ABF7`である。

```text
$ABF7  JSR $B201      behavior bits7-2からstate index
       JSR $8EA9      直後のinline tableへ間接dispatch
$ABFD  .word $AC68    state 0
       .word $AC05    state 1
       .word $ACDE    state 2
       .word $AD01    state 3
```

Ghostはbehavior下位2bit 0/1を使うため横移動、Neulは2/3を使うため縦移動になる。強化Ghost initはID偶奇から0/2を生成するので、右IDはbehavior 0、左IDはbehavior 2を`$9D1C`へ渡す。原作setupが初期metadataを加味した後、実際のGhost方向は右・左として成立する。この0/2はBullet方向encodeではなく、原作entity初期化用の入力である。

原作stateの要点は次である。

| state | CPU | 動作 |
|---:|---:|---|
| 0 | `$AC68` | Dana方向、衝突、速度を更新。壁接触時は補助sub-slotを確保してstate 1へ |
| 1 | `$AC05` | 10frame待ち、4隅衝突とブロック破壊 |
| 2 | `$ACDE` | 25frameまで待ち、補助slotを`$B05E`で解放してstate 3へ |
| 3 | `$AD01` | 壁から離れたらstate 0へ戻る |

追加発射cooldownは、原作AI実行後のbehavior state bits `$0C`が0の時だけ進む。このため壁待ちstate 1-3では発射せず、通常移動state 0でだけ発射する。

## 共通入口とhook経路

| 場所 | 強化Ghost経路 | 役割 |
|---:|---|---|
| 原作AI call `$A1C3` | 共通AI `$BBE2` -> Ghost分類 `$BD51` -> `$E283` | 原作AIと追加発射 |
| setup hook `$8ACB` | 共通setup `$BC32` -> `$BD5F` -> `$E258` | group別body metadata |
| init hook `$A2F2` | 共通init `$BC84` -> `$BD6F` -> `$E26A` | status、方向、cooldown初期化 |
| animation hook `$8676` | 共通animation `$BCD0` -> `$8789` | 原作animation更新 |
| property共有hook | Panel final property -> `$E313` | `$B0-$BB`へGhost property `$4A`を返す |
| Bullet spawn | `$E323` -> `$AE76` -> `$E59B` | stock Bullet生成後に速度markerを初期化 |

共通AI入口は原作dispatch値`type-$14`をstackへ保存して分類する。Ghost分類へ入る時にPLAでその値をAへ戻す。`$BD51`は`$9C-$A7`、すなわち`$B0-$BB - $14`だけを`$E283`へ送り、それ以外は原作dispatch `$A329`へ戻す。

setup分類ではAに未加工typeが残る。init分類ではmain type `$05`を読み直す。両方とも`$B0-$BB`の境界比較が成立している。

## setup runtime `$E258-$E269` 18B

```text
LDY #$01
LDA ($08),Y      ; main typeを未加工で再読込
AND #$0E
LSR A
TAX              ; group 0..5
LDA $ED88,X      ; body metadata index $1A/$1E
STA $0E
TAY
LDA $D9D3,Y      ; setup metadata pointer low
RTS
```

hook元`$8ACB`は本来`LDA $D9D3,Y`を行う場所である。runtimeはAへ同じpointer lowを返し、`$0E`も選択済みmetadata indexへ更新する。hook後の原作`$8ACE`は`$D9D4,Y`からhigh byteを読むため、Yを同じindexにして返す必要があり、TAYがその契約を満たす。

Xはgroup indexでclobberされるが、hook後はmetadata pointer解決処理でXを別用途へ再設定する。stackは使わない。

## init runtime `$E26A-$E282` 25B

共通init入口は原作`JSR $9D1C`を置換するため、呼出時AをPHAしている。強化Ghost経路はtail JMPで入る。

```text
PLA              ; 共通入口が保存したstock init inputを破棄
LDA #$C0
STA $04          ; active、gravityなし
LDA $05
AND #$01
ASL A            ; 偶数ID=0、奇数ID=2
JSR $9D1C        ; main[0..3]を初期化
LDA $06
JSR $B156        ; 自身のsub-slot pointerを$00/$01へ
LDY #$07
LDA #$80
STA ($00),Y      ; 初回発射をarm、残りcount 0
RTS
```

PLAは余分なdata stack要素を1個だけ消費し、JSRのreturn addressには触れない。`$9D1C`はA bit7が0なのでmain behaviorを書き、status `$C0`、type `$B0-$BB`、sentinel `$FF`も設定する。

cooldown `$80`は「armedかつ残り0」である。最初のstate 0 AI frameで発射試行へ入る。

## AI runtime `$E283-$E312` 144B

### parameter退避と原作AI呼出

AIは親typeからgroup indexを得て、次の順で3parameterをPHAする。

```text
1. interval | $80
2. Bullet speed marker
3. fire direction
```

その上へ`$2C/$2D/$2E/$2F`を4byte退避して原作`$ABF7`をJSRし、逆順にpointerを復元する。原作AIは壁判定・補助slot処理でzero-page pointerを利用するため、追加処理が必ず元の親main/sub pointerで継続できる。

原作AIの前後を含むstack収支は次である。

| 経路 | parameter push | pointer push/pop | parameter pop | 収支 |
|---|---:|---:|---:|---:|
| state 1-3 | +3 | +4/-4 | -3 | 0 |
| cooldown継続 | +3 | +4/-4 | -3 | 0 |
| 空きslotなし | +3 | +4/-4 | -3 | 0 |
| 発射成功 | +3 | +4/-4 | direction/speed/interval各1 | 0 |

### cooldown

原作AI後のbehavior`main[3] & $0C`が0でなければ、parameter3個を捨てて終了する。

state 0では親`sub[7]`を読む。

- bit7=0: cooldown未armとして終了。
- bit7=1、下位7bit>0: 1減算し、bit7を再設定して保存。
- bit7=1、下位7bit=0: 発射試行。

発射成功後はparameter tableの`$80 | interval`を親`sub[7]`へ再設定する。空きslotがない場合は現在値`$80`を維持するため、次の発射可能frameで再試行する。

### sub-slot確保と親子link

`$B2EA`成功時は、Xが新sub-slot index、`$04/$05`が新sub-slot pointer、Carry=1で返る。

```text
child sub[0] = $80
parent sub[0] |= $01
parent sub[6] = child index
```

これはstock Bullet API `$AE76`が期待する一時的な親子linkである。`$AE76`はparent `sub[6]`からchild indexを読み、直後に`parent sub[0] &= $FE`でlink bitをclearする。そのため、Bullet生成後に親`sub[6]`へ古いindexが残っても原作`$B05E`の解放対象にはならない。

原作Ghostが壁接触時に作る補助slotもparent `sub[6]`を使うが、補助slotを生成した同じ原作AI呼出でbehaviorはstate 1へ変わる。追加発射側は原作AI後にstate bitsを検査して終了するため、そのframeに`sub[6]`を上書きしない。state 1-3の間も発射しない。従って2用途の生きた期間は重ならない。

### 発射方向

| 設定 | Bullet X | 動作 |
|---:|---:|---|
| 2 | 2 | 上 |
| 3 | 3 | 下 |
| 0 | 0または1 | 親の進行方向と逆 |

後方設定では原作AI実行後のmain X velocity `main[8]`を比較する。原作Ghost速度encodeは右向き正値が`<$40`、左向き負値が`>=$40`である。

```text
velocity < $40  -> X=1 左へ発射
velocity >=$40  -> X=0 右へ発射
```

Bullet APIの方向は0右、1左、2上、3下なので、どちらも親の逆向きになる。

### Bullet速度marker

`$E323`はstock spawn `$AE76`を呼び、A=0で`$E59B`へtail JMPする。`$E59B`は`$02`に残るchild indexから子sub-slot pointerを求め、child `sub[7]`を0へする。これは再利用slotの古いmarkerを必ず消す処理である。

AIへ戻った後、速度parameterが0ならそのままにする。`$88-$8B`ならchild `sub[7]`へ上書きする。Panel Monster v2のBullet AI拡張がこのmarkerを読み、1/4、1/2、2倍、3倍を適用する。

## property runtime `$E313-$E322` 16B

spawn中type `$05`から`$B0`を引き、結果が12未満ならA=`$4A`でRTSする。`$4A`は原作Ghostと同じproperty入力である。

範囲外はhook元の原作命令`LDA $A30E,Y`を再実行してRTSする。SBCのunderflowは大きなunsigned値になりCMPで範囲外となるため、`$00-$AF`を誤分類しない。XとYは保持し、AとC/Z/Nは戻り値に応じて変わる。

## Bullet spawn wrapper `$E323-$E32A` 8B

```text
JSR $AE76
LDA #$00
JMP $E59B
```

stock `$AE76`は、事前確保したchildをparent `sub[6]`から取得し、座標、status `$C0`、type `$20`、behavior方向を初期化し、SE `$17`を鳴らす。`$9D1C`はzero-page `$02`を書き換えないため、後続`$E59B`がchild indexとして`$02`を読む契約も成立する。

tail JMP先`$E59B`のRTSが、もともと`JSR $E323`したAIへ直接戻る。wrapper自身のreturn addressを余分に積まないため、stack収支は正しい。

## register・flag・stack検査

| 入口 | A | X | Y | stack/flag |
|---|---|---|---|---|
| setup `$E258` | metadata pointer lowを返す | group index | metadata index | stack不使用 |
| init `$E26A` | cooldown値等でclobber | `$B156`でclobber | 7 | 保存AをPLA、JSR元へRTS |
| AI `$E283` | 判定・parameterでclobber | group/slot/directionでclobber | field indexでclobber | 全4終了経路で収支0 |
| property `$E313` | propertyを返す | 保持 | fallback table indexを保持 | stack不使用 |
| spawn `$E323` | 0をmarker helperへ渡す | stock spawnでclobber | stock spawnでclobber | JSR後にtail JMP、最終RTSで収支0 |

このAIは原作`$ABF7`と同様にA/X/Y/condition flagsを保存するAPIではない。AI dispatch callerもそれらの保持を要求しない。

## code chunkと命令境界

| chunk | CPU | size | disassembly |
|---|---:|---:|---|
| setup | `$E258-$E269` | 18B | 18B全消費、10命令 |
| init | `$E26A-$E282` | 25B | 25B全消費、13命令 |
| AI | `$E283-$E312` | 144B | 144B全消費、84命令 |
| property | `$E313-$E322` | 16B | 16B全消費、9命令 |
| Bullet wrapper | `$E323-$E32A` | 8B | 8B全消費、3命令 |

全relative branchはchunk内の命令先頭へ着地する。Python builderはbranch距離`-128..127`も検査する。

## ROM/RAM配置

| file | CPU | size | 内容 |
|---:|---:|---:|---|
| `0x3D61-0x3D98` | `$BD51-$BD88` | 56B | 共通入口側Ghost分類extension |
| `0x6268-0x633A` | `$E258-$E32A` | 211B | 強化Ghost本体 |
| `0x633B-0x6341` | `$E32B-$E331` | 7B | 現行runtime予約なし |
| `0x65AB-0x65B6` | `$E59B-$E5A6` | 12B | Panel runtime所有のstatic marker helper |
| `0x6D98-0x6DAF` | `$ED88-$ED9F` | 24B | A-F parameter table |

新規専用RAMは使わない。既存の親`sub[7]`をcooldown、子Bullet `sub[7]`を速度markerとして使う。親`sub[6]`はspawn APIへ渡す一時的child indexである。

## 確定した問題・保守上の問題

### [P2] 外部marker helperの署名をGhost writer単体で検査しない

Ghost本体は`$E323`から固定アドレス`$E59B`へ直接JMPする。実体は`panel_monster_stage_variant.py`が所有する12B helperであり、現行workstateでは正しいbyte列と一致する。Panel runtimeを常設する現行保存経路でも毎回書かれる。

しかし`ghostb0_runtime.current_settings()`と`apply_settings()`は、Ghost本体211Bとparameter 24Bだけを検査する。`$E59B`が空、旧版、未知codeのいずれでもGhost runtimeを正常と判定できる。`new_enemy_runtime.apply()`もGhost本体を検査するが、この外部helperの所有確認はPanel writer側まで進まないと成立しない。

通常の完成ROMでは直ちに再現するバグではないが、モジュール単体のfail-closed境界と依存宣言が不完全である。helperが欠けたROMでは全Ghost発射が未知codeへ入るため、影響は大きい。

### [P3] 旧pre-compact runtimeを互換入力として受け入れる

`PRE_COMPACT_RUNTIME`は現行runtime末尾JMP先`$E59B`だけを旧`$E5D5`へ戻した211Bである。`current_settings()`と`new_enemy_runtime.apply()`はこれを明示的に許容し、現行byte列へ置換する。

これは古い内部ROMを読み替えるmigrationであり、正式版前は古い実験ROM・途中生成ROMを救済しないという現行方針に合わない。生きた6502処理の誤りではないが、不要な入力状態を正常扱いする保守負担になっている。

### [P3] 旧ID配置監査のGhost節が現行実装と不一致

`docs/new_enemy_id_placement_audit.md`にはGhost `$86/$87`と`ghost86_runtime.py`を前提にしたBomber/Cannon構想が残り、ROM使用範囲`0x6D98-0x6E15`を別runtimeとして説明している。現行実装は`ghostb0_runtime.py`、ID `$B0-$BB`、本体`0x6268-0x633A`、parameter表`0x6D98-0x6DAF`である。

正式ROM管理簿は現行配置と一致しているためROM重複そのものではない。ただし、旧監査を設計根拠に使うとID数、所有module、`0x6D98`の用途を誤認する。

## 正常と確認した事項

- `$B0-$BB`全12IDがA-Fの6pairへ重複・漏れなく分類される
- 右・左の偶奇IDが同じparameter groupを共有する
- `$1A/$1E`が有効な偶数metadata indexで、原作Ghost setup pointerを選ぶ
- init入口のPHA/PLAとJSR/RTS stack収支成立
- initが親`sub[7]=$80`として初回発射をarmする
- 原作AIを先に実行し、その後のstate 0だけでcooldownを進める
- cooldown 1-127の減算、再arm、空きなし再試行が成立
- state 1-3の壁待ち中は追加発射しない
- 原作壁補助slotと追加Bulletのparent `sub[6]`使用期間が競合しない
- `$B2EA`成功/失敗両経路で不正なslot writeなし
- 後方、上、下の3方向設定がstock Bullet encodeと一致
- stock Bullet marker 0と高速marker `$88-$8B`の初期化・上書き順序成立
- propertyのGhost範囲とstock fallback成立
- animationがsetup済みmetadataを使って原作`$8789`へ入る
- 5 chunk全て命令分断なし、全branch target有効
- 現行workstateの本体211B、parameter 24B、共通4入口、56B extension、12B marker helperがbuilderと一致
- 現行設定6groupは全てbody `$1A`、interval 64、stock Bullet、下向き
- 設定無変更`apply_settings()`の変更report 0件、変更byte 0件

## 未実施と、この文書だけで保証しないこと

- 今回はROMを新規生成していない。
- Mesenで12ID、2 body速度、127 interval、5 Bullet速度、3発射方向の全組合せを新たに動的網羅していない。
- 敵slotが常時満杯、壁補助slot生成とBullet死亡が連続する長時間stress testは新規実行していない。
- 外部helper依存、旧pre-compact受入れ、旧監査文書不一致は記録のみで修正していない。
