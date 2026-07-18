# 14/26 Phantom preset A-D runtime 6502静的解析

解析日: 2026-07-19
対象: `magatu_skc/core/phantom_preset_runtime.py`、`new_enemy_runtime.py`、原作Bullet AI `$AFBB`
一次資料: コメント付き原作ASM、日本版原作ROM、現行mapper66保存ROM、正式ROM管理簿、CHANGELOG、ID配置監査資料

## 結論

Phantom presetは敵ID `$A0-$AF`をA-Dの4group、各groupを右・左・上・下の4方向として扱う。各groupは進行速度`$01-$3F`、sine振幅0-200%、開始phase 0-63を持つ。原作Bulletの待機state 0を使った後、壁・block判定を通らない専用state 2で進行軸速度と直交軸waveを適用する。

専用領域は292Bで、file `0x3DAC-0x3ECF`、CPU `$BD9C-$BEBF`に置かれる。加えて原作共通物理call `$8670-$8672`をpre-physics入口へ置換する。builderのdefault 292Bとhookは既存mapper66保存ROM 3本に一致した。

全section、設定生成、4group×4方向、原作property前後、phase、signed scale、pre-physics、共通物理、animation paletteを追跡し、確定バグは2件である。

1. 上方向のY速度へ原作物理が毎frame`+3`するため、上下速度が非対称になる。速度1・2は上指定でも下へ進み、速度3は停止する。
2. group Aだけ原作property後段がsub-slot `[6]`の`$FF` sentinelを方向0-3で上書きし、条件一致時に最初のwave deltaを飛ばす。

技術的負債は、追加敵16IDが原作property table外4Bへ依存すること、standard ROM検出がDemon Mirror内のPhantomを見ないことである。

ROM/RAM配置は変更していない。修正も行っていない。

## IDと設定対応

| ID | group | direction | 進行軸 | wave軸 |
|---:|---:|---|---|---|
| `$A0/$A4/$A8/$AC` | A/B/C/D | 右 | X | Y |
| `$A1/$A5/$A9/$AD` | A/B/C/D | 左 | X | Y |
| `$A2/$A6/$AA/$AE` | A/B/C/D | 上 | Y | X |
| `$A3/$A7/$AB/$AF` | A/B/C/D | 下 | Y | X |

groupは`(type >> 2) & 3`、directionは`type & 3`で得る。4ID単位の連続配置と計算は一致する。

velocity tableは各group 4Bで、現行builderは次を生成する。

```text
[right, left, up, down] = [speed, -speed, -speed, speed]
```

axis tableは`[8, 5]`で、direction bit1が0ならmain `[8]`のX velocity、1ならmain `[5]`のY velocityを選ぶ。

## 4入口と共通物理hook

| 機能 | 入口 | 処理 |
|---|---:|---|
| AI | `$BBE2` | `$BDBD`の3-state dispatchへ送る |
| setup | `$BC32` | `$BD9C`でBullet group `$10`を返す |
| init | `$BC84` | `$BDA5`でstatus/direction/phase sentinelを設定する |
| animation | `$BCD0` | 原作`$8789`後にSPR #2 paletteへ補正する |
| pre-physics | `$8670` | `JSR $BE4A`へhookし、最後は原作`$8689`へtail JMPする |

pre-physics hookは全active entityが通るが、type `$A0-$AF`かつbehavior state 2の場合だけ進行軸速度を書き換える。それ以外は直接原作物理へ戻る。

## setup `$BD9C`

setupはA=`$10`、zero-page `$0E=$10`、Y=`$10`として`LDA $D9D3,Y / RTS`を実行する。原作Bullet `$20-$23`のspeed/animation metadata groupを再利用する。

原作setup後段はtype下位2bitで方向別animation pointerを選ぶ。Phantomの各4ID groupも下位2bitを同じ方向順にしているため、右左上下の見た目が一致する。

Bullet groupのstate 0 behavior `$00-$03`はY/X velocityとも0である。従って原作property前段が生成時に残したvelocityは、最初の共通物理より前のsetupで0へ上書きされる。

## 原作property表外読出

原作敵初期化`$A2B8`のindexは`(type-$18)>>2`である。Phantom 4groupは正式table外の次のbyteをpropertyとして読む。

| group | ID | 読出先 | byte | 原作後段のsub `[6]/[7]`書込 |
|---:|---:|---:|---:|---|
| A | `$A0-$A3` | `$A330` | `$9D` | あり |
| B | `$A4-$A7` | `$A331` | `$A4` | なし |
| C | `$A8-$AB` | `$A332` | `$00` | なし |
| D | `$AC-$AF` | `$A333` | `$A7` | なし |

これらはAI pointer table内のbyteで、enemy propertyではない。status、生成時behavior、Y velocityへの前段副作用は専用initと最初のBullet setupで上書きされる。

ただしpropertyを3bit右shiftして積んだ値を、専用init後の原作`$A2F5`が再びPLA/LSRする。group Aの`$9D`だけ最終Carryがsetになり、type下位2bitをsub `[6]`、その変換値をsub `[7]`へ書く。この書込は専用initの後に行われるため、phase sentinelを壊す。

## init `$BDA5`

専用initは次を行う。

1. PLAで共通init入口が保存したproperty由来behavior候補を捨てる。
2. zero-page `$04=#$C0`にする。
3. `$05`のtype下位2bitをAへ取り、原作writer `$9D1C`をJSRする。
4. main-slot index `$06`を`$B156`へ渡してsub-slot pointerを得る。
5. sub-slot `[6]=#$FF`として最初のphase適用を強制する。
6. RTSする。

writerはtype `$A0-$AF`を保持し、main `[0]=$C0`、`[2]=$FF`、`[3]=direction 0-3`を書く。state 0から開始する。

common initのPHAは先頭PLAで均衡する。専用writerはJSR/RTS、sub pointer helperもJSR/RTSで均衡する。その後、原作側が自分のproperty stack値をPLAする。

## state dispatch `$BDBD`

`JSR $B201`でbehaviorを2bit右shiftし、`JSR $8EA9`で3-entry tableへdispatchする。

| state | handler | 役割 |
|---:|---:|---|
| 0 | `$AFC7` | 原作Bullet待機。sub `[1] >= $0A`でbehavior bit3をsetしstate 2へ移る |
| 1 | `$B00A` | 原作Bullet消滅counter。通常Phantom遷移では未到達 |
| 2 | `$BDC9` | 専用wave処理。壁・block処理を呼ばない |

専用state 2は原作Bullet state 2 `$AFD8`を置き換える。原作の周囲block scan、block破壊、自身のstate 1移行/despawnを意図的に呼ばないため、Phantomは壁を貫通する。

## pre-physics `$BE4A`

pre-physicsはtypeとstateを検査し、Phantom state 2なら`$BE32`をJSRする。

`$BE32`は次を行う。

1. `type & $0F`で16B velocity tableを読む。
2. direction bit1でaxis table `[8,5]`を選ぶ。
3. velocity byteをmain `[8]`または`[5]`へ書く。
4. RTSする。

その後`JMP $8689`で原作共通物理へ入る。JMP先のRTSが元のentity loop `$8673`へ戻るため、hookによるstack増分は0である。

進行軸velocityは毎frame metadataや衝突処理より後ではなく、物理直前に再設定される。壁衝突で0にされても次frameに設定値へ戻るため、壁抜け仕様になる。

## 上方向速度の重力バグ

原作共通物理`$8689`はY velocityのbit7が1なら、座標適用前にvelocityへ`+3`する。status `$C0`はこの処理を止めない。

上方向はtableに`-speed`を書き、直後に同じframeの原作物理へ渡す。従って実効Y velocityは次になる。

```text
requested up = -speed
actual up    = -speed + 3
down         = +speed
```

| UI speed | 上方向の実効値 | 結果 |
|---:|---:|---|
| 1 | `+2` | 下へ進む |
| 2 | `+1` | 下へ進む |
| 3 | `0` | 停止 |
| 4 | `-1` | 上へ進むが設定より3遅い |
| 63 | `-60` | 下方向`+63`と非対称 |

水平左のX velocityにはY重力処理がないため、右左は対称である。問題は上方向だけである。

同size修正候補は、上方向table byteだけ`-(speed+3)`として焼き込み、原作物理後に`-speed`へなるよう補償することである。speed最大63でもrawは`$BE`で表現可能であり、table size、runtime size、ROM/RAM配置は変わらない。実装修正は別承認後に行う。

## state 2 wave `$BDC9`

処理はouter Xを`TXA/PHA`で保存してからgroupをXへ展開する。

1. amplitude tableを読む。0ならwave計算をせずrestoreする。
2. `$043C >> 1`へgroup phase offsetを加え、`& $3F`でphase 0-63を作る。
3. sub `[6]`の前回phaseと同じならrestoreする。
4. 新phaseをsub `[6]`へ保存する。
5. 64B sine delta tableを読む。
6. `$BE0C`で振幅units 1-8を掛け、4で割る。
7. 横進行ならmain Y `[7]`、縦進行ならmain X `[10]`へsigned deltaを直接加える。
8. 保存したouter XをPLA/TAXし、RTSする。

phaseはglobal frame low byteを2frame単位で使うため、周期は128frameである。複数Phantomは同じgroup/phase offsetなら同期する。生成時刻基準ではない。

## signed scale `$BE0C`

入力deltaは`-5..+5`、amplitude unitsは`percent/25`の0-8である。

- 負値はabsolute値へ変換し、Y=1をsign flagにする。
- absolute deltaをunits回加算する。最大`5*8=40`で8bit overflowしない。
- LSR 2回で4除算する。
- sign flagが1なら結果を再び2の補数負値へ戻す。

0-200%の全9設定でscale後64stepの合計は0になる。従って1周期ごとの累積driftは静的にはない。正負をabsolute値で同じfloorへ通すため、roundingも符号対称である。

## group Aの初回phase欠落

専用initはsub `[6]=$FF`を入れるが、group Aではその後の原作property後段がsub `[6]=direction 0-3`へ上書きする。

state 2へ初めて入った時のglobal phaseとgroup phase offsetの合計がそのdirection値と一致すると、`CMP sub[6] / BEQ restore`が成立する。最初のdeltaを適用せず、次phaseから開始する。

group B-Dはsentinel `$FF`が残るため必ず最初のdeltaを適用する。group Aだけ、生成frame・phase offset・方向の組合せで開始波形が1stepずれる。1周期合計0でも、飛ばした1step分だけ中心線offsetが残る場合がある。

修正には原作`$A2F5`後段の書込を抑えるか、後段より後でsentinelを設定する必要がある。現行292Bは直後まで使用中なので、必要byteと利用範囲を算定してから修正する。現時点ではROM/RAM空きや台帳を変更していない。

## animation palette

共通animation入口はtype `$A0-$AF`で次を行う。

1. `JSR $8789`で原作Bullet animationを更新する。
2. main attr `[19]`を読む。
3. `AND #$33 / ORA #$48`で両spriteのflip bitを残し、SPR #2 paletteへする。
4. 書き戻してRTSする。

mask `$33`はpacked attrのsprite1 H/V flip bits4-5とsprite2 H/V flip bits0-1を残す。palette bitだけを上書きするため、方向animationを壊さない。

## ROM/RAM配置

| file | CPU | size | 内容 |
|---:|---:|---:|---|
| `0x0680-0x0682` | `$8670-$8672` | 3B | pre-physics hook |
| `0x3DAC-0x3DB4` | `$BD9C-$BDA4` | 9B | setup |
| `0x3DB5-0x3DCC` | `$BDA5-$BDBC` | 24B | init |
| `0x3DCD-0x3DD8` | `$BDBD-$BDC8` | 12B | state dispatch |
| `0x3DD9-0x3E1B` | `$BDC9-$BE0B` | 67B | state 2 wave |
| `0x3E1C-0x3E41` | `$BE0C-$BE31` | 38B | signed scale |
| `0x3E42-0x3E59` | `$BE32-$BE49` | 24B | apply speed |
| `0x3E5A-0x3E75` | `$BE4A-$BE65` | 28B | pre-physics entry |
| `0x3E76-0x3E85` | `$BE66-$BE75` | 16B | velocity table |
| `0x3E86-0x3E87` | `$BE76-$BE77` | 2B | axis table |
| `0x3E88-0x3E8B` | `$BE78-$BE7B` | 4B | amplitude table |
| `0x3E8C-0x3E8F` | `$BE7C-$BE7F` | 4B | phase table |
| `0x3E90-0x3ECF` | `$BE80-$BEBF` | 64B | sine delta table |

runtime直前`0x3D99-0x3DAB`は現行runtime予約なし19B、直後`0x3ED0`からSpark Ball 24ID runtimeが始まる。本体直後の空きは0Bである。

新規global RAMは使わない。各Phantom自身のsub-slot `[6]` 1Bをlast phaseに使い、既存global frame counter `$043C`をphase sourceにする。zero-page `$0E/$0F`はstate 2実行中だけ振幅unitsとabsolute deltaに使用する。

## レジスタ・flag・stack

| 処理 | A | X | Y | stack/戻り |
|---|---|---|---|---|
| setup | metadata lowを返す | 維持 | `$10` | stack操作なし、RTS |
| init | type/directionでclobber | helperでclobber | `[6]` | common PHA/PLA、2 JSR均衡 |
| state dispatch | state/handlerでclobber | 原作dispatcherでclobber | behavior field | dispatcherの間接return規約 |
| state 2 | delta/座標でclobber | group/phase後にouter X復元 | axis field | outer X PHA/PLA、delta PHA/PLA、全branch均衡 |
| scale | magnitude/resultでclobber | units counterでclobber | sign flag 0/1 | stack操作なし、RTS |
| apply speed | velocityでclobber | 維持 | direction/axis | velocity PHA/PLA均衡 |
| pre-physics | type/stateでclobber | stock physicsでclobber | field index | JSR後tail JMP、最終RTSは`$8689` |

state 2のamplitude 0、同phase、horizontal、verticalの全経路でouter XのPLAは1回である。deltaをPHAするのは新phaseかつamplitude非0だけで、その経路はaxis書込前に必ずPLAする。

## 成立している点

- `$A0-$AF`のgroup/direction bit配置と4入口分類が一致する。
- state 0の10frame待機後に専用state 2へ入る。
- pre-physicsはPhantom state 2以外のentity velocityを変更しない。
- 右左と下方向の進行速度table、axis選択は成立する。
- 横進行はY、縦進行はXへwave deltaを加える。
- scaleは0-200%の全設定で符号対称かつ1周期合計0である。
- same phaseの二重加算をsub `[6]`で防ぐ。ただしgroup A初回を除く。
- amplitude 0ではwave座標もphase記録も変更しない。
- state 2、scale、apply speed、pre-physicsのstackは全branchで均衡する。
- default 292Bとhook、設定読出は既存mapper66保存ROM 3本に一致する。

## 確定問題

### [P1] 上方向速度へ重力`+3`が混入する

pre-physicsが上方向Y velocityを`-speed`へしても、直後の原作物理が負のY velocityへ`+3`する。UIの最小値1-3では方向自体が壊れ、全設定で上下が非対称である。

上方向tableを`-(speed+3)`へ補償する修正は16B tableの値だけが変わる。同sizeなのでROM/RAM使用量、予約範囲、残り空き、正式管理簿に変更はない。既存ROM救済は行わず、これから新しく作るROMの生成tableだけを直す候補である。

### [P2] group Aだけ初回phase sentinelが壊れる

原作property後段が専用init後にsub `[6]`を0-3へ書き、phase一致時の初回deltaを飛ばす。group B-Dには発生せず、同じ設定でもAだけ開始位置が条件付きでずれる。

原作postlude stackまたはsentinel表現を変える必要がある。現時点で追加byte数は確定していない。PRG0を増やす場合は直前19B空きの現物確認、runtime入口移動、4入口/hook、`RESERVED_SPANS`、管理簿更新が必要になるため、修正前に配置案を提示する。

## 技術的負債・問題候補

### [P2] property table外4Bへの依存

4groupはAI pointer tableの`$9D/$A4/$00/$A7`をpropertyとして読む。現行副作用は追跡できるが、原作tableまたはhook順序が変わると別のstatus、velocity、sub書込が生じ得る。

property入口で追加敵を正式分類する修正はSpark/Panel/他追加敵と共有するため、Phantom局所修正として扱わない。

### [P3] Demon Mirror内のPhantomをstandard ROM検出が見ない

`new_enemy_runtime.levels_need_runtime()`はdirect enemyの`$A0-$AF`だけを走査し、Demon Mirrorの`enemy_codes`を見ない。expanded mapper66保存ではruntime常設のため主経路には影響しないが、非expanded ROM拒否用validationとして漏れている。

修正はlevel走査だけでROM/RAM配置、空き、台帳に影響しない。9/26の共通validation修正へまとめる候補である。

## 仕様として成立しているが注意が必要な点

- 専用state 2は壁・block衝突と原作despawnを意図的に通さない。画面外へ進んでもslotが自動解放される保証はこのruntime内にない。
- phaseは生成時刻でなくglobal frame基準なので、同groupの複数個体は同期する。
- wave deltaは座標へ直接加えるため、振幅200%では1phase最大10px動く。block collisionは行わない。
- 鍵持ち敵に指定した場合、画面外へ進む前に倒せなければ鍵へ到達できなくなる可能性がある。現行仕様は`$A0-$AF`を禁止していないため、実機で4方向の撃破・鍵出現を最終確認する必要がある。

## 未検証点

- Mesenで速度1-4の上/下Y velocityと座標差分を動的traceしていない。
- group Aで初回phase一致/不一致の両方を動的traceしていない。
- 4group×4方向×振幅9値×phase offsetの全組合せは実機未検査である。
- 画面外wrap後のslot存続、再出現、鍵持ち時の進行可否は未確認である。
- ダーナ火球撃破、通常drop、鍵dropの高ID `$A0-$AF`全方向は未確認である。
- Demon Mirror生成での4入口とphase初期化は未確認である。

## 修正時の検証条件

- 上下で同じspeed絶対値を設定した時、物理後のY velocity絶対値と移動量が一致すること。
- speed 1、2、3の上方向がそれぞれ上へ進むこと。
- A-D全groupで最初のstate 2 invocationが必ず現在phaseのdeltaを1回だけ適用すること。
- 同phaseの2frame目はdeltaを重複適用しないこと。
- 64phase後のwave軸累積差分が0へ戻ること。
- pre-physics OFF経路でDana、原作Bullet、Panel Monster、他追加敵のvelocityが変わらないこと。
- 4方向の壁貫通、画面外、火球撃破、鍵dropを実機確認すること。

