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

## 初回機械棚卸し

`magatu_skc.core.*` の `RESERVED_SPANS` から、PRG0範囲の予約を抽出した。

生の抽出結果:

- PRG0予約件数: 75件
- 生合計: 2098B
- 重複をまとめた実占有: 1913B

4096B跡地内:

- 生合計: 614B
- 実占有: 614B
- セグメント数: 19

4096B跡地外:

- 生合計: 1484B
- 実占有: 1299B
- セグメント数: 30

重複予約は主に `panel_monster_variant.py` と
`panel_monster_stage_variant.py` の最終runtime差し替え関係で発生している。
これはそのまま移動量として数えない。

## customizer実装起点の追加プログラム量

`RESERVED_SPANS` を持つ core モジュールを実装起点で集計した。
これは原作ROMとの差分ではなく、customizerが「ここへ書く」と定義している
PRG0追加プログラム側から見た一覧。

| module | 4096B内 entries | 4096B内 raw | 4096B外 entries | 4096B外 raw |
|---|---:|---:|---:|---:|
| `final_stage_redirect` | 0 | 0B | 1 | 13B |
| `gargoyle_variant` | 0 | 0B | 3 | 90B |
| `key_enemy_runtime` | 1 | 15B | 14 | 271B |
| `panel_monster_stage_variant` | 10 | 365B | 11 | 327B |
| `panel_monster_variant` | 0 | 0B | 7 | 396B |
| `saramandor_variant` | 0 | 0B | 4 | 165B |
| `solomon_seal_block` | 1 | 11B | 0 | 0B |
| `spark_ball_variant` | 2 | 72B | 6 | 119B |
| `stage_announcement` | 10 | 151B | 1 | 13B |
| `title_screen` | 0 | 0B | 4 | 90B |

この表を最初の移動候補リストの入口にする。
原作差分は、この一覧に漏れた追加処理や、実際のhook/即値変更の検証に使う。

## 機能単位の初期分類

実装定義から拾った追加プログラムを、機能単位で仮分類する。
ここではまだ移動しない。移動可否の判断材料を作る段階。

| 機能 | 主なmodule | 現在位置 | 量 | 初期判断 |
|---|---|---|---:|---|
| Stage start announcement | `stage_announcement` | 主に4096B内、`KEY_GATE`だけ `0x33D0-0x33DC` | 164B | 4096B側へ集約しやすい候補。分割scriptsとmain/draw/tableをまとめ直す対象。 |
| Key/Fairy enemy runtime | `key_enemy_runtime` | bank0 cave中心、1片だけ4096B内、1片は `0x5005-0x500F` | 286B raw | 分割が多い。機能単位ではまとめたいが、複数hookから入るので呼び出し元確認が必要。 |
| Spark Ball variant | `spark_ball_variant` | bank0 cave、`0x2569`、`0x4FEE`、4096B末尾 | 191B raw | `0x2569` はメイン側差し込みに近いので要注意。AI wrapper類は移動候補。 |
| Panel Monster base variant | `panel_monster_variant` | bank0 cave、`0x5BEF`、`0x40D2` | 396B raw | `panel_monster_stage_variant` が上書きする箇所あり。旧/基礎runtimeと最終runtimeを分けて判断する。 |
| Panel Monster A/B/C final runtime | `panel_monster_stage_variant` | 4096B内とbank0 caveに広く分散 | 692B raw | 最大の整理対象。速度、AI、弾、classifier、markerを機能単位に分ける。 |
| Gargoyle variant | `gargoyle_variant` | bank0 cave `0x3D0B-0x3D88` | 90B | まとまっている。移すならhook先3か所を更新するだけか確認する。 |
| Saramandor variant | `saramandor_variant` | bank0 cave `0x3E10-0x3F4F` | 165B | まとまっているが複数hookから入る。移動候補だが優先度は中。 |
| Final stage redirect | `final_stage_redirect` | `0x3D28-0x3D34` | 13B | 小さい。単独で移すより周辺整理時に扱う。 |
| Solomon Seal block helper | `solomon_seal_block` | `0x7005-0x700F` | 11B | 4096B末尾に既にいる。仮置き末尾設計と相性がよい。 |
| Wide title / ending PRG0 helper | `title_screen` | `0x3719-0x371B`, `0x4C5F-0x4CB5` | 90B | タイトル処理の所有領域。一般的な移動候補から外す。 |

## 最初に見るべき移動候補

現時点では、いきなり最大のPanel runtimeへ手を入れない。
先に小さく、機能単位が見えやすいものから確認する。

優先候補:

1. `stage_announcement`
   - 理由: 大半が4096B内にあり、分割scriptsをまとめる目的と合う。
   - 注意: `OFF_KEY_GATE = 0x33D0` だけ4096B外なので、呼び出し元と分岐距離を確認する。
2. `spark_ball_variant` のAI wrapper類
   - 理由: wrapper本体は小さく、場所依存が薄い可能性がある。
   - 注意: `0x2569` property selector はメイン側差し込みに近いので、最初の移動対象にしない。
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

理由:

- 合計164Bで小さい。
- 大半は既に4096B跡地内にある。
- 4096B外に出ているのは `KEY_GATE` 13Bだけ。
- `MAIN`、`DRAW`、`KEY_GATE`、`PTR_TABLE` は生成時にCPUアドレスを埋め込む構造なので、定数を変えれば追従できる可能性が高い。
- 相対分岐は各routine内部だけで閉じている。

注意:

- `$9061` hook は残る。これはroutine本体ではなく呼び出し元変更。
- CHRの `K/P` タイル追加はPRG0整理対象ではない。
- `KEY_GATE` は現在 `0x33D0-0x33DC` にあるため、ここを空けられる可能性がある。

4096B先頭側への移動結果:

4096B跡地は `0x6010` から上へ詰める。
各追加routineは本体と、その直後の空きを別管理する。
空きは空きとして扱い、routine本体のreserveとは書かない。

`stage_announcement` は本体164Bの直後に24Bの空きを置く。
この24Bは将来別処理が入る可能性があるため、管理簿では独立した空きとして見えるようにする。

| part | new file | new CPU | size |
|---|---:|---:|---:|
| `MAIN` | `0x6010-0x6027` | `$E000-$E017` | 24B |
| `MASK_TABLE` | `0x6028-0x602C` | `$E018-$E01C` | 5B |
| `DRAW` | `0x602D-0x6045` | `$E01D-$E035` | 25B |
| `PTR_TABLE` | `0x6046-0x6051` | `$E036-$E041` | 12B |
| `KEY_GATE` | `0x6052-0x605E` | `$E042-$E04E` | 13B |
| `DARK ROOM` | `0x605F-0x606B` | `$E04F-$E05B` | 13B |
| `FIRE LOSS` | `0x606C-0x6078` | `$E05C-$E068` | 13B |
| `HIDDEN DOOR` | `0x6079-0x6087` | `$E069-$E077` | 15B |
| `FIRE SEALED` | `0x6088-0x6096` | `$E078-$E086` | 15B |
| `SPELL SEALED` | `0x6097-0x60A6` | `$E087-$E096` | 16B |
| `KEY ENEMY` | `0x60A7-0x60B3` | `$E097-$E0A3` | 13B |
| free | `0x60B4-0x60CB` | `$E0A4-$E0BB` | 24B |

合計:

- `stage_announcement` 本体: 164B
- 直後の空き: 24B
- この候補で使う範囲: `0x6010-0x60CB`
- 次の配置開始候補: `0x60CC`

新規配置では使わなくなる旧候補:

- 4096B内の旧分散候補: 151Bぶん
- 4096B外 `0x33D0-0x33DC`: 13B
- 既存ROM救済や旧配置掃除のために、ここを保存時に自動で上書きしない。

実装で確認したこと:

- 新本体 `0x6010-0x60B3` が、他の `RESERVED_SPANS` と重ならないこと。
- 新空き `0x60B4-0x60CB` を本体reserveとして扱わないこと。
- `MAIN` 内の `CPU_MASK_TABLE`、`CPU_DRAW`、`CPU_KEY_GATE` が新アドレスへ更新されること。
- `DRAW` 内の `CPU_PTR_TABLE` が新アドレスへ更新されること。
- `PTR_TABLE` が新scriptアドレスを指すこと。
- `$9061` hook が新 `CPU_MAIN = $E000` を呼ぶこと。

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

- `0x675C-0x6773` と `0x678C-0x6797` は、どちらも `$C0F0` の特殊セル変換scannerから使われる同一機能の小routine。
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
- 既存ROM救済や旧配置掃除のために、ここを保存時に自動で上書きしない。

実装で確認すること:

- `$C0F0` scanner内の `JSR` が新 `$E234` を指すこと。
- helper内部の `BCC` が新 `$E24C` extensionへ届くこと。
- 新本体 `0x6244-0x6267` が、他の予約と重ならないこと。
- 新空き `0x6268-0x627F` を本体reserveとして扱わないこと。
- 旧2断片へ消去・復元・互換目的の書き込みを入れないこと。

## Spark Ball runtime 移動結果

`spark_ball_variant.py` の追加routineのうち、property selector `0x2569` 以外を
7断片から1本体へまとめる。

理由:

- Spark Ball系は pause、AI wrapper、animation、透明OAM hide が複数箇所に散っている。
- `0x2569` property selector は原作コード差し替えに近いため、今回の「追加routine集約」から外す。
- 残り7断片はSpark Ball機能単位でまとめられ、検証もSpark Ball系として一括で行える。

移動前:

| part | old file | old CPU | size |
|---|---:|---:|---:|
| Dragon slow AI wrapper | `0x3FE8-0x3FF7` | `$BFD8-$BFE7` | 16B |
| Dragon fast AI wrapper | `0x3D36-0x3D45` | `$BD26-$BD35` | 16B |
| Transparent Golem-ID AI wrapper | `0x681C-0x6832` | `$E80C-$E822` | 23B |
| pause hook | `0x6FD4-0x7004` | `$EFC4-$EFF4` | 49B |
| animation hook | `0x4FEE-0x5004` | `$CFDE-$CFF4` | 23B |
| animation setter | `0x3EFA-0x3F02` | `$BEEA-$BEF2` | 9B |
| transparent OAM hide hook | `0x3ED7-0x3EF8` | `$BEC7-$BEE8` | 34B |

移動後:

| part | new file | new CPU | size |
|---|---:|---:|---:|
| packed Spark Ball runtime | `0x6280-0x6329` | `$E270-$E319` | 170B |
| free | `0x632A-0x6341` | `$E31A-$E331` | 24B |

合計:

- 旧分散配置: 170B
- 新本体: 170B
- 直後の空き: 24B
- この候補で使う範囲: `0x6280-0x6341`
- 次の配置開始候補: `0x6342`

新規配置では使わなくなる旧候補:

- `0x3FE8-0x3FF7`
- `0x3D36-0x3D45`
- `0x681C-0x6832`
- `0x6FD4-0x7004`
- `0x4FEE-0x5004`
- `0x3EFA-0x3F02`
- `0x3ED7-0x3EF8`
- 既存ROM救済や旧配置掃除のために、ここを保存時に自動で上書きしない。

実装で確認すること:

- Dragon/Golem AI tableが新 `$E270/$E280/$E290` を指すこと。
- `$AB13` pause dispatchが新 `$E2A7` を指すこと。
- `$8B05` animation dispatchが新 `$E2D8` を指すこと。
- animation hook内のSpark setter JMPが新 `$E2EF` を指すこと。
- `$85FA` transparent OAM dispatchが新 `$E2F8` を指すこと。
- pause digit設定とtransparent period設定のROM内offsetが、新pause/OAM routine内の相対位置で読めること。
- `0x2569` property selectorは移動しないこと。
- 旧7断片へ消去・復元・互換目的の書き込みを入れないこと。

## 4096B跡地内の現行予約

| file | CPU | size | 原作状態 | module |
|---|---:|---:|---|---|
| `0x6010-0x60B3` | `$E000-$E0A3` | 164B | `EA` | `stage_announcement` |
| `0x60CC-0x60F5` | `$E0BC-$E0E5` | 42B | `EA` | `m66.initial_draw_low_classifier` |
| `0x610E-0x622B` | `$E0FE-$E21B` | 286B | `EA` | `key_enemy_runtime` |
| `0x6244-0x6267` | `$E234-$E257` | 36B | `EA` | `room_flags.visible_item_inblock` |
| `0x6280-0x6329` | `$E270-$E319` | 170B | `EA` | `spark_ball_variant` |
| `0x67A3-0x67B3` | `$E793-$E7A3` | 17B | mixed | `panel_monster_stage_variant` |
| `0x67B4-0x67D0` | `$E7A4-$E7C0` | 29B | mixed | `panel_monster_stage_variant` |
| `0x67D1-0x6817` | `$E7C1-$E807` | 71B | mixed | `panel_monster_stage_variant` |
| `0x6833-0x6882` | `$E823-$E872` | 80B | mixed | `panel_monster_stage_variant` |
| `0x68AC-0x68BB` | `$E89C-$E8AB` | 16B | `00` | `panel_monster_stage_variant` |
| `0x68C4-0x68FE` | `$E8B4-$E8EE` | 59B | mixed | `panel_monster_stage_variant` |
| `0x693C-0x6959` | `$E92C-$E949` | 30B | mixed | `panel_monster_stage_variant` |
| `0x696C-0x697E` | `$E95C-$E96E` | 19B | `00` | `panel_monster_stage_variant` |
| `0x697F-0x699E` | `$E96F-$E98E` | 32B | mixed | `panel_monster_stage_variant` |
| `0x69D4-0x69DF` | `$E9C4-$E9CF` | 12B | `00` | `panel_monster_stage_variant` |
| `0x7005-0x700F` | `$EFF5-$EFFF` | 11B | `EA` | `solomon_seal_block` |

この範囲は、最終的には4096B先頭側へ詰め直して、routine本体と直後の空きを別管理する候補にする。

## 跡地外の主な整理候補

跡地外のPRG0予約は、実占有で1165Bある。
このうち、機能的に場所依存が薄い小routineは4096B側へ集約できる可能性がある。

最初に重点確認する範囲:

- `0x3C27-0x420F`: bank0 cave 系。複数敵runtimeとPanel系が集中している。
- `0x4FEE-0x500F`: Spark Ball animation / key enemy compare 系。
- `0x5BEF-0x5C0A`: Panel/Spark property selector。
- `0x2569-0x257D`: Spark Ball property selector。原作命令上の差し込みに近いので要注意。
- `0x4C5F-0x4CB5`: wide title 系。タイトル処理所有領域なので、一般空き扱いしない。

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

4096B跡地内の現行予約748Bと、跡地外の実占有1165Bを単純合算しても1913B。
重複や場所固定を除けば、場所依存のない追加routineは4096B跡地へ収まる可能性が高い。

ただし、すべてを機械的に移動してよいわけではない。
hook命令、原作即値変更、タイトル所有領域、原作データ断片上書きは個別確認が必要。
