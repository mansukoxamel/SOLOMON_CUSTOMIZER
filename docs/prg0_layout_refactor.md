# PRG0配置リファクタリング作業記録

この文書は `codex/prg0-layout-refactor` ブランチの作業記録です。
ROM予約の正式なマスターではありません。正式な予約情報は
`docs/rom_map_jp_mapper66_current.html` を正とします。

## 目的

日本版 mapper66 wide ROM の PRG0 bank0 について、追加プログラムの
虫食い配置を整理する。

主対象:

- CPU: `$E000-$EFFF`
- NES file: `0x6010-0x700F`
- size: `4096B`

この4096Bは、旧原作ステージデータ跡地として `EA` 初期化しても
現行の読み込み・保存フローが成立することを確認済み。

## 調査の主軸

原作ROMとの差分比較は最終確認として使う。

ただし、今回の主軸は差分比較ではなく、Solomon Customizer の実装側から
「customizerが追加しているプログラム」を拾うこと。

理由:

- 原作との差分だけでは、即値変更、hook、データ変更、追加routine本体が混ざる。
- 4096B跡地は旧ステージデータを `EA` 初期化しているため、差分が大きく出る。
- 本当に移動したいのは、customizerが追加したroutine本体。
- そのため `RESERVED_SPANS`、書き込み関数、`bytes.fromhex()` などの実装定義から拾う方が確実。

## 整理方針

- 4096B内に再注入されている処理を棚卸しする。
- PRG0の他の場所に散っている追加処理も棚卸しする。
- 本来一連の機能なのに、空き容量の都合で2つ以上に分割された処理を見つける。
- メインプログラム中の隙間へ差し込まれた追加処理を見逃さない。
- 場所依存がない追加処理は、4096B跡地側へ集約する候補にする。
- 即値パッチ、ジャンプ先変更、原作処理そのものの変更は、追加routine本体と別扱いにする。

## 旧配置を救済・掃除しないルール

この整理は、これから新しく保存するROMの追加routine配置を変える作業である。
過去に作ったROMや旧配置入りROMを救済、掃除、移行する作業ではない。

- 新しい配置へroutine本体を書くだけにする。
- hookや参照先は新しい配置へ向ける。
- 旧分散配置に対して、保存時に `EA` / `00` などを書いて消さない。
- 旧分散配置の元データを復元しようとしない。
- 旧hookや旧routineを互換目的で受け入れない。
- 旧配置の下にもともと何があったかを保証できないため、「きれいに戻す」処理は入れない。
- 旧配置跡は、台帳と差分確認で今後の整理候補として扱うだけにする。

## 現在の機械棚卸し

`magatu_skc.core.*` の `RESERVED_SPANS` から、PRG0範囲の予約を抽出した。

生の抽出結果:

- PRG0予約件数: 75件
- 生合計: 2331B
- 重複をまとめた実占有: 2331B

4096B跡地内:

- 生合計: 1923B
- 実占有: 1923B
- セグメント数: 12

4096B跡地外:

- 生合計: 408B
- 実占有: 408B
- セグメント数: 12

現行の `RESERVED_SPANS` 起点では重複予約なし。
原作コード上のhook、即値変更、原作データ復元はこの集計とは別に扱う。

## customizer実装起点の追加プログラム量

`RESERVED_SPANS` を持つ core モジュールを実装起点で集計した。
これは原作ROMとの差分ではなく、customizerが「ここへ書く」と定義している
PRG0追加プログラム側から見た一覧。

| module | 4096B内 entries | 4096B内 raw | 4096B外 entries | 4096B外 raw |
|---|---:|---:|---:|---:|
| `final_stage_redirect` | 1 | 13B | 0 | 0B |
| `gargoyle_variant` | 1 | 90B | 0 | 0B |
| `key_enemy_runtime` | 15 | 286B | 0 | 0B |
| `m66_expander` | 1 | 33B | 1 | 3B |
| `panel_monster_stage_variant` | 23 | 746B | 0 | 0B |
| `panel_monster_variant` | 0 | 0B | 7 | 396B |
| `saramandor_variant` | 1 | 165B | 0 | 0B |
| `solomon_seal_block` | 1 | 11B | 0 | 0B |
| `spark_ball_variant` | 8 | 191B | 0 | 0B |
| `stage_announcement` | 15 | 230B | 0 | 0B |
| `title_screen` | 2 | 96B | 3 | 9B |
| `warp_zone_trial` | 1 | 128B | 0 | 0B |

この表を最初の移動候補リストの入口にする。
原作差分は、この一覧に漏れた追加処理や、実際のhook/即値変更の検証に使う。

## 機能単位の初期分類

実装定義から拾った追加プログラムを、機能単位で仮分類する。
ここではまだ移動しない。移動可否の判断材料を作る段階。

| 機能 | 主なmodule | 現在位置 | 量 | 初期判断 |
|---|---|---|---:|---|
| Stage start announcement | `stage_announcement` | `0x6B06-0x6BEB` | 230B | 8項目版へ更新済み。右下表示は `MIRROR LINK`。 |
| Key/Fairy enemy runtime | `key_enemy_runtime` | bank0 cave中心、1片だけ4096B内、1片は `0x5005-0x500F` | 286B raw | 分割が多い。機能単位ではまとめたいが、複数hookから入るので呼び出し元確認が必要。 |
| Spark Ball variant | `spark_ball_variant` | `0x6280-0x633E` | 191B raw | Spark Ball追加routineはproperty selectorも含めてpacked blockへ集約済み。 |
| Panel Monster base variant | `panel_monster_variant` | bank0 cave、`0x5BEF`、`0x40D2` | 396B raw | 新規保存ROMでは書かない。旧base候補跡は保存時に掃除しない。 |
| Panel Monster A/B/C final runtime | `panel_monster_stage_variant` | `0x6496-0x677F` + PRG1 loader/settings/helper | 746B raw + 114B PRG1 | 現行Panel runtime。速度、AI、弾、classifier、marker、property/animation hook本体を新cleanupブロックへ集約。Spark selectorは `0x632A` に置き、Panel fallback先だけ新hookへ向ける。 |
| Gargoyle variant | `gargoyle_variant` | bank0 cave `0x3D0B-0x3D88` | 90B | まとまっている。移すならhook先3か所を更新するだけか確認する。 |
| Saramandor variant | `saramandor_variant` | bank0 cave `0x3E10-0x3F4F` | 165B | まとまっているが複数hookから入る。移動候補だが優先度は中。 |
| Final stage redirect | `final_stage_redirect` | `0x6342-0x634E` | 13B | 4096B先頭側へ移動済み。旧 `0x3D28-0x3D34` は新規出力では書かない。 |
| Solomon Seal block helper | `solomon_seal_block` | `0x7005-0x700F` | 11B | 4096B末尾に既にいる。仮置き末尾設計と相性がよい。 |
| Wide title / ending PRG0 helper | `title_screen` | `0x6929-0x697F` + hooks `0x3719-0x371B`, `0x4BC3-0x4BC5`, `0x4CD1-0x4CD3`, `0x4D9B-0x4D9D`, `0x6871-0x6879` | 87B body + hooks | 旧 `0x4C5F-0x4CB5` のhelper本体を4096B側へ移動済み。`0x4C5F-0x4CC5` は原作decoderへ戻す。 |

## 最初に見るべき移動候補

現時点では、いきなり最大のPanel runtimeへ手を入れない。
先に小さく、機能単位が見えやすいものから確認する。

優先候補:

1. `stage_announcement`
   - 完了: `0x6B06-0x6BEB` へ移設し、8項目版へ更新済み。
2. `spark_ball_variant` のAI wrapper類
   - 完了: property selectorも含めて `0x6280-0x633E` へ集約済み。
3. `gargoyle_variant`
   - 理由: 90Bでまとまっている。
   - 注意: hook先と設定値読み書きが移動後も追従するか確認する。

後回し:

- `panel_monster_stage_variant`
  - 理由: 最大かつ複数機能が絡む。先に小さい移動で手順を固める。
- `title_screen`
  - 理由: wide title所有領域であり、PRG0汎用整理とは別扱い。
- 即値変更・hook命令本体
  - 理由: routine本体ではない。移動対象ではなく参照更新対象。

## Stage announcement 移動結果

最初の具体候補として `stage_announcement` を見る。

現在の移設結果:

`stage_announcement` は、Warp Mirror Mode runtime後の24B緩衝を空けて
`0x6B06` / `$EAF6` から配置する。旧 `0x6010-0x60CB` には新規出力で書かない。
保存時に旧配置の残骸掃除はしない。

| part | new file | new CPU | size |
|---|---:|---:|---:|
| buffer before | `0x6AEE-0x6B05` | `$EADE-$EAF5` | 24B |
| `MAIN` | `0x6B06-0x6B23` | `$EAF6-$EB13` | 30B |
| `MASK_TABLE` | `0x6B24-0x6B28` | `$EB14-$EB18` | 5B |
| `DRAW` | `0x6B29-0x6B41` | `$EB19-$EB31` | 25B |
| `PTR_TABLE` | `0x6B42-0x6B51` | `$EB32-$EB41` | 16B |
| `KEY_GATE` | `0x6B52-0x6B5E` | `$EB42-$EB4E` | 13B |
| `FAIRY_GATE` | `0x6B5F-0x6B6B` | `$EB4F-$EB5B` | 13B |
| `MIRROR_LINK_GATE` | `0x6B6C-0x6B78` | `$EB5C-$EB68` | 13B |
| `DARK ROOM` | `0x6B79-0x6B85` | `$EB69-$EB75` | 13B |
| `FIRE LOSS` | `0x6B86-0x6B92` | `$EB76-$EB82` | 13B |
| `HIDDEN DOOR` | `0x6B93-0x6BA1` | `$EB83-$EB91` | 15B |
| `FIRE SEALED` | `0x6BA2-0x6BB0` | `$EB92-$EBA0` | 15B |
| `SPELL SEALED` | `0x6BB1-0x6BC0` | `$EBA1-$EBB0` | 16B |
| `KEY ENEMY` | `0x6BC1-0x6BCD` | `$EBB1-$EBBD` | 13B |
| `FAIRY ENEMY` | `0x6BCE-0x6BDC` | `$EBBE-$EBCC` | 15B |
| `MIRROR LINK` | `0x6BDD-0x6BEB` | `$EBCD-$EBDB` | 15B |
| buffer after | `0x6BEC-0x6C03` | `$EBDC-$EBF3` | 24B |

合計:

- `stage_announcement` 本体: 230B
- 前後の緩衝: 24B + 24B
- 残り空き: `0x6C04-0x7004` / `$EBF4-$EFF4` の1,025B

新規配置では使わなくなる旧候補:

- 旧 `0x6010-0x60B3`: 164B
- 旧 `0x60B4-0x60CB`: 24B
- 既存ROM救済や旧配置掃除のために、ここを保存時に自動で上書きしない。

実装で確認したこと:

- 新本体 `0x6B06-0x6BEB` が、他の `RESERVED_SPANS` と重ならないこと。
- 前後の24B緩衝を本体reserveとして扱わないこと。
- `MAIN` 内の `CPU_MASK_TABLE`、`CPU_DRAW`、`CPU_KEY_GATE`、`CPU_FAIRY_GATE`、`CPU_WARP_GATE` が新アドレスへ更新されること。
- `DRAW` 内の `CPU_PTR_TABLE` が新アドレスへ更新されること。
- `PTR_TABLE` が新scriptアドレスを指すこと。
- `$9061` hook が新 `CPU_MAIN = $EAF6` を呼ぶこと。

## Initial draw low classifier 移動結果

`m66.py` のひび割れブロック内アイテム用初期描画低値分類helperを、
4断片から1本体へまとめる。

理由:

- 現行の48Bは、空き断片へ分散配置するために遠距離JMPを含んでいる。
- ブロック系処理は今後の整理でぶつかる可能性が高い。
- ひび割れ/透明ブロック系は仕様確認しながら扱う必要があるため、小さい単位で先に移す。
- 容量圧縮が主目的ではなく、断片削減と管理しやすさを優先する。

移動前:

| part | old file | old CPU | size |
|---|---:|---:|---:|
| helper body | `0x6774-0x6789` | `$E764-$E779` | 22B |
| cont1 | `0x6798-0x67A1` | `$E788-$E791` | 10B |
| cont2 | `0x63FC-0x6403` | `$E3EC-$E3F3` | 8B |
| mask table | `0x62ED-0x62F4` | `$E2DD-$E2E4` | 8B |

移動後:

| part | new file | new CPU | size |
|---|---:|---:|---:|
| packed helper + table | `0x60CC-0x60F5` | `$E0BC-$E0E5` | 42B |
| free | `0x60F6-0x610D` | `$E0E6-$E0FD` | 24B |

合計:

- 旧分散配置: 48B
- 新本体: 42B
- 直後の空き: 24B
- この候補で使う範囲: `0x60CC-0x610D`
- 次の配置開始候補: `0x610E`

新規配置では使わなくなる旧候補:

- `0x62ED-0x62F4`
- `0x63FC-0x6403`
- `0x6774-0x6789`
- `0x6798-0x67A1`
- 現行では `0x6774-0x677F` はPanel Variant final block内、`0x6798-0x67A1` はRoomFlag packed cave runtime内で再利用済み。
- 既存ROM救済や旧配置掃除のために、ここを保存時に自動で上書きしない。

実装で確認すること:

- `$9620` hook が新 `CPU_HELPER = $E0BC` を呼ぶこと。
- packed helper内のtable参照が新 `CPU_TABLE = $E0DE` を指すこと。
- 新本体 `0x60CC-0x60F5` が、他の `RESERVED_SPANS` と重ならないこと。
- 新空き `0x60F6-0x610D` を本体reserveとして扱わないこと。
- 旧4断片へ消去・復元・互換目的の書き込みを入れないこと。

## Key/Fairy enemy runtime 移動結果

`key_enemy_runtime.py` の敵から鍵が出るruntimeを、
15断片から1本体へまとめる。

理由:

- `0x6465-0x6473` の15Bだけでなく、鍵敵runtime全体が多数の小断片に分散している。
- 旧配置はbank0 caveや4096B跡地外にも散っており、今後のPRG0整理で何度もぶつかる。
- 敵から鍵が出る処理は機能単位で一体なので、断片単位ではなくruntime全体をまとめる方が安全に管理できる。
- `_migrate_old_layout()` は旧ROM救済・旧配置掃除なので、原作ROMからの新規保存だけを対象にする今回の方針から外す。

移動前:

| part | old file | old CPU | size |
|---|---:|---:|---:|
| item tile recorder | `0x3C27-0x3C2D` | `$BC17-$BC1D` | 7B |
| status writer | `0x3C52-0x3C57` | `$BC42-$BC47` | 6B |
| fall-death handler | `0x3CC8-0x3CDD` | `$BCB8-$BCCD` | 22B |
| defeat chunks | `0x3E3F-0x3E4C / 0x3E84-0x3E8D / 0x3EA4-0x3EAE / 0x3EC6-0x3ECC / 0x3F03-0x3F0F / 0x3FFD-0x400E / 0x4201-0x420F` | mixed | 88B |
| door-light helper | `0x3F60-0x3F78` | `$BF50-$BF68` | 25B |
| dropped-key handler | `0x4190-0x41E5` | `$C180-$C1D5` | 86B |
| initial-slot binder | `0x41E6-0x41FF` | `$C1D6-$C1EF` | 26B |
| fall-slot compare | `0x5005-0x500F` | `$CFF5-$CFFF` | 11B |
| status value helper | `0x6465-0x6473` | `$E455-$E463` | 15B |

移動後:

| part | new file | new CPU | size |
|---|---:|---:|---:|
| packed key/fairy enemy runtime | `0x610E-0x622B` | `$E0FE-$E21B` | 286B |
| free | `0x622C-0x6243` | `$E21C-$E233` | 24B |

合計:

- 旧分散配置: 286B
- 新本体: 286B
- 直後の空き: 24B
- この候補で使う範囲: `0x610E-0x6243`
- 次の配置開始候補: `0x6244`

新規配置では使わなくなる旧候補:

- `0x3C27-0x3C2D`
- `0x3C52-0x3C57`
- `0x3CC8-0x3CDD`
- `0x3E3F-0x3E4C`
- `0x3E84-0x3E8D`
- `0x3EA4-0x3EAE`
- `0x3EC6-0x3ECC`
- `0x3F03-0x3F0F`
- `0x3F60-0x3F78`
- `0x3FFD-0x400E`
- `0x4190-0x41E5`
- `0x41E6-0x41FF`
- `0x4201-0x420F`
- `0x5005-0x500F`
- `0x6465-0x6473`
- 既存ROM救済や旧配置掃除のために、ここを保存時に自動で上書きしない。

実装で確認すること:

- 各hookが新runtime内のCPUアドレスを指すこと。
- dropped-key handler内の内部分岐先が新本体内アドレスを指すこと。
- fall-death handlerが新 `CPU_FALL_KEY_COMPARE = $E211` と新 `CPU_ENEMY_DEFEAT + 3` を呼ぶこと。
- 新本体 `0x610E-0x622B` が、他の `RESERVED_SPANS` と重ならないこと。
- 新空き `0x622C-0x6243` を本体reserveとして扱わないこと。
- `_migrate_old_layout()`、旧hook受け入れ、旧配置消去を入れないこと。

## Visible item in-block runtime 移動結果

`room_flags.py` の透明ブロック内アイテムruntimeを、
2断片から1本体へまとめる。

理由:

- `0x675C-0x6773` と `0x678C-0x6797` は、どちらも当時の `$C0F0` 特殊セル変換scannerから使われる同一機能の小routine。
- helper内部の相対分岐で旧 `$E77C` extensionへ飛ぶ構造だったため、離れた2断片として置く必要はない。
- 4096B跡地の先頭側へ寄せることで、後続の `0x67xx` 周辺整理時にぶつかる小断片を減らせる。

移動前:

| part | old file | old CPU | size |
|---|---:|---:|---:|
| visible item bitmask helper | `0x675C-0x6773` | `$E74C-$E763` | 24B |
| white in-block runtime extension | `0x678C-0x6797` | `$E77C-$E787` | 12B |

移動後:

| part | new file | new CPU | size |
|---|---:|---:|---:|
| packed visible item in-block runtime | `0x6244-0x6267` | `$E234-$E257` | 36B |
| free | `0x6268-0x627F` | `$E258-$E26F` | 24B |

合計:

- 旧分散配置: 36B
- 新本体: 36B
- 直後の空き: 24B
- この候補で使う範囲: `0x6244-0x627F`
- 次の配置開始候補: `0x6280`

新規配置では使わなくなる旧候補:

- `0x675C-0x6773`
- `0x678C-0x6797`
- 現行では `0x675C-0x6773` はPanel Variant final block内、`0x678C-0x6797` はPanel直後24B buffer内。
- 既存ROM救済や旧配置掃除のために、ここを保存時に自動で上書きしない。

実装で確認すること:

- 当時の `$C0F0` / 現行 `$E81D` scanner内の `JSR` が新 `$E234` を指すこと。
- helper内部の `BCC` が新 `$E24C` extensionへ届くこと。
- 新本体 `0x6244-0x6267` が、他の予約と重ならないこと。
- 新空き `0x6268-0x627F` を本体reserveとして扱わないこと。
- 旧2断片へ消去・復元・互換目的の書き込みを入れないこと。

## Spark Ball runtime 移動結果

`spark_ball_variant.py` の追加routine 8断片を1本体へまとめる。

理由:

- Spark Ball系は pause、AI wrapper、animation、透明OAM hide が複数箇所に散っている。
- `0x2569` property selector は、原作の敵property table取得そのものではなく、Panel Monster発射処理跡へ置いた追加routineだった。
- Spark Ball packed runtime直後の24B空きはこの種の入れ忘れを吸収するための緩衝なので、property selectorをそこへ移す。
- Spark Ball機能単位でまとめられ、検証もSpark Ball系として一括で行える。

移動前:

| part | old file | old CPU | size |
|---|---:|---:|---:|
| Dragon slow AI wrapper | `0x3FE8-0x3FF7` | `$BFD8-$BFE7` | 16B |
| Dragon fast AI wrapper | `0x3D36-0x3D45` | `$BD26-$BD35` | 16B |
| Transparent Golem-ID AI wrapper | `0x681C-0x6832` | `$E80C-$E822` | 23B |
| pause hook | `0x6FD4-0x7004` | `$EFC4-$EFF4` | 49B |
| property selector | `0x2569-0x257D` | `$A559-$A56D` | 21B |
| animation hook | `0x4FEE-0x5004` | `$CFDE-$CFF4` | 23B |
| animation setter | `0x3EFA-0x3F02` | `$BEEA-$BEF2` | 9B |
| transparent OAM hide hook | `0x3ED7-0x3EF8` | `$BEC7-$BEE8` | 34B |

移動後:

| part | new file | new CPU | size |
|---|---:|---:|---:|
| packed Spark Ball runtime | `0x6280-0x633E` | `$E270-$E32E` | 191B |
| free | `0x633F-0x6341` | `$E32F-$E331` | 3B |

合計:

- 旧分散配置: 191B
- 新本体: 191B
- 直後の空き: 3B
- この候補で使う範囲: `0x6280-0x6341`
- 次の配置開始候補: `0x6342`

新規配置では使わなくなる旧候補:

- `0x3FE8-0x3FF7`
- `0x3D36-0x3D45`
- `0x681C-0x6832`
- `0x6FD4-0x7004`
- 現行では `0x681C-0x6832` はRoomFlag packed cave runtime内、`0x6FD4-0x7004` はmapper66 l_a1 body後の空き `0x69B9-0x7004` 内。
- `0x2569-0x257D`
- `0x4FEE-0x5004`
- `0x3EFA-0x3F02`
- `0x3ED7-0x3EF8`
- 既存ROM救済や旧配置掃除のために、ここを保存時に自動で上書きしない。

実装で確認すること:

- Dragon/Golem AI tableが新 `$E270/$E280/$E290` を指すこと。
- `$AB13` pause dispatchが新 `$E2A7` を指すこと。
- `$A2CC` property dispatchが新 `$E31A` を指すこと。
- `$8B05` animation dispatchが新 `$E2D8` を指すこと。
- animation hook内のSpark setter JMPが新 `$E2EF` を指すこと。
- `$85FA` transparent OAM dispatchが新 `$E2F8` を指すこと。
- pause digit設定とtransparent period設定のROM内offsetが、新pause/OAM routine内の相対位置で読めること。
- `$A556-$A558` Panel final fire hook siteにSpark property selector本体を埋め込まないこと。
- `$A559-$A574` の原作Panel fire本体は、hook後は通常実行されないが、空き扱いせず原作バイトのまま残すこと。
- 旧8断片へ消去・復元・互換目的の書き込みを入れないこと。

## Final stage redirect 移動結果

`final_stage_redirect.py` の13B runtimeを、bank0 cave側から4096B跡地の先頭側へ移す。

理由:

- Panel Monster系ではなく、単独機能の小routineとして切り出せる。
- 呼び出し元は `$C6F5` の `JSR` 1か所だけで、移動後は `JSR $E332` に変える。
- 旧配置 `0x3D28-0x3D34` はGargoyle周辺のbank0 cave内にあり、今後の周辺整理でぶつかりやすい。

移動前:

| part | old file | old CPU | size |
|---|---:|---:|---:|
| final-stage redirect runtime | `0x3D28-0x3D34` | `$BD18-$BD24` | 13B |

移動後:

| part | new file | new CPU | size |
|---|---:|---:|---:|
| final-stage redirect runtime | `0x6342-0x634E` | `$E332-$E33E` | 13B |
| free | `0x634F-0x6366` | `$E33F-$E356` | 24B |

合計:

- 旧配置: 13B
- 新本体: 13B
- 直後の空き: 24B
- この候補で使う範囲: `0x6342-0x6366`
- 次の配置開始候補: `0x6367`

新規配置では使わなくなる旧候補:

- `0x3D28-0x3D34`
- 既存ROM救済や旧配置掃除のために、ここを保存時に自動で上書きしない。

実装で確認すること:

- `$C6F5` clear後hookが新 `$E332` を指すこと。
- runtime内の戻り先が原作 `$C70E` のままであること。
- `0x3D28-0x3D34` へ消去・復元・互換目的の書き込みを入れないこと。

## Gargoyle variant 移動結果

`gargoyle_variant.py` の強化ガーゴイルruntimeを、
3断片から1本体へまとめる。

理由:

- Gargoyle系は cooldown gate、materialize gate、cooldown tail の3断片に分かれている。
- 3断片は同一機能で、hook先2か所から入るだけなので、機能単位で連続配置できる。
- bank0 caveの `$BCFB-$BD78` 周辺はPanel/Spark/Final-stageの整理候補と隣接しており、今後の整理でぶつかりやすい。
- 既存の相対分岐は、新しい連続配置では `BEQ +0` で直後のtailへ落とせる。

移動前:

| part | old file | old CPU | size |
|---|---:|---:|---:|
| enhanced cooldown gate | `0x3D0B-0x3D26` | `$BCFB-$BD16` | 28B |
| slow-Bullet gate | `0x3D4B-0x3D7E` | `$BD3B-$BD6E` | 52B |
| enhanced cooldown tail | `0x3D7F-0x3D88` | `$BD6F-$BD78` | 10B |

移動後:

| part | new file | new CPU | size |
|---|---:|---:|---:|
| packed Gargoyle runtime | `0x6367-0x63C0` | `$E357-$E3B0` | 90B |
| free | `0x63C1-0x63D8` | `$E3B1-$E3C8` | 24B |

合計:

- 旧分散配置: 90B
- 新本体: 90B
- 直後の空き: 24B
- この候補で使う範囲: `0x6367-0x63D8`
- 次の配置開始候補: `0x63D9`

新規配置では使わなくなる旧候補:

- `0x3D0B-0x3D26`
- `0x3D4B-0x3D7E`
- `0x3D7F-0x3D88`
- 既存ROM救済や旧配置掃除のために、ここを保存時に自動で上書きしない。

実装で確認すること:

- `$AE6F` materialize hook が新 `$E357` を指すこと。
- `$AE48` cooldown hook が新 `$E38B` を指すこと。
- `gargoyle_hack.py` の通常cooldown読み書きが新runtime内の値を読むこと。
- cooldown gate末尾の `BEQ` が新 `$E3A7` tailへ届くこと。
- 新本体 `0x6367-0x63C0` が、他の予約と重ならないこと。
- 新空き `0x63C1-0x63D8` を本体reserveとして扱わないこと。
- 旧3断片へ消去・復元・互換目的の書き込みを入れないこと。

## Saramandor variant 移動結果

`saramandor_variant.py` のSaramandor #2 Bullet variant runtimeを、
4断片から1本体へまとめる。

理由:

- Saramandor系は spawn setup、substatus、flame behavior、distance check の4断片に分かれている。
- 4断片は同一機能で、hook先から個別entryへ入るだけなので、機能単位で連続配置できる。
- bank0 caveの `$BE00-$BF3F` 周辺はPanel Variantや旧Key/Spark跡と隣接しており、今後の整理でぶつかりやすい。
- Panel Monster本体より小さく、Gargoyleの次に単独で確認しやすい。

移動前:

| part | old file | old CPU | size |
|---|---:|---:|---:|
| spawn setup | `0x3E10-0x3E3E` | `$BE00-$BE2E` | 47B |
| substatus | `0x3E50-0x3E71` | `$BE40-$BE61` | 34B |
| flame behavior | `0x3E90-0x3EA3` | `$BE80-$BE93` | 20B |
| distance check | `0x3F10-0x3F4F` | `$BF00-$BF3F` | 64B |

移動後:

| part | new file | new CPU | size |
|---|---:|---:|---:|
| packed Saramandor runtime | `0x63D9-0x647D` | `$E3C9-$E46D` | 165B |
| free | `0x647E-0x6495` | `$E46E-$E485` | 24B |

合計:

- 旧分散配置: 165B
- 新本体: 165B
- 直後の空き: 24B
- この候補で使う範囲: `0x63D9-0x6495`
- 次の配置開始候補: `0x6496`

新規配置では使わなくなる旧候補:

- `0x3E10-0x3E3E`
- `0x3E50-0x3E71`
- `0x3E90-0x3EA3`
- `0x3F10-0x3F4F`
- 既存ROM救済や旧配置掃除のために、ここを保存時に自動で上書きしない。

実装で確認すること:

- `$B105` spawn hook が新 `$E3C9` を呼ぶこと。
- `$B0A9` substatus hook が新 `$E3F8` を呼ぶこと。
- `$B0C6` flame behavior hook が新 `$E41A` を呼ぶこと。
- `$B1E9` distance hook が新 `$E42E` へJMPすること。
- `$B121` child mark restore、`$AFD1` bullet init、`$866D` speed guard受け入れは今回の移動で変えないこと。
- 新本体 `0x63D9-0x647D` が、他の予約と重ならないこと。
- 新空き `0x647E-0x6495` を本体reserveとして扱わないこと。
- 旧4断片へ消去・復元・互換目的の書き込みを入れないこと。

## Panel Variant final runtime ブロック

`panel_monster_stage_variant.py` のA/B/C Panel Variant final runtimeを、
既存の旧Panel配置へ上書きせず、4096B跡地の新しい空きへ一式で書く。

理由:

- 旧Panel base runtime 396Bは新規保存ROMでは書かない。
- A/B/C final runtimeと通常Panel/Borrowed Panelのhookは、この新ブロックへ切り替える。
- 今回は旧ROM救済や旧配置掃除はしない。

移動後:

| part | new file | new CPU | size |
|---|---:|---:|---:|
| Panel Variant final runtime block | `0x6496-0x677F` | `$E486-$E76F` | 746B |
| free buffer | `0x6780-0x6797` | `$E770-$E787` | 24B |
| RoomFlag packed cave runtime | `0x6798-0x6870` | `$E788-$E860` | 217B |

合計:

- A/B/C final runtime実体: 746B
- 新ブロック予約: 746B
- Panel直後の緩衝空き: 24B (`0x6780-0x6797`)
- RoomFlag cave runtime: 217B (`0x6798-0x6870`)
- RoomFlag後の空き: 1940B (`0x6871-0x7004`)
- この候補で使う範囲: `0x6496-0x6870`
- RAM新規使用: なし
- PRG1新規使用: なし

この段階の差し引き:

- 旧base Panel runtime 396Bは新規出力では書かない。
- 旧A/B/C final runtime断片も、このA/B/C applyでは新ブロックへ切り替える。
- 新A/B/C final + PRG1の予約unionは848B。
- 変更前の旧base+旧A/B/C final+PRG1の予約unionは1005B。
- 旧base停止後は-157B。

実装で確認すること:

- `$A556` fire hook が新 `$E486` を指すこと。
- `$AFBB` Bullet hook が新 `$E737` を呼ぶこと。
- 新ブロック `0x6496-0x677F` が他の予約と重ならないこと。
- `0x40D2-0x40FF` と `0x5BEF-0x5C0A` へ新規出力で書かないこと。
- Spark Ball property/animation selectorのPanel fallback先が `$E73A` / `$E748` を指すこと。
- 新空き `0x6780-0x6797` を本体reserveとして扱わないこと。
- RoomFlag packed cave runtimeが `0x6798-0x6870` に収まり、Panel Variant final blockと重ならないこと。
- 旧base 396Bへ新規出力で書かないこと。
- 旧A/B/C final断片へ消去・復元・互換目的の書き込みを入れないこと。

将来の整理メモ:

- Panel Variant の PRG1 loader/settings と RAM `$0740-$0745` は、当時PRG0の空きが足りなかったため、PRG0側の処理量を減らす目的で導入した。
- これは「RAMを使わないと成立しない仕様」というより、PRG0不足を回避するために一部設定を部屋ロード時RAMへ逃がした設計。
- 将来RAM不足が問題になった場合は、Panel Variant の `$0740-$0745` 使用と PRG1 settings table を整理対象にする。
- ただし今は動作中の仕様なので、PRG0整理作業のついでに勝手に消さない。RAM整理を目的にした別作業で、使用量、代替配置、PRG0増加量を出して判断する。

## RoomFlag cave runtime ブロック

`room_flags.py` のbank0 cave runtimeを、Panel Variant final runtime直後の24Bを空けた後ろへ集約する。

理由:

- 旧bank0 cave側にRoomFlag小routineが散っていて、今後の整理対象と混ざりやすい。
- 画像上の連続空き `0x6780-0x7004` を、24B緩衝 + RoomFlag本体 + 残り空きとして台帳と実装で一致させる。
- 旧ROM救済や旧配置掃除はしない。新規保存ROMで旧位置へ書かなくなるだけ。

移動後:

| part | old file | old CPU | new file | new CPU | size |
|---|---:|---:|---:|---:|---:|
| Panel直後 buffer | - | - | `0x6780-0x6797` | `$E770-$E787` | 24B |
| LOADER | `0x3BF0-0x3C1D` | `$BBE0-$BC0D` | `0x6798-0x67C5` | `$E788-$E7B5` | 46B |
| MAGICGATE | `0x3C30-0x3C51` | `$BC20-$BC41` | `0x67C6-0x67E7` | `$E7B6-$E7D7` | 34B |
| DOORPREDRAW | `0x3C60-0x3C6A` | `$BC50-$BC5A` | `0x67E8-0x67F2` | `$E7D8-$E7E2` | 11B |
| DARK | `0x3C90-0x3CC7` | `$BC80-$BCB7` | `0x67F3-0x682A` | `$E7E3-$E81A` | 56B |
| dark tempo | `0x3CE0-0x3CE1` | `$BCD0-$BCD1` | `0x682B-0x682C` | `$E81B-$E81C` | 2B |
| special-cell scanner | `0x4100-0x4143` | `$C0F0-$C133` | `0x682D-0x6870` | `$E81D-$E860` | 68B |
| free (RoomFlag単体時点) | - | - | `0x6871-0x7004` | `$E861-$EFF4` | 1940B |

合計:

- RoomFlag runtime実体: 217B
- Panel直後の緩衝空き: 24B
- `0x6780-0x7004` の元空き: 2181B
- RoomFlag単体移動直後の残り空き: 1940B
- 後続のwide-title idle-demo cleanup / Gap fix / Wide title helper / mapper66 l_a1移動後は `0x6871-0x6879` wide-title stub、`0x687A-0x6888` buffer、`0x6889-0x6910` gap_fix、`0x6911-0x6928` buffer、`0x6929-0x697F` wide-title helper、`0x6980-0x6997` buffer、`0x6998-0x69B8` l_a1 body、`0x69B9-0x7004` free。
- RAM新規使用: なし
- PRG1新規使用: なし

実装で確認すること:

- `$9071` hook が `$E788` を指すこと。
- `$8326` hook が `$E7B6` を指すこと。
- `$91CC` hook が `$E7D8` を指すこと。
- `$8055` hook が `$E7E3` を指すこと。
- `$909A` hook が `$E81D` を指すこと。
- DARK tempo比較が `$E81B/$E81C` を参照すること。
- 旧RoomFlag配置へ新規出力で書かないこと。

## Warp Mirror Mode runtime

`warp_zone_trial.py` のStage4固定検証runtimeを、StageExt byte0 bit5でON/OFFするワープミラーモードruntimeへ置き換える。

移動/増分:

| part | old file | old CPU | new file | new CPU | size |
|---|---:|---:|---:|---:|---:|
| buffer before Warp Mirror Mode runtime | - | - | `0x6A56-0x6A6D` | `$EA46-$EA5D` | 24B |
| Warp Mirror Mode runtime | `0x6A56-0x6AB4` | `$EA46-$EAA4` | `0x6A6E-0x6AED` | `$EA5E-$EADD` | 128B |
| buffer after warp runtime | `0x6AB5-0x7004` | `$EAA5-$EFF4` | `0x6AEE-0x6B05` | `$EADE-$EAF5` | 24B |
| Stage start announcement 8 entries | - | - | `0x6B06-0x6BEB` | `$EAF6-$EBDB` | 230B |
| buffer after Stage start announcement | - | - | `0x6BEC-0x6C03` | `$EBDC-$EBF3` | 24B |
| free after announcement move | - | - | `0x6C04-0x7004` | `$EBF4-$EFF4` | 1025B |
| PRG1 stage flag helper | - | - | `0x8A76-0x8A81` | `$8A66-$8A71` | 12B |
| PanelVariant PRG1 reserve | `0x8A76-0x8E7F` | `$8A66-$8E6F` | `0x8A82-0x8E7F` | `$8A72-$8E6F` | 1022B |

合計:

- PRG0 runtime実体: 95B -> 128B (+33B)
- PRG0後続空き: 1360B -> 1303B
- PRG1新規使用: 12B
- PRG1 PanelVariant reserve: 1034B -> 1022B
- RAM新規使用: なし。既存 `$0770` を bit5=mode / bit6=cooldown に再定義。

実装で確認すること:

- Panel Variant combined loaderが最後に `$8A66` helperへ飛び、helperがTransparent Seal suppress guardへ戻すこと。
- StageExt byte0 bit5がONの面だけ `$0770` bit5が立つこと。
- `$C551` hookは常時入れること。Warp Mirror Mode OFF面では、`$0770` bit5=0によりPRG0 runtime内で原作アイテムセル判定へ戻る。
- ON面で鏡セル `$05` に触れると、同じ部屋の別の `$05` セルへ移動し、item pickup SE `$0D` が鳴ること。

## Gap fix runtime ブロック

`gap_fix.py` の落下中横穴侵入安定化runtimeを、RoomFlag packed cave runtime直後の24Bを空けた後ろへ移す。

理由:

- CAVE本体は保存ROM構造固定のため毎回同じ位置へ書く。
- チェックボックスON/OFFは `$8784` hook を `JMP $E879` にするか原作命令へ戻すかだけで切り替える。
- CAVE本体は内部絶対JMPなしで、hook `$8784` のJMP先だけを新CPUへ変えれば移動できる。
- 旧ROM救済や旧配置掃除はしない。新規保存ROMで旧位置へ書かなくなるだけ。

移動後:

| part | old file | old CPU | new file | new CPU | size |
|---|---:|---:|---:|---:|---:|
| wide-title idle-demo cleanup | `0x3C1E-0x3C26` | `$BC0E-$BC16` | `0x6871-0x6879` | `$E861-$E869` | 9B |
| RoomFlag後 buffer | - | - | `0x687A-0x6888` | `$E86A-$E878` | 15B |
| gap_fix runtime | `0x4010-0x4097` | `$C000-$C087` | `0x6889-0x6910` | `$E879-$E900` | 136B |
| free buffer | - | - | `0x6911-0x6928` | `$E901-$E918` | 24B |
| wide-title PRG0 helpers | `0x4C5F-0x4CB5` | `$CC4F-$CCA5` | `0x6929-0x697F` | `$E919-$E96F` | 87B |
| free buffer | - | - | `0x6980-0x6997` | `$E970-$E987` | 24B |
| mapper66 l_a1 body | `0x1985-0x19A5` | `$9975-$9995` | `0x6998-0x69B8` | `$E988-$E9A8` | 33B |
| free | - | - | `0x69B9-0x7004` | `$E9A9-$EFF4` | 1612B |

合計:

- Gap fix runtime実体: 136B
- wide-title idle-demo cleanup実体: 9B
- RoomFlag後の緩衝空き: 15B
- RoomFlag後の元空き: 1940B
- mapper66 l_a1移動後の残り空き: 1612B
- RAM新規使用: なし
- PRG1新規使用: なし

実装で確認すること:

- チェックON時は `$8784` hook が `JMP $E879` (`4C 79 E8`) を指すこと。
- チェックOFF時も新本体 `0x6889-0x6910` は書かれ、`$8784` hook は原作 `A0 0B 91` のままであること。
- 新本体 `0x6889-0x6910` が他の予約と重ならないこと。
- 旧 `0x4010-0x4097` へ新規出力で書かないこと。
- 落下中に左右を押して横穴へ入る挙動が維持されること。

## 4096B跡地内の現行予約

| file | CPU | size | 原作状態 | module |
|---|---:|---:|---|---|
| `0x6010-0x60CB` | `$E000-$E0BB` | 188B | `EA` | free; old `stage_announcement` area no longer written |
| `0x60CC-0x60F5` | `$E0BC-$E0E5` | 42B | `EA` | `m66.initial_draw_low_classifier` |
| `0x610E-0x622B` | `$E0FE-$E21B` | 286B | `EA` | `key_enemy_runtime` |
| `0x6244-0x6267` | `$E234-$E257` | 36B | `EA` | `room_flags.visible_item_inblock` |
| `0x6280-0x633E` | `$E270-$E32E` | 191B | `EA` | `spark_ball_variant` |
| `0x633F-0x6341` | `$E32F-$E331` | 3B | `EA` | free |
| `0x6342-0x634E` | `$E332-$E33E` | 13B | `EA` | `final_stage_redirect` |
| `0x6367-0x63C0` | `$E357-$E3B0` | 90B | `EA` | `gargoyle_variant` |
| `0x63D9-0x647D` | `$E3C9-$E46D` | 165B | `EA` | `saramandor_variant` |
| `0x6496-0x677F` | `$E486-$E76F` | 746B | `EA` | `panel_monster_stage_variant` |
| `0x6780-0x6797` | `$E770-$E787` | 24B | `EA` | free buffer |
| `0x6798-0x6870` | `$E788-$E860` | 217B | `EA` | `room_flags.packed_cave_runtime` |
| `0x6871-0x6879` | `$E861-$E869` | 9B | `EA` | `title_screen.wide_title_idle_demo_cleanup` |
| `0x687A-0x6888` | `$E86A-$E878` | 15B | `EA` | free buffer |
| `0x6889-0x6910` | `$E879-$E900` | 136B | `EA` | `gap_fix` |
| `0x6911-0x6928` | `$E901-$E918` | 24B | `EA` | free buffer |
| `0x6929-0x697F` | `$E919-$E96F` | 87B | `EA` | `title_screen.wide_title_prg0_helpers` |
| `0x6980-0x6997` | `$E970-$E987` | 24B | `EA` | free buffer |
| `0x6998-0x69B8` | `$E988-$E9A8` | 33B | `EA` | `m66_expander.l_a1_body` |
| `0x69B9-0x69D0` | `$E9A9-$E9C0` | 24B | `EA` | free buffer |
| `0x69D1-0x69FA` | `$E9C1-$E9EA` | 42B | `EA` | `ice_flame_runtime` |
| `0x69FB-0x6A12` | `$E9EB-$EA02` | 24B | `EA` | free buffer |
| `0x6A13-0x6A55` | `$EA03-$EA45` | 67B | `EA` | `spark85_runtime` |
| `0x6A56-0x6A6D` | `$EA46-$EA5D` | 24B | `EA` | free buffer |
| `0x6A6E-0x6AED` | `$EA5E-$EADD` | 128B | `EA` | `warp_zone_trial` |
| `0x6AEE-0x6B05` | `$EADE-$EAF5` | 24B | `EA` | buffer before `stage_announcement` |
| `0x6B06-0x6BEB` | `$EAF6-$EBDB` | 230B | `EA` | `stage_announcement` |
| `0x6BEC-0x6C03` | `$EBDC-$EBF3` | 24B | `EA` | buffer after `stage_announcement` |
| `0x6C04-0x7004` | `$EBF4-$EFF4` | 1025B | `EA` | free |
| `0x7005-0x700F` | `$EFF5-$EFFF` | 11B | `EA` | `solomon_seal_block` |

この範囲は、最終的には4096B先頭側へ詰め直して、routine本体と直後の空きを別管理する候補にする。

## 跡地外の主な整理候補

跡地外のPRG0予約は、現行 `RESERVED_SPANS` 起点では実占有408Bある。
このうち、機能的に場所依存が薄い小routineは4096B側へ集約できる可能性がある。

最初に重点確認する範囲:

- `0x3C27-0x420F`: bank0 cave 系。複数敵runtimeとPanel系が集中している。
- `0x4FEE-0x500F`: Spark Ball animation / key enemy compare 系。
- `0x5BEF-0x5C0A`: 旧Panel property hook候補跡。新規出力では書かない。
- `0x2566-0x2568`: Panel final fire hook。後続 `0x2569-0x2584` は原作Panel fire本体を残す。Spark Ball property selector本体は `0x632A-0x633E` へ移動済み。
- `0x4C5F-0x4CB5`: 旧wide title helper本体。現行は `0x6929-0x697F` へ移動し、`0x4C5F-0x4CC5` は原作decoderへ戻す。

## 原作ROM差分の使い方

原作ROMとの差分は、customizer実装から拾った追加プログラム一覧の検証に使う。
差分だけを根拠に移動対象を決めない。

差分確認では、次を分類する。

- 即値変更
- hook先変更
- 追加routine本体
- データ変更
- 原作データ断片上書き
- メインプログラム中の隙間差し込み

移動候補にするのは、基本的に「場所依存がない追加routine本体」だけ。

## 次の実作業

1. customizer実装からPRG0追加プログラム一覧を作る。
2. `RESERVED_SPANS` だけでなく、実際の書き込み関数と生成されるバイト列を確認する。
3. 一覧を機能単位に分類する。
4. 原作ROMとの差分で、一覧に漏れた追加処理がないか確認する。
5. 4096B跡地外にある追加routine本体のうち、場所依存がないものを移動候補にする。
6. 移動前に、移動元、移動先、バイト数、呼び出し元、残り空きを出す。

## 現時点の判断

4096B跡地内の現行予約1923Bと、跡地外の実占有408Bを単純合算して2331B。
残件は大きな追加routineではなく、旧base Panel、Spark selector、hook/即値系を個別確認する段階。

ただし、すべてを機械的に移動してよいわけではない。
hook命令、原作即値変更、タイトル所有領域、原作データ断片上書きは個別確認が必要。
