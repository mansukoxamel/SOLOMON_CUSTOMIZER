# 自作6502 runtime静的解析

このディレクトリは、`SOLOMON_CUSTOMIZER`がROMへ書き込む自作6502 runtimeを、原作ASMと現行Python実装の両方から静的に検証した記録である。

目的は、バイト列が生成できることだけでなく、原作の呼出規約、状態機械、レジスタ、CPU flag、stack、敵slot、RAM、フレーム順序と整合しているかを、人間が読み直せる文章として残すことである。

## 共通の記載項目

各解析には、少なくとも次を記載する。

1. runtimeの目的と対象ID
2. ROM/CPU配置と全hook
3. 原作ASMの呼出元と戻り先
4. データ構造とmain/sub-slot field
5. 状態遷移とフレーム上の実行順序
6. A/X/Y、Carry/Zero/Negative等のflag、stack収支
7. 全branchと失敗経路
8. 共有hook、共有RAM、他runtimeとの依存
9. 確定した正常系、問題候補、未検証点
10. 実装への修正は行わず、先に解析事実を固定する

## 解析対象と進捗

| No. | runtime機能 | 主な実装 | 状態 |
|---:|---|---|---|
| 1 | [Panel Monster v2](01_panel_monster_v2.md) | `panel_monster_stage_variant.py` / `panel_monster_variant.py` | 完了（問題4件） |
| 2 | [Enhanced Saramandor A/B/C](02_enhanced_saramandor_abc.md) | `saramandor_variant.py` | 完了（確定バグ1件、文書不一致1件） |
| 3 | [Spark Ball 24ID](03_spark_ball_24id.md) | `spark24_runtime.py` / `spark_ball_variant.py` | 完了（問題2件） |
| 4 | [Enhanced Ghost A-F](04_enhanced_ghost_af.md) | `ghostb0_runtime.py` | 完了（問題3件） |
| 5 | [Enhanced Neul A/B](05_enhanced_neul_ab.md) | `neul84_runtime.py` | 完了（問題2件） |
| 6 | [Key Enemy / Fairy Enemy](06_key_fairy_enemy.md) | `key_enemy_runtime.py` | 完了（問題2件） |
| 7 | [Enemy Clear Key Open](07_enemy_clear_key_open.md) | `enemy_clear_key_open.py` | 完了（確定問題2件） |
| 8 | [Special Item / Fire2](08_special_item_fire2.md) | `fire2_item_runtime.py` | 完了（問題5件） |
| 9 | [New Enemy ID shared entry center](09_new_enemy_entry_center.md) | `new_enemy_runtime.py` | 完了（確定問題3件） |
| 10 | [Ice Flame / Ice Burn](10_ice_burn.md) | `ice_flame_runtime.py` | 完了（6502本体問題なし、validation候補1件） |
| 11 | [Dark Fairy `$9C`](11_dark_fairy_9c.md) | `fairy9c_runtime.py` | 完了（6502本体問題なし、候補2件） |
| 12 | [Seraphic Radiance `$9D`](12_seraphic_radiance_9d.md) | `seraphic_radiance9d_runtime.py` | 完了（確定問題4件） |
| 13 | [Chaos Dragon `$9E`](13_chaos_dragon_9e.md) | `chaos_dragon9e_runtime.py` | 完了（6502本体問題なし、候補3件） |
| 14 | [Phantom preset A-D](14_phantom_preset_ad.md) | `phantom_preset_runtime.py` | 完了（確定バグ2件、候補2件） |
| 15 | Enhanced Gargoyle A/B | `gargoyle_variant.py` | 未着手 |
| 16 | Blue Key Queen | `blue_key_queen_runtime.py` | 未着手 |
| 17 | Warp Mirror Mode | `warp_zone_trial.py` | 未着手 |
| 18 | Final Stage Redirect | `final_stage_redirect.py` | 未着手 |
| 19 | Room Flags | `room_flags.py` | 未着手 |
| 20 | StageExt loader | `stage_ext.py` | 未着手 |
| 21 | Solomon Seal Block | `solomon_seal_block.py` | 未着手 |
| 22 | Stage Announcement | `stage_announcement.py` | 未着手 |
| 23 | mapper66特殊セルloader | `m66.py` | 未着手 |
| 24 | mapper66拡張l_a1/l_a2 | `m66_expander.py` | 未着手 |
| 25 | Gap Fix | `gap_fix.py` | 未着手 |
| 26 | Wide Title runtime | `title_screen.py` | 未着手 |

## 対象外

- `drop_pickup_guard.py`は現在`apply()`が何も書かない明示的な無効化guardのため、現行runtime数に含めない。
- 通常のパラメータ、速度表、初期値、デモ入力などの単純なstock byte書き換えは、この26件の6502 runtime解析には含めない。
- 解析中に、上記以外の現行呼出可能な自作runtimeが見つかった場合は、総数を黙って変えず、理由と新しい総数を先に記録・報告する。
