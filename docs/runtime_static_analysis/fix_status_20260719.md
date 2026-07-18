# 6502 runtime静的解析 修正反映状況（2026-07-19）

この文書は、1/26から6/26の解析で確定した問題に対する`codex/runtime-static-bugfixes`上の修正結果をまとめる。各解析文書は発見時点の証拠を保持し、本書を修正後状態の追補とする。

## 1/26 Panel Monster v2

- loaderは、PRG1 slot、mapper66 tail、StageExt helperをすべて検査してから書く。helper異常時の3B先行変更を解消した。
- `panel_monster_v2_settings_save_report()`はPanel単体slotとFire2重畳slotをともに正常と判定する。
- 未到達の`0x64B9-0x64D7`（31B）と`0x6509-0x650A`（2B）を書込み・予約対象から外した。
- pre-compact移行と未使用`_build_state1_fire_marker()`を削除した。
- `$8B05`は旧Spark中継`$CFDE`を使わず、現行Panel animation helper `$E6ED`へ直接接続する。

## 2/26 Enhanced Saramandor A/B/C

- 攻撃終了時、通常groupは従来どおりXのbit maskで`$B05E`へ入り2枠を解放する。
- Enhanced groupだけ`LDX #$01`で未使用の`sub[6]`を解放し、実体化したBulletの`sub[7]`は残す。
- 4Bを追加使用し、先頭runtime範囲は`0x63D9-0x6495`（189B）になった。直後のPanel開始`0x6496`は不変である。
- 全7 chunkの書込先所有検査を、hook書込みより前に行う。

## 3/26 Spark Ball 24ID

- 179B runtime配置先の現行byte列または空きbyteを、hook書込み前に検査する。
- 最小ROM長を明示検査する。
- 無効化済みDragon/Golem borrowed-ID実装を削除し、現行24ID専用writerへ一本化した。
- 本体範囲`0x3ED0-0x3F82`は不変である。

## 4/26 Enhanced Ghost A-F

- 外部marker helper `$E59B`を、Ghost単体writerと共通writerの書込み前に検査する。
- 旧`PRE_COMPACT_RUNTIME`を正常入力として受け入れる経路を削除した。
- 本体211Bとparameter 24Bの配置は不変である。

## 5/26 Enhanced Neul A/B

- Ghost Bullet spawn wrapper `$E323`とPanel marker helper `$E59B`を、Neul単体writerと共通writerの書込み前に検査する。
- 「全弾生成失敗でもcooldownを満額消費する」挙動は仕様未確定のため変更していない。
- 本体212Bとparameter 6Bの配置は不変である。

## 6/26 Key/Fairy Enemy

- Key/Fairy writerからStageExt loaderの検査・書込みを外した。loaderの所有者はStageExt、Panel、Fire2に限定する。
- 最終Fire2/Panel loaderが入った状態でも、Key/Fairy単体適用はloaderを拒否・変更しない。
- 重複していた`RAM_RESERVED_SPANS`定義を1つにした。ROM/RAM範囲は不変である。

## 配置差分

| 項目 | 変更前 | 変更後 | 差分 |
|---|---:|---:|---:|
| Enhanced Saramandor先頭runtime | 185B | 189B | PRG0 4B使用 |
| Panel未到達領域 | 33B予約 | 33B空き | PRG0 33B解放 |
| 旧Spark/Panel animation中継 | 23B使用扱い | 23B空き | PRG0 23B解放 |
| 合計 | - | - | PRG0空き52B増 |
| RAM | 変更なし | 変更なし | 0B |

正式ROM管理簿と`RESERVED_SPANS`はこの状態へ更新した。

## 検査範囲

- ROM領域重複、正式管理簿、敵ID/runtime登録、RAM予約の整合性検査を実施する。
- 未知byteを入れたメモリ内試験で、Panel、Spark、Ghost、Neulが例外前に入力を変更しないことを確認する。
- ROMは新規生成していない。
- Mesenによる動的試験は未実施である。
