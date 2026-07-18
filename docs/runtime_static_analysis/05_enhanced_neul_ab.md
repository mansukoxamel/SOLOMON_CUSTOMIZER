# 5/26 強化ヌエル A/B runtime 6502静的解析

解析日: 2026-07-18
対象バージョン: v0.9.40 / commit `5db3d29` 後の作業ツリー
対象: `magatu_skc/core/neul84_runtime.py`、共有処理`ghostb0_runtime.py`、`new_enemy_runtime.py`、`panel_monster_stage_variant.py`
一次資料: `解析資料/ROM完全解析/solomon_commented.asm`、日本版原作ROM、現行mapper66 workstate、正式ROM管理簿

## 結論

強化ヌエルruntimeは、敵ID `$84-$87`をA/Bの2group、各group上・下の2IDへ割り当てる。原作Neul/Ghost共通AI `$ABF7`を縦移動Neulとして再利用し、通常移動stateで左右2方向のBulletを同時発射する212Bのruntimeである。A/Bごとに本体速度、発射間隔、Bullet速度を独立設定できる。

setup、init、AIの3 code chunkはすべて命令境界で末尾まで分解できた。二連射の空きslot 0/1/2個の全経路、原作壁待ちslotとの競合、stack、pointer復元、高速Bullet markerを追跡し、確定した実動作バグは見つからなかった。

問題は2件ある。

1. Ghost本体のBullet wrapper `$E323`とPanel本体のmarker helper `$E59B`へ直接依存するが、Neul writer単体では両方の署名を検査しない。
2. 2発ともslot不足で生成できない場合もcooldownを満額へ戻す。仕様として決定済みかコード・UIから判別できず、発射機会を不必要に失う可能性がある。

この解析ではruntimeコード、ROM配置、管理簿を変更していない。

## IDと設定表

| group | 上 | 下 | group index |
|---|---:|---:|---:|
| A | `$84` | `$85` | 0 |
| B | `$86` | `$87` | 1 |

group indexは`(type-$84) >> 1`で得る。設定表`$EF95-$EF9A`は3種類を2byteずつ並べる。

| offset | size | 内容 | 許容値 |
|---:|---:|---|---|
| `+0` | 2B | body metadata index | `$18`通常 / `$1C`高速 |
| `+2` | 2B | 発射間隔 | 1-127 |
| `+4` | 2B | Bullet速度marker | `$00/$88/$89/$8A/$8B` |

body値は速度byteそのものではなくsetup table `$D9D3,Y`のindexである。`$18`は原作Neul `$30/$31`相当、`$1C`は別速度Neul `$38/$39`相当のmetadata pointerを選ぶ。

## 原作Neul AIとの関係

原作NeulとGhostは同じ4-state AI `$ABF7`を使う。

```text
state 0  $AC68  移動方向・衝突更新、壁接触時に補助slot生成
state 1  $AC05  10frame待ち、ブロック破壊
state 2  $ACDE  25frame待ち、補助slot解放
state 3  $AD01  壁を離れたらstate 0へ
```

強化Neul initはID偶奇からbehavior入力0/2を作る。setupでNeulの縦速度metadataを選ぶことと組み合わせ、偶数IDが上、奇数IDが下として成立する。

追加発射は原作AIを先に実行し、その後の`main[3] & $0C`が0の場合だけ進む。原作AIが壁補助slotを生成したframeはstate 1へ変わっているため、そのframeに追加Bulletがparent `sub[6]`を上書きしない。state 1-3でも発射しないので、Ghost解析と同様に2用途の生存期間は重ならない。

## 共通入口と依存先

| 場所 | 強化Neul経路 | 役割 |
|---:|---|---|
| AI hook `$A1C3` | `$BBE2` -> `$EEEE` | 原作AIと二連射 |
| setup hook `$8ACB` | `$BC32` -> `$EEC1` | group別body metadata |
| init hook `$A2F2` | `$BC84` -> `$EED4` | status、上下、cooldown初期化 |
| animation hook `$8676` | `$BCD0` -> stock `$8789` | 原作animation |
| Bullet wrapper | Neul `$EEEE` -> Ghost `$E323` | stock Bullet生成とmarker 0初期化 |
| marker helper | Ghost `$E323` -> Panel `$E59B` | child `sub[7]`書込み |

AI共通入口では`$84-$87`を専用dispatchへ送る。setup/init共通入口でも同じ4IDだけを専用routineへ送る。animationは専用処理を持たず、setup済みmetadataを使ってstock updaterへ入る。

propertyはGhost helperのstock fallbackを通る。Neul setupが有効なmetadata indexを`$0E/Y`へ設定しているため、原作property table readが成立する。

## setup `$EEC1-$EED3` 19B

```text
LDY #$01
LDA ($08),Y
SEC
SBC #$84
LSR A
TAX                  ; A/B index 0/1
LDA $EF95,X          ; $18/$1C
STA $0E
TAY
LDA $D9D3,Y
RTS
```

hook後の原作`$8ACE`は同じYで`$D9D4,Y`を読む。Aにpointer low、Yにindex、`$0E`にanimation/setup groupを返す契約が成立する。分類入口が範囲を保証するためSBC underflowは起きない。

## init `$EED4-$EEED` 26B

```text
PLA
LDA #$C0
STA $04
LDA $05
AND #$01
ASL A
NOP
JSR $9D1C
LDA $06
JSR $B156
LDY #$07
LDA #$80
STA ($00),Y
RTS
```

共通init入口がPHAしたstock入力をPLAで1byteだけ捨てる。`$9D1C`はmain status `$C0`、type `$84-$87`、sentinel `$FF`、上下用behaviorを設定する。自身の`sub[7]`へ`$80`を入れ、初回発射をarmする。

ASL後のNOPは意味を持たない1Bだが、到達不能codeや不正命令ではない。現行予約は実使用212Bだけなので、削除するなら後続entryを1Bずつ詰める必要がある。

## AI `$EEEE-$EF94` 167B

### 原作AIとcooldown

最初に`$2C-$2F`を4byte PHAし、原作`$ABF7`をJSRした後に逆順で復元する。AI前後のpointer stack収支は0である。

原作AI後にstate 0でなければRTSする。state 0ではparent `sub[7]`を読む。

- bit7=0: 未armとしてRTS。
- 下位7bit>0: 1減らし、bit7を再設定して保存。
- 下位7bit=0: 二連射へ進む。

### 二連射

発射方向A=0で`fire_one`を呼び、続いてA=1でもう一度呼ぶ。stock Bullet encodeは0右、1左なので、Neul本体の左右へ1発ずつ生成する。

`fire_one`は方向AをPHAし、`$B2EA`で空きsub-slotを探す。

成功時:

```text
child sub[0] = $80
parent sub[0] |= $01
parent sub[6] = child index
directionをPLAしてXへ
$2C-$2Fを4byte保存
JSR $E323
$2C-$2Fを復元
group別speed markerをchild sub[7]へ設定
RTS
```

失敗時は方向AだけをPLAしてRTSする。親、child、pointerを変更しない。

2回の呼出は独立している。

| 空きslot | 右弾 | 左弾 | 不正write |
|---:|---|---|---|
| 0 | 失敗 | 失敗 | なし |
| 1 | 成功 | 失敗 | なし |
| 2以上 | 成功 | 成功 | なし |

最初の成功Bulletはchild `sub[0]=$80`のため、2回目の`$B2EA`からfreeと誤認されない。stock `$AE76`は各回でparent link bit0をclearするため、次の`fire_one`が新しいchild indexを安全にparent `sub[6]`へ設定できる。

### pointerとstack収支

`$E323->$AE76->$E59B`はzero-page `$00-$05`、X、Yをclobberする。特に`$E59B`はchild sub-slot pointerを`$00/$01`へ置く。Neul側は各Bullet spawnの前後で親pointer `$2C-$2F`を保存・復元するため、2発目とcooldown table計算は正しい親を参照する。

各`fire_one`のstackは次で均衡する。

| 経路 | direction | pointer | JSR/RTS | 収支 |
|---|---:|---:|---:|---:|
| 空きなし | +1/-1 | 0 | 均衡 | 0 |
| 発射成功 | +1/-1 | +4/-4 | 均衡 | 0 |

外側AIの原作呼出用pointer +4/-4も別に均衡する。

### cooldown再設定

2回の`fire_one`から戻ると、親typeからgroup indexを再計算し、`$EF97,X`のintervalへbit7を立ててparent `sub[7]`へ書く。各`fire_one`は成功/失敗をCarryやAで返さないため、弾が0発、1発、2発のどの場合も同じcooldownへ戻る。

## Bullet速度

speed 0ではGhost wrapperが書いたchild `sub[7]=0`を維持する。`$88-$8B`では`fire_one`がparent `sub[6]`から今生成したchildを引き直し、markerを上書きする。

Panel Monster v2のBullet AI拡張がmarkerを解釈する。

| marker | 速度 |
|---:|---:|
| `$00` | 原作 |
| `$88` | 1/4 |
| `$89` | 1/2 |
| `$8A` | 2倍 |
| `$8B` | 3倍 |

Neul runtimeだけでは高速移動を実装せず、Ghost wrapperとPanel Bullet拡張の両方が必要である。

## code chunk・ROM/RAM配置

| chunk | CPU | size | disassembly |
|---|---:|---:|---|
| setup | `$EEC1-$EED3` | 19B | 19B全消費、11命令 |
| init | `$EED4-$EEED` | 26B | 26B全消費、14命令 |
| AI | `$EEEE-$EF94` | 167B | 167B全消費、96命令 |

| file | CPU | size | 内容 |
|---:|---:|---:|---|
| `0x6ED1-0x6FA4` | `$EEC1-$EF94` | 212B | 強化Neul本体 |
| `0x6FA5-0x6FAA` | `$EF95-$EF9A` | 6B | A/B parameter table |
| `0x6FAB-0x7004` | `$EF9B-$EFF4` | 90B | 現行runtime予約なし |

新規専用RAMは使わない。親`sub[7]`をcooldown、各Bullet `sub[7]`を速度marker、親`sub[6]`をspawn中のchild indexに使う。

## 確定した問題・要確認点

### [P2] 2段の外部runtime依存をNeul writerが検査しない

Neul AIは固定アドレス`$E323`をJSRする。そこは`ghostb0_runtime.py`所有の8B wrapperで、さらにPanel runtime所有の`$E59B`へJMPする。

`neul84_runtime.current_settings()`と`apply_settings()`が検査するのは、自身の212Bと6B parameterだけである。`$E323`または`$E59B`が空・旧版・未知codeでもNeul設定を正常と判定できる。現行完成ROMでは3領域とも常設され、最新workstateでも全byte一致しているため直ちに再現する不具合ではない。しかしwriter単体のfail-closed境界は不完全で、どちらかが欠けると発射時に未知codeへ入る。

### [P3] 全弾生成失敗でもcooldownを満額消費する

`fire_one`は成功/失敗を呼出側へ返さず、二連射後は無条件にintervalを再armする。空きsub-slotが0個だった場合、見た目には1発も発射していないが、次の発射試行まで設定intervalだけ待つ。

Ghost A-Fは空きなしの場合に`sub[7]=$80`を維持し、次のstate 0 frameで再試行するため、同じ共有Bullet系でも挙動が異なる。UIとCHANGELOGにはslot不足時の仕様がない。従って確定バグとは断定しないが、多敵面で発射機会が欠落する挙動として明示しておく。

## 正常と確認した事項

- `$84-$87`の4IDがA/B、上/下へ漏れなく分類される
- setup `$18/$1C`が原作Neul metadata pointerを選ぶ
- init入口のPHA/PLA、上下behavior、cooldown初期化が成立
- 原作AI前後のparent pointer保存・復元が成立
- state 1-3の壁待ち中は発射せず、原作補助slotと競合しない
- cooldown 1-127の減算と再armが成立
- 右・左の二連射direction encodeがstock `$AE76`と一致
- 空きslot 0/1/2個の全経路で不正slot writeなし
- 各`fire_one`と外側AIの全stack経路で収支0
- 各Bullet spawn後に親pointerを復元する
- speed marker 0と`$88-$8B`の初期化・上書き順序成立
- setup/init/AIの3 chunk全て命令分断なし、全branch target有効
- 現行workstateの本体212B、parameter 6B、AI/setup/init共通入口、Ghost wrapper、Panel marker helperがbuilderと一致
- 現行設定はA/Bともbody `$18`、interval 64、stock Bullet
- 設定無変更`apply_settings()`の変更report 0件、変更byte 0件

## 未実施と、この文書だけで保証しないこと

- 今回はROMを新規生成していない。
- Mesenで4ID、2 body速度、127 interval、5 Bullet速度の全組合せを新たに動的網羅していない。
- slot不足時に即時再試行すべきかは仕様文書がなく、今回確定していない。
- 外部依存の署名検査とslot不足時cooldownは記録のみで修正していない。
