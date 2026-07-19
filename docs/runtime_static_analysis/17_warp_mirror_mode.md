# 17/26 Warp Mirror Mode runtime 6502静的解析

解析日: 2026-07-19
対象: `magatu_skc/core/warp_zone_trial.py`、`stage_ext.py`、`panel_monster_stage_variant.py`、`m66.py`、`main_window.py`、原作item判定 `$C532-$C5B5`
一次資料: コメント付き原作ASM、日本版原作ROM、現行mapper66検証ROM、正式ROM/RAM管理簿、CHANGELOG

## 結論

Warp Mirror Modeは、StageExt byte0 bit5がONのroomで、Danaが可視Demon Mirrorのcell `$05`へ触れると同じroomの別の`$05`へ移動する常設runtimeである。OFF roomとmirror以外のcellでは原作item判定を維持する。

128Bの全命令、224 grid cell、item hook、mode/cooldown、Dana座標・state・速度再初期化、StageExt loader、UI成立条件、stackを追跡した。6502本体の確定ロジックバグは見つからなかった。

data validation問題は1件あり、修正した。

1. UIのON操作と保存前整合性検査が同じcore validatorを使うよう統一した。ON後のmirror移動・block/item重ね、XML入力、3個以上のmirrorを保存前に拒否する。

ROM/RAM配置と6502バイト列は変更していない。

## hook位置と呼出契約

原作item判定はDana中心をgrid indexへ変換し、A=`$0304,X`、X=source cellとして次を呼ぶ。

```asm
$C54E: LDA $0304,X
$C551: JSR $C55B
$C554: LDA $02
```

現行hookは`JSR $EA5E`へ置換する。runtimeの終了形は3種類である。

| 経路 | 終了 | 戻り先 |
|---|---|---|
| mirror以外 | `JMP $C55B` | 原作`RTS`から`$C554` |
| mirror、mode OFF | `JMP $C55B` | 原作`RTS`から`$C554` |
| warp/no destination/cooldown | runtime内`RTS` | `$C554` |

tail `JMP`で原作subroutineへ入るため、hookのJSR return addressを原作`RTS`がそのまま消費する。追加stack frameは残らない。mirror以外のPHA/PLAも全経路で均衡する。

## StageExt modeの受渡し

StageExt byte0のbit5がWarp Mirror設定である。mapper66 room loader末尾のPRG1 helperは現在roomのbyte0を読み、次のように`$0770`を毎room再構築する。

| `$0770` bit | 機能 | loader入力 |
|---:|---|---|
| 4 | Enemy Clear Key Open mode | StageExt byte0 bit6を右へ2bit |
| 5 | Warp Mirror mode | StageExt byte0 bit5 |
| 6 | Warp Mirror cooldown | runtimeが一時使用、room loadでclear |
| 7 | Enemy Clear発火latch | runtimeが一時使用、room loadでclear |

helperはbit4/bit5だけから新しい値を書き、前roomのcooldown/latchを保持しない。Warp runtimeがbit6をset/clearする時は`ORA #$40`または`AND #$BF`なので、Enemy Clearのbit4/bit7とmode bit5を保持する。

## mirror以外のcell

Aが`$05`以外なら、runtimeは次を行う。

1. AをPHAする。
2. `$0770 &= #$BF`でcooldownだけをclearする。
3. AをPLAする。
4. 原作`$C55B`へJMPする。

従ってmirrorから1cellでも離れた最初のitem判定で再warp可能になる。同じcellが通常itemなら、cooldownをclearした同じ呼出で原作item取得も継続する。A、X、item cell値は原作へ正しく渡る。

## mirror cellとcooldown

A=`$05`では最初にmode bit5を調べる。

- mode OFFならAを`$05`へ戻して原作`$C55B`へ渡す。原作はitem最小値`$06`未満として何もしない。
- mode ONかつcooldown bit6が1なら即RTSする。
- mode ONかつcooldownが0ならsource cell Xをzero-page `$03`へ保存してdestination探索へ進む。

warp成功時は座標を書き換える前にcooldownをsetする。Danaはdestination mirror上へ出るため、次のitem判定でもA=`$05`になるがbit6により元mirrorへ即座に戻らない。mirror外へ動いた時だけ前節の経路でbit6がclearされる。

## 224 cell探索

探索はY=`$DF`から`$01`まで降順で`$0304,Y == $05`を探し、source Xと異なる最初のcellをdestination `$04`へ保存する。

原作live gridは`$0304-$03E3`の224B、16列×14行である。editorの16列×12行はroom loaderにより上下境界の間へ置かれ、配置可能cellはruntime index `$10-$CF`になる。従って`$DF-$01`走査は両境界を含むが配列外へは出ず、editorのcell `(0,0)`もruntime index `$10`として探索対象に入る。Y=`$00`を検査しないことによる配置mirrorの欠落はない。

正常editor dataでは可視mirrorは2個だけなので、source以外の1個が選ばれる。別の`$05`が3個以上存在する不正dataでは、indexが最大のcellが選ばれる。

destinationが無ければY=0から`no_item`へ入り、cooldownをsetせずRTSする。そのため進行不能やstack破壊は起こさないが、Danaがそのmirror上にいる毎loop 224cellを再走査する。

## destination座標

destination grid indexは上下境界込みの値である。runtimeは原作`$91A3`と等価な中心座標を直接作る。

```text
Y pixel = (cell & $F0) + $10
X pixel = ((cell & $0F) << 4) + $08
```

editor row 0はruntime row 1=`$10-$1F`なのでY=`$20`となる。editor row 11はruntime row 12=`$C0-$CF`なのでY=`$D0`となる。Xはcolumn中心8,24,...,248である。加算は各有効範囲でoverflowしない。

## Dana stateと速度再初期化

warp後はdestination Xのbit7をcarryへ取り、Dana stateを`$14`または`$15`へする。

```text
destination X < $80  -> state $14
destination X >= $80 -> state $15
```

どちらもDana state index 5で、bit0だけが左右を選ぶ。次に`$0581=#$FF`としてentity loopのtype cacheを意図的に不一致にし、次回`$8AC0`の速度・animation setupを強制する。

Dana typeの原作behavior tableではstate `$14/$15`がspeed index 6/7を選ぶ。速度表は次である。

| state | Y velocity | X velocity |
|---:|---:|---:|
| `$14` | `$80` | `$18` |
| `$15` | `$80` | `$68` |

従ってwarpは単純な座標teleportではなく、stage開始と同じstate/速度を再設定し、上向きの再出現と左右移動を伴う。runtimeが先に`$0587/$0588=0`としても、次のsetupでX velocityがstateに対応する値へ更新される。これは`$0581`を故意に`$FF`へする実装とコメントから意図された挙動と判断した。

runtimeは現在のY/X subpixel `$0585/$0588`とX velocity `$0587`を0へする。Y velocity `$0584`は直接clearしないが、強制setupがspeed tableの`$80`へ上書きするため、warp前のjump/fall速度は残らない。

## soundとitem action抑制

warp時はY=`$0D`で`JSR $8E8D`し、原作item pickup SEをqueueする。その後A=0で`$02=0`とする。

呼出元`$C554`は`LDA $02 / BEQ`でitem actionの有無を判定するため、warpだけを実行して通常item取得action `$8D5F`へは入らない。sound helperのJSR/RTSは均衡する。

## 修正済み問題

### [解消] mode成立条件を保存時に再検証しない

`main_window._warp_mirror_can_enable()`は、ON操作時に次を検査する。

- mirrorが2個ある。
- 位置が異なる。
- 2個ともeditor範囲内。
- mirror cellが空気である。
- 特殊block markerと重ならない。
- itemと重ならない。

修正後は`warp_zone_trial.level_has_valid_warp_mirrors()`を唯一の成立判定とし、UIのON操作と`validate_level_consistency()`の保存前検査が同じ関数を呼ぶ。

判定条件は「mirrorがちょうど2個」「別位置」「editor範囲内」「通常空気cell」「特殊block markerなし」「item重複なし」である。ON後にdataが変わった場合やXMLから不正状態を読んだ場合も、ROM byteを書き始める前のステージ整合性検査で保存を中止する。6502本体は変更していない。

## ROM/RAM配置

| file | CPU | size | 内容 |
|---:|---:|---:|---|
| `0x6A6E-0x6AED` | `$EA5E-$EADD` | 128B | Warp Mirror Mode runtime |
| `0x4561-0x4563` | `$C551-$C553` | 3B | item cell hook |

直前`0x6A0D-0x6A6D`は97B、直後`0x6AEE-0x6B05`は24Bの正式な空きである。現行mapper66検証ROMの128BとPython builder、および3B hookはbyte単位で一致した。

RAMは`$0770`の1BをEnemy Clearとbit分割共有する。zero-page `$03/$04`はitem判定中のscratchとしてだけ使い、呼出後に保持する契約はない。Dana main-slot `$057F-$0592`内ではstate、cache、座標、速度/subpixelだけを更新する。

## Python書込み側

`apply()`はruntime 128Bとhook 3Bを常設する。`levels_need_runtime()`は設定有無を返すが、mapper66保存では設定OFFでも`apply()`を呼ぶため、runtime本体の有無はstage内容で変わらない。

書込み前にhookが原作または現行、runtimeが全`00/EA`または現行builderであることを検査する。両検査後に初めて書くため、未知署名で部分適用を残さない。旧runtime救済用byte列の受入れはない。

## 正常と確認した事項

- `$C551`のA/X入力と`$C554`への全復帰経路
- mode OFF時の原作item判定
- mirror以外でのcooldown clearとA保存
- cooldownによる往復loop防止
- 224B gridの始終端とeditor 12行のoffset
- source除外、destinationあり/なし、複数候補
- destination中心座標の算術範囲
- Dana state `$14/$15`と左右選択
- `$0581=$FF`による原作速度setup強制
- warp前速度/subpixelの破棄
- SE呼出と`$02=0`によるitem action抑制
- `$0770`のbit分割とroom load時のlatch/cooldown clear
- PHA/PLA、JSR/RTS、tail JMPのstack均衡
- `RESERVED_SPANS`、正式ROM/RAM管理簿、現行ROM byte列の一致

## 未実施

- ROM生成
- emulatorでのwarp動的実行
- ROM/RAM管理簿の変更
