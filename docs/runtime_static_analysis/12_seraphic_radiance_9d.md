# 12/26 Seraphic Radiance `$9D` runtime 6502静的解析

解析日: 2026-07-19
対象: `magatu_skc/core/seraphic_radiance9d_runtime.py`、`new_enemy_runtime.py`、`key_enemy_runtime.py`
一次資料: コメント付き原作ASM、日本版原作ROM、現行mapper66 workstate、正式ROM管理簿、ID配置監査資料

## 結論

Seraphic Radianceは画面内を斜めに往復し、重なった他敵を通常死亡処理を通さず消す無敵敵である。専用本体はinit 44B、phase 12B、AI 212B、animation 28Bの計296Bで、file `0x6C04-0x6D2B`、CPU `$EBF4-$ED1B`に置かれる。setupはDark Fairyと同じ共有Fairy group helper `$E000`を使う。

修正前workstateの297Bが修正前builderと一致することを確認し、原作敵初期化、共通物理、phase切替、全branch、17slot衝突走査、鍵敵runtimeとの接続を静的追跡した。確定問題4件は修正した。

1. 専用initでmain `[5]`を0にし、原作property table範囲外byte `$A3`が書くY速度`$80`を消す。
2. 上端反転後はAND結果のN clearを使う`BPL`で必ず衝突走査へ入り、X移動へfall-throughしない。
3. 衝突走査で鍵持ち敵slot RAM `$072A`を除外し、通常の撃破・鍵drop経路を維持する。
4. 10/26の共通validation修正でDemon Mirror内の`$9D`も検出する。

重複setup 8Bを共有化し、上端branch 2Bと鍵slot除外5Bを追加したため、本体は差引1B縮小した。PRG0明示空きは1036B、RAM追加と後続runtime移動はない。正式ROM管理簿は同じ修正で更新した。

## 4入口

| 機能 | 共通入口 | 専用処理 |
|---|---:|---|
| AI | `$BBE2` | `$EC20`のphase切替から`$EC2C`または`$EC66`へ入る |
| setup | `$BC32` | 共有helper `$E000`でFairy group `$0E`を返す |
| init | `$BC84` | `$EBF4`でstatus/Y速度/初期方向を設定する |
| animation | `$BCD0` | `$ED00`で2frameのtile/attrを直接書く |

共通入口センター側の分類は4入口とも`$9D`を専用本体へ送る。AI入口はphase本体を入口とし、Y/Xのどちらを今回実行するかを毎回切り替える。

## 共有setup `$E000`

Dark Fairy runtime先頭の共有setupはzero-page `$0E=#$0E`、Y=`$0E`として`LDA $D9D3,Y / RTS`を実行する。原作Fairy groupのmetadata pointerを返すため、無重力を想定したsetupとsprite metadataを再利用する。

ただし、このsetupは原作敵初期化`$A2B8`がsetupより前に行うproperty読出を置き換えない。後述のY速度汚染はsetup group `$0E`では防げない。

## 原作property読出とinit `$EBF4`

原作敵初期化は次を計算する。

```text
Y = (type - $18) >> 2
property = $A30E,Y
```

`$9D`ではY=`$21`となり、正式property table外の`$A32F`を読む。日本版原作ROMと現行workstateの`$A32F`は`$A3`である。このbyteは次のAI pointer tableに属し、enemy propertyとして設計された値ではない。

`$A3`のbit判定により、原作前段はmain-slot `[5]`へY速度`$80`を書く。共通init入口はproperty由来値をPHAした後で`$9D`を分類する。専用initは最初のPLAで保存値を捨て、status `$C4`とbehavior 0を準備し、A=0のままmain `[5]`へ書いてY速度を消してから原作writer `$9D1C`を呼ぶ。type `$05=$9D`は原作前段が既に設定しているため、冗長な再設定を削除した。

`$9D1C`後はmain `[0]=$C4`、`[1]=$9D`、`[3]=$00`、`[5]=$00`となる。

init後は生成座標を画面中心と比較する。

- X `>= $88`: horizontal bit1を1にして左向き。
- X `< $88`: horizontal bit1を0にして右向き。
- Y `>= $78`: vertical bit0を1にして上向き。
- Y `< $78`: vertical bit0を0にして下向き。
- phase bit2は0で開始する。

方向byteはmain-slot index `$06`を`$B156`へ渡してsub-slot pointerを得た後、sub-slot `[7]`へ保存する。方向値のPHA/PLAは均衡する。

## 共通物理とY速度clear

原作entity main loopはactive status `>= $C0`に対し、必ず次の順で呼ぶ。

```text
$8670 JSR $8689  ; 共通物理
$8673 JSR $87E0  ; 敵AI dispatch
$8676 JSR $8789  ; animation
```

Seraphic Radianceのstatus `$C4`でも`$8689`は省略されない。`$8689`はmain-slot `[5]`を参照するため、専用initで0へ戻してから原作writerへ入る。

これによりproperty由来の約-4px初動と毎frameの余計な縦移動を除き、専用AIの「X/Y交互に1px」だけを座標変化として残す。

## phase切替 `$EC20`

sub-slot `[7]`のbit2を`EOR #$04`で毎回反転する。

- 反転後bit2=1: `$EC66`のX処理へbranchする。
- 反転後bit2=0: 直後の`$EC2C`へfall-throughし、Y処理を実行する。

初期phaseは0なので最初のAI invocationはX、その次はYとなる。共通物理汚染を除けば、各軸は2 invocationに1回、1px動く。

## Y移動 `$EC2C-$EC65`

- 下向き: Y `< $D0`ならY+1、`>= $D0`なら上向きへ反転。
- 上向き: Y `>= $21`ならY-1、`< $21`なら下向きへ反転。
- Y移動または反転後に`$EC9F`の衝突走査へ入る。

下端反転と通常の上下移動には`BNE collide`があるが、上端の`turn_down`後だけbranchが完全に欠けていた。

修正前builderには`turn_down`から`collide`へのbranch自体がなく、`AND #$FE / STA`の直後に`move_x`へfall-throughしていた。解析資料にあった「`BNE`が値0で不成立」という説明は現行builderと一致していなかったため訂正する。

修正後は`AND #$FE`が必ずN clearになることを利用し、同サイズbranch命令の`BPL collide`を追加した。方向byteが0でも2でも必ず衝突走査へ入り、上端反転frameにX移動を混ぜない。

## X移動 `$EC66-$EC9E`

- 右向き: X `< $E8`ならX+1、`>= $E8`なら左向きへ反転。
- 左向き: X `>= $09`ならX-1、`< $09`なら右向きへ反転。
- X処理後はRTSし、衝突走査を行わない。

右端反転後は方向byteにbit1をORするため結果は必ず非0、左端反転後の`AND #$FD`はbranchを置かず直接RTSへ流れる。X側にはY上端と同じbranch成立条件の誤りはない。

## 17slot衝突走査 `$EC9F-$ECFF`

Y処理後だけX=`$10`から0まで17 enemy slotを走査する。

1. scan Xが鍵持ち敵slot RAM `$072A`と一致すればskipする。
2. pointer table `$B32C/$B341`で対象main-slotを得る。
3. status bit7が0ならskipする。
4. type `$9D`ならskipし、Radiance同士は消さない。
5. `abs(targetX - selfX) < $10`を確認する。
6. `abs(targetY - selfY) < $10`を確認する。
7. 重なれば対象main statusと対応sub statusへ0を書く。
8. Y=`$08`で原作sound `$8E8D`を呼ぶ。

符号付き差分の絶対値化は、負値なら`EOR #$FF / ADC #$01`を行う。差分`$80`も結果`$80`となって`CMP #$10`で除外されるため、8bit wrapによる遠距離誤衝突はない。

sound helperはXを保存し、走査counter Xは維持される。衝突後にpointer `$00/$01`はsub-slotへ変わるが、次loop先頭でmain pointerを再設定するため問題ない。

## 鍵持ち敵slotの除外

鍵敵runtimeは選択された初期敵のruntime slotをRAM `$072A`へ記録する。通常のダーナ火球撃破hook `$C267`、落下死亡hook、Red Burn消滅hookでそのslotを照合し、鍵生成処理へ接続する。

Radianceの衝突処理は通常死亡経路を呼ばず、対象のmain/sub statusへ0を直接書く。このためscan XをRAM `$072A`と比較し、選択鍵slotなら座標・typeを読む前に`next`へ送る。

鍵敵はRadianceとの接触では消えず、通常のダーナ火球、落下死亡、Red Burn消滅等の既存経路で倒された時に鍵をdropする。未選択sentinel `$FF`はscan X `$10..0`と一致しない。

## animation `$ED00`

global frame counter `$21`のbit3で8frameごとに切り替える。

| bit3 | tile1/tile2 | packed attr |
|---:|---:|---:|
| 1 | `$B2/$B2` | `$CF` |
| 0 | `$B0/$B0` | `$CE` |

main-slot `[17]`、`[18]`、`[19]`へ直接書く。Xをpacked attr一時値に使うが、animation hook呼出後のentity loopはslot counterをRAM `$0D`から再取得するため、X破壊は次slot処理へ影響しない。

## ROM/RAM配置

| file | CPU | size | 内容 |
|---:|---:|---:|---|
| `0x6010-0x6018` | `$E000-$E008` | 9B | Dark Fairyと共有するFairy group setup |
| `0x6C04-0x6C2F` | `$EBF4-$EC1F` | 44B | init/Y速度clear/初期方向 |
| `0x6C30-0x6C3B` | `$EC20-$EC2B` | 12B | phase |
| `0x6C3C-0x6D0F` | `$EC2C-$ECFF` | 212B | AI/move/collision/鍵slot除外 |
| `0x6D10-0x6D2B` | `$ED00-$ED1B` | 28B | animation |
| `0x6D2C` | `$ED1C` | 1B | 現行runtime予約なし |

297Bのcapacityに対して296Bを使用し、直後1Bを空きとして解放した。`0x6D2D`から始まるEnhanced Gargoyle runtimeは移動していない。Radiance専用RAMは増設せず、自身のsub-slot `[7]`を方向3bitとphase 1bitで使用する。鍵敵runtimeの既存選択slot RAM `$072A`を読取り専用で参照する。

## レジスタ・flag・stack

| 処理 | A | X | Y | stack/戻り |
|---|---|---|---|---|
| 共有setup | metadata lowを返す | 維持 | `$0E` | stack操作なし、RTS |
| init | 比較/方向値でclobber | 方向一時値でclobber | main/sub field index | 共通入口PHAを先頭PLA、方向PHA/PLA均衡 |
| phase/Y/X | field値でclobber | 原則維持 | `[7]/[10]` | stack操作なし、RTS |
| collision | 差分/statusでclobber | `$10..0`走査 | pointer field/sound ID | sound JSR後RTS、stack均衡 |
| animation | frame/tile/attrでclobber | attr値でclobber | `$11-$13` | stack操作なし、RTS |

Y/Xの移動加算は境界内の座標に対してだけ行うため8bit overflowを境界判定後に持ち込まない。衝突の絶対値化はSEC/SBC後のCarryを見て正負を分け、負値経路のADCはSBCがborrowでCarry clearのため`~A + 1`となる。

## 成立している点

- `$9D`はAI/setup/init/animationの4入口で専用分類される。
- 生成位置から画面中心へ向かう縦横方向bitの計算は正しい。
- phase bitはX/Yを交互に選び、上端反転frameも衝突走査へ戻る。
- X/Y境界値そのものは`$08-$E8`、`$20-$D0`に収まる。
- 17slot pointer tableと対応sub-slot tableのindexは一致する。
- Radiance同士はtype比較で衝突消去から除外される。
- collision sound呼出後も走査Xは維持される。
- 選択鍵slotは衝突消去から除外され、既存の鍵drop経路を維持する。
- 現行builderの296B、予約範囲、正式ROM管理簿は一致する。

## 修正した確定問題

### [P1] Y速度`$80`が残り、共通物理が専用AIを汚染する

修正前の原因はtype `$9D`が原作property table外`$A32F=$A3`を読み、原作前段がmain `[5]=#$80`を書いた後、専用initが0へ戻さなかったことである。entity loopはstatus `$C4`でも共通物理を先に呼ぶため、専用runtimeの意図した交互1px移動になっていなかった。

原作writer呼出前、A=0の時点で`LDY #$05 / STA ($00),Y`を追加した。同時に原作前段ですでに設定済みのtype `$05=$9D`を再設定する4Bを削除したため、initは44Bのままである。

### [P1] 鍵持ち敵を直接消して鍵が出ない

修正前のRadianceは通常死亡、drop、score、鍵dropを呼ばずstatusを0にし、鍵敵slot `$072A`も照合しなかったため、鍵持ち敵消去時は鍵が出ず進行不能になり得た。

選択鍵slotを衝突対象から外した。鍵をRadiance接触で強制dropする新経路は作らず、既存の通常撃破・落下死亡・Red Burn消滅のdrop契約を維持する。

### [P2] 上端反転後にX移動へfall-throughする

`turn_down`後にbranchが存在しないため、左右どちらの向きでも衝突走査を1回飛ばしてX移動へ入り、次のAI invocationもphase切替によりX移動となっていた。

修正前builderには資料で想定していた`BNE`が存在せず、branch自体が欠けていた。AND結果が必ずbit7 clearであることを利用した`BPL collide` 2Bを追加し、方向byteが0でも2でも衝突走査へ送る。

### [P3] Demon Mirror内の`$9D`をstandard ROM検出が見ない

10/26で共有validationがDemon Mirrorの`enemy_codes`も走査するようになり、`$9D`を含む全追加敵familyを検出する。stock IDだけのミラーはFalseを維持する。

## 未検証点

- Mesenで修正後initの`[5]=$00`と、共通物理後のY座標を動的traceしていない。
- 上端反転後に衝突走査へ入り、次frameまでX移動しないことを動的traceしていない。
- Radianceが選択鍵slotと重なった時に対象が残り、通常撃破後に鍵が出る実機確認はしていない。
- status bit7だけが立つ`$80-$BF`の予約/遷移中slotを衝突走査が消す可能性はあるが、生成時の全status遷移を動的確認していないため確定問題には含めない。
- sprite tile/attrとピッカー/キャンバスのpixel単位比較は行っていない。

## 修正時の検証条件

- init完了時のmain `[5]`が0で、毎frameの共通物理がY座標へ余計な移動を加えないこと。
- X/Y phaseが交互で、上下左右の4境界全てで反転frameの軸回数と衝突走査回数が対称であること。
- 鍵敵との組合せ仕様を先に決め、鍵が出ないまま選択slotだけ消える経路を残さないこと。
- Radiance同士を消去しないこと。
- 17slot全てでmain/subの同一indexだけを解放し、sound後もscan Xが壊れないこと。
- 296B本体、直後1B空き、後続Enhanced Gargoyleの非移動を予約と管理簿で照合すること。
