# 11/26 Dark Fairy `$9C` runtime 6502静的解析

解析日: 2026-07-19
対象: `magatu_skc/core/fairy9c_runtime.py`、`new_enemy_runtime.py`、原作Fairy AI `$A700`
一次資料: コメント付き原作ASM、日本版原作ROM、現行mapper66 workstate、正式ROM管理簿、ID配置監査資料

## 結論

Dark FairyはFairyを取る動作を原作へ実行させ、取得を検出した60frame後にDanaの死亡action `$31`を起動する罠敵である。専用本体はsetup 9B、init 4B、AI 56Bの計69Bで、file `0x6010-0x6054`、CPU `$E000-$E044`に置かれる。animation palette補正は新敵ID共通入口センター側にある。

修正前workstateの86Bが修正前builderと一致することを確認した。原作Fairy取得経路、`$0453`の10個目wrap、typeの一時変更、毒counter、stack、despawnを静的追跡し、AI本体の確定ロジックバグは見つからなかった。

技術的負債・validation候補2件は修正した。

1. 共有property末端で`$9C`へ原作Fairyと同じproperty `$0A`を返し、原作property table範囲外の`$A3`を読まないようにした。
2. standard ROM保存用`levels_need_runtime()`は10/26の共通修正でDemon Mirror内の`$9C`も検出する。

Dark Fairy initから不要になった17Bを削除し、共有property末端を7B拡張したため、PRG0明示空きは差引10B増加して1035Bとなった。RAM追加と後続runtime移動はない。正式ROM管理簿は同じ修正で更新した。

## ID `$9C`固定の理由

Dark Fairyのモデルは原作Fairy `$1C`である。`$9C`は`$1C`と下位7bitが同じであり、原作animationとFairy系分岐が参照する下位bitを維持する。

setup group `$0E`、AI中の一時type `$1C`、animation palette補正を組み合わせて成立しているため、IDだけを別値へ移してはいけない。移動する場合は原作type下位bit、setup、init property、AI取得、animation、死亡処理を全て再検証する必要がある。

## 4入口

| 機能 | 共通入口 | 専用処理 |
|---|---:|---|
| AI | `$BBE2` | `$E00D`へJMP |
| setup | `$BC32` | `$E000`でFairy group `$0E`を返す |
| init | `$BC84` | `$E009`で保存Aを戻し原作writerへtail-call |
| animation | `$BCD0` | 原作`$8789`後にDark Fairy属性へ補正 |

## setup `$E000`

共有setup本体は`$0E=#$0E`、Y=`$0E`とし、`LDA $D9D3,Y / RTS`を実行する。これにより原作Fairyのsetup/animation metadata pointerを返す。Dark Fairy `$9C`とSeraphic Radiance `$9D`が同じ入口を使う。

共通setup入口からJMPではなくJSR相当のreturn先を保ったまま専用本体へJMPするため、専用RTSは原作`$8ACB`の呼出元へ直接戻る。stack追加はない。

## 共有property分類とinit `$E009`

原作敵初期化`$A2B8`はtypeから次を計算する。

```text
Y = (type - $18) >> 2
property = $A30E,Y
```

`$9C`では通常計算のYが`$21`となり、そのままなら正式property table外の`$A32F`を読む。日本版原作ROMの`$A32F`は`$A3`であり、これは直後のAI pointer tableに属するbyteで、enemy propertyとして設計された値ではない。

修正後は`$A2CC`から続くSpark/Panel/共有property chainの最終段で、type `$9C`へ原作Fairy `$1C`と同じproperty `$0A`を返す。従って`$A32F`は読まれない。

property `$0A`を通した原作前段は、status `$E2`、behavior候補X=`$00`を作る。Y velocity `[5]`への`$80`書込みと、init後のsub-slot方向初期値書込みは行わない。

共通init入口は原作writerへ渡すAをPHAしてからtype `$9C`を分類する。Dark Fairy initはPLAでA=`$00`を戻し、`JMP $9D1C`で原作writerへtail-callする。原作writerによりmain-slotは少なくとも`[0]=$E2`、`[1]=$9C`、`[2]=$FF`、`[3]=$00`となる。`$E2`はactive/AI対象で、Fairy相当の接触特性を持つ。

init側でstatus/type/behaviorやY velocityを作り直す後処理は不要になった。property処理が積んだ値も原作`$A2F5`以降で正常に消費され、sub-slot `[6]/[7]`への方向初期値書込みは行わない。

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
| `0x6019-0x601C` | `$E009-$E00C` | 4B | init tail-call |
| `0x601D-0x6054` | `$E00D-$E044` | 56B | AI/poison |
| `0x6055-0x6065` | `$E045-$E055` | 17B | 現行runtime予約なし |
| `0x6066-0x6084` | `$E056-$E074` | 31B | Blue Key Queen runtime |

共有property末端はGhost runtime内の`$E313-$E329`でDark Fairy/Ghost/原作を分類する。Ghost runtimeは218Bの既定上限まで使用する。Dark Fairy直後には17Bの空きができた。専用RAMは確保せず、Dark Fairy自身のsub-slot `[7]` 1Bを毒counterとして時分割利用する。原作Fairy AIの静的経路ではsub-slot `[7]`の競合はない。

## レジスタ・flag・stack

| 処理 | A | X | Y | stack/戻り |
|---|---|---|---|---|
| setup | pointer lowを返す | 維持 | `$0E` | stack操作なし、RTS |
| init | 保存Aを復元後、原作writerでclobber | 原作Xを維持 | 原作writerでclobber | 共通入口PHAをPLA、JMP先RTSで復帰 |
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
- property `$0A`で原作前段のstatus/behaviorが正式に成立し、範囲外tableを読まない。
- init/AI/animationのstackとreturnは均衡する。
- Dark Fairy 69B、共有property末端を含むGhost 218B、正式ROM管理簿の範囲が一致する。

## 修正した問題

### [P2] property table範囲外byte `$A3`への依存

共有property末端で`$9C`を先に分類し、原作Fairyと同じ`$0A`を返すよう修正した。Ghost `$B0-$BB`は従来通り`$4A`、それ以外は従来通り原作tableへ戻る。範囲外値を読んでから後処理で打ち消す依存はなくなった。

### [P3] Demon Mirror内の`$9C`をstandard ROM検出が見ない

10/26で共有validationがDemon Mirrorの`enemy_codes`も走査するようになり、`$9C`を含む全追加敵familyを検出する。stock IDだけのミラーはFalseを維持する。

## 未検証点

- Mesenで取得frameから60frame後のdeath action/despawnまでの動的traceは採取していない。
- Dark Fairyが複数同frameに取得された場合、複数のdeath action `$31`が同frameに重なる実挙動は未確認である。
- key enemyまたはfall-death Fairy targetへDark Fairyを指定した組合せの動的挙動は未確認である。
- 実機OAM属性とピッカー/キャンバスのpixel単位比較は行っていない。

## 修正時の検証条件

- `$9C`のsetup/init/AI/animation分類を共通入口センター内に維持すること。
- `$9C`はproperty `$0A`、Ghost `$B0-$BB`は`$4A`、Spark/Panel/stock fallbackは従来経路を維持すること。
- 取得前後の`$0453`が通常増加と9->0の両方で検出されること。
- typeを`$1C`へしている間だけ原作Fairy AIを呼び、return後は必ず`$9C`へ戻すこと。
- poison counterが60 AI invocationで、death action後にslotを解放すること。
- 原作Fairy `$1C`とFairy Princess/Seal `$1D-$1F`へ副作用を出さないこと。
