# 6/26 鍵持ち敵・妖精持ち敵 runtime 6502静的解析

解析日: 2026-07-18
対象: `magatu_skc/core/key_enemy_runtime.py`、`stage_ext.py`、`saver.py`
一次資料: コメント付き原作ASM、日本版原作ROM、現行mapper66 workstate、正式ROM/RAM管理簿

## 結論

このruntimeは、StageExtに保存した「初期配置敵の順番」をroom load時の実runtime slotへ結び付ける。鍵持ち敵は通常撃破・落下死・Red Burn消滅から鍵tileを生成し、妖精持ち敵は原作の落下死Fairy置換を利用する。

302B、16 code chunkを全て命令境界まで分解した。初期配置番号からslotへのbinding、status bit6、通常撃破、落下死、Red Burn、鍵tile pickup、扉発光位置の各経路を追跡し、現行workstateの本体・8hookは全てbuilderと一致した。確定した実動作バグは見つからなかった。

保守上の問題は2件である。

1. `apply()`は保存pipelineの特定順序に依存し、完成ROMへ単独再適用すると現行PRG1統合loaderを拒否する。
2. `RAM_RESERVED_SPANS`がソース内で同じ内容に2回定義される。

## StageExtとRAM

StageExtは選択値をzero-based initial enemy indexとして保持する。PRG1 room loaderは次へコピーする。

| RAM | 意味 |
|---:|---|
| `$072B` | 鍵持ちinitial index |
| `$077E` | 妖精持ちinitial index |

room内のinitial enemy loader `$95C5`を通る回数を`$0729`で数える。各回の`$B2EA`が返したruntime slot Xを、index一致時に次へ保存する。

| RAM | 意味 |
|---:|---|
| `$072A` | 鍵持ちruntime slot |
| `$077F` | 妖精持ちruntime slot |

その他の専用状態は`$0723-$0728`である。生成key tile+1、active flag、pickup tile、zero-page pointer退避、生成tileを保持する。専用RAM予約は`$0723-$072B` 9Bと`$077E-$077F` 2B、合計11Bで、正式RAM管理簿と一致する。

## 初期slot binding `$E0FE-$E117`

hook元の原作`JSR $B2EA`を最初に再実行する。現在initial countと`$072B/$077E`を比較し、一致した側へXを保存してcountを1増やす。Carryは`$B2EA`のまま返る。比較、STX、INCはいずれもCarryを変更しないため、hook元がCarryを参照しても原作結果を維持する。

status hookは通常A=`$80`を返し、Xが鍵または妖精target slotならA=`$C0`を返す。bit6は原作の落下死Fairy置換経路を有効にする。両target以外の敵は原作status `$80`のままである。

## 通常撃破と鍵生成

Dana火球の敵撃破hook `$C267`は、まず原作`JSR $9D1C`を実行する。その時の対象slot `$02`が`$072A`と一致すれば、7個の連続chunkで次を行う。

1. `$B14A`で対象main-slot pointerを取得。
2. 中央座標Y+8、X+8をblock座標へ変換。
3. grid index+1を`$0723/$0724`へ保存。
4. gridへkey cell `$06`を書き、`$9D53`で描画更新。
5. `$072A=$FF`として同じtargetの再発火を止める。
6. PHAした元slot `$02`を復元してRTS。

対象外は原作`$9D1C`だけを実行してRTSする。対象経路のPHA/PLAは1対1で、7chunk間のJMPはstackを増減しない。

## key pickupと扉発光

item tile read hookは現在grid index Xを`$0725`へ記録して原作`LDA $0304,X`を返す。

key handlerは`$0723`が0なら原作処理へ戻る。active keyがある場合は生成tile indexとpickup indexを比較する。

- 不一致: 原作item pointer処理を呼び、drop stateをclearして原作継続へ。
- 一致: tileを通常key処理用状態へ更新し、drop activeをclearして原作継続へ。

処理中に`$30/$31`を`$0726/$0727`へ保存し、全終了経路で復元する。door-light hookはY=6かつdrop active時だけ、生成key位置を`$04`へ返してactive flagをclearする。それ以外は原作`LDA ($30),Y / STA $04`を再現する。

## 落下死

原作Fairy置換入口 `$AF06`をJMP hookする。`$E211`はtarget key slotからsub-slot pointer table low byteを読み、現在pointer `$2C` lowと比較する。17 sub-slotのlow byteは全て一意なので、同一pageを含む現行表ではslot同定が成立する。

- 鍵target: 通常撃破drop本体`$E130`を呼び、原作despawn `$B376`へ。
- それ以外: 原作Fairy template4Bを書き、RTS。

妖精targetはstatus bit6によってこの入口へ到達し、鍵target比較に一致しないため原作Fairy置換を受ける。鍵targetもbit6で入口へ到達するが、Fairyではなく鍵へ分岐する。

Red Burn `$80`の消滅出口 `$A5CB`もhookされる。鍵target sentinelがnegativeなら即原作despawnへ戻す。一致すれば通常撃破drop本体を呼んでからdespawnする。

## 設定不可IDとの関係

runtimeは敵typeではなくinitial index/runtime slotだけを見る。設定不可ID `$81/$83/$9D`の制限はUI・enemy slot rules側の責務であり、6502側にはtype blacklistがない。

従って、不正な保存dataや別writerがこれらをtargetへ設定した場合、runtime自身は拒否しない。現行UIが禁止する前提では正常だが、runtime単体の防御ではない。特に撃破不能`$9D`は鍵生成経路へ到達せず、stage進行不能になり得る。

## code・配置

| CPU | size | 内容 |
|---:|---:|---|
| `$E0FE-$E117` | 26B | initial slot binder |
| `$E118-$E12C` | 21B | status writer/helper |
| `$E12D-$E184` | 88B | 通常撃破drop 7chunk |
| `$E185-$E19D` | 25B | door light |
| `$E19E-$E1A4` | 7B | pickup tile recorder |
| `$E1A5-$E1FA` | 86B | dropped-key handler |
| `$E1FB-$E210` | 22B | fall-death dispatcher |
| `$E211-$E21B` | 11B | fall slot compare |
| `$E21C-$E22B` | 16B | Red Burn key handler |

全16 chunk、302Bを命令境界まで全消費した。runtimeは`$E22C-$E233`の8Bを占有せず、空きとして残す。

## 確定した問題・保守上の問題

### [P2] `apply()`が保存順序へ強く依存する

`PRG1_STAGE_EXT_COPY`は`stage_ext.RUNTIME_LOADER`をimport時に固定する。`key_enemy_runtime.apply()`は`0x8A10`先頭をこのbyte列、空の`00/EA`、または同一key codeとしてしか受け入れない。

現行完成workstateの`0x8A10`はFire2+Panel統合loaderなので、`key_enemy_runtime.apply()`を単独で設定無変更再適用すると`cave overlap`例外になる。実際にメモリ上のコピーで再現した。

通常save pipelineでは、直前の`stage_ext.apply_runtime_loader()`が一度basic StageExt loaderへ戻し、Key writer後に後続writerが最終統合loaderへ更新するため成功する。従って現行保存が直ちに壊れる確定バグではないが、module API単体ではidempotentでなく、save順序変更・個別検査・将来統合で破損しやすい。

### [P3] `RAM_RESERVED_SPANS`を同じ内容で二重定義する

module先頭で`RAM_RESERVED_SPANS`代入が完全に同じ2回連続している。後者が前者を上書きするだけなので実行時の予約値は正しい。しかし片方だけ将来更新すると見た目と実値が食い違う明白な保守欠陥である。

## 正常と確認した事項

- initial indexからruntime slotへのkey/fairy独立binding
- targetだけstatus bit6を追加し、他敵は`$80`
- 通常撃破のslot比較、座標変換、grid key生成、target無効化
- 対象外撃破の原作処理維持
- 落下死でkey targetとFairy targetを分離
- Red Burn消滅時のunset sentinel guard
- key handler全経路の`$30/$31`復元
- 16 chunk全302Bの命令境界とstack収支
- 現行workstateの本体全chunkと8hookがbuilderに一致

## 未実施

- ROMを新規生成していない。
- Mesenで通常撃破、落下死、Red Burn、同時key/fairy、slot満杯を新規動的試験していない。
- save pipeline全体は今回実行していない。単独`apply()`の失敗だけをメモリ上で確認した。
- 問題2件は記録のみで修正していない。
