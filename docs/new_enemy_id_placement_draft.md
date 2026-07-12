# 新敵ID暫定配置図

## 位置づけ

この文書は、`docs/new_enemy_id_placement_audit.md`で確定したID数と借用方針を一枚にまとめた暫定配置案である。正式なROM/RAM管理簿ではない。

- ID番号は実装しながら移行可能性とruntime量を確認する。
- 実装、ROM出力、バイト列比較、副作用検査が完了するまでは正式確定としない。
- 古い実験ROM、途中生成ROM、旧ID配置の救済・移行処理は作らない。
- 原作ROMから新しく生成する完成形ROMだけを対象にする。

## 結論

暫定配置は次のとおりとする。

| ID範囲 | ID数 | 用途 | 状態 |
|---:|---:|---|---|
| `$00` | 1 | 敵リスト終端 | 原作固定・敵IDとして使用禁止 |
| `$01-$7F` | 127 | 原作ID、原作ID借用variant | 原則維持 |
| `$80/$81` | 2 | 原作Red/White Flame | 原作維持 |
| `$82` | 1 | Ice Burn | 現行`$84`から移動 |
| `$83` | 1 | 原作White Flame #2 | 原作IDとして維持 |
| `$84-$9B` | 24 | Spark系 | 新規24ID連番 |
| `$9C` | 1 | Dark Fairy | 固定・移動禁止 |
| `$9D` | 1 | Seraphic Radiance | 固定 |
| `$9E-$AD` | 16 | Phantom Bullet系 | 新規16ID連番 |
| `$AE-$B5` | 8 | Ghost射撃系 | 新規8ID連番、末尾2ID予約 |
| `$B6-$B7` | 2 | Neul Twin Cannon | 新規2ID連番 |
| `$B8` | 1 | Chaos Dragon | 新規単独ID |
| `$B9-$FF` | 71 | 未割当 | 将来用。現時点で予約しない |

## 専用ID詳細

### Ice Burn

| ID | 敵 | 備考 |
|---:|---|---|
| `$82` | Ice Burn | 1方向・1速度・単独ID |

`$82`は原作Red Flame #2の未使用ID位置を利用する。現行Ice Burn `$84`はSpark系ブロックへ明け渡す。

### Spark系24ID

| ID範囲 | 種類 | 速度 | 方向順 |
|---:|---|---|---|
| `$84-$87` | 停止型Spark Ball | 速度1 | 右・左・上・下 |
| `$88-$8B` | 停止型Spark Ball | 速度2 | 右・左・上・下 |
| `$8C-$8F` | 透明型Spark Ball | 速度1 | 右・左・上・下 |
| `$90-$93` | 透明型Spark Ball | 速度2 | 右・左・上・下 |
| `$94-$97` | 停止後反転型Spark Ball | 速度1 | 右・左・上・下 |
| `$98-$9B` | 停止後反転型Spark Ball | 速度2 | 右・左・上・下 |

24ID内のoffset規則は次のとおり。

- 下位2bit: `0=右 / 1=左 / 2=上 / 3=下`
- `+04`: 同種類の速度2
- `+08`: 次の種類
- 現行Spark85 `$85`は単独IDとして残さない。
- Dragon/Golemから借りていた`$6A/$6B/$6E/$6F/$72/$73/$76/$77`はすべて返却済みとし、新Spark IDへは引き継がない。

### 固定単独ID

| ID | 敵 | 固定理由 |
|---:|---|---|
| `$9C` | Dark Fairy | Fairy `$1C`と下位bitを揃え、見た目と原作アニメ分岐を成立させる |
| `$9D` | Seraphic Radiance | 現行成立IDを維持する |

### Phantom Bullet系16ID

| ID範囲 | 種類 | 速度枠 | 方向順 |
|---:|---|---|---|
| `$9E-$A1` | Phantom Bullet | 1 | 右・左・上・下 |
| `$A2-$A5` | Phantom Bullet | 2 | 右・左・上・下 |
| `$A6-$A9` | Phantom Bullet Wave | 1 | 右・左・上・下 |
| `$AA-$AD` | Phantom Bullet Wave | 2 | 右・左・上・下 |

- 下位2bitをBullet方向へそのまま使う。
- 16ID内bit 2が速度枠、bit 3が通常/Waveを表す。
- 速度値、Wave振幅、軸変換値はCustomizer側でROMへ即値として書く。

### Ghost射撃系8ID

| ID | 敵 | 移動方向 | 射撃 |
|---:|---|---|---|
| `$AE` | Bomber Ghost | 右 | Bomber |
| `$AF` | Bomber Ghost | 左 | Bomber |
| `$B0` | Cannon Ghost | 右 | Cannon |
| `$B1` | Cannon Ghost | 左 | Cannon |
| `$B2` | Back Fire | 右 | Back Fire |
| `$B3` | Back Fire | 左 | Back Fire |
| `$B4` | 未使用予約 | - | Ghost系内予約 |
| `$B5` | 未使用予約 | - | Ghost系内予約 |

- 先頭4IDはbit 0が左右、bit 1がBomber/Cannonを表す。
- Back Fireもbit 0を左右に使う。
- `$B4/$B5`は他の敵へ流用しない。

### Neul Twin Cannon

| ID | 敵 | 初期方向 | 原作相当 |
|---:|---|---|---|
| `$B6` | Neul Twin Cannon | 上 | Neul `$30`相当 |
| `$B7` | Neul Twin Cannon | 下 | Neul `$32`相当 |

- 速度違いは作らない。
- 上下とも左右へBulletを1発ずつ発射する。

### Chaos Dragon

| ID | 敵 | 備考 |
|---:|---|---|
| `$B8` | Chaos Dragon | 単独ID。左右別ID・速度別IDを作らない |

## 借用維持ID

### Saramandor

| ID | 用途 | 色 |
|---:|---|---|
| `$5E/$5F` | 強化Saramandor速度1・右左 | SPR2 |
| `$62/$63` | 強化Saramandor速度2・右左 | SPR2 |
| `$66/$67` | Panel Monster 3-way上・下 | Panel側への貸出維持 |

通常Saramandor `$5C/$5D/$60/$61/$64/$65`は原作挙動・原作色を維持する。強化速度3は作らない。

### Dragon / Golem色違い

| ID | 用途 | 色 |
|---:|---|---|
| `$6A/$6B` | Dragon速度1 #2・右左 | SPR2 |
| `$6E/$6F` | Dragon速度2 #2・右左 | SPR0 |
| `$72/$73` | Golem速度1 #2・右左 | SPR2 |
| `$76/$77` | Golem速度2 #2・右左 | SPR0 |

これら8IDはSpark借用を返上し、原作Dragon/Golem AIを使用する。色だけ共通animation入口で変更する。

### Gargoyle

| ID | 用途 |
|---:|---|
| `$7A/$7B` | 強化Gargoyle速度1・右左 |
| `$7E/$7F` | 強化Gargoyle速度2・右左 |

借用を維持する。通常Gargoyle `$78/$79/$7C/$7D`も原作どおり残す。

### Panel Monster

| 系統 | ID |
|---|---:|
| 原作 | `$24/$25/$26/$27` |
| Variant C | `$31/$33/$35/$37` |
| Variant A | `$41/$43/$45/$47` |
| Variant B | `$49/$4B/$4D/$4F` |
| 2-way | `$52/$53/$56/$57` |
| 3-way | `$5A/$5B/$66/$67` |

追加20IDの借用を維持する。原作Stage 29の`$4D`は原作ROM読込時に`$4C`へ正規化する現行処理を維持する。

## 移行前後の対応

| 現行ID | 現行用途 | 暫定最終位置 |
|---:|---|---:|
| `$84` | Ice Burn | `$82` |
| `$85` | 停止後反転Spark | `$94-$9B`内へ統合 |
| `$86/$87` | Bomber/Cannon Ghost | `$AE-$B1` |
| `$88` | Neul Twin Cannon上 | `$B6`、下を`$B7`へ追加 |
| `$89` | Chaos Dragon | `$B8` |
| `$8A` | Back Fire | `$B2/$B3` |
| `$8B/$8C` | Phantom Bullet / Wave | `$9E-$AD` |
| `$9C` | Dark Fairy | `$9C`固定 |
| `$9D` | Seraphic Radiance | `$9D`維持 |

## 実装順序

1. `$82`へIce Burnを移し、`$84`を空ける。
2. Spark 24IDを`$84-$9B`へ構築する。
3. Phantom 16IDを`$9E-$AD`へ構築する。
4. Ghost 8IDを`$AE-$B5`へ構築する。
5. Neul 2IDを`$B6/$B7`へ構築する。
6. Chaos Dragonを`$B8`へ移す。
7. 共通入口センターを最終範囲分類へ一度で再構築する。
8. runtimeを実サイズで詰め、hook、`RESERVED_SPANS`、assertを更新する。
9. UI名称、方向表、速度設定、鍵持ち判定を最終IDへ揃える。
10. 新規ROM出力、バイト列比較、原作敵副作用検査を行う。
11. 実装、`RESERVED_SPANS`、正式ROM/RAM管理簿を同じ確定コミットへ入れる。

## 未確定事項

- この配置は暫定案であり、runtime実装時に成立しない技術的理由が見つかった場合は後続ブロックをまとめて後ろへずらしてよい。
- Spark 24IDを32ID境界へ合わせるための未使用8IDは確保しない。現時点では24IDだけを詰める。
- `$B9-$FF`は空きだが、将来予約として正式管理簿へ先取り記載しない。
- 鍵持ち可否が実機未検査の敵は、IDを配置してもOK扱いにしない。
- 正式確定は、全ID移行、ROM出力、実ROMバイト列比較、原作敵を残した副作用検査の完了後とする。
