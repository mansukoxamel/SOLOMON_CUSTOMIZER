# 23/26 mapper66特殊セルloader 6502静的解析

解析日: 2026-07-19
対象: `magatu_skc/core/m66.py`、`room_flags.py`、`solomon_seal_block.py`、mapper66 l_a2内patch、原作初期描画`$95E4-$9627`
一次資料: 現行Python実装、コメント付き原作ASM、現行mapper66検証ROM、正式ROM/RAM管理簿

## 結論

mapper66特殊セルloaderは、roomの192 cellを直接PRG1から読むl_a2へ複数patchを加え、`$C0-$FF`特殊cellの保持、white/cracked in-block itemのside data copy、死亡respawn、初期描画class、白block内鍵を成立させるruntime群である。

4 helper計203B、l_a2内2 patch、原作描画hook、鍵patch、24B mask＋8B position listを命令単位で追跡した。確定問題2件は修正した。

1. 32B side-data copy helper `$8E70`のroom pointer high計算を、`$F84F + room*32`の16bit加算へ修正した。全53 roomで期待pointerと一致する。
2. preflightは初期変換直後のmapper66 base loaderと現行形だけを受け入れ、中間世代のl_a2 patch受入れを削除した。初回修正ではbase loader定数を誤って別世代の配列へ向けていたため、`change_mapper()`が実際に生成するrespawn 49Bとside-copy空き34Bへ訂正した。

respawn変換、cracked one-shot復元、初期描画mask classifier、白block内鍵の各命令列自体は成立する。side-data helperは43Bから42Bへ縮み、file `0x8EAA`の1Bを空きとして解放した。runtime移動、PRG0/RAM消費はない。

## runtime構成

| file | CPU | size | 内容 |
|---:|---:|---:|---|
| `0x801F-0x804F` | PRG1 `$800F-$803F` | 49B | l_a2 respawn入口を`JSR $9009`へ置換 |
| `0x80A2-0x80C3` | PRG1 `$8092-$80B3` | 34B | side copy `$8E70`＋cracked helper `$903D` call |
| `0x8E80-0x8EA9` | PRG1 `$8E70-$8E99` | 42B | 32B side-data copy helper |
| `0x8EAA` | PRG1 `$8E9A` | 1B | 空き |
| `0x9019-0x904C` | PRG1 `$9009-$903C` | 52B | respawn direct-cell helper |
| `0x904D-0x908F` | PRG1 `$903D-$907F` | 67B | cracked in-block respawn helper＋8B mask table |
| `0x1627` | `$9617` | 1B | initial white threshold `$F8->$C0` |
| `0x1630-0x1636` | `$9620-$9626` | 7B | initial draw classifier hook |
| `0x60CC-0x60F5` | `$E0BC-$E0E5` | 42B | initial draw mask classifier＋8B bit table |
| `0x17ED` | `$97DD` | 1B | no-key branch調整 |
| `0x17F5-0x1803` | `$97E5-$97F3` | 15B | in-block key state patch |
| `0xF860-0xFEFF` | PRG1 `$F850-$FEEF` | 1696B | 53 room×32B side data |

side dataの各room先頭24Bは192-cell mask、末尾8Bはcracked in-block cell位置である。RAM copy先は`$0750-$0767`と`$0768-$076F`である。

## l_a2 direct-cell respawn helper `$9009`

l_a2の元49Bを`JSR $9009`＋46 NOPへ置換する。Yはroom cell indexを192から1へ降順に走査し、helperが1 cellを`$0313,Y`へ書く。

`$7C bit0`が0の初回loadでは、全cellをそのままcopyする。死亡respawn時は次に分類する。

| source cell | respawn値 |
|---:|---:|
| `$F4-$FF` | そのまま |
| `$F0-$F3` | `$F9` empty breakable white |
| `$C0-$EF` | そのまま |
| `$00-$BF`かつbase `< $2E` | そのまま |
| base `>= $2E`、bit7=1 | `$90` brown block |
| base `>= $2E`、bit7=0 | `$10` empty |

`$F0-$F3`だけをone-shot white in-block itemとして消費後`$F9`へし、`$C0-$EF`の通常white in-block状態を死亡で消さない。原作SKCHAINのone-shot判定も保持する。

helperはAとflagを作業に使い、Xを使わない。Yを1減らしてBNEで全192 cellを回り、最後にRTSする。l_a2側のJSR frameと収支は一致する。

## 32B side-data copy `$8E70`

l_a2末尾近くは次の2 callへ置換される。

```asm
JSR $8E70   ; current roomの32Bを$0750-$076Fへcopy
JSR $903D   ; death respawn時のcracked one-shot補正
NOP ...
```

helperはsource pointerを作り、Y=`$20`から1まで次をcopyする。

```asm
LDA ($00),Y
STA $074F,Y
```

従ってpointerは対象room先頭の1B前、正しくは次でなければならない。

```text
$00/$01 = $F84F + room*32
copy source = pointer+1 .. pointer+32
```

しかし現行43Bはlowとhighを独立に次で作る。

```text
low  = (room*32 + $4F) & $FF
high = $F8 + (room >> 4)
```

32B/roomなのでhighは単純な`room>>4`ではなく、`room*32+$4F`の全page carryを含める必要がある。現行式は含めない。

## 確定した6502バグ

### [解消] Stage 7以降のside-data source pointerが誤る

全53 roomについて現行命令を模擬し、期待値`$F84F + room*32`と比較した。正しく一致するのは0-based room 0～5、すなわちStage 1～6だけである。

差は次の区間で変化する。

| stage | actual - expected |
|---:|---:|
| 1～6 | 0 |
| 7～14 | `-$0100` |
| 15～16 | `-$0200` |
| 17～22 | `-$0100` |
| 23～30 | `-$0200` |
| 31～32 | `-$0300` |
| 33～38 | `-$0200` |
| 39～46 | `-$0300` |
| 47～48 | `-$0400` |
| 49～53 | `-$0300` |

Stage 7～8はside tableより前のmirror/drop schedule末尾を読み、以後も別roomのmask/listを読む。結果は次である。

- visible in-block itemのmaskが設定roomと一致しない。
- cracked in-block itemの位置listが設定roomと一致しない。
- Room Flags scannerが別cellをin-block item化するか、必要cellを変換しない。
- death respawn helperが別位置を復元対象として読む。
- 透明Solomon Sealの取得済みmask解除も、元の32B copyが誤っているため正しいmaskを前提にできない。

正式ROM管理簿には「page-crossing carry preserved」と記載されているが、現行命令列はcarryを維持せず、上記の通りである。管理簿記述も現物と不一致である。

helperを次の計算へ変更した。

```text
low  = (room << 5) & $FF
high = room >> 3
pointer = $F84F + (high:low)
```

low byteへの`ADC #$4F`で出たCarryを、high byteへの`ADC #$F8`へそのまま渡す。全53 roomを機械計算し、`$F84F + room*32`と一致した。新helperは42Bで、旧43B枠から1Bを解放した。

## cracked in-block respawn helper `$903D`

初回loadでは`$7C bit0=0`を見て即RTSする。死亡respawn時だけ`$0768-$076F`を後ろから走査する。

各position byteについてlive gridが`$10`になっている場合だけ、one-shot itemが消費済みと判断して次を行う。

1. gridをcracked brown `$01`へ戻す。
2. position byteから`cell_index = position-$10`を作る。
3. `cell_index>>3`でmask byte、`cell_index&7`でbitを選ぶ。
4. 末尾8B inverse-mask tableで`$0750-$0767`の対応bitをclearする。

Yのlist indexはPHA/PLAで保存し、Xはgrid位置、bit indexへ順に使う。2回のPHAと2回のPLAは均衡する。未使用`$FF`、live gridが`$10`でないcellはskipし、最大8件で必ず終了する。

## 初期描画classifier `$E0BC`

原作`$9620`の`LDX #$10 / CMP #$40 / BCS / TAX` 7Bを`JSR $E0BC`＋NOPへ置換する。上流のwhite thresholdも`$F8`から`$C0`へ下げる。

- A `< $40`は原作通りX=Aで戻る。
- A `$40-$7F`は現在grid index `$00-$10`から24B mask byte/bitを求める。
- mask bit ONならX=1、OFFならX=`$10`を返す。
- A `>= $80`は上流branchでこのhelperへ来ない。

mask index計算はm66 writerのLSB-first形式と一致し、`$0304`実プレイ192 cellの範囲に収まる。helper内PHA/PLAは均衡し、42B末尾8B tableへのX indexも0～7である。

## white in-block key patch

原作key cell生成を、key状態byte `$00`のbit7をhidden `$40`、bit6をin-block `$80`へ変換してitem `$06`とORする15Bへ置換する。

| `$00` bit7/6 | grid key値 |
|---:|---:|
| 00 | `$06` normal key |
| 10 | `$46` hidden key |
| 01 | `$86` brown in-block key |
| 11 | `$C6` white in-block key |

ASLのCarryで元bit7を保持し、元bit6はASL後のbit7として`AND #$80`で取り出す。branch先、A、X/Y不使用、15B固定長は成立する。

## Python writerと方針不一致

`_preflight_runtime_block_loader()`は全patch、4 helper、loader tail、guardの最大終端までROM長とsignatureを先に検査する。通常の未知競合では部分適用を残さない。

修正後は、respawn入口とside-copy入口のどちらも、初期変換直後のmapper66 base loaderと現行helper-callだけを受け入れる。respawn入口のbase署名は`change_mapper()`のl_a2 literal file `0x801F-0x804F`から直接確定した次の49Bである。

```text
a5 7c 6a 90 24 b1 00 c9 f4 b0 1e c9 f0 b0 04 c9
c0 b0 16 29 3f c9 2e 90 10 b1 00 29 80 2a 90 05
a9 90 18 90 06 a9 10 90 02 b1 00 99 13 03 88 d0 cf
```

side-copy入口file `0x80A2-0x80C3`のbase署名は34Bすべて`EA`である。変換直後の空きに現行の`JSR $8E70 / JSR $903D`を入れる契約なので、別世代の`ad 28 04 0a ...`命令列はbaseとして受け入れない。respawn側の`ad 28 04 c9 30 ...`、threshold-C0、bypass、disabled、旧mask-copyなど他の中間世代も引き続き拒否する。

## 現行ROM・配置照合

現行mapper66検証ROMでは、4 helper、2 l_a2 patch、draw hook/helper、white threshold、key patch、tail hook/guardの全byteがPython定数と一致した。side tableはfile `0xF860-0xFEFF`、RAMは`$0750-$076F`で管理簿と一致する。

`RESERVED_SPANS`は4 helper本体の実占有だけを登録し、l_a2内patchと原作位置patchは既存code置換として別管理される。配置重複は見つからなかった。

## 正常と確認した事項

- respawn初回/死亡分岐と`$F0-$F3/$C0-$EF`分類
- cracked list 8件走査、grid復元、mask bit解除
- initial draw classifierの192-cell mask index
- white in-block key 4状態
- l_a2 call、register、stack、branch終端
- Python preflightの必要長と事前signature検査
- 現行ROM byte列、`RESERVED_SPANS`、正式ROM/RAM配置
- 全53 roomの`$F84F + room*32` pointer
- 中間世代respawn layoutと旧43B helperの拒否
- `change_mapper()`出力のrespawn 49B・side-copy空き34Bとpreflight定数の完全一致

## 未実施

- ROM生成
- emulatorでの動的実行
