# 13/26 Chaos Dragon `$9E` runtime 6502静的解析

解析日: 2026-07-19
対象: `magatu_skc/core/chaos_dragon9e_runtime.py`、`new_enemy_runtime.py`、原作Dragon AI `$A64A`
一次資料: コメント付き原作ASM、日本版原作ROM、現行mapper66保存ROM、正式ROM管理簿、CHANGELOG、ID配置監査資料

## 結論

Chaos Dragonは原作Dragonの見た目とAIを使い、speed metadataだけを別groupへ接続して落下・貫通・不規則な火吹き挙動を作る敵である。専用本体はsetup 10B、init 16B、AI 3Bの計29Bで、file `0x6EB4-0x6ED0`、CPU `$EEA4-$EEC0`に置かれる。専用animation本体はない。

builderの29Bは既存mapper66保存ROM 3本の同範囲と一致した。新敵共通入口、原作property前段、entity setup、共通物理、Dragon state dispatch、火炎child、通常撃破・鍵dropを追跡し、6502本体の確定ロジックバグは見つからなかった。現行29Bを固定する単体テストを追加した。

確認事項は次の3件である。

1. type `$9E`は原作property table範囲外`$A32F=$A3`を読む。専用initで現行副作用を打ち消すが、表外byteへの構造的依存は残る。
2. setupの「Y速度を書かない」とinitの「初期Y速度0」は実際の最初のsetup後状態を表していなかった。state 5 setupは同frameにY速度`$80`を書き直すため、コードコメントと監査資料を現物に合わせて訂正した。
3. standard ROM保存用`levels_need_runtime()`のDemon Mirror内`$9E`検出漏れは、9/26の共通入口センター修正で解消済みである。

ROM/RAM配置と6502バイト列は変更していない。

## 入口構成

| 機能 | 共通入口 | 専用処理 |
|---|---:|---|
| AI | `$BBE2` | `$EEBE`の3B JMPから原作`$A64A`へ入る |
| setup | `$BC32` | `$EEA4`でspeed group 0、animation group `$34`を設定する |
| init | `$BC84` | `$EEAE`でstatus、Y速度、behaviorを設定する |
| animation | `$BCD0` | 専用分類せず原作`$8789`へfallbackする |

AI専用入口の正確な範囲は`$EEBE-$EEC0`である。原作Dragon AIへtail JMPするため、原作AIのRTSが共通AI hookの呼出元へ直接戻る。

## 原作property読出とinit `$EEAE`

原作敵初期化`$A2B8`は次を計算する。

```text
Y = (type - $18) >> 2
property = $A30E,Y
```

`$9E`ではY=`$21`となり、正式property table外の`$A32F`を読む。日本版原作ROMのbyteは`$A3`である。原作前段はこれをpropertyとして解釈し、main-slot `[5]`へY速度`$80`を書き、behavior候補Xへ`$18`をORする。

共通init入口は原作前段が作ったbehavior候補AをPHAし、type `$9E`を分類する。専用initは次を行う。

1. PLAで共通入口の保存Aを捨てる。
2. zero-page `$04=#$C0`にする。
3. main-slot `[5]=#$00`にしてproperty由来Y速度を消す。
4. A=`$14`として原作writer `$9D1C`へJMPする。

`$05`は原作`$A2BF`で既にtype `$9E`が入っており、専用initは変更しない。writerはmain `[0]=$C0`、`[1]=$9E`、`[2]=$FF`、`[3]=$14`を書く。

専用initはJMPでwriterへ入り、writerのRTSが元の`JSR $BC84`のreturn addressを消費する。共通入口のPHAは専用initのPLAと対になり、その下にある原作property stack値`$0A`は`$A2F5`がPLAする。`$0A >> 1`のCarryはclearなので、原作後段はsub-slot `[6]/[7]`へ追加方向を書かない。

## setup `$EEA4`の二重group

setupは次の2種類のgroupを意図的に分離する。

- zero-page `$0E=#$34`: 原作Dragon右 `$68`のanimation metadata group。
- Y=`$00`: speed metadata pointerをgroup 0から読む。

custom setup hookは`$8ACB`の`LDA $D9D3,Y`を置き換える。専用RTS後、原作は`$8ACE`から続行し、返したlow byteとY=0で`$D9D4,Y`のhigh byteを組み合わせる。その後speed更新を終えると、`$8B03`がzero-page `$0E=$34`を読み、Dragon animation pointerを構築する。

従ってspeedはgroup 0、見た目はDragon group `$34`という組合せが成立する。

## 実際の速度値

group 0のspeed pointerは日本版原作ROMで`$DA15`である。Chaos Dragonが使うbehaviorに対する実値は次の通りである。

| behavior | state | speed entry | Y velocity | X velocity |
|---:|---:|---:|---:|---:|
| `$0C-$0F` | 3・火吹き | `$02` | `$C3` | `$00` |
| `$14` | 5・右主行動 | `$06` | `$80` | `$18` |
| `$15` | 5・左主行動 | `$07` | `$80` | `$68` |
| `$16-$17` | 5・中間phase | `$03` | `$80` | `$00` |

entity loopはtype/state変化を検出すると、共通物理`$8689`より先にsetup `$8AC0`を呼ぶ。従って生成時に専用initが`[5]=0`としても、同じ最初の処理frameでstate 5 metadataが`[5]=$80`へ書き直す。

`$80`は共通物理で上向き約4px/frameから始まり、重力更新される。state 3では`$C3`が設定される。これは「Dragon AIを崩した落下・貫通・不規則な火吹き」を固定仕様とするCHANGELOGに合う。Y速度を止めるruntimeではない。

## AI tail JMP `$EEBE`

専用AIは`JMP $A64A`の3Bだけである。`$A64A`はmain behavior `[3]`を2bit右shiftしてstate indexを作り、7-entry tableへdispatchする。

| state | handler | Chaos初期stateからの役割 |
|---:|---:|---|
| 0 | `$A41C` | no-op、通常遷移では未到達 |
| 1 | `$AEC8` | 寿命/fairy/despawn系、通常遷移では未到達 |
| 2 | `$A65E` | Dragon固有遷移、通常遷移では未到達 |
| 3 | `$B075` | Saramandor共有の短射程火炎sequence |
| 4 | `$A41C` | no-op、通常遷移では未到達 |
| 5 | `$A669` | 主行動、壁・Dana距離・火吹き開始判定 |
| 6 | `$B04F` | 共有遷移、通常遷移では未到達 |

専用initはbehavior `$14`、すなわちstate 5・右向きで開始する。

## state 5主行動

`$A669`はDanaとの距離、進行方向の壁、前方cell、現在X velocityを調べる。

- Danaが近い場合はdirectionを整え、空きslotを確保できればstate 3へ移る。
- 壁や前方block条件ではdirection bit0を反転する。
- 進行可能時はbehaviorを`$14-$17`のstate 5範囲内で更新し、速度metadataを切り替える。
- state indexは5のままで、state 1へ直接落ちるbranchはない。

`$14/$15`は左右移動、`$16/$17`はX速度0の中間phaseになる。group 0の速度値と原作Dragonの壁判定を組み合わせるため、通常Dragonより大きいX速度と頻繁な停止・反転が生じる。

## state 3火炎sequence

state 5の攻撃開始は空きmain/sub slotを2つ確保し、親sub-slot `[6]/[7]`へchild slot indexを保存してbehavior `$0C/$0D`へ移す。

state 3はSaramandor `$B075`を共有する。

1. sub-slot `[1]`が`$18`まで待つ。
2. type `$04`、status `$C6`の短射程Flame childを親の左右へ生成する。
3. `$20-$2B`を維持する。
4. `$2C`以降でchild status bitを切り替える。
5. `$34`でchildをdespawnし、親behaviorを`$14/$15`へ戻す。

火炎childはAI `$A64A`へ入らず、原作type `$04`の短命ハザードとして動く。親type `$9E`の下位bitはchild生成方向に使われず、親behavior bit0が使われる。

## 鍵持ち敵としての静的判定

現行UI/保存検証はChaos Dragon `$9E`を鍵持ち敵に指定可能としている。

専用initから到達する通常state graphはstate 5とstate 3、および各state内の方向/phase違いである。state 1の`$AF03: JMP $B376`自然despawnへ入る遷移は、この初期stateからの命令列には見つからない。

ダーナ火球で撃破された場合は原作`$C267`の敵撃破hookを通る。Key Enemy runtimeは選択slot `$072A`と現在slotを照合し、一致時に通常dropを鍵生成へ置き換える。従って静的に確認できる通常撃破経路では鍵が出る。

Chaos Dragonを鍵持ち可とする現行設定に、確定した静的矛盾はない。ただし画面外座標wrap、外部status変更、足場破壊を含む長時間動的traceは未実施なので、実機最終確認は残る。

## animation

専用animation分類はない。setupがzero-page `$0E=$34`として原作Dragon右groupのanimation pointerをmain `[15]/[16]`へ設定し、その後は原作`$8789`がmain `[17-$19]`を更新する。

type `$9E`の下位2bitは2であるが、animation pointerの方向選択が必要な場合はsetup時のtype参照`AND #$03`にも影響する。現行setupはgroup `$34`のentryとtype `$9E`の組合せで保存ROMに実装済みで、CHANGELOG上の見た目確認済み仕様である。IDを変更する場合は下位bitを含めて再確認が必要である。

## ROM/RAM配置

| file | CPU | size | 内容 |
|---:|---:|---:|---|
| `0x6EB4-0x6EBD` | `$EEA4-$EEAD` | 10B | setup |
| `0x6EBE-0x6ECD` | `$EEAE-$EEBD` | 16B | init |
| `0x6ECE-0x6ED0` | `$EEBE-$EEC0` | 3B | AI tail JMP |

直前`0x6E19-0x6EB3`は現行runtime予約なし155B、直後`0x6ED1`からNeul A/B runtimeが始まる。本体直後の空きは0Bである。専用RAMは確保せず、原作Dragonのmain/sub-slot fieldだけを使う。

## レジスタ・flag・stack

| 処理 | A | X | Y | stack/戻り |
|---|---|---|---|---|
| setup | speed pointer lowを返す | 維持 | 0 | stack操作なし、RTS |
| init | `$14`でwriterへ入る | 原作値を維持 | `[5]` | 共通入口PHAをPLA、JMP先RTSで元へ戻る |
| AI entry | 原作Dragon AIでclobber | 原作AIでclobber | 原作AIでclobber | tail JMP、原作RTS |
| state 3 child生成 | behavior/statusでclobber | slot indexでclobber | field index | JSR/RTS均衡 |
| animation | 原作`$8789`でclobber | entity indexを維持 | frame field | 原作RTS |

setupはY=0を返すことが必須である。原作`$8ACE`がhigh byteを`$D9D4,Y`から読むため、Yを別値にするとlow/highのpointer pairが崩れる。

## 成立している点

- `$9E`はAI/setup/initで専用分類され、animationは意図的に原作へfallbackする。
- speed group 0とanimation group `$34`を分離するsetupのpointer構築は成立する。
- property由来Y速度、status、behaviorは専用initで一旦再構築される。
- state 5から原作Dragon主行動、state 3からSaramandor共有火炎へ正しく接続する。
- child slot確保失敗時はstate 5を維持し、不正pointerを書かない。
- 通常state graphから自然despawn state 1への遷移は見つからない。
- ダーナ火球撃破はKey Enemy runtimeのhookを通る。
- 現行29B、`RESERVED_SPANS`、正式ROM管理簿、既存保存ROM 3本の本体byteが一致する。

## 技術的負債・問題候補

### [P2] property table範囲外byte `$A3`への依存

type `$9E`は原作property tableの外を読む。現行`$A3`が残すstatus、behavior、Y velocityは専用initで上書きし、property stack後段もsub-slotを書かないため、現在のROMでは成立する。

ただし`$A32F`、原作property前段、共通init hook位置が変わると副作用が変わる。追加敵propertyを正式分類する共通修正は`$A2CC`周辺のSpark/Panelを含むため、Chaos Dragon局所修正として扱わない。

### [解消] setup/initコメントと実速度の不一致

`chaos_dragon9e_runtime.py`はsetupを「speed metadata with no vertical write」、initを「no initial vertical movement」と説明する。しかしgroup 0のstate 5 entryはY速度`$80`を書き、最初の共通物理前に有効になる。

実挙動はCHANGELOGの「落下・貫通・不規則な火吹き」と一致する。コードコメントとID配置監査資料を実際の速度表に合わせて訂正した。6502バイト列、ROM/RAM、空き、台帳には影響しない。

### [解消] Demon Mirror内の`$9E`をstandard ROM検出が見ない

9/26の共通入口センター修正で、Demon Mirrorの`enemy_codes`も追加敵全familyについて走査するようになった。`$9E`をmirror内だけに設定したlevelも`new_enemy_runtime.levels_need_runtime()`で検出される単体テストがある。

## 未検証点

- Mesenで`init [5]=0 -> setup [5]=$80 -> physics`の同frame traceは採取していない。
- state 5と3を長時間追跡し、外部要因を含めてstate 1へ入らないことは動的確認していない。
- Chaos Dragonを鍵持ちにした火球撃破と鍵出現は実機未確認である。
- 画面外へ出た場合の座標wrap、壁貫通、足場破壊後の全挙動は未確認である。
- type `$9E`下位bitによるDragon animationの全frame比較は行っていない。

## 修正時の検証条件

- 挙動を変更しない文書修正では、group 0の`$DA15`と`$DB99/$DB9A`の実値を根拠にすること。
- speed groupまたは初期Y速度を変える場合、現在の「落下・貫通・不規則」仕様を変更する作業だと明示すること。
- state 5/3のbehavior、X/Y velocity、child slot `[6]/[7]`をframe traceすること。
- 鍵持ち時に火球撃破が`$C267`を通り、選択slot `$072A`一致で鍵が出ること。
- 原作Dragon `$68-$6F`とSaramandor `$5C-$67`の共有AIへ副作用を出さないこと。
