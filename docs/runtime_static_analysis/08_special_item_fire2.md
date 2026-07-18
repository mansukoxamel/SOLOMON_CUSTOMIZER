# 8/26 Special Item / Fire2 runtime 6502静的解析

解析日: 2026-07-19
対象: `magatu_skc/core/fire2_item_runtime.py`、`enemy_clear_key_open.py`、`panel_monster_stage_variant.py`、`stage_ext.py`、`saver.py`
一次資料: コメント付き原作ASM、日本版原作ROM、現行mapper66 workstate、正式ROM/RAM管理簿、実装履歴

## 結論

Special Item runtimeは、通常item IDと部屋別16cell位置表を組み合わせ、Firejar x2、Fairy x2、Philosopher's Stone、Crystal max fire rangeの4効果を実現する。PRG0には取得、描画、通常火球hitの326Bを置き、PRG1にはroom loader 140Bと64room×16B表を置く。

現行workstateでPRG0本体、4hook/patch、PRG1 loader helper、loader entry、range capがbuilderと一致することを確認した。全builderのbranch、stack、原作fallbackを静的追跡した。

確定問題・要仕様確認は5件である。

1. 扉削除面でPhilosopher's Stoneを取ると、存在しない扉cell `$00`を使ってgrid先頭`$0304`を`$46`へ破壊的変更する。
2. Crystal終了時の復元値はCHANGELOG記載の「取得前」ではなく、基礎item `$1B`の`+$04`適用後である。
3. Crystal実装と同時に通常range itemの成長上限も`$02`から`$0F`へ変更しているが、ユーザー向け変更記録にない。
4. 旧runtime 3世代と旧draw hook 3世代を受け入れる救済経路が残る。
5. PRG1予約長が現行Panel loaderではなくhard-coded snapshotから算出され、将来のloader変更で実書込長と予約長がずれ得る。

ROM/RAM配置は変更していない。修正もまだ行っていない。

## データ方式

UI上の追加item IDはroom gridへ直接保存しない。通常item IDへ変換し、そのcellだけをPRG1位置表へ登録する。

| UI ID | 保存base ID | 特殊効果 |
|---:|---:|---|
| `$34` | `$15` | Firejar x2 |
| `$35` | `$18` | Fairy x2 |
| `$36` | `$08` | Philosopher's Stone |
| `$3A` | `$1B` | Crystal max fire range |

PRG1 `0x9310-0x970F`は64room×16Bである。1byteは`byte_from_position()`形式のcell、`$FF`は未使用slotを表す。各roomで有効な特殊cellは最大16個で、保存時に位置をY/X順へsortする。

room loaderは現在room番号`$0428`から次のpointerを作る。

```text
low  = room << 4
high = $93 + (room >> 4)
```

これによりPRG1 CPU `$9300 + room*16`を指し、16Bを逆順でRAM `$0740-$074F`へコピーする。

## 取得hook `$C55B -> $C000`

原作`$C532`はDana中心cellをXへ求め、`LDA $0304,X / JSR $C55B`でitem取得判定へ入る。runtimeは`$C55B`先頭3Bを`JMP $C000`へ変更する。

入口契約はA=live grid cell値、X=cell indexである。runtimeはAをPHAし、Xをzero-page `$00`へ保存して16cell表をY=15..0で走査する。

### 一覧に無いcell

PLAでAを戻し、原作先頭の`CMP #$38`を再実行する。Aが`$38`以上ならRTS、それ未満なら`JMP $C55F`で残りの原作item range/dispatchへ戻る。Xは表走査で変更しない。

### 一覧にあるがbase IDが4種でないcell

同じ原作fallbackへ戻る。位置表だけが誤って残っても、別itemへ特殊効果を誤適用しない。

### 共通成功判定

4種とも最初に`JSR $C55F`でbase itemの取得処理を1回実行する。戻り後`$02==0`なら取得不成立として追加効果を出さない。`$02!=0`の時だけ特殊効果へ進む。

## Firejar x2

base `$15`の原作処理を1回実行した後、`JSR $C7A3`でもう1回同じstock追加処理を行う。`$C7A3`は`$00=#$55`を設定して`$C7D5`へ入り、fire stock bit-pairを追加する。

runtime内定数名`CPU_ADD_FIRE_JAR`はこの入口を指す。2回目はitem取得actionやSE全体を再実行せず、stock追加本体だけを呼ぶ。

## Fairy x2

base `$18`の原作処理は`$C7AA`で`$0454`を1増やし、Fairy spawnを予約する。追加分は即時に増やさず、`$0771=#$20`へ設定する。

7/26のEnemy Clear main-loop runtime先頭が毎フレーム`$0771`を減らし、0到達時だけ`JSR $C7AA`を呼ぶ。room load時はPRG1 loaderが`$0771=0`へclearするため、未発火の2体目は次roomへ持ち越さない。

単一counterなので、32フレーム以内にFairy x2を2個取得できる場合は後の取得がcounterを再設定し、前の2体目予約を1回分失う可能性がある。ただし原作item action時間との組合せを動的確認していないため、現時点では未確定問題とする。

## Crystal max fire range

原作の火球持続上限は16bit `$0432/$0433`である。発射後の経過`$042C/$042D`と比較され、上限を超えると火球が終了する。

Crystal branchはbase `$1B`の原作処理を実行した後、次を行う。

1. `$0433 >= $1F`ならbackupを更新しない。
2. それ未満なら`$0432/$0433`を`$0772/$0773`へbackupする。
3. `$0432/$0433 = $1F/$1F`へ設定する。

room load時、現在の`$0433 >= $1F`ならbackupを`$0432/$0433`へ戻す。従ってCrystal効果は次room loadまたは同room再loadまでである。Crystal中に再取得してもbackupを上書きしないため、二重取得で元値を失わない。

### 復元値の実際

base `$1B`は原作`$C7B5`へ入り、score加算後にrange lowへ`+$04`する。その後でruntimeがbackupする。

```text
取得直前        $0100
base $1B効果    $0104
backup          $0104
Crystal中       $1F1F
次room復元      $0104
```

したがって「取得前の成長値へ復元」ではなく、「通常item `$1B`の恒久`+$04`を受けた値へ復元」が実装事実である。

## 通常range cap変更

原作`$C7C5: CPX #$02`はrange highが2以上なら通常range itemの加算を止める。runtime writerはoperandを常に`#$0F`へ変更する。

これはCrystalの`$1F1F`直接書込みには不要である。Crystal中はhigh `$1F >= $0F`なので、通常range itemを取っても加算されない。一方、Crystal未取得時の通常range itemはhigh 2で止まらず15まで成長できる。

実装commitとCHANGELOGには「Crystalを一時Max化」「通常火球を敵hitで消す」は記録されているが、通常range成長上限の拡張は記載されていない。意図した追加仕様か、Crystal実装時の過剰patchかを確定する必要がある。

## 通常火球hit `$8153`

原作は敵との衝突時に`$05A8`を読み、値が`$10`未満ならその値を経過counter high `$042D`へ書く。現行10B hookは`JSR $C139`と7B NOPへ置き換える。

helperは次の動作である。

- `$05A8 >= $10`: Super Fireとして何もせずRTSし、貫通を維持する。
- `$05A8 < $10`: `$042D=#$F0`へ進めて、通常火球を寿命終了側へ送る。

helperは13Bで、A/flagsをclobberするが原作後続`$815D`はそれらを契約として使わない。JSR/RTSは1対1である。

## Philosopher's Stone

base `$08`の原作score処理が成功した後、X=`$10-$CF`の192 visible cellを走査する。各cellは次の順で選別する。

1. 現在door cell `$077C`なら通常走査から除外する。
2. live値が`$40`未満または`$F8`以上なら除外する。
3. `AND #$3F`でhidden/in-block/white flagを外す。
4. key `$06`、item `$08-$33`を表示対象にする。
5. `$10`は原作無効果slotなので除外する。

対象cellはbase IDを`$0304,X`へ戻し、`$9D53`で描画する。XはPHA/PLAで走査indexへ復元するため、複数cellを連続処理できる。

### 隠し扉

通常item走査後、`$077C`のdoor cellを別処理する。

- live値 `$07`（開扉）または`$10`（通行可能）なら何もしない。
- それ以外は見た目だけcell `$02`として描画する。
- live gridは`$46`へ戻し、扉そのものはhidden状態を維持する。

これによりStoneは隠し扉を可視化するが、取得だけで開けない。

## 描画hook `$9DE8`

描画入口はA=cell値、`$00`=描画cell indexである。runtimeはAをPHAし、RAM位置表を走査する。

- 一覧外またはbase不一致: PLA後、原作`ASL / ASL / TAY`を再現して`JMP $9DEB`。
- 一覧内4種: `$06/$07`を専用4B metatileへ向け、A=0から同じ原作処理へ入る。

専用metatileは次の連続16Bである。

| CPU | tile bytes | 用途 |
|---:|---|---|
| `$C129-$C12C` | `60 65 66 67` | Firejar x2 |
| `$C12D-$C130` | `9C 9D 9E 9F` | Fairy x2 |
| `$C131-$C134` | `70 71 72 73` | Philosopher's Stone |
| `$C135-$C138` | `6C 6D 6E 6F` | Crystal |

全経路でPHA/PLAは1対1である。custom branchのA=0はBEQを必ず成立させ、共有normal tailへ入るためのunconditional relative branchとして使う。

## PRG1 loader合成

mapper66 room loaderの最終chainは次である。

```text
PRG1 $8A00 slot先頭
  JMP $9270
    special item 16B copy
    Fairy2 counter clear
    Crystal range restore
    inline Panel/StageExt loader
      StageExt flags/key/fairy/door/seal copy
      transparent seal helperへJMP
```

Fire2 writerはPanel loader slot先頭3Bだけを`JMP $9270`へ変える。helper末尾へ現行`panel_monster_stage_variant.RUNTIME_LOADER`をinlineするため、StageExt/Panel処理を失わない。

## ROM/RAM配置

### PRG0

| file | CPU | size | 内容 |
|---:|---:|---:|---|
| `0x4010-0x40E1` | `$C000-$C0D1` | 210B | item取得runtime |
| `0x40E2-0x4138` | `$C0D2-$C128` | 87B | 描画runtime |
| `0x4139-0x4148` | `$C129-$C138` | 16B | 4 metatile |
| `0x4149-0x4155` | `$C139-$C145` | 13B | 通常火球hit helper |

本体は326Bで`$C000-$C145`を隙間なく使う。直後`$C146`から7/26 Enemy Clear Key Open runtimeが始まるため、単純な末尾拡張余地は0Bである。

### PRG1

| file | CPU | size | 内容 |
|---:|---:|---:|---|
| `0x9280-0x930B` | `$9270-$92FB` | 140B | loader helper |
| `0x9310-0x970F` | `$9300-$96FF` | 1024B | 64room位置表 |

間の`0x930C-0x930F` 4Bは正式管理簿上のgeneral reserveであり、本runtimeは使わない。

### RAM

| RAM | size | 用途 |
|---:|---:|---|
| `$0740-$074F` | 16B | 現在roomの特殊cell表 |
| `$0771` | 1B | Fairy x2 delay |
| `$0772-$0773` | 2B | Crystal取得前range backup |
| `$077C` | 1B | StageExtと共有するdoor cell |

正式ROM/RAM管理簿と現行`RESERVED_SPANS`は一致する。

## レジスタ・flag・stack

| 入口 | A | X | Y | stack/戻り |
|---|---|---|---|---|
| item `$C000` | live cellを受け、各effectでclobber | cell indexを保持、Stoneでscan | table/effectでclobber | 入口PHAは全経路で1回PLA |
| draw `$C0D2` | live cellを受け、原作metatile index計算へ渡す | custom branch以外保持 | table scan後metatile index | 入口PHAは全経路で1回PLA |
| fire hit `$C139` | fire typeを読みclobber | 保持 | 保持 | JSR/RTS 1対1 |
| Stone draw loop | item ID | scan Xをpush/popで復元 | `$9D53`でclobber可 | cellごとにPHA/PLA 1対1 |
| PRG1 loader | clobber | base loaderでclobber | copy loopでclobber | inline tail、local stack操作なし |

## 確定した問題・要仕様確認

### [P1] 扉削除面でgrid先頭を破壊する

扉削除は`fixed_door_pos.y < 0`で表現される。通常のoff-grid位置`(0,-1)`は`byte_from_position()`で`$00`になり、StageExt loaderが`$077C=$00`へコピーする。

Stoneのdoor処理は`$077C`の範囲を検査せず、必ず次を行う。

```text
LDX $077C          ; X=$00
LDA $0304,X        ; grid境界先頭
...
JSR $9D53          ; cell $00へ隠し扉を描画
LDA #$46
STA $0304,X        ; $0304を破壊
```

UI・保存時検証は「扉削除面にPhilosopher's Stoneを置く」組合せを禁止しない。従って正常操作で発生可能である。

正しいruntime側修正は、door cellがvisible範囲`$10-$CF`にある時だけdoor redrawを行うことである。ただし現行PRG0本体の直後に空きがない。境界guard追加には既存命令の圧縮、別空きへのhelper分離、または後続Enemy Clear runtime移動のいずれかが必要である。

### [P2] Crystal復元値と説明が一致しない

CHANGELOGと管理簿は「取得前の成長値へ復元」と説明するが、実装はbase `$1B`効果`+$04`の後でbackupする。これは静的に確定した差である。

- base item効果も恒久的に残す仕様なら、文書を「通常効果適用後の値へ復元」へ訂正する。
- 本当に取得直前へ戻す仕様なら、base処理より前にbackupするか、復元値から通常加算分を除く必要がある。

### [P2] 通常range成長上限も変更する

writerはSpecial itemの有無に関係なく`$C7C6`を`$02→$0F`へ変える。runtime常設方針として書込み自体は正しいが、効果はCrystal限定でなく全通常range itemへ及ぶ。

この全体変更はv0.9.32のCHANGELOGに記載されていない。意図的仕様ならユーザー向け説明が不足し、意図していないなら原作`#$02`へ戻すべき過剰patchである。

### [P2] 旧runtime救済経路が残る

現行入力以外に次を正常として受け入れる。

| 対象 | 内容 |
|---|---|
| `OLD_RUNTIME` | 初期Fire/Fairy x2時代 |
| `PRE_PHILOSOPHER_STONE_RUNTIME` | Stone追加前 |
| `PRE_CRYSTAL_RUNTIME` | Crystal追加前 |
| `OLD_DRAW_HOOK` | 旧draw入口 |
| `PRE_PHILOSOPHER_STONE_DRAW_HOOK` | Stone前draw入口 |
| `PRE_CRYSTAL_DRAW_HOOK` | Crystal前draw入口 |

これらは途中ROMを現行へ自動置換する救済であり、正式版前の救済禁止ルールに反する。現行ROM成立には不要である。

### [P3] PRG1予約長がhard-coded Panel snapshotに依存する

実際のhelperは`_build_loader_helper(panel_monster_stage_variant.RUNTIME_LOADER)`で作る。一方、`PRG1_RESERVED_SPANS`の長さはソース内へ複製した古いPanel loader byte literalを渡して算出する。

現在は両方140Bで一致する。しかしPanel loaderの命令数が変わってもsnapshotを更新し忘れると、実際のhelperが予約範囲を越えるか、不要領域を使用中として残す。ROM整合性検査は予約値同士の一致を見るため、この「実書込blob対予約長」のずれを直接検出しない。

## 正常と確認した事項

- UI pseudo IDを通常base ID+位置表へ分離する方式
- room番号から64×16B表pointerを作る計算
- 取得・描画両hookの位置表scanと原作fallback
- 4特殊効果のbase item成功guard
- Firejar x2のstock追加2回
- Fairy x2の遅延2体目予約とroom load clear
- Crystal二重取得時のbackup維持
- 通常火球とSuper Fireのhit分岐
- Stoneの192 visible cell走査、door cell除外、X保存
- 開扉後に隠し扉を閉じた表示へ戻さないguard
- draw runtime全経路のPHA/PLA収支
- PRG1 loaderがPanel/StageExt処理をinlineして維持すること
- 現行workstateの本体、hook、loader、range capがbuilderと一致
- 正式ROM/RAM管理簿と現行予約の一致

## 未実施

- ROMを新規生成していない。
- Mesenで4itemの通常/隠し/各block内取得、複数Fairy x2、Crystal取得・死亡・次面、扉削除面Stoneを新規動的試験していない。
- 問題5件は記録のみで修正していない。
