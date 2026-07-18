# 2/26 Enhanced Saramandor A/B/C runtime 6502静的解析

解析日: 2026-07-18
対象バージョン: v0.9.40 / commit `5db3d29` 後の作業ツリー
対象: `magatu_skc/core/saramandor_variant.py`、速度初期化の接続元`panel_monster_stage_variant.py`、接続先`gargoyle_variant.py`
一次資料: `解析資料/ROM完全解析/solomon_commented.asm`、日本版原作ROM、現行mapper66 workstate、`docs/サラマンダーASM処理詳細.txt`

## 結論

Enhanced Saramandor A/B/Cは、原作Saramandorの未使用側IDを利用し、原作のState 3火吐きシーケンスを維持したまま、生成する子だけをFlame type `$04`からBullet type `$20`へ変更するruntimeである。

- A=`$5E/$5F`、B=`$62/$63`、C=`$66/$67`。偶数IDが右、奇数IDが左である。
- A/B/Cは、それぞれ独立した本体移動速度、Bullet速度、最低歩行時間、発射後停止時間を持つ。
- 通常Saramandor `$5C/$5D/$60/$61/$64/$65`とDragonは、分類結果0となり、原作処理へ戻る。
- 全9個の6502 code blobは命令境界で末尾まで分解できた。各hookのJSR/JMP接続、stack、group table index、Carry返却は成立している。
- 現行workstateに書かれたhook/runtimeは、現行Python builderと全て一致した。設定を変えない`apply()`は0バイト変更だった。

ただし、プレイ継続に影響する確定バグを1件見つけた。発射準備で確保する2個の子sub-slotのうち、実体化しない1個目を発射終了時に解放していない。攻撃のたびに1slotずつ使用不能になり、同じ部屋で繰り返し攻撃すると、最終的に新しい攻撃へ入れなくなる。この文書作成では修正していない。

## 対象IDと設定group

| variant | ID | 向き | group戻り値 |
|---|---:|---|---:|
| A | `$5E` | 右 | 1 |
| A | `$5F` | 左 | 1 |
| B | `$62` | 右 | 2 |
| B | `$63` | 左 | 2 |
| C | `$66` | 右 | 3 |
| C | `$67` | 左 | 3 |

間の通常ID `$60/$61/$64/$65`はgroup 0になる。classifierは`type-$5E`が`0-9`の範囲で、差分bit1が0のpairだけを受理する。

```text
delta 0,1 -> group 1
delta 2,3 -> group 0
delta 4,5 -> group 2
delta 6,7 -> group 0
delta 8,9 -> group 3
その他    -> group 0
```

groupは1-basedである。各parameter参照はtable本体の1バイト前をbaseにし、`base,Y`のY=1/2/3でA/B/Cを読む。0-based tableを1-based indexで1バイトずらして読む不整合はない。

## 原作Saramandorの状態機械

AI入口は`$B038`である。

```text
$B038  JSR $B384       共通起動条件
       JSR $B201       behavior >> 2 = state index
       JSR $8EA9       inline word tableへ間接分岐
```

| state | 原作入口 | 役割 |
|---:|---:|---|
| 0 | `$B21F` | 短い待機/寿命側処理 |
| 1 | `$B162` | 子slot管理を含む遷移 |
| 2 | `$AE30` | 共通短遷移 |
| 3 | `$B075` | 火吐き本体 |
| 4 | `$A41C` | no-op |
| 5 | `$B176` | 通常歩行、距離判定、再発射入口 |

通常はState 5で歩き、条件成立時に`$B1A7`で子slotを2個確保してState 3へ入る。State 3は`sub[1]`を時間軸にし、`$18`で子を実体化し、原作では`$34`で終了してState 5へ戻る。

## 主なentity field

| ポインタ | field | 用途 |
|---|---:|---|
| `($2E)` main | `[0]` | entity status |
| `($2E)` main | `[1]` | type `$5C-$67` |
| `($2E)` main | `[3]` | behavior。bit0=左右、上位bit=state |
| `($2E)` main | `[4]` | 前回速度初期化時のbehavior |
| `($2E)` main | `[5]` | Y速度 |
| `($2E)` main | `[8]` | X速度 |
| `($2E)` main | `[10]` | X座標 |
| `($2C)` sub | `[0]` | 親の子link bit。bit0=`sub[6]`、bit1=`sub[7]` |
| `($2C)` sub | `[1]` | 状態経過counter、再発射counter |
| `($2C)` sub | `[4]` | DanaとのY距離/2 |
| `($2C)` sub | `[5]` | DanaとのX距離/2 |
| `($2C)` sub | `[6]` | 1個目に確保した子slot index |
| `($2C)` sub | `[7]` | 2個目の子slot index。実体化するFlame/Bullet |
| 子`($00)` sub | `[7]` | Enhanced Bulletの速度marker `$00/$88/$89` |

新しい専用RAMは使わない。原作の親子slotと、Panel Monster v2のBullet marker解釈を共有する。

## hook一覧

| 原作CPU | 変更後 | 役割 |
|---:|---|---|
| `$B105` | `JSR $E3C9` + NOP | 子type/status/behaviorをFlameまたはBulletに分岐 |
| `$B0A9` | `JSR $E3ED` + NOP | Enhanced BulletではFlame固有status bitを立てない |
| `$B0C6` | `JSR $E402` | Enhancedでは原作の子2個一括despawnを飛ばす |
| `$B1E9` | `JMP $E40B` | Enhancedだけ横反応距離を`$60`へ拡張 |
| `$B121` | `JSR $E430` | materialize後、Bulletの`sub[7]`へ速度markerを書く |
| `$B17B` | `JSR $E448` + `BCC` | 初回/再発射の最低歩行counterを比較 |
| `$B0B3` | `JMP $E465` | group別の発射後停止終了counterを比較 |
| `$866D` | Panel共有`JSR $E4C8` | `$E9A9`で本体速度用IDだけ正規化して原作`$8AC0`へ連鎖 |

`$AFD1`のBullet初期速度hook候補は定義されているが、現行runtimeは原作`LDA #$08 / ORA ($2E),Y / STA / RTS`を変更しない。Bullet速度は生成時ではなく、Panel Monster v2のBullet state 2 hookがmarkerを読んで適用する。

## 発射までの流れ

### 1. Danaとの距離

State 5 `$B176`は最初に`$B1E9`を呼ぶ。Enhanced版は横距離だけを変更する。

| 対象 | X閾値 | Y閾値 |
|---|---:|---:|
| Enhanced A/B/C | `$60` = 96px | `$10` = 16px |
| 通常Saramandor / Dragon / その他 | `$14` = 20px | `$10` = 16px |

Xが閾値以上ならCarry setで即returnする。X内ならYを比較し、最後の`CMP #$10`のCarryを呼出元へ返す。通常側の閾値と命令順は原作を再現している。

### 2. 最低歩行時間

距離条件が成立した後、`$B17B` hookが`sub[1]`を比較する。

- 初回攻撃前は親`sub[7]=0`なので、Enhancedでも原作`$20`を使う。
- 一度State 3へ入ると、2個目に確保したslot indexが親`sub[7]`へ残る。2回目以降はA/B/C別の`refire_wait`を使う。
- `refire_wait`は1-255。比較結果のCarryをhook直後の`BCC`へそのまま渡す。

2個目のslot indexが0になる心配はない。`$B2EA`はindex 0から探索するため、0が空いていれば1個目の確保が必ず0を取る。2個目の成功indexは必ず1以上になる。

### 3. 2個の子slot確保

条件成立後の原作`$B1A7-$B1E8`は次の順で動く。

```text
$B2EAで1個目を確保
  -> indexを親sub[6]へ保存
  -> 1個目sub[0]=$80
$B2EAで2個目を確保
  -> 失敗なら1個目sub[0]=0へ戻して中止
  -> 成功なら2個目sub[0]=$80
親sub[0] |= $03
親sub[1] = 0
親behavior = State 3 + direction
2個目indexを親sub[7]へ保存
```

成功時には2slotとも`sub[0]=$80`で予約済みになる。main-slotへtype/status/座標を書いて実体化するのは、この後の2個目だけである。

## State 3の時間軸

| 親`sub[1]` | 原作/Enhancedの処理 |
|---:|---|
| `$00-$17` | 発射準備。State 3速度0で親は停止 |
| `$18` | 子`sub[7]`側を実体化。SE再生、親の口元へ配置 |
| `$18-$1F` | 子準備 |
| `$20-$2B` | 表示/status段階 |
| `$2C`以降 | 原作Flame status段階。Enhanced BulletはFlame固有bit変更を抑止 |
| `stop_end` | 親の発射終了、State 5へ戻る |

`stop_end = $18 + post_fire_stop`である。設定可能な`post_fire_stop`は28-231なので、終了counterは原作と同じ`$34`から最大`$FF`までに収まる。

## FlameからBulletへ変える処理

### 原作

`$B105`以降は、子へ次を設定する。

```text
type   = $04
status = $C6
behavior = $0A/$0B
X位置 = 親の右+16 / 左-17
```

原作Flameは短い口火であり、移動するBulletではない。

### Enhanced

`$E3C9`はgroup非0なら次を設定する。

```text
type   = $20
status = $C0
behavior = $00/$01
X位置 = 原作と同じ口元
```

方向は親behavior bit0から作る。classifierの最後の`CLC/ADC`によりCarry=0で戻るため、その後の原作`ROR A`はA bit0をCarryへ移し、右/左の口元offsetも正しく選ぶ。

`$9D1C`によるmaterialize後、`$E430`が親`sub[7]`から同じ子のsub-slot pointerを取り、子`sub[7]`へmarkerを書く。

| 炎速度設定 | marker | Bullet state 2での速度 |
|---|---:|---|
| 通常 | `$00` | 原作Bullet速度 |
| 1/2 | `$89` | 正`$18` / 負`$68` |
| 1/4 | `$88` | 正`$0C` / 負`$74` |

markerの解釈本体は1/26 Panel Monster v2 runtime側にある。従ってEnhanced Saramandor単独では完結せず、Panelの常設Bullet hookが必須である。

## 本体移動速度の正規化

原作速度初期化入口`$866D`ではXがentity typeである。現行hook chainは次である。

```text
$866D
  -> Panel parent speed guard $E4C8
     -> Saramandor normalizer $E9A9
        -> Gargoyle normalizer $EDA0
           -> original speed initializer $8AC0
     -> Panelなら速度fieldを0へ戻す
```

Saramandor normalizerはEnhanced IDだけを、設定されたstock速度groupのbase IDへ一時的に置き換える。

| 移動速度preset | 一時base ID | 右/左 |
|---:|---:|---|
| 1 | `$5E` | `$5E/$5F` |
| 2 | `$62` | `$62/$63` |
| 3 | `$66` | `$66/$67` |

RAM上の本当のentity typeは変更しない。Xだけを一時正規化し、Aをstackで保持してGargoyle normalizerへtail jumpする。Enhancedでない場合もAをpopして同じ接続先へ進む。両経路のstack収支は0である。

## register・flag・stack検査

| helper | A/X/Y | flag/stack契約 |
|---|---|---|
| group `$E9D3` | A=0/1/2/3、X保持、Y=1 | PHA/PLA全経路で収支0。呼出側は主にZeroを使用 |
| spawn `$E3C9` | variantでA/X=direction、Y=3 | Carry=0で原作`ROR A`へ戻る。stockは原作14Bを実行 |
| substatus `$E3ED` | A=子status、Y=0 | inner PHA/PLA収支0。variantはbit1を立てずstockはORA `$02` |
| flame behavior `$E402` | groupでA/Y clobber | JSRからRTS。stockは`JMP $B05E`のtail call |
| distance `$E40B` | X=abs X distance、Y=4/5 | 最終CMPのCarryを返す。stack不使用 |
| child marker `$E430` | X=group、Y=7 | groupをPHAし、`$B156`後に必ずPLA。収支0 |
| refire `$E448` | X=timer、Y=groupまたは7 | stock、初回、再発射の3経路でPHA/PLA収支0。CMPのCarryを返す |
| exit `$E465` | X=State 3 counter、Y=0 | stackはclassifier内のみ。待機は`JMP $B0D8`、終了は`JMP $B0B7` |
| speed `$E9A9` | Xを一時正規化、Aは`$EDA0`入口まで保持 | outer PHAとvariant内PHAの全経路で対応するPLAあり |

9 code blob、合計257BをMOS 6502としてディスアセンブルし、全blobで消費byte数とblob長が一致した。parameter table 12Bはcodeではないため、この数に含めない。

## ROM/RAM配置

正式ROM管理簿上の現行配置は次の2範囲である。

| file | CPU | size | 内容 |
|---:|---:|---:|---|
| `0x63D9-0x6491` | `$E3C9-$E481` | 185B | spawn/substatus/flame/distance/marker/refire/exit helper |
| `0x69B9-0x6A0C` | `$E9A9-$E9FC` | 84B | speed normalizer、group classifier、12B parameter table |

合計269Bである。`RESERVED_SPANS`も同じ2領域を、前半は内部的に連続する2span、後半は84Bとして登録している。新規RAM予約はないが、原作sub-slot `$04F7-$057E`を使用する。

## 確定した問題

### [P1] 攻撃のたびに1個の子sub-slotが永久に予約されたままになる

これは推測ではなく、確保と解放の命令列から確定できる。

1. `$B1A7`以降で1個目を確保し、indexを親`sub[6]`へ保存する。
2. 1個目のsub-slot `[0]`へ`$80`を書き、`$B2EA`から見て使用中にする。
3. 2個目を確保し、indexを親`sub[7]`へ保存する。
4. `$B105/$9D1C`で実体化するのは2個目`sub[7]`だけである。
5. 原作終了時は、親`sub[0]&3`をXへ入れ、`$B0C6 JSR $B05E`でbit0の`sub[6]`とbit1の`sub[7]`を両方despawnする。
6. Enhanced hook `$E402`はgroup非0なら即RTSし、`$B05E`を丸ごと飛ばす。
7. その直前に親`sub[0]`は`AND #$F8`で子link bitを消しているため、後続処理が1個目を追跡して解放する経路も残らない。

2個目のBulletは自分のAIで後に消滅できる。しかし1個目はtype/status/AIを持つentityへ実体化しておらず、sub-slot `[0]=$80`だけが残る。entity AIから自己解放することはできない。`$B2EA`はsub-slot `[0]`のbit7を見て空きを探すため、そのslotは以後選ばれない。

結果として、各攻撃で使用可能sub-slotが1個減る。残りが1個になると、次の攻撃準備は1個目を一時確保した後、2個目の確保に失敗して1個目を戻すため、以後は攻撃開始に必要な2slotを確保できない。同じ部屋に複数のEnhanced Saramandorがいる場合は、さらに早く枯渇する。

本来必要なのは「1個目`sub[6]`だけ解放し、2個目`sub[7]`のBulletは残す」処理である。ただし、この解析作業では修正、ROM再配置、管理簿更新を行っていない。

### [P3] 旧監査文書と現行C variantの記述が矛盾する

`docs/new_enemy_id_placement_audit.md`の一部には、`$66/$67`をPanel Monsterへ貸し出したままにし、Enhanced Saramandor速度3を作らないという古い判断が残る。一方、現行runtime、UI、parameter tableは明確に`$66/$67`をEnhanced Saramandor Cとして有効化している。

現行コードと現行workstateを解析対象としたため、本書ではCを正式な現行挙動として扱う。これは6502動作バグではないが、後の保守で誤ったID判断を招く文書不一致である。

## 正常と確認した事項

- A/B/Cと通常pairのclassifier全10入力を展開し、漏れ・巻込みなし
- 通常SaramandorとDragonの距離閾値、spawn setup、substatus、despawn fallbackが原作相当
- group 1-based indexと4列のparameter table参照位置が一致
- 初回だけ原作`$20`、2回目以降だけgroup別refireになる分岐が成立
- stop end値が8bit内に収まり、`$FF`設定でもwrap前に終了
- spawn時のCarryと方向bitが原作口元offsetへ正しく渡る
- child markerはmaterializeした2個目のBullet sub-slotへ書かれる
- speed normalizerはRAMのtypeを変更せず、Xだけを一時正規化
- Saramandor -> Gargoyle -> 原作`$8AC0` -> Panel cleanupの共有hook chain成立
- 現行workstateの全hook、全固定blobがbuilderと一致
- 設定無変更の`apply()`が変更0件、変更byte 0件
- 全code blobが命令分断なく末尾までディスアセンブル可能

## 未実施と、この文書だけで保証しないこと

- 今回はROMを新規生成していない。
- Mesenでslot残数を表示しながら攻撃を繰り返す動的試験は行っていない。ただしslot残留自体は全確保・解放命令を追跡して確定している。
- Bullet速度marker `$88/$89`の最終移動量は1/26 Panel Monster v2側の静的証明を参照する。
- 複数Enhanced Saramandor、他の子生成敵、Panel Bulletが同時にいる場合の枯渇までの実フレーム数は計測していない。
- 確定バグ1件と文書不一致1件は記録のみで、実装コード、ROM配置、管理簿は変更していない。
