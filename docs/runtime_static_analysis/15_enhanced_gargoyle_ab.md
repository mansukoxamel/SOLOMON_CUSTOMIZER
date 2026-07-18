# 15/26 Enhanced Gargoyle A/B runtime 6502静的解析

解析日: 2026-07-19
対象: `magatu_skc/core/gargoyle_variant.py`、`saramandor_variant.py`、`panel_monster_stage_variant.py`、原作Gargoyle AI `$AE1C`
一次資料: コメント付き原作ASM、日本版原作ROM、現行mapper66保存ROM、正式ROM管理簿、CHANGELOG、ID配置監査資料

## 結論

Enhanced Gargoyleは借用ID `$7A/$7B`をA、`$7E/$7F`をBとして使う。A/Bは本体移動速度1/2、Bullet速度1x/1/2/1/4、発射間隔、発射後cooldownを独立設定できる。1回の攻撃で必ず2発、LIFE百の位が奇数なら3発発射する。

現行実装はprimary/cooldown 71B、2/3発目105B、helper 105Bの計281Bを3領域へ置き、原作Gargoyleのmaterialize、cooldown、state 3、state 4をhookする。本体速度normalizerは`$866D`のSaramandor共通速度hookから呼ばれる。

全ID分岐、state 0/3/4、slot成功/失敗、LIFE parity、marker、速度hook、cooldown、stackを追跡し、6502本体の確定ロジックバグは見つからなかった。

問題候補は2件である。

1. `current_settings()`は未知のBullet速度markerをエラーにせずdefault 1/2として読む。runtime byte破損の検出として弱い。
2. ID配置監査資料は旧2発共通設定・旧172B配置のままで、現行A/B独立設定・2/3発・281B配置と一致しない。

ROM/RAM配置は変更していない。修正も行っていない。

## 対象ID

| ID | variant | 初期方向 | 原作上の組 |
|---:|---:|---|---|
| `$7A` | A | 右 | Gargoyle速度1右の借用 |
| `$7B` | A | 左 | Gargoyle速度1左の借用 |
| `$7E` | B | 右 | Gargoyle速度2右の借用 |
| `$7F` | B | 左 | Gargoyle速度2左の借用 |

通常Gargoyle `$78/$79/$7C/$7D`は1発の原作経路を維持する。分類はtypeへ`AND #$FA / CMP #$7A`を行い、bit0の左右とbit2のA/Bを除いて4IDを1範囲へまとめる。

## hookとruntime配置

| hook/file | CPU | 置換後 |
|---:|---:|---|
| `0x2E7F-0x2E85` | `$AE6F-$AE75` | `JMP $E33F` + NOP 4B |
| `0x2E58-0x2E5B` | `$AE48-$AE4B` | `JMP $E36A` + NOP |
| `0x2E38-0x2E39` | `$AE28-$AE29` | state 3 table word=`$ED1D` |
| `0x2E3A-0x2E3B` | `$AE2A-$AE2B` | state 4 table word=`$ED1D` |

| file | CPU | size | 内容 |
|---:|---:|---:|---|
| `0x634F-0x6395` | `$E33F-$E385` | 71B | first-shot gate + cooldown entry |
| `0x6D2D-0x6D95` | `$ED1D-$ED85` | 105B | state 3/4、2発目・3発目 |
| `0x6DB0-0x6E18` | `$EDA0-$EE08` | 105B | movement、marker、cooldown、interval helper |

`0x6D96-0x6D97`は2B空き、`0x6D98-0x6DAF`はEnhanced Ghost parameter tableである。helper直後`0x6E19-0x6EB3`は155B空きである。3領域は連続していないが、全て現行`RESERVED_SPANS`と正式管理簿に登録される。

## 本体速度normalizer `$EDA0`

entity setup入口`$866D`はSaramandor speed extensionを経由し、そのfallbackで`$EDA0`へ入る。入口はA=behavior、X=実typeである。

1. AをPHAする。
2. Xが`$7A-$7F`外ならAをPLAし原作`$8AC0`へJMPする。
3. type bit1が0なら通常`$7C/$7D`なので同じfallbackへ入る。
4. bit2からA/Bを選び、2B movement tableを読む。
5. tableのbase `$7A`または`$7E`へ元type bit0を加え、Xだけを正規化する。
6. AをPLAして原作`$8AC0`へJMPする。

実typeはmain-slot内で変更しない。Xだけを選択した原作metadata pairへ置き換えるため、見た目のID、鍵判定、AI分類は維持し、本体速度だけをA/B設定へ合わせる。

movement設定1はbase `$7A`、設定2はbase `$7E`をtableへ焼き込む。右左は元type bit0で保持される。PHA/PLAは対象外、通常Gargoyle、Enhanced A/Bの全経路で均衡する。

## 1発目gate `$E33F`

原作materialize `$AE6F`の7Bを再現し、behaviorをXへ保存、bit1をsetして書き戻した後、`JSR $AE76`で1発目Bulletを生成する。

生成後は親sub `[6]`のchild indexを`$B156`へ渡し、marker helper `$EDCB`を呼ぶ。helperは親typeを分類し、次をchild sub `[7]`へ書く。

| 親 | marker |
|---|---:|
| 通常Gargoyle | `$00` |
| Enhanced 1x | `$01` |
| Enhanced 1/2 | `$89` |
| Enhanced 1/4 | `$88` |

marker 0なら通常Gargoyleとして原作1発経路へ戻る。marker非0なら親behaviorをdirection bit保持の`$0C/$0D`、すなわちstate 3へし、sub `[1]`を0へしてRTSする。

通常Bulletへ0を明示するため、以前同じchild slotが強化Bulletに使われていても速度markerを引き継がない。

## Bullet速度marker

Panel Monster v2の共通Bullet state 2入口はchild sub `[7]`を読む。

- `$88`: dynamic speed preset 1/4。
- `$89`: dynamic speed preset 1/2。
- `$01`:正値かつ`<$88`なのでdynamic decodeへ入らず、原作Bullet metadataの1x速度を維持する。
- `$00`:通常Bulletとして原作速度を維持する。

markerは1発目、2発目、3発目の全てで同じhelperから設定される。A/B個別値の選択はparent type bit2で行い、発射番号には依存しない。

## state 3/4共通handler `$ED1D`

先頭で親typeをmask分類し、Enhanced 4IDでなければ`JMP $A41C`へ戻る。通常Gargoyleの原作state 3/4 no-opを維持する。

Enhancedではsub `[1]`を読み、`$EDF8`でA/B別inter-shot thresholdと比較する。未到達ならRTS相当のno-opへ戻る。到達後は`$B2EA`で空きslotを確保する。

### slot不足

Carry clearなら発射せず`JMP $A41C`へ戻る。behavior stateとsub `[1]`を変更しないため、次frameもthreshold到達済みのまま再試行する。slot不足で2/3発目を永久省略したり、不正child indexを書いたりしない。

### slot成功

1. child indexを親sub `[6]`へ保存する。
2. child main statusへ`$80`を書く。
3. 親sub status bit0をsetする。
4. 親direction bit0をXへ取り、`JSR $AE76`でBulletを生成する。
5. marker helperでchild sub `[7]`へA/B別速度markerを書く。

原作`$AE76`は親sub `[6]`をchild indexとして読み、親座標から左右offsetを付け、type `$20`、status `$C0`、behavior right/leftでBulletを完成させる。

## 2発/3発のstate遷移

2発目生成時の親はstate 3でbehavior bit4=0である。

- LIFE百の位RAM `$0439` bit0=0: directionを保持してbehavior `$02/$03`へし、cooldownへ入る。
- `$0439` bit0=1: behavior `$10/$11`のstate 4へし、sub `[1]`を0へする。

state 4は同じinter-shot thresholdをもう一度待つ。3発目生成後はbehavior bit4が1なのでLIFEを再判定せず、directionを保持して`$02/$03`へ入りcooldownへ進む。

2発目から3発目の間隔も、1発目から2発目と同じA/B設定値である。state 4へ移るbranchは`JMP $ED7C`でtimer clear共通尾部へ接続し、fall-throughによるclear漏れはない。

## cooldown `$E36A`

原作state 0 handler `$AE3B`はbehavior bit1 set時、sub `[1]`をXへ読み`CPX #$50`でcooldownを判定する。hookはこの比較を差し替える。

親typeがEnhancedなら`$EDEA`をJSRし、type bit2からA/B別thresholdとXを比較する。未到達は`JMP $AEC1`、到達は`JMP $AE4C`でtimer clear、X velocity再設定、state 5復帰へ進む。

通常Gargoyleは保存している原作/global設定のthresholdで比較し、原作と同じ2出口へ進む。Enhanced A/B値は通常へ漏れない。

threshold 0は`CPX #$00`が常にCarry setなので即時復帰、255はXが255に到達した時だけ復帰する。8bit範囲内で比較は成立する。

## inter-shot compare `$EDF8`

入口Aは現在timerである。helperはPHAし、親type bit2でA/Bを選び、対応する`CMP #NN`の直前にPLAする。A/B両経路でPHA/PLAが1対1になり、CMPのCarryをそのままcallerへ返す。

threshold 0/255の境界はcooldownと同じく成立する。

## レジスタ・pointer・stack

| 処理 | 主な契約 |
|---|---|
| speed normalizer | AをPHA/PLA、Xだけmetadata用に正規化、`JMP $8AC0` |
| first shot | X=directionを`$AE76`へ渡す。`$2C/$2E`は親、`$00`はchild pointerへ変化 |
| marker | parent `$2E`からtypeを読み、parent sub `[6]`経由でchild `$00`を得る |
| state 3/4 | slot成功時X=child index、発射前にX=directionへ再設定 |
| interval helper | timer AをPHA/PLA、CMP flagを保持してRTS |
| cooldown helper | X=timerを保持、A/Yだけを分類に使用 |

`$AE76`と`$B156`はA/X/Yをclobberする前提で、必要なdirection、timer、markerは呼出前後に再取得している。return addressは全てJSR/RTSまたはtail JMPで均衡する。

## 成立している点

- Enhanced 4IDだけをmask分類し、通常4IDを原作1発経路へ残す。
- A/B本体速度の選択はXだけを正規化し、main typeを変更しない。
- 1/2/3発目へ同じA/B別Bullet markerを書く。
- 通常Bulletのmarkerを0へし、slot再利用の速度漏れを防ぐ。
- 2/3発目slot不足ではstate/timerを保持して再試行する。
- LIFE parityは2発目成功後だけ評価し、奇数時だけstate 4へ入る。
- state 4開始時timerを0へ戻し、同じinter-shot間隔を測る。
- cooldownとinter-shotはA/B独立、0-255全域をunsigned CMPで扱う。
- 通常cooldownはEnhanced設定から分離される。
- 全PHA/PLA、JSR/RTS、tail JMPは静的に均衡する。

## 技術的負債・問題候補

### [P3] 未知markerをdefaultとして読む

`is_applied()`はhelper内の設定byteをmaskして構造一致を確認する。`current_settings()`はmarkerが`$01/$88/$89`のどれでもない場合、エラーにせずdefault 1/2を返す。

runtime実行時は未知正値`<$88`ならstock 1x扱い、未知負値は別marker処理へ入る可能性があり、UI表示と実ROM挙動が一致しない。設定読出時に未知markerを拒否する方が正直である。修正はPython validationだけでROM/RAM配置、空き、台帳に影響しない。

### [P3] ID配置監査資料が現行実装より古い

`docs/new_enemy_id_placement_audit.md`は2発固定、A/B共通設定、172Bの旧2blockを記載する。現行はLIFE parityによる2/3発、A/B独立設定、281Bの3blockである。

runtime挙動には影響しない文書不一致である。管理簿は現行3領域と一致しているため、正式ROM台帳の変更は不要である。

## 未検証点

- MesenでLIFE百の位偶数/奇数の2発/3発を全4IDについて動的traceしていない。
- inter-shot/cooldown 0、1、255の実frame数は未計測である。
- 2発目と3発目のslot不足が長時間続いた後の再試行は実機未確認である。
- 1x/1/2/1/4のBullet座標差分は全発射番号で未確認である。
- 通常GargoyleとEnhancedを同roomへ置いた時のmarker slot再利用は動的未確認である。
- 鍵持ちEnhanced Gargoyleの火球撃破・鍵出現は未確認である。

## 修正時の検証条件

- `$78/$79/$7C/$7D`が1発、`$7A/$7B/$7E/$7F`が2発または3発であること。
- A/Bの本体速度、Bullet速度、interval、cooldownを互いに異なる値へして混線しないこと。
- LIFE百の位偶数で2発、奇数で3発になり、3発目前にも設定intervalを待つこと。
- slot不足では不正pointerを書かず、空き発生後に同じ発射を再試行すること。
- 通常Bullet child sub `[7]`が0、Enhanced各弾が設定markerになること。
- `$866D`速度hook連鎖でSaramandor、Panel Monster、通常GargoyleのX/A/stackを壊さないこと。

