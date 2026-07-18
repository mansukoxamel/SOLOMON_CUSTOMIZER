# 11/26 Dark Fairy `$9C` runtime 6502静的解析

解析日: 2026-07-19
対象: `magatu_skc/core/fairy9c_runtime.py`、`new_enemy_runtime.py`、原作Fairy AI `$A700`
一次資料: コメント付き原作ASM、日本版原作ROM、現行mapper66 workstate、正式ROM管理簿、ID配置監査資料

## 結論

Dark FairyはFairyを取る動作を原作へ実行させ、取得を検出した60frame後にDanaの死亡action `$31`を起動する罠敵である。専用本体はsetup 9B、init 21B、AI 56Bの計86Bで、file `0x6010-0x6065`、CPU `$E000-$E055`に置かれる。animation palette補正は新敵ID共通入口センター側にある。

現行workstateの86Bがbuilderと一致することを確認した。原作Fairy取得経路、`$0453`の10個目wrap、typeの一時変更、毒counter、stack、despawnを静的追跡し、6502本体の確定ロジックバグは見つからなかった。

技術的負債・validation候補は2件である。

1. 原作property table範囲外の`$A3`を一度読み、その副作用を専用initで打ち消すことに依存する。
2. standard ROM保存用`levels_need_runtime()`がDemon Mirror内の`$9C`を検出しない。

ROM/RAM配置は変更していない。修正も行っていない。

## ID `$9C`固定の理由

Dark Fairyのモデルは原作Fairy `$1C`である。`$9C`は`$1C`と下位7bitが同じであり、原作animationとFairy系分岐が参照する下位bitを維持する。

setup group `$0E`、AI中の一時type `$1C`、animation palette補正を組み合わせて成立しているため、IDだけを別値へ移してはいけない。移動する場合は原作type下位bit、setup、init property、AI取得、animation、死亡処理を全て再検証する必要がある。

## 4入口

| 機能 | 共通入口 | 専用処理 |
|---|---:|---|
| AI | `$BBE2` | `$E01E`へJMP |
| setup | `$BC32` | `$E000`でFairy group `$0E`を返す |
| init | `$BC84` | `$E009`でstatus/type/behaviorを再構築 |
| animation | `$BCD0` | 原作`$8789`後にDark Fairy属性へ補正 |

## setup `$E000`

setup本体は`$0E=#$0E`、Y=`$0E`とし、`LDA $D9D3,Y / RTS`を実行する。これにより原作Fairyのsetup/animation metadata pointerを返す。

共通setup入口からJMPではなくJSR相当のreturn先を保ったまま専用本体へJMPするため、専用RTSは原作`$8ACB`の呼出元へ直接戻る。stack追加はない。

## 原作property読出とinit `$E009`

原作敵初期化`$A2B8`はtypeから次を計算する。

```text
Y = (type - $18) >> 2
property = $A30E,Y
```

`$9C`ではY=`$21`となり、正式property table外の`$A32F`を読む。日本版原作ROMと現行workstateの`$A32F`は`$A3`である。これは直後のAI pointer tableに属するbyteで、enemy propertyとして設計された値ではない。

`$A3`の原作前段での作用は次である。

- 一時statusは`$C2`。
- property判定によりmain-slot Y velocity `[5]`へ`$80`を書く。
- init writerへ渡すbehavior候補Xへ`$18`をORする。
- property由来stack値は`$0A`となり、init後の追加sub-slot方向設定には入らない。

共通init入口は原作のproperty由来AをPHAしてからtype `$9C`を分類する。Dark Fairy initは最初のPLAでその保存値を捨て、次を行う。

1. main-slot `[5]`を0にし、範囲外propertyが書いたY velocityを消す。
2. zero-page `$04=#$E2`を設定する。
3. zero-page `$05=#$9C`を設定する。
4. A=`$00`として原作`$9D1C`を呼ぶ。

原作writerによりmain-slotは少なくとも`[0]=$E2`、`[1]=$9C`、`[2]=$FF`、`[3]=$00`となる。`$E2`はactive/AI対象で、Fairy相当の接触特性を持つ。

専用initの後、原作`$A2F5`は自分がproperty処理で積んだ別の`$0A`をPLAする。LSR結果はCarry clearなので、sub-slot `[6]/[7]`への方向初期値書込みを行わない。従って現在の原作byte `$A3`では毒counter `[7]`を上書きしない。

## 通常AIとtype一時変更

毒counterが0なら次を行う。

1. `$0453`のFairy取得数をPHAで保存する。
2. main-slot type `[1]`を`$9C`から`$1C`へ一時変更する。
3. 原作Fairy AI `$A700`をJSRする。
4. main-slot typeを`$9C`へ戻す。
5. 保存した取得数と現在の`$0453`を比較する。

原作Fairy AI内部はtype `$1C-$1F`で挙動が分かれる。取得処理後の`$A773`はtype `$1C`ならRTSし、それ以外なら星座/封印側の処理へ進む。一時typeを正確に`$1C`へすることで、Dark Fairyは通常Fairy取得側に固定される。

原作AIが通常の時間切れ等で`JMP $B376`へ入りslotをdespawnした場合も、`$B376`のRTSが専用AIへ戻る。専用側はtype fieldを`$9C`へ書き戻すが、statusはinactiveのままなので次frameのentity loop対象にはならない。stack上の取得数もPLAされる。

## 取得検出

原作Fairy取得stateは初回だけ次を行う。

- main status bit2をsetする。
- sub-slot timerを1へする。
- Fairy取得SEを鳴らす。
- `$0453`を1増やす。
- 10個目なら追加処理後に`$0453=0`へ戻す。

専用AIは原作AIの直前と直後で`$0453`を比較する。通常増加でも9から0へのwrapでも値が変わるため、どちらも取得として検出できる。

値が変わった時はsub-slot `[7]=#$3C`を設定する。保存した旧値はPLAで必ず消費され、取得有無の両経路でstack差分は0である。

## 60frame毒counter

次frame以降、sub-slot `[7]`が非0なら原作Fairy AIを呼ばない。

```text
counter > 1  : counter--, RTS
counter == 1 : counter=0, death action, despawn
```

取得frameに`#$3C`を設定し、そのframeでは減算しない。次の59回は`$3B`から1まで進み、counter 1のframeで0へして毒処理を行う。設定から毒処理までのAI invocation間隔は60回である。

毒処理はA=`$31`で`JSR $8D5F`を呼び、Dana死亡sequenceを起動する。その後`JMP $B376`でDark Fairy自身をdespawnする。JMP先のRTSが共通AI hookの呼出元へ戻るため、専用AIに余分なreturn addressは残らない。

## animation属性

共通animation入口はtype `$9C`で次を行う。

1. `JSR $8789`で原作Fairy groupのframeを更新する。
2. Y=`$13`でmain-slot attrを読む。
3. `AND #$13 / ORA #$48`でDark Fairy用palette/flip属性へする。
4. 書き戻してRTSする。

固定値でattr全体を潰さず、原作Fairy animationが生成した必要な反転bitを残す。CHANGELOGの「反転フレームでも属性が崩れない」実装と一致する。

## ROM/RAM配置

| file | CPU | size | 内容 |
|---:|---:|---:|---|
| `0x6010-0x6018` | `$E000-$E008` | 9B | setup |
| `0x6019-0x602D` | `$E009-$E01D` | 21B | init |
| `0x602E-0x6065` | `$E01E-$E055` | 56B | AI/poison |
| `0x6066-0x6084` | `$E056-$E074` | 31B | Blue Key Queen runtime |

Dark Fairy直後に空きはない。専用RAMは確保せず、Dark Fairy自身のsub-slot `[7]` 1Bを毒counterとして時分割利用する。原作Fairy AIの静的経路ではsub-slot `[7]`の競合はない。

## レジスタ・flag・stack

| 処理 | A | X | Y | stack/戻り |
|---|---|---|---|---|
| setup | pointer lowを返す | 維持 | `$0E` | stack操作なし、RTS |
| init | 定数/原作writerでclobber | 原作Xを維持 | `[5]`書込等でclobber | 共通入口PHAを先頭PLA |
| stock AI wrapper | count/type/AIでclobber | 原作AIでclobber | type書込でclobber | count PHA/PLA 1対1 |
| countdown | counterでclobber | 維持 | `[7]` | stack操作なし |
| poison | A=`$31`後clobber | action/despawnでclobber | `[7]` | JSR後JMP、最終RTSは`$B376` |
| animation | attrでclobber | entity index維持 | `$13` | JSR/RTS 1対1 |

countdownのSBC結果はcounter 1でZero setになるためBEQ poisonが成立する。counter 0は先にBEQ stock_aiへ入るため、SBC underflowは起きない。

## 成立している点

- 正式ID `$9C`とFairy `$1C`の下位bitが一致する。
- setup group `$0E`と一時type `$1C`により原作Fairyの見た目・取得分岐を使う。
- `$0453`比較は同期的な原作AI呼出の前後だけで行われ、10個目wrapも検出する。
- 取得後はstock AIを止めるがslotをactiveのまま保持し、専用counterを実行できる。
- counter 60回後にdeath actionを呼び、自身をdespawnする。
- init/AI/animationのstackとreturnは均衡する。
- 現行workstateの86Bと正式ROM管理簿の範囲は現行実装と一致する。

## 技術的負債・問題候補

### [P2] property table範囲外byte `$A3`への依存

type `$9C`は原作property tableの範囲外であり、`$A32F`のAI pointer byte `$A3`をpropertyとして読む。現行initはstatus、behavior、Y velocityを上書きし、現行`$A3`ではinit後のsub-slot追加書込みも発生しないため成立する。

ただし`$A32F`のbyte、原作property前段、共通init hook位置のいずれかが変われば、専用init後に新たな副作用が残り得る。現時点のROMでは動作不良ではないが、追加敵のpropertyを共通入口センターで正式分類せず、偶然読む範囲外値を後から打ち消す構造は脆い。

property入口で`$9C`へ明示的なFairy相当propertyを返す修正は、Spark/Panelが共有する`$A2CC` hook chainの変更になる。ROM/RAM空きと台帳影響を事前算定し、Spark/Panel/全追加敵のinitを再検証する必要があるため、局所修正として扱わない。

### [P3] Demon Mirror内の`$9C`をstandard ROM検出が見ない

`levels_need_runtime()`はdirect enemyだけを走査し、Demon Mirrorの`enemy_codes`を見ない。通常の日本版入力はmapper66へ拡張され、expanded保存ではruntimeが常設されるため主経路には影響しないが、非expanded ROM拒否用validationとしては漏れである。

修正自体はlevel走査だけで、ROM/RAM配置、空き、台帳に影響しない。9/26の共通validation修正として他の追加敵とまとめる方が一貫する。

## 未検証点

- Mesenで取得frameから60frame後のdeath action/despawnまでの動的traceは採取していない。
- Dark Fairyが複数同frameに取得された場合、複数のdeath action `$31`が同frameに重なる実挙動は未確認である。
- key enemyまたはfall-death Fairy targetへDark Fairyを指定した組合せの動的挙動は未確認である。
- 実機OAM属性とピッカー/キャンバスのpixel単位比較は行っていない。

## 修正時の検証条件

- `$9C`のsetup/init/AI/animation分類を共通入口センター内に維持すること。
- 原作property範囲外読出を解消する場合、`$A2CC`のSpark/Panel fallbackを壊さないこと。
- 取得前後の`$0453`が通常増加と9->0の両方で検出されること。
- typeを`$1C`へしている間だけ原作Fairy AIを呼び、return後は必ず`$9C`へ戻すこと。
- poison counterが60 AI invocationで、death action後にslotを解放すること。
- 原作Fairy `$1C`とFairy Princess/Seal `$1D-$1F`へ副作用を出さないこと。

