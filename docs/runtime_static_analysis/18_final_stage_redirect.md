# 18/26 Final Stage Redirect runtime 6502静的解析

解析日: 2026-07-19
対象: `magatu_skc/core/final_stage_redirect.py`、`stage_ext.py`、`panel_monster_stage_variant.py`、`saver.py`、`hack_dialog.py`、原作stage clear `$C687-$C727`
一次資料: コメント付き原作ASM、日本版原作ROM、現行mapper66検証ROM、正式ROM/RAM管理簿、CHANGELOG

## 結論

Final Stage Redirectは、選択したroomをクリアした後、原作の通常進行・特殊route判定で決まった次room番号をStage 50へ上書きする常設13B runtimeである。直接endingを起動せず、原作Stage 50を経由する。

13B本体、stage clearの全room更新、StageExt loader、hook/stack、UIの全選択肢、Python書込み境界を追跡し、確定バグ2件を修正した。

1. UIからStage 50を除外し、保存前にもStage 50自身のflagを拒否する。Stage 51～53からStage 50へ戻す設定は維持する。
2. Python `_verify()`の必要長をhook、後続signature、cave終端の最大値へ修正した。

redirect元がStage 50以外なら6502本体の分岐・stack・room番号は成立する。ROM/RAM配置と6502バイト列は変更していない。

## 原作stage clearのroom更新

開いた扉へDanaが入るとitem `$07` handler `$C687`がstage clearを開始する。room番号に関係する順序は次である。

1. `$85`のclear room総数を1増やす。
2. `$28 bit6`が立つ特殊復帰経路なら`$0428 += 5`する。
3. `$0429 != 0`なら通常advanceをskipする。
4. 通常roomではX=`$0428`を読み、Stage 48かつSolomon's Seal数が8未満ならXを余分に1増やす。
5. Xを1増やして`$0428`へ書く。
6. Shrine panel/Seal数による特殊route flagを`$78`へ設定する。
7. `$28 bit5`をclearする。
8. 原作`JSR $C70E`でentityをclearする。
9. stage一時flagをclearし、clear演出action `$14`を開始する。

redirect hookは手順8の原作callを差し替える。従って通常advanceと特殊route判定の後に実行され、flag ON時はそれまでの`$0428`計算結果を最後に捨てて固定値へ変える。

## hookと13B runtime

原作は次である。

```asm
$C6F5: JSR $C70E
$C6F8: STA $042A
```

現行hookは`JSR $E332`である。runtimeは次の13Bだけで構成される。

```asm
LDA $077A
BPL normal
LDA #$31
STA $0428
normal:
JMP $C70E
```

`$077A bit7`が0ならroom番号を触らず原作clearへ入る。bit7が1なら`$0428=$31`としてから同じ原作clearへ入る。

runtimeは`JMP $C70E`を使うため、`$C70E`末尾のRTSが最初の`JSR $E332`のreturn addressを消費し、`$C6F8`へ戻る。原作の`JSR $C70E / RTS`とstack深度は同じである。`$C70E`はA=0で戻るので、後続`STA $042A/$0429`の入力契約も維持する。

## `$31`がStage 50になる理由

`$0428`は0-based room indexである。

| `$0428` | 表示stage | 原作上の意味 |
|---:|---:|---|
| `$2F` | 48 | 通常room最終分岐点 |
| `$30` | 49 | Seal 8個時のSolomon route room |
| `$31` | 50 | 原作最終room |
| `$32` | 51 | 通常bonus room |
| `$33` | 52 | 特殊route A |
| `$34` | 53 | 特殊route B |

原作はStage 48 clear時、Seal数8未満なら`$2F`から2増やして`$31`、8以上なら1増やして`$30`へ進む。Stage 49を経るrouteも最終的にはStage 50へ進む。runtimeはどの選択stageからでも最終戦room `$31`へ直接送る。

## StageExt flagの受渡し

設定はStageExt entry byte0 bit4=`$10`である。mapper66 room loaderは現在roomのentryを読み、次を行う。

```text
(entry[0] & $10) << 3 -> $077A
```

従ってOFF roomでは`$077A=$00`、ON roomでは`$80`となる。loaderはroom開始時に`$077A=0`へ初期化してから現在entryを書き、前roomの値を持ち越さない。

redirect実行時に`$0428`はStage 50へ変わるが、`$077A`はその場ではclearされない。ただしclear演出後のStage 50 loadでentryを読み直すため、Stage 50自身にflagが無ければ0になる。通常のredirect元では再発火しない。

## 修正済みバグ

### [解消] Stage 50をredirect元にするとStage 50を永久loopする

ゲーム挙動改造dialogはStage 1～53を全てcomboへ追加し、原作相当のStage 48だけを特別値`-1`にする。Stage 50も正常な選択肢として残る。

Stage 50を選ぶとStageExtのlevel index49へbit4が立つ。Stage 50 clear時の流れは次になる。

```text
Stage 50をclear
  -> 原作room advance
  -> hookで現在roomの$077A bit7を検出
  -> $0428=$31（Stage 50）
  -> Stage 50を再load
  -> Stage 50 entry自身のflagが再び$077A bit7へ入る
```

毎回同じ条件が再構築されるため脱出できず、通常のendingへ到達しない。UI操作だけで作れる確定バグである。

UI comboからStage 50を除外し、global設定から50が渡された場合は原作相当のStage 48へ正規化する。さらに`final_stage_redirect.validate_levels()`を保存前整合性検査とruntime writerの両方から呼び、XML等でStage 50自身のbit4が立っていても拒否する。Stage 51～53からStage 50へ戻す設定は有効な用途として維持する。

### [解消] cave終端を含むROM長検査がない

`_verify()`の最初の長さ検査は次だけを見る。

```text
OFF_SIG_AFTER_CLEAR_RESET + len(SIG_AFTER_CLEAR_RESET)
```

これはおよそfile `0x4714`までで、runtime cave終端`0x634F`より小さい。長さがその中間にあるbytearrayではhook/signature検査を通過できる。

その後のcave sliceが空または短い場合、次の条件は誤って成功し得る。

```python
cur != CAVE and any(b not in (0xEA, 0x00) for b in cur)
```

空`cur`では`any(...)`がFalseなのでエラーにならない。`apply()`の`rom_data[0x6342:0x634F] = CAVE`は、startが現在長より後なら所定offsetを埋めず現在末尾へ13Bをappendする。hookだけは本来位置へ書かれるため、壊れた部分適用になる。

`_verify()`はhook終端、後続signature終端、cave終端の最大値を`required_end`とし、それより短い入力をslice検査前に拒否する。writer単体へ短いbytearrayを渡しても末尾appendや部分適用は起きない。ROM/RAM配置は変わらない。

## ROM/RAM配置

| file | CPU | size | 内容 |
|---:|---:|---:|---|
| `0x6342-0x634E` | `$E332-$E33E` | 13B | Final Stage Redirect runtime |
| `0x4705-0x4707` | `$C6F5-$C6F7` | 3B | clear-reset hook |
| `0x4708-0x4713` | `$C6F8-$C703` | 12B | 後続原作signature、変更なし |

runtime直前`0x633F-0x6341`は3B空きで、直後`0x634F`からEnhanced Gargoyle primary runtimeが始まる。現行配置には緩衝がなく、13B終端と次runtime先頭は隣接する。正式ROM管理簿と`RESERVED_SPANS`はこの実占有に一致する。

現行mapper66検証ROMの13B、hook 3B、後続signature 12BはPython定数とbyte単位で一致した。

専用RAMは`$077A`の1Bで、bit7だけを使用する。StageExt loader、Room Flags loaderと同じroom load chainが所有する正式予約である。

## Python書込み側の正常事項

十分な長さのROMでは、書込み前に次を検査する。

1. `$C6F8`以降12Bが原作signatureである。
2. hookが原作`JSR $C70E`または現行`JSR $E332`である。
3. caveが現行13Bまたは全`00/EA`である。

検査後にcave、hookの順で書くため、通常mapper66 ROMの未知署名では部分適用を残さない。`levels`の設定数にかかわらず本体とhookを常設し、OFFは`$077A bit7`で原作処理へ戻す。旧runtime救済用byte列の受入れはない。

`enabled_in_any_level()`は設定確認helperだが、現行save pathはこれでruntime本体を切り替えない。常設方針に一致する。

## 正常と確認した事項

- stage clear内のhook実行順
- 通常advance、Stage 48 Seal分岐、特殊route flag設定との前後関係
- `$31`とStage 50の対応
- OFF/ON両branch
- `$C70E`のA=0復帰契約
- JSR→tail JMP→RTSのstack均衡
- StageExt bit4から`$077A bit7`への変換
- room load時のflag再構築
- runtime/hookの常設
- 現行ROM byte列、`RESERVED_SPANS`、正式ROM/RAM管理簿の一致

## 未実施

- ROM生成
- emulatorでの動的実行
- emulatorでのredirect動的実行
- ROM/RAM管理簿の変更
