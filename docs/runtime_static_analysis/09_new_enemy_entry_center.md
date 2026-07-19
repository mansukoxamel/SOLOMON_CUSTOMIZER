# 9/26 新敵ID共通入口センター 6502静的解析

解析日: 2026-07-19
対象: `magatu_skc/core/new_enemy_runtime.py`、各追加敵runtime、`saver.py`、ピッカー/キャンバス描画
一次資料: コメント付き原作ASM、日本版原作ROM、現行mapper66 workstate、正式ROM管理簿

## 結論


AI/setup/initのstackと原作fallbackは静的に成立している。Ice Burn `$82`がAIでは原作Flameへ自然に流れ、setup/init/animationだけ専用補正を受ける構成も意図通りである。

確定問題は3件である。

1. Enhanced Saramandor C `$66/$67`だけanimation属性のSPR#2補正から抜け、ピッカー/キャンバスと実機表示が一致しない。
2. 移動前の旧入口センターを検出すると、現行書込先の所有確認を全面的に飛ばし、未確認の42Bを含む領域まで上書きする救済経路が残る。
3. 旧animation本体の短いprefixだけで許可するため、その後ろの最大115Bが何であっても現行129Bで上書きできる。


## 原作hookと入口契約

| 原作hook | 原作処理 | 現行入口 | size |
|---:|---|---:|---:|
| `$A1C3` | `JSR $A329` AI dispatch | `$BBE2` | 80B |
| `$8ACB` | `LDA $D9D3,Y` setup metadata | `$BC32` | 82B |
| `$A2F2` | `JSR $9D1C` init/status | `$BC84` | 76B |
| `$8676` | `JSR $8789` animation/OAM | `$BCD0` | 133B |

Enhanced Ghost `$B0-$BB`用の共通拡張56Bが`$BD55-$BD8C`に続く。4入口同士とGhost拡張の間に空きやNOP paddingはない。

## 対象ID

| ID | runtime |
|---:|---|
| `$82` | Ice Burn |
| `$84-$87` | Enhanced Neul A/B |
| `$9C` | Dark Fairy |
| `$9D` | Seraphic Radiance |
| `$9E` | Chaos Dragon |
| `$A0-$AF` | Phantom preset A-D |
| `$B0-$BB` | Enhanced Ghost A-F |
| `$C0-$D7` | Spark Ball 24ID |
| `$E0-$F7` | Panel Monster v2 |

Enhanced Saramandor `$5E/$5F/$62/$63/$66/$67`、Dragon variant `$6A/$6B/$6E/$6F`、Goblin variant `$72/$73/$76/$77`は新敵専用AIへは送らない。原作AIを維持し、animation入口でpalette属性だけを補正する。

## AI入口 `$BBE2`

原作`$A1BF`はenemy IDから`#$14`を引き、Carryが立つ時だけ`$A1C3`を呼ぶ。従って入口Aは`enemy ID - $14`である。

入口は最初にPHAし、`ADC #$14`でIDを復元して分類する。直前の原作`SBC #$14`がCarry setで到達するため、CLCなしのADCで元IDへ戻る。

分類順はPanel、Neul、Chaos、Fairy、Radiance、Phantom、Sparkである。該当時はPLAで原作dispatch値を捨てて各AIへJMPする。非該当時もPLAしてGhost拡張へ入り、`$B0-$BB`ならGhost AI、それ以外なら原作`$A329`へ戻る。

- Ice Burn `$82`は共通入口で分類しない。復元前のA=`$6E`を原作`$A329`へ渡し、stock Flame AIを使う。
- PanelはPLA後、Panel共有AI wrapperへ入る。
- 全経路で入口PHAは1回PLAされ、RTS return addressをstackに残さない。
- 原作fallbackへ渡すAは`enemy ID - $14`のままで、原作dispatch契約を維持する。

## setup入口 `$BC32`

原作`$8ACB`は、X=entity typeから作ったY=`(X >> 1) & $FE`を使い、setup group pointerを読む入口である。hook時点では`($08),Y`のY=0がentity typeであるため、共通入口はそこからIDを直接読む。

- Panel `$E0-$F7`とSpark `$C0-$D7`: group `$14`を使う。
- Neul、Chaos、Fairy、Radiance、Phantom: 各専用setupへJMPする。
- Ghost `$B0-$BB`: Ghost拡張でgroup metadataを返す。
- Ice `$82`: stock Flameと同じgroup計算へ戻る。
- その他: 原作通り`LDY $0E / LDA $D9D3,Y / RTS`。

入口はstackを使わない。fallbackは原作命令列を再現し、Aにpointer lowを返す。

## init入口 `$BC84`

原作`$A2F1`でA=Xとなり、`JSR $9D1C`を呼ぶ。共通入口は最初にPHAしてこの原作入力を保存し、main slot type `$05`で分類する。

- Neul、Ghost、Fairy、Radiance、Chaos、Phantomの専用initは先頭でPLAし、原作入力を自分で消費する。
- Sparkは入口内でPLA後、原作`$9D1C`を実行する。
- IceはGhost拡張fallbackがPLA、原作`$9D1C`、type再読込を行った後、Ice専用initへJMPする。
- Panelとその他の敵も同じfallbackでPLAして原作initを実行する。

従って全分類でPHA/PLAは1対1である。呼出元`$A2F5`がさらにPLAする値は、`$A2E4`で積まれた別の原作値であり、共通入口が保存したAではない。

## animation入口 `$BCD0`

原作entity loopは`$8676`で毎frame `JSR $8789`を呼ぶ。共通入口は`($08),Y`のtypeを読み、次の順で処理する。

| 対象 | 処理 |
|---|---|
| Panel `$E0-$F7` | 原作`$8789` |
| Spark `$C0-$D7` | 原作`$8789` |
| Ghost `$B0-$BB` | 原作`$8789` |
| Ice `$82` | Ice専用固定frame更新 |
| Fairy `$9C` | 原作更新後、OAM属性を`AND #$13 / ORA #$48` |
| Radiance `$9D` | Radiance専用更新 |
| Phantom `$A0-$AF` | 原作更新後、OAM属性を`AND #$33 / ORA #$48` |
| stock color variant | ID pairを偶数へ正規化してpalette補正 |
| その他 | 原作`$8789` |

stock color variantはtypeを`AND #$FE`し、左右pairを同じ判定へまとめる。

| pair | 現行処理 | UI/renderer |
|---:|---|---|
| `$5E/$5F` | SPR#2 | SPR#2 |
| `$62/$63` | SPR#2 | SPR#2 |
| `$66/$67` | **原作fallback** | **SPR#2** |
| `$6A/$6B` | SPR#2 | SPR#2 |
| `$6E/$6F` | SPR#0 | SPR#0 |
| `$72/$73` | SPR#2 | SPR#2 |
| `$76/$77` | SPR#0 | SPR#0 |

SPR#2 branchは原作`$8789`後、OAM属性`($08),Y`のpalette bitを`AND #$33 / ORA #$48`で置き換える。SPR#0 branchは`AND #$33`だけを行う。どちらもJSR/RTSが1対1である。

## 共有runtimeの配置と依存

共通入口writerは分類入口だけでなく、次の子runtimeを同時に検証・配置する。

- Ice Burn
- Enhanced Neul A/Bとparameter table
- Chaos Dragon
- Phantom presetとphysics hook
- Dark Fairy
- Seraphic Radiance
- Enhanced Ghost A-Fとparameter table
- Spark variantの共有hook

Panel本体は保存処理の後段で常設配置される。AI入口からPanel共有wrapperへ直接JMPするため、expanded ROM保存では両方が必須である。

現行`apply()`は全hook、子runtime、設定依存、共通入口の検証を済ませた後で最初の書込みへ進む。従って、既知の現行形式に対する検証失敗で途中までROMを書き換える問題はない。

## ROM配置

| file | CPU | size | 内容 |
|---:|---:|---:|---|
| `0x3BF2-0x3C41` | `$BBE2-$BC31` | 80B | AI入口 |
| `0x3C42-0x3C93` | `$BC32-$BC83` | 82B | setup入口 |
| `0x3C94-0x3CDF` | `$BC84-$BCCF` | 76B | init入口 |
| `0x3CE0-0x3D64` | `$BCD0-$BD54` | 133B | animation入口 |
| `0x3D65-0x3D9C` | `$BD55-$BD8C` | 56B | Ghost分類拡張 |
| `0x3D9D-0x3DAB` | `$BD8D-$BD9B` | 15B | 現行runtime予約なし |

共通入口本体は427Bである。RAMは新規に確保せず、各子runtimeが定義する既存main/sub-slot fieldと設定RAMだけを使う。

## レジスタ・flag・stack

| 入口 | A | X | Y | stack/戻り |
|---|---|---|---|---|
| AI | `ID-$14`を受ける | 原作entity index | 分類先でclobber可 | PHA/PLA 1対1、各先へJMP |
| setup | type/pointer lowを返す | entity typeを保持 | type読出・group indexでclobber | stack操作なし、RTS/JMP |
| init | 原作X値をAで受ける | 原作値を保持 | 専用initでclobber可 | 入口PHAを全経路でPLA |
| animation | type/OAM属性でclobber | entity indexを保持 | type読出、OAM属性offset | 専用branchのJSR/RTS 1対1 |

AIの`ADC #$14`は原作SBC後のCarry setを契約として使う。setup fallbackのA、init後のX、animation後のentity pointerは原作後続が必要とする状態を維持する。

## 確定した問題

### [P1] Enhanced Saramandor Cだけ実機paletteが一致しない

ピッカー`ENEMY_PICKER_PALETTE_OVERRIDE`とキャンバス`ENEMY_PALETTE_OVERRIDE`は、A/B/C全6IDへpalette index 6、すなわちSPR#2表示を適用する。visual sourceもC `$66/$67`をstock `$64/$65`へ正規化する。

一方、実ROMのanimation入口は`$5E`、`$62`の後に`$6A`を比較し、`$66`を比較しない。従ってCだけ原作`$8789`へ流れ、stock Saramandor Cの属性のまま表示される。これは通常操作で再現するピッカー/キャンバス/PNGと実機表示の不一致である。

単純に`CMP #$66 / BEQ stock_spr2`を追加すると4B増える。現在animation直後にGhost拡張が隙間なく続くため、Ghost拡張を4B後ろへ移し、その内部入口を参照するAI/setup/initのJMP先も更新する必要がある。末尾の19B空きから4Bを使用し、残りは15Bとなる。ROM管理簿と`RESERVED_SPANS`の更新が必要で、RAM消費はない。命令列を圧縮してサイズを維持する案は別途可能だが、分類ロジック変更の検証範囲が広がる。

### [P1] 旧入口センター救済が現行領域の所有確認を迂回する

`previous_center`は、移動前の5本が次の旧位置に揃うとTrueになる。

```text
old AI      0x3BF2-0x3C35
old setup   0x3C36-0x3C7F
old init    0x3C80-0x3CC0
old anim    0x3CC1-0x3D36
old Ghost   0x3D37-0x3D6E
```

## 修正状況（2026-07-19）

確定問題3件は修正済みである。ユーザーのエミュレーター確認でも、修正前はEnhanced Saramandor CだけA/Bと色が異なることを確認した。

- animation入口へ`CMP #$66 / BEQ stock_spr2`を追加し、A/B/Cの6IDを同じSPR#2補正へ送る。
- animation入口は133B、Ghost分類拡張は4B後ろの`0x3D65-0x3D9C`へ移動した。AI/setup/init内の参照先も`$BD55/$BD63/$BD73`へ更新した。
- 共通入口全体は427B、直後の正式な空きは`0x3D9D-0x3DAB`の15Bである。
- 旧入口センターの一括移行、旧hook、旧短縮runtimeの受入れを削除した。空きまたは現行byte列の完全一致だけを許可する。

以下の「確定した問題」は、修正前の解析結果と原因を記録したものである。

Trueの場合、現行5領域に対する`_expect_blank_or_one_of()`をすべて飛ばす。その後は現行配置`0x3BF2-0x3D98`を無条件で書く。旧signatureが保証するのは`0x3D6E`までであり、`0x3D6F-0x3D98`の42Bは未確認である。そこに別データが存在しても上書きする。

これは古い途中ROMを現行配置へ移すための救済であり、プロジェクトの救済禁止ルールにも反する。削除して現行領域のblank/current完全一致だけを受け入れる場合、ROM/RAM配置・空き・管理簿は変わらない。

### [P1] 短い旧animation prefixの後ろ115Bを確認しない

`_expect_blank_or_one_of()`は最大長129Bを読み出すが、旧候補との比較は各旧blobの長さだけで行う。animation候補には14B、32B、124Bの旧本体がある。

最短14Bが先頭一致すれば、後続115Bの内容を検査せず許可し、現行129Bで上書きする。blank確認時だけは全129Bを見るため、旧prefix許容だけが所有確認を弱めている。

これも旧runtime救済を削除し、blankまたは現行129Bの完全一致だけを許可すれば解消する。ROM/RAM配置・空き・管理簿は変わらない。

## 未検証点

- Mesenで全追加敵を同室へ置いた動的なdispatch網羅試験は行っていない。
- standard ROM保存用`levels_need_runtime()`は、Panel以外の追加敵についてdirect配置だけを調べ、Demon Mirrorの`enemy_codes`を調べない。通常対象は自動拡張される日本版mapper66 ROMであるため現行主経路には影響しないが、防御用validationとしては不完全である。

## 修正時の検証条件

- Saramandor `$5E/$5F/$62/$63/$66/$67`が全て実機SPR#2になり、通常`$5C-$65`を変えないこと。
- 共通入口4本とGhost拡張の全branch先が移動後CPUアドレスを指すこと。
- AI/initの全分類でstack差分0、setup fallbackのA、AI fallbackのAを維持すること。
- 旧入口、旧hook、旧短縮runtimeを入力として受理しないこと。
- 現物ROM、builder、`RESERVED_SPANS`、正式ROM管理簿の範囲が一致すること。
- ROM配置を変更した場合は`python -B tools/check_rom_consistency.py`の3項目が全てOKであること。
