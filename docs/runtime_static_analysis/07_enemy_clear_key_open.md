# 7/26 Enemy Clear Key Open runtime 6502静的解析

解析日: 2026-07-19
対象: `magatu_skc/core/enemy_clear_key_open.py`、`key_enemy_runtime.py`、`stage_ext.py`、`panel_monster_stage_variant.py`、`saver.py`
一次資料: コメント付き原作ASM、日本版原作ROM、現行mapper66 workstate、正式ROM/RAM管理簿

## 結論

Enemy Clear Key Openは、各フレームのメインループ末尾で17個の敵用main-slotを走査し、対象が全て消えた時に原作鍵取得処理と扉オープン演出を起動する常設runtimeである。StageExtの設定がOFFなら原作メインループへ即座に戻る。

現行124Bを命令単位で追跡し、原作`$9EC0-$9F09`、鍵取得`$C663`、action `$34`、座標変換`$918A`、Key Enemyの扉発光位置hookとの接続を照合した。現行workstateの本体とhookはbuilderに完全一致する。

確定問題は2件である。

1. 撃破不能なBlue Burn `$81/$83`を含む面でもモードを有効にでき、runtimeは両IDを永続的に敵として数えるため扉が開かない。
2. 正式版前の救済禁止方針に反し、旧111B版と旧114B版runtimeを正常入力として受け入れて現行版へ置換する経路が残る。

ROM/RAMの新規配置変更は行っていない。修正もまだ行っていない。

## 原作メインループとの接続

原作ゲームプレイのtask 3は`$9EC0`から始まり、1フレーム内で次を実行する。

1. `$A01F` timer更新
2. `$A134` enemy distance/sub-slot counter更新
3. `$9F67` mirror処理
4. `$9F0C` Demon Mirror spawn
5. `$8DB4` yield
6. `$A19C` 17敵slot AI
7. `$C532` item/player collision
8. `$A264` mirror関連処理
9. fireball在庫処理
10. `$9F09: JMP $9EC0`

runtimeは最後の3Bだけを`JMP $C146`へ変える。`$C146`の全終了経路は`JMP $9EC0`なので、JSR/RTSを追加せず次フレームへtail callする。メインループのstack深度は原作と同じである。

| file | CPU | 原作 | 現行hook |
|---:|---:|---|---|
| `0x1F19-0x1F1B` | `$9F09-$9F0B` | `JMP $9EC0` | `JMP $C146` |

`room_flags.py`の旧hook `JMP $9EC0`も入力署名として認めるが、出力は常に`JMP $C146`へ統一される。

## runtime全体の状態遷移

```text
$C146
  |
  +-- $0771 != 0 ? -- DEC -- 0到達時だけ JSR $C7AA
  |
  +-- $0770 bit4 OFF ------------------------> JMP $9EC0
  |
  +-- $0770 bit7 latch済み ------------------> JMP $9EC0
  |
  +-- main-slot 16..0 を走査
        |
        +-- status < $C0 ---------------------> 次slot
        +-- type == $14 ----------------------> 次slot
        +-- type == $9D ----------------------> 次slot
        +-- その他のactive entity ------------> JMP $9EC0
  |
  +-- $0303 bit4 active ----------------------> JMP $9EC0
  |
  +-- $0770 bit7をset
  +-- Dana中心cell+1を$0724へ保存
  +-- JSR $C663（鍵取得処理）
  +-- action $34を開始（扉オープン演出）
  +-- JMP $9EC0
```

bit7 latchは同じroomでの再発火を防ぐ。room load時、PRG1 StageExt helperが`$0770`をbit4/bit5だけから再構築するため、前roomのbit6 cooldownとbit7 latchは持ち越さない。

## Fairy x2遅延処理

runtime先頭13BはEnemy Clearとは独立した共有処理である。Special ItemのFairy x2取得時、`fire2_item_runtime.py`が`$0771=#$20`を設定する。

- 0なら何もしない。
- 1以上なら毎フレーム`DEC $0771`する。
- 0へ到達したフレームだけ`JSR $C7AA`を呼ぶ。
- `$C7AA`は`INC $0454 / RTS`だけで、2体目Fairyのspawn予約を1増やす。

本runtimeはEnemy Clear設定が全53面でOFFでもmapper66保存時に常設されるため、Fairy x2の遅延counterは常に処理される。これはruntime常設方針と一致する。

## modeとlatch

`$0770`の割当は次である。

| bit | 所有機能 | 意味 |
|---:|---|---|
| 4 | Enemy Clear Key Open | 現在roomで有効 |
| 5 | Warp Mirror | 現在roomで有効 |
| 6 | Warp Mirror | 接触cooldown |
| 7 | Enemy Clear Key Open | このroomで発火済み |

mode検査は`LDA $0770 / AND #$10`、latch検査は`LDA $0770 / BPL`である。bit4が0、またはbit7が1なら、敵slotやaction状態を一切触らず原作ループへ戻る。

## 17 main-slot走査

Xを`#$10`から0まで減らし、原作pointer table `$B32C,X/$B341,X`からmain-slot baseをzero-page `$00/$01`へ作る。対象は敵用slot 0～16の17個であり、Dana・専用Dana fireball・表示専用後続slotは含めない。

各slotは次の順で判定する。

1. `main[0] < $C0`ならinactive/setup前として無視する。
2. `main[1] == $14`なら撃破後item remnantとして無視する。
3. `main[1] == $9D`ならSeraphic Radianceとして無視する。
4. それ以外のstatus `$C0-$FF`を1つでも見つけたら即座に原作ループへ戻る。

原作AI主ループもstatus `$C0`未満をskipするため、active閾値は原作と一致する。item remnant `$14`は敵撃破後に同じslotへ置かれる取得物であり、敵全滅を妨げない。撃破不能かつ通常死亡処理を持たないSeraphic Radiance `$9D`も明示除外される。

走査はtypeの敵分類tableを使わない。このためFriendly Fairy `$1C`、敵projectileとしてmain-slotを使う追加ID、その他type `$15-$FF`もactiveなら全滅対象に含まれる。現在の仕様が「敵用17slotが空になること」ならコードどおりだが、「撃破対象だけがいなくなること」とは一致しない可能性がある。特にFairyが残っている間も待つ挙動は動的未確認である。

## action group 4待機

敵slotが全て条件を通過しても、`$0303 & #$10`が非0なら発火しない。`$0303`はcooperative action taskのactive bitmapで、bit4はaction `$40-$4F` groupを示す。

item pickup cleanupが動作中のフレームで扉処理を重ねないためのguardである。item remnant type `$14`自体は無視する一方、取得actionが完了するまでは待つ構造になっている。

## 鍵取得と扉オープン演出

発火時は、最初に`$0770 |= #$80`でlatchする。その後、DanaのY/Xへそれぞれ8を加え、`$04/$05`へ入れて`JSR $918A`を呼ぶ。

`$918A`は次を返す。

```text
X = A = ((Y - $10) & $F0) | ((X - $08) >> 4)
```

runtimeは`TXA / CLC / ADC #1`によりDana中心cell+1を`$0724`へ保存する。0を「未設定」とするための+1符号化である。

次に原作鍵取得入口`$C663`を呼ぶ。現行ROMではKey Enemy hook `$E1A5`を経由するが、`$0723`にdrop keyが無ければ原作処理へ戻る。原作側は次を行う。

- level data byte5の扉cellをgrid `$0304`へ`$07`として書く。
- `$28` bit5の鍵取得flagを立てる。
- 鍵SE `$16`をqueueする。
- task 4を切り替える。

その後、runtimeはA=`$34`で`JSR $8D5F`し、原作action `$34 -> $C33C`を開始する。action `$34`はentityを一時停止し、扉を通行可能状態へ変え、発光描画を行ってmain taskへ戻る。

## `$0724`共有の意味

`$0724`は正式RAM管理簿上、Key Enemy runtimeの`RAM_DROP_ACTIVE`である。Enemy Clear runtimeは同じbyteを「発光開始cell+1」として一時共有する。

action `$34`内の原作`$C3A8`は現行Key Enemy hook `$E185`へ接続される。Y=6かつ`$0724!=0`なら、level dataの通常位置でなく`$0724-1`を発光開始cellとして返し、その場で`$0724=0`へclearする。従ってEnemy Clear発火時の光輪はDana中心から始まり、1回だけ消費される。

Key Enemy dropとEnemy ClearはUIで同時ONを禁止している。両機能が同時に`$0724`を所有する正常経路はない。これは意図された時間分割共有であり、RAM重複検査でもcontractとして登録されている。

## レジスタ・flag・stack

| 経路 | A | X | Y | stack/flag |
|---|---|---|---|---|
| mode OFF / latch済み | clobber | 呼出時値を保持 | 保持 | `JMP $9EC0`、stack追加なし |
| active敵発見 | type値 | 現在slot | 1 | `JMP $9EC0`、stack追加なし |
| 全slot通過 | clobber | scan後`$FF`、後にcell index | 0/1 | local pushなし |
| Fairy2 delay | counterでAをclobber | 保持 | 保持 | `$C7AA`のJSR/RTSが1対1 |
| `$918A` | cell index | cell index | 保持 | JSR/RTSが1対1、Cは途中でclobber |
| `$C663` | clobber | clobber可 | clobber | 原作JSR/RTSが1対1 |
| `$8D5F` | clobber | clobber | clobber | action task stackを構築後RTS |

hookは原作のフレーム末尾にあり、次命令へ戻す必要がないため、A/X/Y/condition flagsを保存する契約はない。全branchはPython assemblerの`finish()`でrelative rangeを検査する。runtime自身にPHA/PLAはなく、2つのJSR経路はいずれもcalleeのRTSと対応する。

## ROM/RAM配置

| file | CPU | size | 内容 |
|---:|---:|---:|---|
| `0x4156-0x41D1` | `$C146-$C1C1` | 124B | Enemy Clear Key Open本体 |
| `0x1F19-0x1F1B` | `$9F09-$9F0B` | 3B | main-loop tail hook |

直後`0x41D2-0x420F`は62Bの正式な空きである。本runtimeの予約は124Bだけで、正式ROM管理簿と`RESERVED_SPANS`が一致する。

RAMは専用新規確保ではなく、次の共有済み領域を使う。

| RAM | 用途 |
|---:|---|
| `$0724` | Key Enemyとの時間分割共有。発光開始cell+1 |
| `$0770` | mode/latch、Warp Mirrorとのbit分割共有 |
| `$0771` | Fairy x2 delay counter |

## 確定した問題

### [P1] `$81/$83`を含む面で永久に扉が開かない

`enemy_slot_rules.py`では、鍵持ち敵にできない撃破不能IDを`$81/$83/$9D`として確定している。Enemy Clear runtimeは`$9D`だけを明示除外し、`$81/$83`は通常active敵として数える。

UIの`_enemy_clear_key_open_can_enable()`は初期配置敵listが空でないことしか検査しない。保存時にも`$81/$83`との組合せを拒否する検証はない。このため、次の構成を正常操作で作れる。

```text
Enemy Clear Key Open = ON
initial enemyに $81 または $83
```

両IDは撃破不能なのでstatus `$C0`以上のslotが残り続け、runtimeは毎フレームactive敵発見経路から`JMP $9EC0`する。latchと鍵処理へ到達せず、鍵を削除した面では進行不能になる。

修正候補は二層ある。

1. 6502側で`$81/$83`も`scan_next`へ送る。
2. UIと保存時検証で、撃破不能IDを含む面へのモード設定を拒否する。

runtime除外だけなら「撃破不能物体は残っていても他敵全滅で開く」仕様になる。UI禁止だけなら不正dataでsoftlockする。どちらを正とするかは仕様判断が必要で、現時点では変更していない。

### [P2] 旧runtime救済経路が残る

`_expect_blank_or()`は現行124Bに加え、次の旧byte列を受け入れる。

| 旧runtime | size | 現行との差 |
|---|---:|---|
| `RUNTIME_WITHOUT_FAIRY2_DELAY` | 111B | 先頭13BのFairy x2遅延処理なし |
| `RUNTIME_BEFORE_GROUP4_WAIT` | 114B | `$0303` bit4待機10Bなし |

旧本体の後ろが`00/EA`なら正常入力として扱い、`apply()`が現行124Bへ上書きする。これは過去途中ROMの自動移行であり、正式版前の救済禁止ルールに反する。現行ROMの成立には不要なので、修正時は旧builder、旧定数、受入れbranchを削除するのが最小である。ROM/RAM配置は変わらない。

## 正常と確認した事項

- `$9F09` tail hookと全終了経路の`JMP $9EC0`
- Enemy Clear設定OFFでもFairy x2 delayだけは処理する常設構造
- StageExt byte0 bit6から`$0770` bit4への変換
- room load時のcooldown/latch clear
- 17 enemy slot pointer tableのindex範囲
- status `$C0`閾値、item remnant `$14`、Radiance `$9D`の分岐
- action group4完了待ち
- latchの一回性
- Dana中心cellの+1符号化
- Key Enemy hook経由の原作鍵処理とaction `$34`
- `$0724`の一回消費とKey Enemyとの時間分割共有
- runtime 124B、hook 3B、正式ROM/RAM管理簿との一致
- 現行workstateのruntime/hookがbuilderと完全一致

## 未実施

- ROMを新規生成していない。
- Mesenで通常全滅、Demon Mirror spawn、item pickup中、Fairy残存、`$81/$83/$9D`混在を動的試験していない。
- `$81/$83`問題と旧runtime救済経路は記録のみで修正していない。
