# 12/26 Seraphic Radiance `$9D` runtime 6502静的解析

解析日: 2026-07-19
対象: `magatu_skc/core/seraphic_radiance9d_runtime.py`、`new_enemy_runtime.py`、`key_enemy_runtime.py`
一次資料: コメント付き原作ASM、日本版原作ROM、現行mapper66 workstate、正式ROM管理簿、ID配置監査資料

## 結論

Seraphic Radianceは画面内を斜めに往復し、重なった他敵を通常死亡処理を通さず消す無敵敵である。専用本体はsetup 8B、init 44B、phase 12B、AI 205B、animation 28Bの計297Bで、file `0x6C04-0x6D2C`、CPU `$EBF4-$ED1C`に置かれる。

現行workstateの297Bがbuilderと一致することを確認し、原作敵初期化、共通物理、phase切替、全branch、17slot衝突走査、鍵敵runtimeとの接続を静的追跡した。確定問題は4件である。

1. 原作property table範囲外byte `$A3`が書くY速度`$80`を専用initが消しておらず、専用AIより先に共通物理が毎frame座標を動かす。
2. 上端で上向きから下向きへ反転する時、右向きかつphase bit clearなら衝突走査へ分岐せずX移動へ落ち、X軸が2回連続で動く。
3. Seraphic Radianceが鍵持ち敵を直接消すと鍵drop hookを通らず、鍵が出現しないため進行不能になり得る。
4. standard ROM保存用`levels_need_runtime()`がDemon Mirror内の`$9D`を検出しない。

ROM/RAM配置は変更していない。修正も行っていない。

## 4入口

| 機能 | 共通入口 | 専用処理 |
|---|---:|---|
| AI | `$BBE2` | `$EC28`のphase切替から`$EC34`または`$EC6C`へ入る |
| setup | `$BC32` | `$EBF4`でFairy group `$0E`を返す |
| init | `$BC84` | `$EBFC`でstatus/type/初期方向を設定する |
| animation | `$BCD0` | `$ED01`で2frameのtile/attrを直接書く |

共通入口センター側の分類は4入口とも`$9D`を専用本体へ送る。AI入口はphase本体を入口とし、Y/Xのどちらを今回実行するかを毎回切り替える。

## setup `$EBF4`

setupはY=`$0E`、zero-page `$0E=#$0E`として`LDA $D9D3,Y / RTS`を実行する。原作Fairy groupのmetadata pointerを返すため、無重力を想定したsetupとsprite metadataを再利用する。

ただし、このsetupは原作敵初期化`$A2B8`がsetupより前に行うproperty読出を置き換えない。後述のY速度汚染はsetup group `$0E`では防げない。

## 原作property読出とinit `$EBFC`

原作敵初期化は次を計算する。

```text
Y = (type - $18) >> 2
property = $A30E,Y
```

`$9D`ではY=`$21`となり、正式property table外の`$A32F`を読む。日本版原作ROMと現行workstateの`$A32F`は`$A3`である。このbyteは次のAI pointer tableに属し、enemy propertyとして設計された値ではない。

`$A3`のbit判定により、原作前段はmain-slot `[5]`へY速度`$80`を書く。共通init入口はproperty由来値をPHAした後で`$9D`を分類する。専用initは最初のPLAで保存値を捨て、status `$C4`、type `$9D`、behavior 0を原作writer `$9D1C`へ渡すが、`[5]`を0へ戻さない。

`$9D1C`はstatus/type/data/behaviorを書き、velocity fieldを消さない。従ってY速度`$80`が残る。

init後は生成座標を画面中心と比較する。

- X `>= $88`: horizontal bit1を1にして左向き。
- X `< $88`: horizontal bit1を0にして右向き。
- Y `>= $78`: vertical bit0を1にして上向き。
- Y `< $78`: vertical bit0を0にして下向き。
- phase bit2は0で開始する。

方向byteはmain-slot index `$06`を`$B156`へ渡してsub-slot pointerを得た後、sub-slot `[7]`へ保存する。方向値のPHA/PLAは均衡する。

## 共通物理によるY座標汚染

原作entity main loopはactive status `>= $C0`に対し、必ず次の順で呼ぶ。

```text
$8670 JSR $8689  ; 共通物理
$8673 JSR $87E0  ; 敵AI dispatch
$8676 JSR $8789  ; animation
```

Seraphic Radianceのstatus `$C4`でも`$8689`は省略されない。`$8689`はmain-slot `[5]`のY速度を更新し、`velocity * 8 / 256`をY座標へ加える。残存値`$80`は初回に約-4pxを加え、その後も重力更新を伴って専用AIより先に座標を動かす。

専用AIは1回につきXまたはYを直接1px動かす設計である。従って現行実行順では「X/Y交互に1px」という専用設計にならず、property由来の大きな縦移動が毎frame混入する。statusコメントの「no gravity」は共通物理呼出自体を止めるflagではない。

## phase切替 `$EC28`

sub-slot `[7]`のbit2を`EOR #$04`で毎回反転する。

- 反転後bit2=1: `$EC6C`のX処理へbranchする。
- 反転後bit2=0: 直後の`$EC34`へfall-throughし、Y処理を実行する。

初期phaseは0なので最初のAI invocationはX、その次はYとなる。共通物理汚染を除けば、各軸は2 invocationに1回、1px動く。

## Y移動 `$EC34-$EC6B`

- 下向き: Y `< $D0`ならY+1、`>= $D0`なら上向きへ反転。
- 上向き: Y `>= $21`ならY-1、`< $21`なら下向きへ反転。
- 正常経路ではY移動または反転後に`$ECA5`の衝突走査へ入る。

下端、通常の上下移動、上端かつhorizontal bit1=1では、移動/反転結果Aが非0なので`BNE collide`が成立する。

上端でhorizontal bit1=0、vertical bit0=1、phase bit2=0の方向byteはちょうど`$01`である。`turn_down`は`AND #$FE`して0を保存するため、直後に想定されている`BNE collide`が成立しない。命令列はそのまま`move_x`へ落ちる。

このframeは衝突走査を飛ばしてX移動し、次AI invocationもphase反転によりX移動となる。従って上端・右向きだけX軸が2回連続で動く。左向きではAND結果`$02`が非0なので発生しない。`BNE`を無条件branchとして利用した誤りである。

## X移動 `$EC6C-$ECA4`

- 右向き: X `< $E8`ならX+1、`>= $E8`なら左向きへ反転。
- 左向き: X `>= $09`ならX-1、`< $09`なら右向きへ反転。
- X処理後はRTSし、衝突走査を行わない。

右端反転後は方向byteにbit1をORするため結果は必ず非0、左端反転後の`AND #$FD`はbranchを置かず直接RTSへ流れる。X側にはY上端と同じbranch成立条件の誤りはない。

## 17slot衝突走査 `$ECA5-$ED00`

Y処理後だけX=`$10`から0まで17 enemy slotを走査する。

1. pointer table `$B32C/$B341`で対象main-slotを得る。
2. status bit7が0ならskipする。
3. type `$9D`ならskipし、Radiance同士は消さない。
4. `abs(targetX - selfX) < $10`を確認する。
5. `abs(targetY - selfY) < $10`を確認する。
6. 重なれば対象main statusと対応sub statusへ0を書く。
7. Y=`$08`で原作sound `$8E8D`を呼ぶ。

符号付き差分の絶対値化は、負値なら`EOR #$FF / ADC #$01`を行う。差分`$80`も結果`$80`となって`CMP #$10`で除外されるため、8bit wrapによる遠距離誤衝突はない。

sound helperはXを保存し、走査counter Xは維持される。衝突後にpointer `$00/$01`はsub-slotへ変わるが、次loop先頭でmain pointerを再設定するため問題ない。

## 鍵持ち敵を消す進行不能

鍵敵runtimeは選択された初期敵のruntime slotをRAM `$072A`へ記録する。通常のダーナ火球撃破hook `$C267`、落下死亡hook、Red Burn消滅hookでそのslotを照合し、鍵生成処理へ接続する。

Radianceの衝突処理はこれらを一切呼ばず、対象のmain/sub statusへ0を直接書く。対象slotがRAM `$072A`と一致していても照合されない。従って選択可能な鍵持ち敵とRadianceを同じroomへ置き、Radianceが先にその敵へ重なると、敵だけが消えて鍵が出ない。

Radiance自身を鍵持ち禁止にする現行validationでは、この組合せを防げない。これは動的未検証ではあるが、現行命令列上は鍵生成経路が存在しないため、静的に確定する仕様不具合である。

## animation `$ED01`

global frame counter `$21`のbit3で8frameごとに切り替える。

| bit3 | tile1/tile2 | packed attr |
|---:|---:|---:|
| 1 | `$B2/$B2` | `$CF` |
| 0 | `$B0/$B0` | `$CE` |

main-slot `[17]`、`[18]`、`[19]`へ直接書く。Xをpacked attr一時値に使うが、animation hook呼出後のentity loopはslot counterをRAM `$0D`から再取得するため、X破壊は次slot処理へ影響しない。

## ROM/RAM配置

| file | CPU | size | 内容 |
|---:|---:|---:|---|
| `0x6C04-0x6C0B` | `$EBF4-$EBFB` | 8B | setup |
| `0x6C0C-0x6C37` | `$EBFC-$EC27` | 44B | init |
| `0x6C38-0x6C43` | `$EC28-$EC33` | 12B | phase |
| `0x6C44-0x6D10` | `$EC34-$ED00` | 205B | AI/move/collision |
| `0x6D11-0x6D2C` | `$ED01-$ED1C` | 28B | animation |

297Bのcapacityを全て使用し、直後`0x6D2D`からEnhanced Gargoyle runtimeが始まる。Radiance専用RAMは増設せず、自身のsub-slot `[7]`を方向3bitとphase 1bitで使用する。鍵敵runtimeの選択slotは共有RAM `$072A`だが、現行Radianceは参照しない。

## レジスタ・flag・stack

| 処理 | A | X | Y | stack/戻り |
|---|---|---|---|---|
| setup | metadata lowを返す | 維持 | `$0E` | stack操作なし、RTS |
| init | 比較/方向値でclobber | 方向一時値でclobber | main/sub field index | 共通入口PHAを先頭PLA、方向PHA/PLA均衡 |
| phase/Y/X | field値でclobber | 原則維持 | `[7]/[10]` | stack操作なし、RTS |
| collision | 差分/statusでclobber | `$10..0`走査 | pointer field/sound ID | sound JSR後RTS、stack均衡 |
| animation | frame/tile/attrでclobber | attr値でclobber | `$11-$13` | stack操作なし、RTS |

Y/Xの移動加算は境界内の座標に対してだけ行うため8bit overflowを境界判定後に持ち込まない。衝突の絶対値化はSEC/SBC後のCarryを見て正負を分け、負値経路のADCはSBCがborrowでCarry clearのため`~A + 1`となる。

## 成立している点

- `$9D`はAI/setup/init/animationの4入口で専用分類される。
- 生成位置から画面中心へ向かう縦横方向bitの計算は正しい。
- phase bitはX/Yを交互に選ぶ。ただし共通物理汚染と上端分岐バグを除く。
- X/Y境界値そのものは`$08-$E8`、`$20-$D0`に収まる。
- 17slot pointer tableと対応sub-slot tableのindexは一致する。
- Radiance同士はtype比較で衝突消去から除外される。
- collision sound呼出後も走査Xは維持される。
- 現行workstateの297Bとbuilder、予約範囲、正式ROM管理簿は一致する。

## 確定問題

### [P1] Y速度`$80`が残り、共通物理が専用AIを汚染する

原因はtype `$9D`が原作property table外`$A32F=$A3`を読み、原作前段がmain `[5]=#$80`を書いた後、専用initが0へ戻さないことである。entity loopはstatus `$C4`でも共通物理を先に呼ぶため、専用runtimeの意図した交互1px移動にはならない。

局所的には原作writer呼出前、A=0の時点で`LDY #$05 / STA ($00),Y`を加えると4BでY速度を消せる。しかしRadiance領域は満杯で直後に別runtimeがある。修正前に4Bを内部短縮で捻出するか、後続配置を動かすかを算定し、ROM空き、残り空き、hook、`RESERVED_SPANS`、管理簿影響を提示する必要がある。

### [P1] 鍵持ち敵を直接消して鍵が出ない

Radianceは通常死亡、drop、score、鍵dropを呼ばずstatusを0にする。鍵敵slot `$072A`を照合しないため、鍵持ち敵消去時は鍵が出ず進行不能になり得る。

修正方針は少なくとも「選択鍵slotを衝突対象から外す」または「Radiance消去を鍵生成経路へ接続する」の2通りがあり、ゲーム仕様が異なる。現時点では勝手に選ばない。前者でも追加命令が必要で、満杯の297B配置問題を同時に解く必要がある。

### [P2] 上端・右向きだけX移動へfall-throughする

`turn_down`後の方向byteが0の場合だけ`BNE collide`が不成立になる。horizontal bit1=0の時だけ発生し、衝突走査を1回飛ばしてXを2 invocation連続で動かす。

この箇所は`BNE`を、AND結果が必ずbit7 clearであることを利用した`BPL`へ1byte opcode置換すれば同sizeで無条件に衝突走査へ送れる。ROM/RAM使用量は増えず、配置・台帳変更も不要である。ただし実装修正は別承認後に行う。

### [P3] Demon Mirror内の`$9D`をstandard ROM検出が見ない

`levels_need_runtime()`はdirect enemyだけを走査し、Demon Mirrorの`enemy_codes`を見ない。expanded mapper66保存ではruntime常設のため主経路には影響しないが、非expanded ROM拒否用validationとして漏れている。

修正はlevel走査だけでROM/RAM配置、空き、台帳に影響しない。9/26で見つかった共通validation問題としてまとめて直す方が一貫する。

## 未検証点

- Mesenで生成直後の`[5]=$80`と、共通物理後のY座標を動的traceしていない。
- 上端・右向きでXが2回連続するframe traceを採取していない。
- Radianceが選択鍵slotを消した後、鍵が出ずroomが継続する実機確認はしていない。
- status bit7だけが立つ`$80-$BF`の予約/遷移中slotを衝突走査が消す可能性はあるが、生成時の全status遷移を動的確認していないため確定問題には含めない。
- sprite tile/attrとピッカー/キャンバスのpixel単位比較は行っていない。

## 修正時の検証条件

- init完了時のmain `[5]`が0で、毎frameの共通物理がY座標へ余計な移動を加えないこと。
- X/Y phaseが交互で、上下左右の4境界全てで反転frameの軸回数と衝突走査回数が対称であること。
- 鍵敵との組合せ仕様を先に決め、鍵が出ないまま選択slotだけ消える経路を残さないこと。
- Radiance同士を消去しないこと。
- 17slot全てでmain/subの同一indexだけを解放し、sound後もscan Xが壊れないこと。
- 297B領域を拡張または移動する場合、後続Enhanced Gargoyle以降のhook、予約、管理簿、現物ROM byteを一括再検証すること。

