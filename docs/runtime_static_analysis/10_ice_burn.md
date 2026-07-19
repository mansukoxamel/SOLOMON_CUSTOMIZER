# 10/26 Ice Flame / Ice Burn runtime 6502静的解析

解析日: 2026-07-19
対象: `magatu_skc/core/ice_flame_runtime.py`、`new_enemy_runtime.py`、原作Flame AI
一次資料: コメント付き原作ASM、日本版原作ROM、現行mapper66 workstate、正式ROM管理簿、ID配置監査資料

## 結論

Ice Burnは敵ID `$82`を利用し、原作Flame AIとsetupをそのまま借り、生成時status/behaviorと固定frameだけを専用runtimeで上書きする敵である。専用本体は29Bのinitと1Bのanimation停止だけで、file `0x6085-0x60A2`、CPU `$E075-$E092`に置かれる。

現行workstateの30Bがbuilderと一致することを確認した。原作AI/setupへの合流、initの呼出順、main-slot field、stack、固定frameとanimation停止を静的追跡し、6502本体の確定ロジックバグは見つからなかった。

周辺validationの問題候補は1件である。standard ROM保存用`levels_need_runtime()`がdirect配置だけを調べ、Demon Mirrorのenemy set内にある`$82`を検出しない。通常の日本版入力はmapper66へ拡張されるため主経路には影響しないが、検出関数の契約としては不完全である。

ROM/RAM配置は変更していない。修正も行っていない。

## ID `$82`を使う理由

原作のFlame/Burn AI groupはID `$80-$83`であり、AI dispatch tableは4IDすべてを`$A5A0`へ送る。setup group計算も次の通りである。

```text
X = $82
TXA / LSR       -> $41
AND #$FE        -> $40
```

従って`$82`は追加のAI stubやsetup stubなしで、原作Flame AIと原作Flame metadata group `$40`へ自然に入る。この性質を使い、共通入口センターではAI分類を行わず、setupでも`$82`をstock計算へ戻す。

## 保存時の4経路

| 機能 | 経路 | Ice Burn処理 |
|---|---|---|
| AI | `$A1C3 -> $BBE2 -> $BD55 -> $A329 -> $A5A0` | 原作Flame AI |
| setup | `$8ACB -> $BC32` | 原作計算group `$40` |
| init | `$A2F2 -> $BC84 -> $BD73 -> $9D1C -> $E075` | 原作共通init後に専用上書き |
| animation | `$8676 -> $BCD0 -> $E092` | `RTS`で固定frameを維持 |

旧定数`HOOK_*`はIce Burn単独入口を使っていた時期の値である。現行writerは4hookを共通入口センターへ向け、`ice_flame_runtime.apply()`自身も共通writerを呼ぶcompatibility wrapperである。

## 原作Flame AI

原作`$A329`は`enemy ID - $14`からAI tableを引く。`$82`はFlame group indexへ入り、`$A5A0`を呼ぶ。

`$A5A0`は`$B201`で共通状態を更新した後、main-slot behavior bitsからState 0-6をdispatchする。Ice Burnの初期behaviorは`$14`なのでState 5から始まる。

State 5は`$A61E`をX=`$10`で呼び、main-slot status bit3が立つまではそのままRTSする。bit3が立つとbit3をclearし、sub-slot timerを0へ戻してbehavior `$10`、State 4へ移る。State 4はX=`$06`で同じ共通処理を呼び、210frame後にbehavior `$14`へ戻る。

専用AIはないため、原作Flameのcollision、足場/衝撃応答、state timer、despawn処理を変更しない。

## setup

原作`$8AC0`はentity type Xから`$0E=(X >> 1) & $FE`を作り、`$D9D3,Y`のmetadata pointerを読む。`$82`では`$0E=$40`となる。

共通setup入口は`CMP #$83 / BCC stock`で`$82`をstock側へ送り、最後に原作と同じ`LDY $0E / LDA $D9D3,Y / RTS`を実行する。従って見た目、速度、初期fieldの基礎は原作Flame groupである。

## init `$E075`

共通init入口はAをPHAし、Ghost拡張fallbackでPLAして原作`$9D1C`を先に実行する。`$9D1C`は次を初期化する。

- main-slot `[0]` = zero-page `$04`のstatus
- main-slot `[1]` = zero-page `$05`のtype `$82`
- main-slot `[2]` = `$FF`
- main-slot `[3]` = 入力A。ただしA bit7 setなら既存値を維持

その後type `$82`を再確認し、Ice Burn initへJMPする。専用initは次のfieldを上書きする。

| main offset | 値 | 意味 |
|---:|---:|---|
| `[0]` | `$E0` | active、接触あり、Dana火球で撃破可能 |
| `[3]` | `$14` | Flame State 5 |
| `[17]` | `$D6` | sprite 1 tile |
| `[18]` | `$D4` | sprite 2 tile |
| `[19]` | `$5A` | 2sprite分のpalette/flip属性 |

`$E0`はentity main loopのactive条件`>= $C0`とAI dispatch条件`>= $E0`を両方満たす。Blue Burn `$81/$83`と異なり、Ice BurnはDana火球で倒せる設計である。

initはYを0、3、17、18、19へ変更し、Aを各定数でclobberする。呼出元は戻り後にA/Yを契約として使わない。Xとzero-page pointer `$00/$01`は変更しない。専用init内にstack操作はなく、共通入口側のPHA/PLAが1対1である。

## 固定frameとanimation停止

原作OAM writerはmain-slot `[17]`/`[18]`を2spriteのtileへ、`[19]`を2sprite分の属性へ展開する。専用initの`D6 D4 5A`は原作ASMのframe dataにも存在する組合せである。

通常の`$8789` animation updaterを毎frame通すと、type/stateに応じてこの3fieldが別frameへ更新される。共通animation入口はtype `$82`を検出して`$E092`へJMPし、専用本体の`RTS`だけを実行する。従ってinitで設定した固定frameを維持する。

撃破等でentity typeが別IDへ変われば、次frameは`$82`分岐に入らず、その新typeの通常animationへ戻る。animation停止はslotそのものではなくtype `$82`だけに限定される。

## ROM/RAM配置

| file | CPU | size | 内容 |
|---:|---:|---:|---|
| `0x6085-0x60A1` | `$E075-$E091` | 29B | init/status/fixed frame |
| `0x60A2` | `$E092` | 1B | animation `RTS` |
| `0x60A3-0x60CB` | `$E093-$E0BB` | 41B | 現行runtime予約なし |

専用runtimeは30Bである。新規グローバルRAM、専用sub-slot、設定tableは使わない。原作main-slot 20Bと対応sub-slot 8Bだけを使う。

## レジスタ・flag・stack

| 経路 | A | X | Y | stack/flag |
|---|---|---|---|---|
| AI fallback | `ID-$14`を原作へ渡す | entity index | 原作AIでclobber | 入口PHA/PLA 1対1 |
| setup fallback | metadata pointer lowを返す | type `$82` | `$0E=$40` | stack操作なし |
| common init | 原作入力後clobber | 原作値維持 | `$9D1C`でclobber | 共通入口PHA/PLA 1対1 |
| Ice init | `$5A`で終了 | 維持 | `$13`で終了 | stack操作なし、RTS |
| animation | type読出後clobber | entity index維持 | type読出offset | JMP先で即RTS |

専用initの最終flagはLDA/STA由来だが、呼出元`$A2F5`は直後にPLA/LSRを行うため依存しない。animationのRTS時flagもentity loop後続のDECで上書きされる。

## 成立している点

- `$82`は原作Flame AI table範囲内で、専用AI分類を必要としない。
- `$82`のsetup group `$40`は原作計算だけで得られる。
- 原作共通initを実行した後に必要fieldだけを上書きし、type/slot基礎初期化を失わない。
- status `$E0`、behavior `$14`、固定frame、animation停止が互いに整合する。
- stack操作とJSR/RTSは全経路で均衡する。
- 現行workstateの30BはPython定義と一致する。

## 問題候補

### [P3] Demon Mirror内の`$82`をstandard ROM検出が見ない

`ice_flame_runtime.levels_need_runtime()`は各levelの`enemies`だけを走査する。Demon Mirrorの`enemy_codes`に`$82`がある場合はFalseのままである。

この関数は非expanded ROM保存時に「新敵IDはmapper66専用」と拒否するための集合判定から呼ばれる。通常編集対象の日本版ROMは読み込み時にmapper66へ拡張され、expanded保存ではruntimeが無条件配置されるため、通常主経路でruntimeが欠落する問題ではない。ただし、関数単体の「levelがIce Burn runtimeを必要とするか」という判定としては漏れである。

修正はmirror enemy codeの走査追加だけで、ROM/RAM配置、空き、台帳に影響しない。9/26共通入口センターで他の追加敵にも同じ問題があるため、個別関数ではなく共通validationとしてまとめて直す方が一貫する。

## 未検証点

- Mesenで足場変化、Dana接触、通常火球撃破、死亡変換まで連続した動的traceは採取していない。
- `D6 D4 5A`の実機画面とピッカー画像のpixel単位比較は行っていない。
- standard ROM保存は通常サポート経路ではないため、Demon Mirror検出漏れの到達可能なUI操作列は確認していない。

## 修正時の検証条件

- direct配置とDemon Mirror生成の両方で`$82`を検出すること。
- `$82`のAIが原作`$A5A0`、setup groupが`$40`であること。
- init後に`[0]=$E0`、`[1]=$82`、`[3]=$14`、`[17..19]=D6 D4 5A`となること。
- `$80/$81/$83`の原作Flame/Burnを変更しないこと。
- 死亡等でtypeが変わった後は固定animation分岐から外れること。

