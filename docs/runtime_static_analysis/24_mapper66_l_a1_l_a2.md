# 24/26 mapper66拡張l_a1/l_a2 6502静的解析

解析日: 2026-07-19
対象: `magatu_skc/core/m66_expander.py`、`m66.py`、原作room load入口`$9975`
一次資料: 現行Python実装、コメント付き原作ASM、日本版原作ROM、正式ROM/RAM管理簿

## 結論

mapper66拡張の基礎loaderは、PRG0 `$E988`のl_a1が16Bのbank-switch trampolineをRAM `$07D0-$07DF`へ複写し、PRG1 `$8001`のl_a2を呼び、room grid、敵/metadata、mirror scheduleをRAMへ展開してPRG0へ復帰する構成である。

l_a1の自己参照、RAM trampoline、JSR/RTS収支、l_a2の3種類のpointer計算、192B room grid copy、64B room tail copy、16B mirror schedule copyは命令上成立している。確定問題は1件、文書不一致は1件である。

1. `expand_rom()`は`m66.patch_breakable_white_data()`でPRG0 `$E0BC-$E0E5`へ42Bの初期描画classifier helperを書いた直後、`_clear_legacy_prg0_level_area()`でfile `0x6010-0x700F`をEA消去する。l_a1だけを退避・復元し、classifier helperを復元しない。hook `$9620`は`JMP $E0BC`のまま残るため、`expand_rom()`直後のメモリ上ROMはhook先がEA列になった不整合状態である。
2. `change_mapper()`内コメントはl_a2を「152B」と記すが、実際のliteralは181Bである。正式管理簿は基礎body 180Bと直後のtail hook 3Bへ分けて管理している。

通常の「ROMを作る」保存経路では`save_all_levels_m66()`が`patch_breakable_white_data()`を再実行し、消されたhelperを再配置する。このため保存完了ROMが常に欠落するとは断定しない。ただし解析時点の`expand_rom()`単体の契約と、自動展開直後から次回save-time patchまでの内部ROMは不整合であった。

修正状況: 2026-07-19にPRG0旧level領域の消去をruntime検査・注入より前へ移し、`expand_rom()`完了時にhelperが残る順序へ修正した。ROM/RAM配置と使用量は変更していない。

## 配置と入口

| file | CPU | size | 内容 |
|---:|---:|---:|---|
| `0x1985-0x1987` | `$9975-$9977` | 3B | `JMP $E988` hook |
| `0x6998-0x69B8` | `$E988-$E9A8` | 33B | l_a1本体＋RAMへ複写する16B trampoline |
| `0x8010` | PRG1 `$8000` | 1B | `RTI` guard |
| `0x8011-0x80C3` | PRG1 `$8001-$80B3` | 179B | l_a2入口と基礎loader |
| `0x80C4-0x80C6` | PRG1 `$80B4-$80B6` | 3B | 元literalの末尾`RTS`位置から始まる現行tail hook |
| `0xC010-0xF50F` | PRG1 `$C000-$F4FF` | 13568B | 53 room×256B level record |
| `0xF510-0xF85F` | PRG1 `$F500-$F84F` | 848B | 53 room×16B mirror/drop schedule |

現行ではl_a2内部の一部と末尾が、mapper66特殊セルloaderおよびStageExt loaderによって上書きされる。本解析では基礎loaderの契約を対象とし、後付け部分の詳細は`23_m66_special_cell_loader.md`と`20_stage_ext_loader.md`に分離する。

## l_a1 `$E988`とRAM trampoline

l_a1は`LDX #$10`から始め、`$E996,X`を`$07CF,X`へX=16から1まで逆順copyする。copy先は`$07D0-$07DF`、copy元は`$E997-$E9A6`であり、X=0のbyteはcopyしない。loop終了時のXは0である。

RAMへ置かれる16Bは次である。

```asm
$07D0  LDA #$13
$07D2  STA $8011,X
$07D5  JSR $8001
$07D8  LDA #$03
$07DA  STA $8011,X
$07DD  JMP $E996
```

最初の`STA`でPRG1へ切り替え、RAM上の次命令からPRG1 `$8001`を呼ぶ。l_a2の`RTS`後も実行位置はRAMなので、2回目の`STA`でPRG0へ戻せる。最後にPRG0 `$E996`へ飛び、そこに置かれた`RTS`が元のroom load呼出frameを消費する。

stack収支は、原作側の`JSR $9975`、l_a1のhook `JMP`、RAM側`JSR $8001`、l_a2の`RTS`、RAM側`JMP $E996`、l_a1の`RTS`で均衡する。l_a2後段はXを変更し得るため、復帰側`STA $8011,X`の書込addressは`$8011+X`になる。しかし書込値`#$03`はPRG bank選択bitを0にするため、ROMとのANDが生じる実装でもPRG0復帰自体は成立する。CHR選択下位bitの一時値はaddress上のROM byteに依存し得る。

## l_a2 room grid展開

入口はPRG1 `$8001`で、`$8000`の`RTI`は誤侵入guardである。room番号は`$0428`を使う。

基礎pointerは次の計算になる。

```text
$00/$01 = $BFFF + room * $0100
Y       = $C0 .. $01
source  = $C000 + room * $0100 .. +$BF
dest    = $0314 .. $03D3
```

`ADC #$BF`をpointer highへ加え、lowを`$FF`、Yを`$C0`から1まで降順にすることで、room record先頭192Bをlive gridへcopyする。現行特殊セルpatchはこのcopy loopをhelper callへ置換するが、source/destination/Yの契約は維持する。

その後、Y=16から1まで`#$F8`を`$0303,Y`と`$03D3,Y`へ書き、上端`$0304-$0313`と下端`$03D4-$03E3`を固定境界にする。

## 64B room tail staging

次のpointerは`$BFBF + room*$0100`で、Y=64から1までcopyする。

```text
source = $C000 + room*$0100 + $C0 .. +$FF
dest   = $0790 .. $07CF
```

これによりroom metadata、通常敵列、mirror敵setなど、level record末尾64Bを固定RAMへ置く。原作の敵pointer tableはmapper変換時に`$07A0`、secondary pointerは`$0790`へ向けられる。元PRG0 level/item pointer領域を消去するため、item pointer loaderも定数`$0790`へ変更される。

source pointer、Yの端点、destinationはすべて1Bずれを含めて一致する。loopはY=0をcopyせず、pointerを1B手前に置く6502 indirect-indexedの定型である。

## 16B mirror/drop schedule staging

room番号から次を計算する。

```text
low  = (room * 16) & $FF
high = $F5 + (room >> 4)
ptr  = high:low - 1
```

Y=16から1まで`($00),Y`を`$077F,Y`へcopyするため、実sourceは`$F500 + room*16`、destinationは`$0780-$078F`になる。room 16ごとのpage carryは`room >> 4`で明示的に加算され、Stage 1～53で成立する。この計算は、23件目で確認した32B side-data helperの誤ったpage計算とは別物である。

## register、flag、stack

- l_a1 copy loop後のXは0。ただしl_a2と後付けtailはXを保存しないため、復帰時Xは不定である。
- l_a2はA/Y、zero page `$00/$01`、RAM staging領域を作業に使う。原作room load専用入口のため、これらを保存しない設計である。
- room grid loop、64B tail loop、16B schedule loopはいずれも`DEY/BNE`で正確な回数を走る。
- pointer減算は`SEC`後にlow、highの順で`SBC`し、borrowを伝播する。
- l_a2基礎本体は追加のPHA/PLAを使わず、RAM trampolineのJSR frameだけを最後のRTSで戻す。

## 確定問題: 展開時のhelper消去

`expand_rom()`の終盤は次の順である。

```text
m66.patch_breakable_white_data(new_data, levels)
  -> hook $9620 = JMP $E0BC
  -> helper $E0BC-$E0E5 = 42B classifier

_clear_legacy_prg0_level_area(new_data)
  -> file 0x6010-0x700F ($E000-$EFFF) = EA
  -> 退避したl_a1 $E988-$E9A8だけ復元
```

`$E0BC-$E0E5`は消去範囲内、hook `$9620`は範囲外である。したがって直後はhookだけが生存し、helper本体は42BすべてEAになる。これは静的なcall順、offset、clear範囲から確定でき、推測ではない。

UIの通常読込はこの後にlevelを再読込しwide-title正規化を行うが、このhelperをその場で再配置しない。後のROM保存では`save_all_levels_m66()`が再patchするため、保存経路が最後まで正常完了すればhelperは戻る。危険なのは次である。

- `expand_rom()`を独立APIとして使った結果をそのまま利用・保存する経路
- 自動展開後、save-time runtime再適用前の`rom.data`を正しい完成形とみなす処理
- 今後、保存処理の順序変更や途中失敗で再patchが実行されない場合

修正方針は別作業で決める必要がある。候補はclearをruntime patchより前へ移すか、clear後に全該当runtimeを再適用することである。現段階では実装変更していない。

## 管理簿と検証範囲

正式ROM管理簿はl_a1 33B、l_a2基礎body 180B、直後のtail hook 3B、PRG1 level/mirror領域を実配置どおり記載している。Pythonの初期literalは基礎bodyに元`RTS` 1Bを加えた181Bで、後続patchがそのRTS位置から3B hookを置く。RAM管理簿は`$0780-$07DF`をprobe書込あり・使用禁止とし、l_a1 trampolineおよび各staging領域と矛盾しない。

原作ROMのbank markerはfile `0x00FF-0x0102`が`10 11 12 13`で、mapper変換は`00 01 02 03`へ変更する。l_a1/l_a2のbank-switch値とともに管理簿へ登録済みである。

ROM生成は行っていない。日本版原作ROMの固定byte、Python生成literal、offset計算、呼出順、正式管理簿を静的に照合した。

## 判定

- l_a1 self-referenceと16B RAM trampoline: 正常
- PRG1切替、l_a2 call、PRG0復帰: 正常
- 192B room grid pointer/copy: 正常
- 上下16B境界書込: 正常
- 64B room tail pointer/copy: 正常
- 16B mirror/drop schedule pointer/copy: 正常
- stack収支: 正常
- `expand_rom()`完了時のruntime整合性: 異常。初期描画classifier helperを消去する
- l_a2 size記載: 誤記。Python初期literalは152Bではなく181B（管理簿上は180B body＋3B tail hook）

## 修正優先度

1. 高: `expand_rom()`のclearとruntime patch順序を直し、関数終了時点でhook/helperを一致させる。
2. 低: l_a2コメントを152Bから181Bへ直し、180B body＋tailの区分を明記する。

実装修正時は、23件目のside-data pointer修正と混同せず、展開直後と通常保存後の双方でhook/helper byte列を比較する必要がある。
