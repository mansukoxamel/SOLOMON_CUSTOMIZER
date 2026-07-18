# 22/26 Stage Announcement runtime 6502静的解析

解析日: 2026-07-19
対象: `magatu_skc/core/stage_announcement.py`、`room_flags.py`、`stage_ext.py`、原作room開始処理`$9021-$90D5`、PPU script処理`$9471-$9630`、CHR bank切替
一次資料: コメント付き原作ASM、日本版原作ROM、現行mapper66検証ROM、`docs/known_issues.md`、正式ROM管理簿

## 結論

Stage Announcementは、原作stage紹介画面の更新callを254B runtimeへ差し替え、room制約9種類をPPU scriptで2列表示してから原作`$915E`へ戻る常設overlayである。

main、mask、draw waiter、9-entry pointer table、KEY ENEMY/ALL KILL共有gate、FAIRY/MIRROR gate、全9 script、CHR glyph書込みを追跡した。PRG0の6502制御本体は成立する。確定問題は3件である。

1. CHR bank 3へ追加K/P glyphを書かないため、bank 3を使うroom、既定ではStage 49以降でK/Pを含むmessageが必ず文字化けする。既知の未修正バグである。
2. writerはruntime終端とCHR書込み終端を含むROM長を検査しない。短いbytearrayでは空sliceを空きと誤認し、所定offsetでなく末尾へappendし得る。
3. 旧hookと旧8-message layoutを明示的に受け入れる互換分岐が残り、現在の救済禁止方針と一致しない。

通常のbank 0～2を使うroomでは、表示順、PPU待機、pointer、stack、原作復帰値は成立し、現行ROM byte列もPython定数と一致する。ROM/RAM配置は変更していない。修正も行っていない。

## hook位置と原作復帰

原作room開始処理は次の順で進む。

```asm
$9053: JSR $9471
$9058: JSR $9471
$905B: JSR $C4D4
$905E: JSR $91EB
$9061: JSR $915E
$9064: LDA #$80
```

hookは`$9061`の`JSR $915E`を`JSR $EAF6`へ置換する。runtimeは全announcementをqueueした後、末尾`JMP $915E`で原作処理へtail-callする。

`$915E`はA=0、`$21=0`、X=`$21`としてRTSする。そのRTSが最初の`JSR $EAF6`のreturn addressを消費し、`$9064`へ戻る。原作と同じA=0、X=`$21`、Z=1で復帰し、stack深度も同じである。

## 254B連続layout

全segmentはfile `0x6B06-0x6C03`へ隙間・重複なしで連続配置され、合計254Bである。

| file | CPU | size | 内容 |
|---:|---:|---:|---|
| `0x6B06-0x6B23` | `$EAF6-$EB13` | 30B | main |
| `0x6B24-0x6B28` | `$EB14-$EB18` | 5B | Room Flag masks |
| `0x6B29-0x6B41` | `$EB19-$EB31` | 25B | draw waiter/pointer setter |
| `0x6B42-0x6B53` | `$EB32-$EB43` | 18B | 9-entry lo/hi pointer table |
| `0x6B54-0x6B6A` | `$EB44-$EB5A` | 23B | KEY ENEMY / ALL KILL gate |
| `0x6B6B-0x6B77` | `$EB5B-$EB67` | 13B | FAIRY ENEMY gate |
| `0x6B78-0x6B84` | `$EB68-$EB74` | 13B | MIRROR LINK gate |
| `0x6B85-0x6C03` | `$EB75-$EBF3` | 127B | 9 PPU scripts |

直後file `0x6C04`からSeraphic Radiance `$9D` runtimeが始まり、空き・緩衝は0Bである。`RESERVED_SPANS`と正式ROM管理簿はこの境界に一致する。

## Room Flag 5項目のmain loop

mainはX=0から4まで`$0778 & mask[X]`を調べ、非0なら同じXでdraw helperを呼ぶ。

| X | mask | 表示 |
|---:|---:|---|
| 0 | bit3 `$08` | DARK ROOM |
| 1 | bit4 `$10` | FIRE LOSS |
| 2 | door bits `$03` | HIDDEN DOOR |
| 3 | bit2 `$04` | FIRE SEALED |
| 4 | bit7 `$80` | SPELL SEALED |

door maskは隠し、茶block内、白block内の3状態を同じHIDDEN DOOR表示へまとめる。loop branchはX=5で終了し、gate 3本を順に呼ぶ。

## KEY ENEMY / ALL KILL共有gate

`$072B`がnon-negativeならKEY ENEMYとしてX=5をdraw helperへtail JMPする。設定なしsentinel `$FF`なら`$0770 bit4`を調べ、ONならX=6でALL KILLを描画する。両方が立つ異常入力ではKEY ENEMYが優先され、1つの左下slotへ重ね書きしない。

現在UIはKEY ENEMYとALL KILLの同時ONを拒否する。鍵敵の初期slotは実際の初期敵数内に制限され、通常roomではbit7が立つ値へ到達しないため、BMIによる`$FF`判定は通常設定範囲で成立する。StageExt byteの一般sentinel契約自体は`CMP #$FF`の方が厳密だが、通常UIから負値slotは作れない。

key/all-kill gateは`JMP draw`を使う。draw末尾RTSがmainからgateを呼んだJSR frameへ戻るためstackは均衡する。

## FAIRY ENEMYとMIRROR LINK gate

FAIRY gateは`$077E != $FF`ならX=7でdrawをJSRする。MIRROR gateは`$0770 bit5`ならX=8でdrawをJSRする。どちらもdraw後に自身のRTSでmainへ戻る。

表示順はRoom Flag 5項目、KEY/ALL KILL、FAIRY、MIRROR、最後に原作`$915E`で固定される。同じrow/columnを共有するのは排他設計のKEY/ALL KILLだけである。

## draw helperとcooperative yield

draw helperは呼出時のXを`TXA/PHA`でtask stackへ保存する。`$1B`が0になるまで、原作`$9471`と同じ`JSR $8DB4`でcooperative yieldし、前のPPU script完了を待つ。

ready後にPLA/TAXでindexを戻し、pointer tableのlo配列とhi配列から次を設定する。

```text
$1A = lo[X]
$1B = hi[X]
```

PPU taskはこのpointerを消費し、完了時に`$1B=0`へ戻す。次のannouncementは前scriptが終わるまで待つため、同一frameにpointerを上書きしない。

`$8DB4`はtaskごとにstack pointerを保存するため、yieldを跨ぐPHAも同じtask stack上で保持される。draw 1回ごとのPHA/PLA収支は0である。A/Yはyieldで変わり得るがdraw後にはpointer設定だけを行い、main末尾の原作`$915E`がA/X契約を再構築する。hook後続はYを引き継がない。

## PPU script形式と画面配置

各scriptは`[PPU hi][PPU lo][0x40+length-1][tile...][00]`である。bit6=literal横書き、low 6bit=文字数-1で、全message長は範囲内に収まる。

| row,col | message |
|---|---|
| 21,3 | DARK ROOM |
| 23,3 | FIRE LOSS |
| 25,3 | KEY ENEMY または ALL KILL |
| 27,3 | FAIRY ENEMY |
| 21,16 | HIDDEN DOOR |
| 23,16 | FIRE SEALED |
| 25,16 | SPELL SEALED |
| 27,16 | MIRROR LINK |

9 scriptはpointer tableのX=0～8と一致し、各terminatorは次scriptの先頭へ食い込まない。

## 確定したバグ

### [P1] CHR bank 3でK/P glyphが欠ける

通常alphabetはA=`$0A`からZ=`$23`だが、この画面で必要なK/Pは追加tile `$25/$27`を使う。writerは8KB CHR bank 0～2のpattern `$125/$127`へ16B glyphを入れる。

```python
for bank in range(3):
    ... write K/P ...
```

CHR bank 3へは書かない。原作はroomのtileset番号でCHR bankを切り替え、既定ではStage 1～16がbank 0、17～32がbank 1、33～48がbank 2、Stage 49以降がbank 3である。

従ってbank 3のroomで次の表示は確実に崩れる。

- DARK ROOM: K
- SPELL SEALED: P
- KEY ENEMY: K
- ALL KILL: K
- MIRROR LINK: K

FIRE LOSS、HIDDEN DOOR、FIRE SEALED、FAIRY ENEMYはK/Pを含まないためこの原因では崩れない。

bank 3の同位置はwide title側が使用するため、単純上書きはtitle表示を壊す。`docs/known_issues.md`でも未修正として管理されており、CHR配置の再設計が必要である。本解析では空き使用量を確定できないため修正していない。

### [P2] runtime/CHR終端のROM長検査がない

`apply()`は最初にhook 3Bを読むが、runtime終端`0x6C04`を含む必要長を検査しない。長さがhook位置より後、runtime位置より前のbytearrayでhookが一致する場合、各runtime sliceは空となり、`all(b in (EA,00) for b in cur)`がTrueなので空きと誤認する。slice代入は所定offsetでなく現在末尾へappendし得る。

`_chr_start()`もiNES magicとPRG countからCHR先頭を計算するだけで、headerが宣言するCHR sizeや、3 bank目のglyph終端が実ファイル内にあることを確認しない。短い入力では同様に誤った末尾追加になる。

通常の日本版ROMとmapper66拡張ROMは十分な長さなので通常saveでは発生しない。hook、runtime最大終端、必要CHR bank glyph終端をまとめて事前検査すれば配置を変えず修正できる。

### [P3] 旧layout受入れが救済禁止方針と不一致

hookは現行`JSR $EAF6`だけでなく旧`JSR`先を受け入れる。runtime検査も`OLD_LAYOUT`から各segmentの旧sliceを生成し、旧8-message配置を許容する。なお、さらに古いmain byte列の定数も残るが、現行`apply()`の受入れ条件には使われていない。

これは旧途中ROMを現行layoutへ上書きするための互換受入れであり、現在の正式版前・救済禁止方針と一致しない。現行日本版ROMの原形と現行runtimeだけを許容する方針へ整理する対象である。

## CHR書込みと現行ROM照合

日本版原作ROMとmapper66拡張ROMはいずれもCHR 4 bank、32KBを持つ。現行mapper66検証ROMではbank 0～2のK/P glyph、hook、main、mask、draw、pointer、3 gate、全9 scriptがPython定数と一致した。bank 3だけは意図的に不一致であり、上記既知バグの状態と一致する。

## 正常と確認した事項

- `$9061` hookの呼出順と`$915E`へのtail return
- main 5-loopのmask/index/branch
- KEY ENEMY優先、ALL KILL共有slot
- FAIRY/MIRROR gateの条件
- `$1B`待機、cooperative yield、X保存、stack収支
- 9-entry lo/hi pointer table
- 全PPU address、文字数、terminator
- 254Bの連続配置と次runtime境界
- bank 0～2のK/P glyph byte列
- `RESERVED_SPANS`と正式ROM管理簿のPRG0位置

## 未実施

- ROM生成
- emulatorでの動的実行
- 修正実装
- ROM/RAM管理簿の変更
