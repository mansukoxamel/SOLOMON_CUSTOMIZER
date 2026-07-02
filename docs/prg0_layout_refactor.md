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

## 4096B跡地内の現行予約

| file | CPU | size | 原作状態 | module |
|---|---:|---:|---|---|
| `0x60CC-0x60D0` | `$E0BC-$E0C0` | 5B | `00` | `stage_announcement` |
| `0x60FC-0x6108` | `$E0EC-$E0F8` | 13B | `00` | `stage_announcement` |
| `0x612C-0x6138` | `$E11C-$E128` | 13B | `00` | `stage_announcement` |
| `0x618C-0x619A` | `$E17C-$E18A` | 15B | `00` | `stage_announcement` |
| `0x61BC-0x61C8` | `$E1AC-$E1B8` | 13B | `00` | `stage_announcement` |
| `0x61EC-0x61F7` | `$E1DC-$E1E7` | 12B | `00` | `stage_announcement` |
| `0x639C-0x63B4` | `$E38C-$E3A4` | 25B | `00` | `stage_announcement` |
| `0x63CC-0x63E3` | `$E3BC-$E3D3` | 24B | `00` | `stage_announcement` |
| `0x6465-0x6473` | `$E455-$E463` | 15B | `00` | `key_enemy_runtime` |
| `0x657C-0x658A` | `$E56C-$E57A` | 15B | `00` | `stage_announcement` |
| `0x66FC-0x670B` | `$E6EC-$E6FB` | 16B | `00` | `stage_announcement` |
| `0x67A3-0x67B3` | `$E793-$E7A3` | 17B | mixed | `panel_monster_stage_variant` |
| `0x67B4-0x67D0` | `$E7A4-$E7C0` | 29B | mixed | `panel_monster_stage_variant` |
| `0x67D1-0x6817` | `$E7C1-$E807` | 71B | mixed | `panel_monster_stage_variant` |
| `0x681C-0x6832` | `$E80C-$E822` | 23B | `00` | `spark_ball_variant` |
| `0x6833-0x6882` | `$E823-$E872` | 80B | mixed | `panel_monster_stage_variant` |
| `0x68AC-0x68BB` | `$E89C-$E8AB` | 16B | `00` | `panel_monster_stage_variant` |
| `0x68C4-0x68FE` | `$E8B4-$E8EE` | 59B | mixed | `panel_monster_stage_variant` |
| `0x693C-0x6959` | `$E92C-$E949` | 30B | mixed | `panel_monster_stage_variant` |
| `0x696C-0x697E` | `$E95C-$E96E` | 19B | `00` | `panel_monster_stage_variant` |
| `0x697F-0x699E` | `$E96F-$E98E` | 32B | mixed | `panel_monster_stage_variant` |
| `0x69D4-0x69DF` | `$E9C4-$E9CF` | 12B | `00` | `panel_monster_stage_variant` |
| `0x6FD4-0x7004` | `$EFC4-$EFF4` | 49B | `EA` | `spark_ball_variant` |
| `0x7005-0x700F` | `$EFF5-$EFFF` | 11B | `EA` | `solomon_seal_block` |

この範囲は、最終的には末尾側へ仮置きして、先頭側から連続空きを作る候補にする。

## 跡地外の主な整理候補

跡地外のPRG0予約は、実占有で1299Bある。
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

4096B跡地内の現行予約614Bと、跡地外の実占有1299Bを単純合算しても1913B。
重複や場所固定を除けば、場所依存のない追加routineは4096B跡地へ収まる可能性が高い。

ただし、すべてを機械的に移動してよいわけではない。
hook命令、原作即値変更、タイトル所有領域、原作データ断片上書きは個別確認が必要。
