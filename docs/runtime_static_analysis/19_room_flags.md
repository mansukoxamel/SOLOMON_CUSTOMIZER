# 19/26 Room Flags runtime 6502静的解析

解析日: 2026-07-19
対象: `magatu_skc/core/room_flags.py`、`stage_ext.py`、`m66_expander.py`、原作level load・A/B action・扉先行描画・NMI・grid描画処理
一次資料: コメント付き原作ASM、日本版原作ROM、現行mapper66検証ROM、正式ROM/RAM管理簿

## 結論

Room Flagsは、現在roomの1B flagと扉cellをStageExt loaderからRAMへ受け取り、特殊扉、A/B魔法禁止、開始時fire所持reset、暗闇、特殊cell変換を5本のhookで実現する常設runtime群である。

loader 46B、magic gate 34B、door predraw 11B、dark 50B、特殊cell scanner 68B、visible-item helper 24B、white in-block extension 12Bを全命令・全branchについて追跡した。6502本体の確定バグは見つからなかった。確定したPython書込み境界バグ1件は修正した。

- `_verify()`のROM長検査がfile `0x4210`までしか要求せず、実際の最後のruntime終端`0x686B`を含まない。短いbytearrayでは空sliceを空きと誤認してruntimeを誤った末尾へappendし、`set_tempo()`では`IndexError`を起こし得る。

通常の日本版mapper66拡張ROMでは、全runtime、hook、StageExt受渡し、stack、A/X/Y、CPU flag、192-cell走査、暗闇周期は成立している。必要ROM長を全hook、signature、helper、tempo、全caveの最大終端から算出するよう修正した。ROM/RAM配置と6502 byte列は変更していない。

## flagとRAM受渡し

`$0778`は現在roomのflag cache、`$0779`は暗闇phase、`$077C`は扉cellである。mapper66 StageExt loaderがroom開始時にPRG1 entryから`$0778/$077C`へコピーするため、PRG0 Room Flags loaderは旧64B tableを直接参照しない。

| `$0778` bit | 用途 |
|---:|---|
| 0 | 隠し扉 |
| 1 | 茶ブロック内扉。bit0+bit1なら白ブロック内扉 |
| 2 | B fireball禁止 |
| 3 | 暗闇 |
| 4 | room開始時fire所持reset |
| 5 | visible in-block item mask使用 |
| 6 | 特殊cell変換使用 |
| 7 | A換石禁止 |

mapper66拡張ROMではruntime本体と5 hookを設定の有無に関係なく常設する。OFF roomは`$0778`の各bitで原作経路へ戻るため、ROM構造固定方針に一致する。

## Room loader `$9071 -> $E788`

原作`JSR $974B`を`JSR $E788`へ置換する。46B runtimeは最初に原作`JSR $974B`を実行し、その後で現在flagを処理する。

bit4が立つ場合は`$042E/$042F`を0にし、`JSR $A1CC`でfire stock HUDを再描画する。bit0/1は6回ASLして、それぞれ`$40/$80/$C0`へ変換する。`$077C`をXに読み、`$0304,X`へORして扉cellに隠し・茶・白の状態bitを付加する。

分岐先は全てruntime末尾RTSまたは次処理先に一致する。PHA/PLAは扉状態値をX loadの間だけ保存し、stack収支は0である。Xは扉cellへ変わるが、原作`$974B`後の呼出規約上、後続はX保存を要求しない。

## A/B magic gate `$8326 -> $E7B6`

原作ではA wrapper `$831E`が`$08=$11`、B wrapper `$80FF`が`$08=$13`を設定し、どちらも`JSR $8326`を呼ぶ。現行hookは原作先頭3B `LDA $28 / ROR A`を`JSR $E7B6`へ置換する。

runtimeはbit2とSE `$13`の組合せだけをB禁止、bit7とSE `$11`の組合せだけをA禁止として扱う。許可時は原作先頭3Bを再実行してRTSし、原作`$8329`へ戻る。A、Carry、Negativeは原作と同じ状態になる。

禁止時は`PLA / PLA / SEC / RTS`で、hookのJSRが積んだ`$8328`のreturn addressだけを捨て、A/B wrapperを呼んだ上位へ戻る。wrapper自身のreturn addressは残るため、stackは均衡する。Carry=1は原作`$836D`のreject契約と一致する。

## 扉先行描画 `$91CC -> $E7D8`

11B runtimeは`$0778 & $03`が0なら原作`JSR $9D53`を実行し、特殊扉なら描画をskipする。いずれもRTSで原作`$91CF`へ戻る。room grid側にはloaderが扉状態を設定済みであり、紹介画面に通常扉を先に出さないためのhookである。

原作ASMと実機確認記録では`$91CC`が扉、`$91E7`が鍵である。runtimeは鍵描画を変更しない。

## 暗闇NMI `$8055 -> $E7E3`

原作`LDA $0301`を毎NMIの`JSR $E7E3`へ置換し、後続`STA $2001`へPPUMASK値をAで返す。

暗闇bitが0、またはDana実プレイ状態`$057F < $C0`なら`$0779=0`として原作`$0301`を返す。暗闇中はphaseを1増やし、`PERIOD`以上で0へ戻す。`phase < LIGHT`なら明、以降はBG bit3をclearした値を返す。ただしDana fireball slot `$05A7`がactiveなら暗phase中も原作値を返す。

`set_tempo()`はLIGHTを1..200、DARKを1..`254-LIGHT`へclampするためPERIODは2..254である。8bit phaseは比較前にoverflowせず、明から始まり、指定frame数で循環する。Aだけを返却値として使用し、XはDana status確認で変わるがNMI呼出側にX保存契約はない。stack操作はない。

## 特殊cell scanner `$909A -> $E817`

68B runtimeは最初に原作`JSR $95E4`を呼び、画面描画を完了してからlive gridだけを変換する。これにより特殊IDの見た目を残し、衝突・破壊処理へ通常cell値を渡す。

X=`$C0`から1まで減らし、`$0313,X`、すなわち`$0314-$03D3`の192 cellを全走査する。Y=`$18`から始め、24B mask `$0750-$0767`をMSB-firstで消費する。Xの下位3bitが0になるたびYを1減らすため、各mask byteと8 cellの対応にずれはない。

mask bitが立つ通常・ひびcellは`ORA #$C0`でvisible in-block itemへ変換する。mask bitがない`$C0-$F7`は`AND #$BF`でlive gridだけを白in-block通常状態へ下げ、`$80-$BF`と`$F8-$FF`は維持する。

直接特殊cellの変換は次である。

| 表示用cell | live grid |
|---:|---:|
| `$F9` | `$90` breakable white |
| `$FA` | `$10` passable white |
| `$01` | `$D0` cracked brown |
| `$40` | `$F8` invisible solid |
| `$50` | `$90` invisible breakable |
| `$A3` | `$10` passable brown |
| `$A4` | `$F8` solid brown |

helperはAをcell値として本体へ返し、X/Yをscan状態として継続利用する。全branchの戻り先と`DEX/BNE` loop終端は成立する。

## 確定したバグ

### [解消] runtime終端を含むROM長検査がない

`_verify()`は次だけを必要長としている。

```python
need = OFF_TABLE + ROOM_COUNT  # 0x4210
```

しかし現行mapper66で書く領域はhelper `0x6244`から始まり、特殊cell runtimeは`0x6827-0x686A`を使用する。必要な最大終端は`0x686B`である。

長さが`0x4210`以上`0x686B`未満のbytearrayは、前方hook/signatureが一致すれば長さ検査を通る。`_verify_runtime_cave()`は短いsliceまたは空sliceについて、非`00/EA` byteが無いという理由で空きと判定する。続くslice代入は、startが現在長より後なら所定offsetを埋めず現在末尾へruntimeをappendする。

`set_tempo()`も同じ`_verify()`を使った後に`rom_data[0x6825]`へ単一index代入するため、短い入力では定義済みの`RoomFlagError`でなく`IndexError`になり得る。

通常save経路のmapper66 ROMは長さ`0x18010`なので通常操作では発生しない。それでもwriter単体の境界検証としては確定バグである。`REQUIRED_ROM_END`を全hook、signature、helper、tempo、全caveの最大終端から算出し、`0x686B`未満を処理前に`RoomFlagError`で拒否するよう修正した。cave単体検査にもslice長の一致を追加した。

## ROM/RAM配置

| file | CPU | size | 内容 |
|---:|---:|---:|---|
| `0x6244-0x625B` | `$E234-$E24B` | 24B | visible in-block mask helper |
| `0x625C-0x6267` | `$E24C-$E257` | 12B | white in-block extension |
| `0x6798-0x67C5` | `$E788-$E7B5` | 46B | room loader |
| `0x67C6-0x67E7` | `$E7B6-$E7D7` | 34B | A/B magic gate |
| `0x67E8-0x67F2` | `$E7D8-$E7E2` | 11B | door predraw |
| `0x67F3-0x6824` | `$E7E3-$E814` | 50B | dark NMI runtime |
| `0x6825-0x6826` | `$E815-$E816` | 2B | LIGHT/PERIOD |
| `0x6827-0x686A` | `$E817-$E85A` | 68B | special-cell scanner |

専用RAMは`$0778-$0779`の2Bと`$077C`の1Bである。visible/cracked side dataは共有予約`$0750-$076F`をStageExt loaderから受け取る。

現行mapper66検証ROMでは、上記7本、tempo 2B、5 hookの全byteがPython定数と一致した。`RESERVED_SPANS`および正式ROM/RAM管理簿とも一致する。

## 正常と確認した事項

- StageExtから`$0778/$077C`へのroomごとの受渡し
- loaderの原作call順、fire reset、特殊扉状態bit
- A/B wrapper、SE識別、許可・禁止のstackとCarry契約
- 扉と鍵の原作描画入口の区別
- NMI後続`STA $2001`へのA返却、暗闇周期、fireball照明
- 192-cell範囲、24B mask、MSB-first bit順
- 全特殊cell変換値と描画後変換の順序
- mapper66でのruntime/hook常設
- 現行ROM byte列、`RESERVED_SPANS`、正式ROM/RAM管理簿の一致
- 短いROMをruntime書込み前に拒否する境界テスト

## 未実施

- ROM生成
- emulatorでの動的実行
- ROM/RAM管理簿の変更
