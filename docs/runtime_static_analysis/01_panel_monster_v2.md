# 1/26 Panel Monster v2 runtime 6502静的解析

解析日: 2026-07-18
対象バージョン: v0.9.40 / commit `5db3d29` 後の作業ツリー
対象: `panel_monster_stage_variant.py`、`panel_monster_variant.py`、接続元の`new_enemy_runtime.py`
一次資料: `解析資料/ROM完全解析/solomon_commented.asm`、日本版原作ROM、現行mapper66 workstate

## 結論

Panel Monster v2の現行生きた6502経路について、以下を確認した。

- `$E0-$F7`の24IDは、原作Panel Monster `$24-$27`と同じAI `$A54C`へ入り、状態0の発射待ちと状態1のBullet生成を再利用する。
- A-Dは「1発の速度と発射間隔をgroup別に変える」、2-way/3-wayは「複数Bulletを生成し、各Bulletの`sub[7]`へ広がり方向markerを持たせる」仕組みである。
- 親PanelはAI入口と速度初期化の両方で速度関連fieldを0にし、原作の状態変更が速度表を読み直しても定点から動かないようにしている。
- 複数発射、速度marker、Bullet追加substepのstack収支に不整合は見つからなかった。全生成code blobは6502命令として末尾まで分解でき、途中の不正opcodeや命令分断はない。
- 現時点で、生きたPanel Monsterのプレイ中動作を壊す確定バグは見つかっていない。

一方で、静的解析中に次の具体的な問題を確定した。この文書作成では修正していない。

1. PRG1 loader helperの署名不一致時、例外前に`0x8A10-0x8A12`の3バイトを書き換える。
2. 正常にFire2 loaderまで適用したROMを、Panelのsave reportが`all_written=False`と誤判定する。
3. 現行hookから到達不可能な33バイトの6502 codeを、現行runtimeとして毎回書き込み・予約している。
4. 旧pre-compact配置を検出して消去・移行する救済経路が残っており、現在の「旧ROM救済を入れない」方針と一致しない。

## Panel Monster v2が扱う24ID

| ID | group | 方向bit | 発射方式 |
|---|---|---|---|
| `$E0-$E3` | A | ID下位2bit | 1発、Aの速度/間隔 |
| `$E4-$E7` | B | ID下位2bit | 1発、Bの速度/間隔 |
| `$E8-$EB` | C | ID下位2bit | 1発、Cの速度/間隔 |
| `$EC-$EF` | D | ID下位2bit | 1発、Dの速度/間隔 |
| `$F0-$F3` | 2-way | ID下位2bit | 中心方向の両側へ2発 |
| `$F4-$F7` | 3-way | ID下位2bit | 中心と1発+両側の2発 |

方向は原作Bullet/Panelと同じく、`0=右、1=左、2=上、3=下`である。新IDの下位2bitをそのまま原作behaviorの方向bitとして使う。

## 原作Panel Monsterの基本構造

原作Panel Monster `$24-$27`のAI入口は`$A54C`である。

```text
$A54C  JSR $B201       behavior / 4 を状態indexにする
       JSR $8EA9       直後の2word tableへ間接分岐

state 0 -> $A575       発射準備待ち
state 1 -> $A556       確保済み子slotへBulletを生成
```

`$A575`は`sub[2] >= $C0`になると`$B2EA`で空きslotを1個確保し、slot indexを親の`sub[6]`へ保存する。その後、方向bitを保ったままbehaviorのbit2を立て、state 1へ移る。

`$A556`は`sub[1] >= $10`を発射前gateとし、方向をXへ入れて`$AE76`を呼ぶ。`$AE76`は親の`sub[6]`から子slotを取得し、status `$C0`、type `$20`のBulletを親の口元へ生成する原作APIである。

Panel Monster v2はこの「待つ -> slot確保 -> `$AE76`でBullet生成」を作り直さず、入口と閾値と生成回数だけを拡張している。

## 主なentity field

| ポインタ | field | 用途 |
|---|---:|---|
| `($2E)` main | `[1]` | enemy type `$E0-$F7` |
| `($2E)` main | `[3]` | behavior。下位2bit=方向、bit2以上=状態 |
| `($2E)` main | `[5]` | Y速度 |
| `($2E)` main | `[6]` | Y座標の小数側 |
| `($2E)` main | `[7]` | Y座標の整数側 |
| `($2E)` main | `[8]` | X速度 |
| `($2E)` main | `[9]` | X座標の小数側 |
| `($2E)` main | `[10]` | X座標の整数側 |
| `($2C)` sub | `[1]` | 状態経過counter。発射前gateとspread間引きに使用 |
| `($2C)` sub | `[2]` | idle側の発射準備値 |
| `($2C)` sub | `[6]` | 次に`$AE76`が使う子slot index |
| `($2C)` sub | `[7]` | v2がBulletへ書くmarker `$80-$84/$88-$8B` |

`sub[7]`は新しい専用RAMではない。子Bullet自身のsub-slot内fieldを、Panelから生まれたBulletの間だけmarkerとして使う。

## hookと呼出規約

| 原作CPU | 変更後 | 役割 |
|---:|---|---|
| `$A556` | `JMP $E486` | enemy typeをnormal/A-D/2-way/3-wayに分類 |
| `$A575` | `JSR $E570` + 3 NOP | `sub[2]`とgroup別間隔をCMPし、Carryを原作`BCC $A59F`へ渡す |
| `$AFBB` | `JSR $E6DC` | Bullet state indexを読み、state 2のみspread/速度処理を入れる |
| `$866D` | `JSR $E4C8` | 共有速度初期化後、Panelの速度fieldを再度0にする |
| `$A2CC` | `JSR $BF43` | Spark property dispatch経由でPanelはproperty `$08`を返す |
| `$8B05` | `JSR $CFDE` | Spark animation dispatch経由でPanel metadata `$D33A`を設定 |
| 新敵AI入口 `$BBE2` | `JMP $E6B7` | `$E0-$F7`をPanel共通AI wrapperへ渡す |

### `$A575` hookがCarryを戻り値に使う理由

原作は次の並びである。

```text
LDY #$02
LDA ($2C),Y
CMP #$C0
BCC not_ready
```

現行hookは最初の6バイトを`JSR $E570` + NOPに置き換える。`$E570`の最後は必ず`CMP settings_interval,X`または`CMP #$C0`で、その直後に`RTS`する。`RTS`はCarry/Zero/Negativeを変えないため、原作の`BCC`は現行間隔の比較結果をそのまま受け取る。

このhelperはXをgroup table offsetで上書きするが、準備成立後の原作は直に`$B2EA`を呼び、そこでXに空きslot indexを返す。従ってこの位置でのX clobberは後続に影響しない。

## A-D settings table

PRG0 `$E4F1-$E4F8` / file `0x6501-0x6508`の8バイトを、次の4pairとして直接読む。

```text
A speed, A interval,
B speed, B interval,
C speed, C interval,
D speed, D interval
```

enemy typeからtable offsetへの変換は次である。

```text
(type - $E0) & $0C
        ↓ LSR
A=$00, B=$02, C=$04, D=$06
```

`$F0-$F7`とstock Panelはこのtableを使わず、原作間隔`$C0`と通常Bullet速度を使う。

## 発射処理の全体流れ

### 1. idleから発射状態へ入る

```text
Panel AI $A54C
  ↓ behavior / 4 = state 0
$A575 hook -> $E570
  ↓ sub[2] >= interval ?
no  -> RTS
yes -> $B2EAで最初の子slotを確保
       sub[6] = slot index
       behavior bit2 = 1
       sub[2] = 0, sub[1] = 0
```

### 2. 発射前gate

state 1へ入っても、直にBulletは出ない。`sub[1] < $10`の間は原作と同じく口元の準備時間を待つ。A-Dの「発射間隔」はこの`$10`を変えない。変えるのは次の攻撃へ入るまでのidle側の閾値である。

### 3. fire dispatch

`$E486`は親のtypeを読み、発射loopの開始indexを決める。

| 種類 | 開始X | marker tableの使用index | 生成数 |
|---|---:|---|---:|
| 2-way `$F0-$F3` | 0 | 0,1,2 | 2 |
| 3-way `$F4-$F7` | 3 | 3,4,5,6 | 3 |
| A-D `$E0-$EF` | 7 | 7,8 | 1 |
| stock/その他 | 9 | 9,10 | 1 |

marker table `$E6D1-$E6DB`は次の11バイトである。

```text
83 84 FF | 81 80 82 FF | FE FF | FF FF
```

`FF`は「markerなし/終了」、`FE`は「A-D settingsから速度markerを動的生成」である。

最初のBulletは原作idle処理が確保済みの`sub[6]`を使う。2発目以降が必要な場合だけ`$B2EA`を再度呼ぶ。追加slotを取れなかった場合は、それまでに生成できたBulletを残し、発射状態の後始末へ入る。存在しないslotを解放する経路はない。

### 4. 発射終了

最後に親behaviorを方向bitだけへ戻し、`sub[2]`と`sub[1]`を0にする。次のAI呼出から再びstate 0の準備待ちに入る。

## 2-way / 3-wayが広がる仕組み

`$AE76`自体は、何発出しても親の向きと同じ方向のBulletを作る。吐き出す角度を変えているのではない。

v2は生成した各Bulletの`sub[7]`へ`$80-$84`を書き、Bulletのstate 2処理の直前に、進行軸と直交する座標を増減する。

| marker | 効果 |
|---:|---|
| `$80` | 中心弾。座標補正なし |
| `$81` | 直交軸を毎回+1 |
| `$82` | 直交軸を毎回-1 |
| `$83` | `sub[1]`が偶数の回だけ直交軸を+1 |
| `$84` | `sub[1]`が偶数の回だけ直交軸を-1 |

横向BulletではY座標`main[7]`、縦方向BulletではX座標`main[10]`を変える。これにより、3-wayの両側弾は中心線から毎回離れ、2-wayはその半分の頻度で広がる。

## A-DのBullet速度

A-Dの発射時は、groupの速度preset `0-3`を`$88-$8B`へ変換し、子Bulletの`sub[7]`へ書く。

| preset | marker | 正方向 | 負方向 | 追加substep |
|---|---:|---:|---:|---:|
| 1/4 | `$88` | `$0C` | `$74` | 0 |
| 1/2 | `$89` | `$18` | `$68` | 0 |
| 2x | `$8A` | `$30` | `$50` | 1 |
| 3x | `$8B` | `$30` | `$50` | 2 |

Bulletの方向bitから、横方向なら`main[8]`、縦方向なら`main[5]`を選ぶ。右/下は表の正方向、左/上は負方向の値を使う。

2x/3xは速度byteをさらに大きくするのではない。原作物理が行う1回分に加え、同じ速度の座標加算をAI内で1回または2回追加する。追加ごとに`$AC39`で衝突maskを再取得する。

追加substepで衝突を見つけた場合、その場で破壊処理やdespawnへ飛ばず、追加loopだけを抜ける。その後に原作Bullet state 2 `$AFD8`が実行され、同じ`$AC39`の結果から原作のブロック破壊/despawn経路へ入る。追加loopから原作impact処理を直接二重呼びしない構造になっている。

## Bullet hookのstack収支

`$AFBB`の原作`JSR $B201`は`JSR $E6DC`へ差し替えられる。`$E6DC`は`JMP $E618`なので、`$E618`の`RTS`は元の`$AFBE`へ直接戻る。

### state 2以外

```text
JSR $B201
PHA          ; state index保存
CMP #2
BNE done
done: PLA
RTS
```

push 1回 / pop 1回で収支0。Aは原作`$B201`の戻り値に復元され、`$AFBE` の間接dispatchへ渡る。

### state 2の通常・spread経路

state Aをpushした後、さらに`TXA/PHA`で呼出元Xを保存する。各minus/plus tailは座標を1変化させた後、`PLA/TAX`でX、次の`PLA`でstate Aを復元してRTSする。push 2回 / pop 2回で収支0。

### speed経路

speed decodeはXを追加substep数0/1/2にする。fast loopは各周回の先頭でXをpushし、通常完了も衝突中断も必ず1回popする。speed tailへ戻ると、その外側に保存していた呼出元Xとstate Aをそれぞれpopする。衝突経路を含めstack深度は必ず元に戻る。

## 親Panelが勝手に動かないための二重guard

Panelは定点敵だが、汎用entity更新`$866D -> $8AC0`はbehaviorが変わると速度表を読み直す。v2は次の2箇所で速度を消す。

1. `$866D`の速度初期化hookで、Saramandor/Gargoyle/原作の速度初期化を先に実行した後、typeが`$E0-$F7`ならmain `[5],[6],[8],[9]`を0にする。
2. 新敵AI共通入口から`$E6B7`へ入るたびに、同じ4fieldを0にする。

1つ目は「状態変更直後の汎用速度読込」、2つ目は「AI実行時の念押し」を止める。この2系統の目的は異なり、単純な二重書き込みではない。

## propertyとanimation

高ID `$E0-$F7`は原作のtable範囲外なので、AIだけをPanelにしても初期statusや表示は成立しない。

- property hookはPanelに原作type `$24-$27`と同じproperty `$08`を返す。
- animation hookはmetadata pointer `$D33A`を`$0A/$0B`へ設定し、type下位2bitを`$0F`へ渡す。
- 実際のhook所有者はSpark側で、PanelはSpark dispatchの「Panelへのfallback」として接続される。

このため、Panel単体の解析でproperty/animation本体の戻り値は確認したが、Spark dispatch全branchとの組合せは3/26 Spark Ball解析で再検査する。

## ROM配置

PRG0のPanel blockはfile `0x6496-0x6724`、CPU `$E486-$E714`の655バイトである。現行placement report上は重複なし、隣接piece間の隙間なしである。

主な配置を実行順にまとめる。

| CPU | size | 内容 |
|---:|---:|---|
| `$E486` | 35 | fire dispatch |
| `$E4A9` | 19 | 到達不可能な旧AI dispatch |
| `$E4BC` | 12 | 上記dispatch内部からのみ参照される旧tail |
| `$E4C8` | 29 | parent speed guard |
| `$E4E5` | 12 | `$E0-$F7` classifier |
| `$E4F1` | 8 | A-D settings table |
| `$E4F9` | 2 | 到達不可能なclassifier tail |
| `$E4FB` | 3 | animation direction helper |
| `$E4FE` | 114 | common fire loop |
| `$E570-$E5C7` | 88 | interval/group/marker/parent clear helpers |
| `$E5C8-$E617` | 80 | speed table 12B + fast loop 68B |
| `$E618-$E67E` | 103 | Bullet entry + 3 tail |
| `$E67F-$E6B6` | 56 | speed marker decode |
| `$E6B7-$E6D0` | 26 | new-ID shared AI wrapper |
| `$E6D1-$E6DB` | 11 | fire marker table |
| `$E6DC-$E6DE` | 3 | Bullet hook trampoline |
| `$E6DF-$E714` | 54 | property + animation hook |

PRG1には`0x8A10-0x8A6F`の96バイトloader slotと、`0x8A76-0x8A8B`の22バイトStageExt gameplay helperを使う。最終保存順ではFire2がloader先頭3バイトを`JMP $9270`へ差し替え、Fire2 helperからPanel/StageExt loader本体へ連鎖する。

## レジスタ・flag・stack検査結果

| 入口 | A | X | Y | flag/stackの契約 |
|---|---|---|---|---|
| classifier `$E4E5` | typeを比較するためclobber | 保持 | 保持 | PanelはC=1、その他はC=0 |
| interval `$E570` | `sub[2]` | group offsetでclobber | 2 | 最終CMPのC/Z/Nを呼出元へ返す |
| fire common `$E4FE` | clobber | marker loop indexでclobber | clobber | 全PHA/PLA経路の収支0 |
| Bullet entry `$E618` | state indexに復元 | 呼出元Xに復元 | clobber | state0/1、spread、speed、collision全経路で収支0 |
| shared AI `$E6B7` | clobber | directionでclobber | clobber | `JMP $A54C`でtail call、追加stackなし |
| speed guard `$E4C8` | clobber | 共有速度初期化でclobber | clobber | `JSR` chain後にRTS、stack収支0 |
| property `$E6DF` | property値を返す | 保持 | 保持 | classifierのCarryは戻り契約ではない |
| animation `$E6ED` | clobber | 保持 | 1 | `$0A/$0B/$0F`へメタデータを返す |

relative branchはPython assemblerの`finish()`が全label解決と`-128..127`を検査する。加えて生成済みの22 code blobをMOS 6502ディスアセンブラへ通し、各blobの全バイトが命令境界で最後まで消費されることを確認した。

## 他runtimeとの依存

### Enhanced Saramandor / Gargoyle

`$866D` hookはPanelだけの速度処理ではない。最初にEnhanced Saramandor `$E9A9`を呼び、そこからGargoyle `$EDA0`と原作`$8AC0`へ連鎖する。Panelはその連鎖が終わった後に自分の速度を0へ戻す。

この呼出順は現行アドレスと一致することを確認したが、Saramandor/Gargoyle内部の全branchは2/26と15/26で個別に再検証する。

### Spark Ball

property `$A2CC`とanimation `$8B05`のhookはSpark側が所有する。Panel helperはSparkの非該当経路から呼ばれる。Panel解析ではPanel helper本体の入出力は確認したが、Spark側のfallback判定は3/26で再検証する。

### Fire2 / StageExt

PRG1 loaderはStageExtをPanelが上書きし、さらにFire2が先頭JMPを上書きする合成構造である。最終ROMでPanel loader slotがPanel単体と一致しないのは正常である。

## 確定した問題

### [P2] PRG1 loader helper異常時に3バイトが先に変更される

`apply_runtime_loader()`は次の順で動く。

1. `0x8A10-0x8A6F`へPanel loader slotを書く
2. `0x8A76-0x8A8B`のStageExt gameplay helperを検査する
3. helperが未知の場合は例外

現行workstateのhelper先頭を`$11`へ変えたメモリ内試験では、例外を正しく出す一方、例外前に`0x8A10-0x8A12`の3バイトがFire2 JMPからPanel loader先頭へ書き換わった。

```text
caught=True
changed_count=3
changed range=0x8A10-0x8A12
```

`save_levels_to_rom()`の通常経路は作業copyを使うため、この例外で元ROMファイルへ部分保存されるとは限らない。しかしwriter単体はfail-closedになっておらず、v0.9.40で他writerへ入れた事前一括検証と同じ問題がPanelに残っている。

### [P2] 正常な最終ROMをsave reportが未適用と誤判定する

Panel適用後にFire2を適用するのが正常な保存順である。Fire2はPanel loader slotの先頭3バイトを正式に差し替える。

しかし`panel_monster_v2_settings_save_report()`は96バイト全体がPanel単体slotと完全一致することだけを正常とする。現行の正常workstateでは次の結果になった。

```text
speed_all=True
settings_table_written=True
runtime_loader_written=False
all_written=False
```

runtime自体の動作バグではないが、今後検査を自動化する際に正常ROMを異常と報告する。

### [P2] 到達不可能な33バイトをruntimeとして占有している

以下は現行保存で毎回書かれるが、現行hook、pointer table、JMP/JSR operandから参照されない。

| file | CPU | size | 内容 |
|---:|---:|---:|---|
| `0x64B9-0x64D7` | `$E4A9-$E4C7` | 31B | `FINAL_AI_DISPATCH_HELPER` + その内部tail |
| `0x6509-0x650A` | `$E4F9-$E4FA` | 2B | `FINAL_PANEL_TYPE_CLASSIFIER_TAIL` |

現行ROM全体からlittle-endian address operandを検索した結果は次の通りである。

```text
$E4A9 references: none
$E4BC references: 0x64CA only
  -> dead $E4A9 block内部のJMPのみ
$E4F9 references: none
```

新敵AI入口は直接`$E6B7`を呼び、原作AI pointer table `$A33C-$A34A`は現在`$ABF7`へ復元される。そのため`$E4A9`系統は完全に孤立している。`$E4F9`もclassifier本体から呼ばれず、builderの`tail_cpu`引数は使われていない。

したがってplacement reportの「655B全使用、隙間0」は物理的に連続して書かれるという意味では正しいが、「655Bすべてが到達可能な現行処理」という意味では誤りである。現行方針の「実処理が占有しない範囲は空きとして解放」とも一致しない。

### [P3] 救済用pre-compact移行経路と未使用builder

`apply_panel_monster_v2_runtime()`は旧pre-compact Panel runtimeを検出すると、旧領域を`EA`で消して現行配置へ移行する。これは機能バグではないが、正式版前の旧ROM救済を入れない現在のプロジェクト方針と矛盾する。

また`_build_state1_fire_marker()`は現行モジュール内から呼ばれないPython builderである。ROM領域は占有しないが、現行実装の読解時に「生きた別経路」と誤解させる。

## 今回の静的検査で実施したこと

- Python builderの全labelとrelative branch範囲の成立を確認
- 22個のcode blobを6502命令として最後までディスアセンブ
- Panel runtime block 655Bの物理重複・隙間レポートを確認
- `$E0-$F7`分類、A-D table offset、marker indexの全範囲を手作業で展開
- fire loopの2-way/3-way/A-D/normalの全開始indexを追跡
- Bullet entryのstate 0/1、static spread、dynamic speed、fast collisionの全stack経路を追跡
- 原作`$A54C/$A556/$A575/$AE76/$AFBB/$AC39/$866D/$8B05/$A2CC`と実装を照合
- 現行workstateに書かれた各speed blobと現行builderを照合
- Panelのsave reportを現行workstateで実行し、Fire2連鎖後の誤判定を確認
- helper署名不一致をメモリ上で作り、例外前の3バイト変更を確認

## 未実施と、この文書だけで保証しないこと

- 今回はROMを新規生成していない。
- Mesenで24IDを全方向・全速度・全間隔で再実行した動的試験ではない。
- 2x/3xの追加substepと原作物理更新の実フレーム比率は、命令上の2回/3回加算を確認したもので、実機の表示フレームを新たに計測したものではない。
- Spark property/animation dispatch、Saramandor/Gargoyle速度chainの内部証明は、それぞれの個別解析で完了させる。
- 上記の問題4件は記録のみで、コードやROM配置は変更していない。
