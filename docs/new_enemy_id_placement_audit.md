# 新敵ID配置・runtime監査

## この文書の目的

原作敵、強化モンスター、新敵について、現在の敵ID配置が完成形として妥当かを1体ずつ精査する。

特に次を判断する。

- 現在の専用IDを維持するか、別IDへ再配置するか
- 原作敵IDの借用を維持するか、専用IDを取得するか
- ID下位bit、4ID単位のAI dispatch group、見た目、方向、速度の関係が成立しているか
- 新敵ID共通入口センターのAI/setup/init/animation分類が必要十分か
- runtimeに重複、無駄、ロジック誤認、危険な前提がないか
- PRG0/PRG1/RAM使用量と実装コストに対して、最適化や移動に意味があるか

現在は正式版前の開発段階なので、追加済みIDも必要なら移動候補にできる。古い実験ROM、途中生成ROM、過去の保存物を救うための互換処理は判断材料に含めない。

## 文書の位置づけ

この文書は調査・判断用の監査記録であり、正式なROM/RAM管理簿ではない。

- 原作IDの基礎データは `docs/enemy_id_ai_map_verified.tsv` を参照する。
- 調査中の候補や未確定事項はこの文書へ記録する。
- 実装、ROM出力、副作用検査が確定してコミットする時だけ、実装コード、`RESERVED_SPANS`、正式なROM/RAM管理簿を同時に更新する。
- 「静的監査済み」と「実機検査済み」を混同しない。実機未検査は必ず未検査と明記する。

## 共通の判断基準

1. 敵ID下位bitによる方向、見た目、原作アニメ分岐を壊さない。
2. AI/setup/init/animationの分類を新敵ID共通入口センターへ置き、分類本体を別場所へ逃がさない。
3. 借用IDによるtype-specific hookや例外処理が、専用ID化より単純で安全なら借用を維持する。
4. 専用ID化で例外処理、衝突、将来の制約を減らせる場合だけ移動候補にする。
5. 将来増やす可能性がある方向別・速度別バリエーションの連続範囲を考慮する。
6. PRG0消費、hook先変更、runtime移動、RAM追加を含む実装コストを明示する。
7. 空き判定は原作ROM、現在の実装、`RESERVED_SPANS`、正式管理簿を突き合わせる。
8. ID移動自体を目的にせず、完成形の見通し、安全性、保守性を優先する。

## 監査状況一覧

| 敵 | 現ID | ID方式 | ID判断 | runtime監査 | 実機検査 | 主な残件 |
|---|---:|---|---|---|---|---|
| Dark Fairy | `$9C` | 専用ID | `$9C`固定 | 静的監査済み | 今回未検査 | 管理簿のanimation attr説明訂正 |
| Ice Burn | `$84` | 専用ID | `$82`再配置推奨・未実装 | 静的監査済み | 今回未検査 | ID移動、名称統一、実ROM比較 |
| Spark85 / 停止後反転型 | `$85` | 専用ID | Spark系24連番の後半8IDへ統合・番号保留 | 静的監査済み | 未検査 | 4方向×2速度、借用Spark群との統合 |
| Bomber Ghost | `$86` | 専用ID | Ghost系8連番内の先頭4IDへ再配置・番号保留 | 静的監査済み | 今回未検査 | 左向き追加、8連番確定、共通射撃化 |
| Cannon Ghost | `$87` | 専用ID | Ghost系8連番内の先頭4IDへ再配置・番号保留 | 静的監査済み | 今回未検査 | 左向き追加、8連番確定、共通射撃化 |
| Neul Twin Cannon | `$88` | 専用ID | 上下2連番へ再配置・番号保留 | 静的監査済み | 現行上移動・左右壁破壊はユーザー確認済み | 上下2ID実装後の実機・実ROM比較 |
| Chaos Dragon | `$89` | 専用ID | 単独1ID・開始位置保留 | 静的監査済み | 今回未検査 | 最終ID配置、実ROM比較、鍵検査 |
| Back Fire | `$8A` | 専用ID | Ghost系8連番内の`+4/+5`・番号保留 | 静的監査済み | 今回未検査 | 左向き追加、共通射撃化、実ROM比較 |
| Phantom Bullet | `$8B` | 専用ID | Phantom系16連番の先頭8IDへ再配置・番号保留 | 静的監査済み | 今回未検査 | 4方向×2速度、速度値、鍵適性 |
| Phantom Bullet Wave | `$8C` | 専用ID | Phantom系16連番の後半8IDへ再配置・番号保留 | 静的監査済み | 今回未検査 | 4方向×2速度、上下Wave軸、鍵適性 |
| Seraphic Radiance | `$9D` | 専用ID | 単独1ID・最終番号保留 | 再監査済み・現状維持 | 今回未検査 | 鍵持ち禁止、鍵持ち敵消去副作用、実ROM比較 |
| Panel Monster variants | 原作ID借用20ID | 借用ID | 借用維持 | 静的監査済み・現状維持 | 既存73ケース保存検査確認済み・今回実機未検査 | 最終ROM比較、原作Stage 29 `$4D` 正規化維持 |
| Spark Ball variants | 原作ID借用 | 借用ID | 停止・透明・停止後反転の24専用IDへ移行 | 静的監査済み | 未検査 | 3種類×4方向×2速度、借用解除 |
| Gargoyle variants | `$7A/$7B/$7E/$7F` | 借用ID | 借用維持 | 動作成立・静的経路確認済み・再整理待ち | ユーザー動作確認済み | 2分割runtimeの1ブロック統合、重複・冗長処理の再監査、最終ROM比較 |
| Saramandor variants | `$5E/$5F/$62/$63` | 借用ID | 借用維持・強化速度3は作らない | 165B静的監査済み・現状維持 | 今回実機未検査 | 速度1/2・左右、Bullet消滅、原作敵副作用の最終ROM検査 |

敵名と対象は今後の現物調査で追加・整理する。この一覧だけを根拠に現行実装の全追加敵を網羅済みとは扱わない。

---

## 全体作業の進め方

敵ごとの精査結果だけで個別実装を始めず、全追加敵の判断と最終配置を確定してからまとめて実装する。

### 1. 全追加敵を同じ体裁で精査する

- 各敵について、基本情報、ID根拠、共通入口、runtime、ROM/RAM、ロジック、重複、文書不一致、検査状況を記録する。
- 専用IDだけでなく、原作IDを借用するPanel/Spark Ball/Gargoyle/Saramandor系なども対象にする。
- 対象は「追加した敵」という呼び方に限定しない。原作IDへ別挙動を載せた強化敵、variant、借用ID敵も同じ監査対象とする。
- 確定、推測、未検査を分離し、未検査をOK扱いしない。

### 2. ID固定・移動推奨・借用維持を決定する

各敵を次のいずれかへ分類し、理由を残す。

- 現ID固定
- 別IDへ移動
- 原作ID借用を維持
- 借用IDから専用IDへ移動

ID下位bit、4ID単位のAI group、見た目、方向、速度、死亡経路、鍵持ち適性、将来派生を判断材料にする。

借用ID敵については、借用維持を前提にしない。借用によるtype-specific hook、例外処理、原作敵との衝突が増える場合は、新規専用IDの取得を候補にする。専用ID化の方が複雑になる場合は借用を維持する。

### 3. 全体の最終ID配置図を作る

- 全追加敵の判断後に、ID範囲全体を一枚の配置図へまとめる。
- 単独ID、方向別ID、速度別ID、4ID group、将来予約を区別する。
- この時点で重複、衝突、不要な空き、連続範囲不足を解消する。
- 個別監査で出た移動推奨は、全体図で他の敵と競合しないことを確認して最終確定する。

### 4. 新敵ID共通入口センターを一度で再構築する

- 最終ID配置に基づき、AI/setup/init/animationの4入口をまとめて再生成する。
- 分類は共通入口センター内へ置き、分類本体を別場所へ逃がさない。
- 入口サイズが変わった場合は、2番目以降の入口アドレスと原作hook先を同時更新する。
- 個別敵ごとに入口を伸縮してアドレスを何度も動かす作業はしない。
- 借用ID敵を専用IDへ移す場合は、その敵が必要とするAI/setup/init/animation分類を共通入口センターへ追加する。
- 専用ID化しても原作経路をそのまま利用できる入口は、不要な専用分類を作らない。各入口を本当に必要なものだけにする。
- 監査途中で借用維持・専用ID化の判断が変わり得るため、全体配置確定までは入口センターの最終形を固定しない。

### 5. runtimeを最終配置へ詰める

- 不要になったAI/setup/init/animation本体を削除する。
- 共通化できる本体処理は、PRG0を増やさない範囲で整理する。
- PRG0は隙間を詰め、必要性のない固定24B緩衝は残さない。
- 伸びる見込みやhook移動コストから緩衝を残す場合は、理由、バイト数、残り空きを明示する。
- runtimeはステージ使用有無に関係なく、完成形ROMの固定位置へ毎回書く。

### 6. UI、名称、鍵持ち判定などを同時修正する

- 敵ピッカー、表示名、説明、統計、描画、保存データ、内部定数を最終IDへ合わせる。
- UI文言は日本語・英語を同時に更新する。
- Ice Burnのような名称変更は、現行ユーザー向け名称へ統一する。過去CHANGELOGは履歴なので書き換えない。
- 鍵持ち敵は「倒せるか」だけでなく、すべての死亡・消滅経路で鍵を生成できるか確認する。
- 撃破不能なSeraphic Radianceのような敵は鍵持ち対象外にする。

### 7. ROM出力・バイト列比較・原作敵副作用検査を行う

- 最新の「ROMを作る」で完成形ROMを新規出力する。
- 実験ROMで成立確認済みの処理は、実験ROMの該当バイト列と完成形ROMの該当バイト列を比較する。
- 整理、短縮、共通化でバイト列やレジスタ保護を変えた場合は、既存敵・既存機能を残したROMを出力して副作用を確認する。
- 新敵ごとに表示、AI、setup、init、animation、死亡、鍵、drop、方向、速度を必要範囲で確認する。
- 原作敵を残した比較ROMで、借用元や同groupの既存敵に副作用がないことを確認する。
- 検証ROM、ログ、画像は上書きせず、目的と日時または連番を含む別名で保存する。

### 8. 実装・予約・正式管理簿を同じコミットで確定する

- 検査が完了するまで正式ROM/RAM管理簿を更新しない。
- 実装コード、`RESERVED_SPANS`、ROM管理簿、必要なRAM管理簿を同じコミットへ入れる。
- ROM配置変更、予約移動、予約解除、空き量を最終状態へ同期する。
- ユーザー向け挙動、UI、ROM出力、保存形式へ影響するため、mainへ取り込みpushする直前にバージョンとCHANGELOGを更新する。

### 途中修正の例外

原則として全体配置確定前に個別実装しない。ただし、現在の精査や検証を妨げる重大バグ、進行不能を作る安全判定漏れ、現物を正しく読めない問題は別作業として先に直してよい。その場合も原因、副作用、ROM/RAM使用、残り空き、台帳更新時点を修正前に明示する。

---

## Ice Burn

### 1. 基本情報

- 現在の表示名: Ice Burn
- 現在のID: `$84`
- ID方式: 専用ID
- モデル敵: Burn/Flame `$80-$83`
- 方向別ID: なし
- 現在の判断: 原作で未配置のBurn偶数派生 `$82` への再配置を推奨する。実装は未変更。
- 実装本体: `magatu_skc/core/ice_flame_runtime.py`
- 共通分類: `magatu_skc/core/new_enemy_runtime.py`

### 2. 名称

ユーザー向けの現行名称はIce Burnである。

- `magatu_skc/skc_config.xml`: Ice Burn
- `magatu_skc/ui/element_picker.py`: Ice Burn
- runtimeファイル名、クラス名、定数説明、ROM管理簿、過去CHANGELOGの多く: Ice Flame

ユーザー向け名称はIce Burnを正とする。内部名の一括変更はID再配置実装と同時に行うか別コミットに分ける。過去CHANGELOGは当時の記録なので書き換えない。

### 3. ID候補の比較

原作Burn/Flame groupは `$80-$83` の4IDで構成される。

| ID | 原作上の派生 | 原作53面直置き | 使用中ミラー敵セット | 備考 |
|---:|---|---|---|---|
| `$80` | Red Burn、偶数派生 | あり | なし | 原作使用中 |
| `$81` | Blue Burn、奇数派生 | あり | なし | 原作使用中 |
| `$82` | Red Burn #2、偶数派生 | なし | なし | Ice Burn再配置候補 |
| `$83` | Blue Burn #2、奇数派生 | なし | なし | 未使用派生 |
| `$84` | 原作範囲外 | なし | なし | 現行Ice Burn専用ID |

原作ROM、全53面の敵直置き、各面が使用するデーモンミラー敵セット、現在の実装を静的確認した範囲では、`$82/$83` を原作が動的生成する経路は見つかっていない。

#### `$82` を推奨する理由

- Ice Burnは方向別・速度別IDを必要とせず、1IDで足りる。
- Ice BurnはBurn/Flame AI `$A5A0` を使う。
- `$82` は原作AI dispatchで自然にFlame index 27へ入る。
- `$82` は原作setup計算で自然にgroup `$40` へ入る。
- `$82` は偶数typeなので原作Burnの赤側派生と同じで、固定Ice Burn frameを与える土台として扱いやすい。
- `$82` のproperty indexは原作表内の26で、原作Flame property `$06` を読む。
- `$82` の敵ドロップ行indexも原作表内の26で、原作Flame用のdropなし行 `$00` を読む。
- 専用 `$84` を1つ解放できる。

#### `$84` を維持する利点

- 原作Burn IDを意味変更せず、専用IDとして見通しがよい。
- 現行実装、UI、保存データ、監査済みruntimeを変更しなくてよい。
- `$82` を将来Red Burnの第2派生として使う余地を残せる。

#### `$84` の構造上の弱点

- `$84` は原作property tableの通常範囲外で、index 27として次の原作コードbyteをproperty値に読む。
- 現物JP ROMではそのbyteは `$4A` であり、専用initがstatus、behavior、固定frameを後から上書きして成立させている。
- `$84` は原作敵ドロップ行割当表 `$C278` の27B範囲外で、直後の `$C293` 先頭byteを読む。
- 現物JP ROMではその値が `$00` なのでdropなしとして成立するが、正式な表外参照である。
- 即時の動作不良は確認していないが、隣接データ値に成立を依存する構造は完成形として弱い。

### 4. 新敵ID共通入口センター

#### 現行 `$84`

| 入口 | 現行入口 | `$84` の接続先・処理 | 必要性 |
|---|---:|---|---|
| AI | `$BBE2` | Ice Burn本体 `$E9C1` からFlame AI `$A5A0` | 現行では必要 |
| setup | `$BC42` | Ice Burn setup本体 `$E9C4`、group `$40` | 現行では必要 |
| init | `$BC91` | Ice Burn init本体 `$E9CD` | 必須 |
| animation | `$BCE6` | Ice Burn animation本体 `$E9EA` | 必須 |

#### `$82` へ移した場合

- AI分類は不要になる。原作AI dispatchがFlame AI `$A5A0` を選ぶ。
- setup分類は不要になる。原作setup計算がgroup `$40` を選ぶ。
- init分類は必要。status、behavior、固定frameをIce Burn用に上書きする。
- animation分類は必要。固定frame維持のため原作animation更新をskipする。
- 分類はinit/animationの2入口に残し、入口センター外へ逃がさない。

### 5. runtime処理

#### AI

- 専用AI本体は `JMP $A5A0` の3Bだけで、原作Flame AIをそのまま使う。
- 初期behavior `$14` によりFlame state 5から開始する。
- 足場変化後は原作Flame state 4/5系へ接続される。

#### setup

- setup group `$40` を設定し、原作metadata `$D9D3,Y` を読む。
- `$82` なら原作setup経路だけで同じgroup `$40` になるため専用本体は不要。

#### init

- main-slot statusを `$E0` に設定する。
- behaviorを `$14` に設定する。
- 固定frame tileを `$D6/$D4` に設定する。
- 固定frame attrを `$5A` に設定する。
- 新規グローバルRAMは使わない。

#### animation

- `RTS` だけを実行し、原作animation updaterを通さない。
- initで設定した固定frameを維持する。

### 6. ROM/RAM使用

#### Ice Burn本体

- file: `0x69D1-0x69FA`
- CPU: `$E9C1-$E9EA`
- 使用量: 42B
- 内訳: AI 3B、setup 9B、init 29B、animation 1B
- 前方の現行runtime予約なし領域: `0x69B9-0x69D0` / `$E9A9-$E9C0`、24B
- 後方の現行runtime予約なし領域: `0x69FB-0x6A12` / `$E9EB-$EA02`、24B
- 次の現行予約: Spark85 runtime `0x6A13-0x6A55` / `$EA03-$EA45`

#### `$82` へ移した場合の削減見込み

- Ice Burn本体からAI 3Bとsetup 9Bを削除可能: 12B削減候補
- 共通入口センターからAI分類8B相当とsetup分類7B相当を削除可能: 15B削減候補
- 合計: 27B削減候補
- 実際の入口アドレスは後続分類とSeraphic Radianceを含めて再構築するため、確定値は実装時に再計算する。
- PRG0入口センターが短くなる方向なので、現行方針に合う。

#### RAM

- 新規グローバルRAM: なし
- 専用sub-slot: なし
- 原作Flame AIが使用する既存entity slot/sub-slotだけを使う。

### 7. 監査結果

#### 成立している点

- 42B runtimeはAI/setup/init/animationの役割が分離されている。
- AIは原作Flame AIへの単純接続で、独自AIの重複はない。
- 固定frame設定とanimation skipは整合している。
- status `$E0` により接触判定とダーナ火球撃破を有効にする設計になっている。
- mapper66完成形ROMではステージ使用有無に関係なくruntimeが毎回書かれる。

#### 明確なロジックミス

- runtime本体の静的解析では見つかっていない。
- ただし `$84` のproperty/drop表外参照は、完成形として避けられるなら避けるべき技術的負債である。

#### 重複・無駄

- `$84` 専用AI 3Bは、`$82` なら原作dispatchで不要になる。
- `$84` 専用setup 9Bは、`$82` なら原作setupで不要になる。
- init 29Bとanimation 1BはIce Burn固有なので残す必要がある。

#### 他機能への影響

- `enemy_slot_rules.FLAME_ENEMY_CODES` は現在 `$80-$83` をFlame扱いし、鍵持ち敵として選べない。
- Ice Burnを `$82` へ移すだけでは、このカスタマイザー判定により鍵持ち敵不可になる。
- Ice Burnは落下死亡せず、ダーナ火球撃破だけで死亡する。
- ダーナ火球撃破は既存の `$C267` 鍵drop hookを通るため、Ice Burn用に落下死亡処理を追加する必要はない。
- Ice Burnは倒せる敵なので、ユーザー仕様としてID移動後も鍵持ち敵に指定可能とする。
- 実装時は `$82` を単純に集合から外すか、Ice Burnを明示許可する判定へ変更する。原作Red/Blue Burnの禁止は維持する。
- 原作Burn `$80` はIce Burnと異なり落下死亡がある。将来 `$80` を鍵持ち敵として許可する場合は、落下死亡経路を鍵出現処理へ接続しなければならない。
- UI表示名、統計、敵ドロップ表示、保存済みステージ内の現開発ID参照を `$84` から `$82` へ同時変更する必要がある。
- 正式版前のため旧保存物救済は実装しない。

### 8. 文書不一致

- ユーザー向け名称はIce Burnへ変更済みだが、runtimeと多くの文書はIce Flameのままである。
- `docs/borrowed_enemy_id_audit.html` はIce Flame `$84` を「移行済み独立ID」として扱っている。
- 現在の再監査結果では `$82` 候補を比較対象に戻したため、ID判断確定時に関連文書を更新する必要がある。
- 過去CHANGELOGは履歴なので名称・IDを遡って書き換えない。

### 9. 検査状況

| 検査 | 状態 | 備考 |
|---|---|---|
| 現行名称確認 | 済み | UI/configはIce Burn |
| 原作 `$80-$83` AI確認 | 済み | 4IDともFlame AI `$A5A0` |
| 原作53面直置き確認 | 済み | `$80/$81`のみ、`$82/$83`は0件 |
| 使用中ミラー敵セット確認 | 済み | `$80-$83`はいずれも0件 |
| 原作動的生成の静的検索 | 済み | `$82/$83`生成経路は未発見 |
| 現行runtime静的解析 | 済み | 42B本体を確認 |
| 現行保存ROMのIce Burn本体比較 | 済み | 既存検証ROMで42B本体一致 |
| 現行保存ROMの最新共通4入口比較 | 未検査 | 現在のPython生成値で新規ROM出力が必要 |
| `$82` 試作ROM | 未作成 | ID移動は未実装 |
| `$82` 実機表示・固定frame | 未検査 | 要試作ROM |
| 足場崩壊後のFlame挙動 | 今回未検査 | `$84` と `$82` の比較が必要 |
| ダーナ火球撃破・drop | 今回未検査 | 表内index26でdropなしになることを確認する |
| 原作Red/Blue Burn副作用 | 今回未検査 | `$80/$81`を残した比較ROMが必要 |

未検査項目はOK扱いにしない。

### 10. 現時点の最終判断

- 名称: Ice Burnを正とする
- 必要ID数: 1
- 推奨ID: `$82`
- 現行ID `$84`: 動作は成立しているが、原作property/drop表外参照が残る
- `$82`: 原作未配置の偶数Burn派生で、AI/setup/property/dropが原作表内に収まる
- 入口センター: `$82` 化後はinit/animation分類だけ残す
- runtime: AI/setupを削除し、init/animationだけ残す構成を推奨
- 期待削減: runtime 12B、入口センター15B相当、合計27B候補
- 実装状態: 未変更
- 鍵持ち敵仕様: Ice Burnは倒せる敵なので、ID移動後も鍵持ち敵として選択可能にする
- Ice Burn死亡経路: 落下死亡なし、ダーナ火球撃破のみ。既存 `$C267` 鍵drop hookを使用する
- カスタマイザー対応: `$82` を原作Flameと同じ理由で一律禁止せず、Ice Burnとして明示的に許可する
- 必要な検査: `$84` と `$82` の該当バイト列比較、実機表示、足場崩壊、火球撃破、原作Burn副作用

---

## Dark Fairy

### 1. 基本情報

- 現在のID: `$9C`
- ID方式: 専用ID
- モデル敵: Fairy `$1C`
- 方向別ID: なし
- 現在の判断: `$9C`固定
- 実装本体: `magatu_skc/core/fairy9c_runtime.py`
- 共通分類: `magatu_skc/core/new_enemy_runtime.py`

### 2. ID配置の根拠

- `$9C` と原作Fairy `$1C` は下位bitが一致する。
- Fairy系はtype下位bitが原作アニメ分岐と見た目に影響する。
- `$9C` はFairy group `$0E` と組み合わせて成立確認された正式IDである。
- Dark Fairyは単独IDで、上下左右や速度別のIDを必要としない。
- 別IDへ移す場合は、原作type下位bit、setup group、実機表示、死亡処理をすべて再検証する必要がある。

以上により、ID整理だけを理由に移動しない。Dark FairyのIDは `$9C` で確定する。

### 3. 新敵ID共通入口センター

現行の共通入口センターは4つの独立入口でDark Fairyを分類する。

| 入口 | 現行入口 | `$9C` の接続先・処理 | 必要性 |
|---|---:|---|---|
| AI | `$BBE2` | Dark Fairy AI本体 `$E01E` | 必須 |
| setup | `$BC42` | Fairy setup/animation group `$0E` | 必須 |
| init | `$BC91` | Dark Fairy init本体 `$E009` | 必須 |
| animation | `$BCE6` | 原作animation後の専用attr処理 | 必須 |

4入口とも分類が必要であり、単なるJMP stubへ置き換えたり、分類本体を入口センター外へ移したりしない。

### 4. runtime処理

#### setup

- setup groupとしてFairy group `$0E` を選ぶ。
- `$D9D3,Y` から原作Fairy用metadataを読む。

#### init

- 共通init入口が保存した値をstackから除く。
- `$9C` の原作property読込によって一時設定されたY速度を0へ戻す。
- status `$E2`、type `$9C`、behavior `$00` を設定し、原作init writer `$9D1C` を呼ぶ。

#### AI

- 通常時はmain-slot typeを一時的に原作Fairy `$1C` へ変更する。
- 原作Fairy AI `$A700` を実行する。
- 実行後にtypeを `$9C` へ戻す。
- 原作Fairy AI実行前後の `$0453` を比較し、Fairy取得処理の発生を検出する。
- 取得を検出したらsub-slot `[7]` に `$3C`、60フレームの待機値を設定する。
- 待機終了後に死亡action `$31` を発動し、Dark Fairy本体をdespawnする。

#### animation

- 原作animation updater `$8789` を実行する。
- 元attrのFairy用反転bitを残し、Dark Fairy用のSPR #2 palette属性を設定する。

### 5. ROM/RAM使用

#### Dark Fairy本体

- file: `0x6010-0x6065`
- CPU: `$E000-$E055`
- 使用量: 86B
- 内訳: setup 9B、init 21B、AI 56B
- 直後の現行予約: Blue Key Queen runtime `0x6066-0x6084` / `$E056-$E074`
- Dark Fairy本体直後の連続空き: 0B
- Blue Key Queen後の連続空き: `0x6085-0x60CB` / `$E075-$E0BB`、71B

#### 共通入口センター

- 全体: file `0x3BF2-0x3D32` / CPU `$BBE2-$BD22`、321B
- Dark Fairy固有の比較・分岐・animation処理の概算: 40B
- センター直後の現行runtime予約なし領域: file `0x3D33-0x3D35` / CPU `$BD23-$BD25`、3B

#### RAM

- 毒待ちカウンタ: Dark Fairy自身のsub-slot `[7]`、1B
- 新規グローバルRAM: なし
- 静的確認した原作Fairy AI経路ではsub-slot `[7]` の競合は見つからない。

### 6. 監査結果

#### 成立している点

- `$9C` の下位bitとFairy `$1C` の下位bitが一致している。
- setup group `$0E`、一時type `$1C`、専用animation attr処理の組合せは設計上整合している。
- `$0453` の比較は、原作Fairy取得処理が同期的に実行される範囲内で行われる。
- `$0453` が10回目で0へ戻る場合も、実行前後の値が変化するため取得を検出できる。
- 原作Fairy AIがtype `$1C` を確認して通常Fairy経路へ戻るため、特殊な別type経路へ入らない。
- runtimeはmapper66完成形ROMへステージ使用有無に関係なく毎回書かれる。

#### 明確なロジックミス

- 静的解析では見つかっていない。

#### 技術的負債・危険な前提

- init hookへ到達する前に、原作初期化前段が `$9C` を原作property tableの通常範囲外として読んでいる。
- その副作用で一時設定されるY速度を専用initが0へ戻し、statusとbehaviorも専用値へ上書きして成立させている。
- 現在のバイト列では成立するが、原作初期化前段や共通init hookを変更する場合は再確認が必要である。
- この構造を根本的に変えるにはhook位置や共通init設計へ影響するため、小さな局所最適化ではない。

#### 重複・無駄

- 明確に削除できる重複処理は見つかっていない。
- setup 9Bは共通入口側へインライン化できるが、PRG1を少し減らす代わりにPRG0入口センターを増やす。
- PRG0を狭い通路として扱う現行方針に反するため、setup本体をPRG1側へ置く現行構成を維持する方がよい。

### 7. 文書不一致

正式ROM管理簿のDark Fairy animation説明は、実装バイト列と一致していない。

- 管理簿の記載: sprite attrを `$88` へ上書き
- 現行実装: `AND #$13`、`ORA #$48`

現行実装は固定値 `$88` を書かず、元attrの必要bitを残してpalette属性を設定する。実装が確定してコミットする時に、管理簿の説明を実装どおりへ訂正する。

### 8. 検査状況

| 検査 | 状態 | 備考 |
|---|---|---|
| ID下位bit確認 | 済み | `$9C` と `$1C` が一致 |
| 入口センター静的確認 | 済み | AI/setup/init/animationを確認 |
| runtime静的解析 | 済み | 86B本体を確認 |
| 原作Fairy AI照合 | 済み | `$A700` と `$0453` 更新経路を確認 |
| 現行保存ROMの全入口バイト列比較 | 未検査 | 現行完成形ROMを新規出力して比較が必要 |
| Dark Fairy実機表示 | 今回未検査 | palette、反転、アニメを要確認 |
| 取得後60F死亡処理 | 今回未検査 | action `$31` とdespawnを要確認 |
| 原作Fairy・Fairy Princess副作用 | 今回未検査 | Dark Fairy入りROMと未使用ROMで確認が必要 |

未検査項目はOK扱いにしない。

### 9. 現時点の最終判断

- ID: `$9C` で固定
- 借用／専用: 専用IDを維持
- 入口センター分類: 4入口すべて現状維持
- runtime本体: 現状維持候補
- 軽微な最適化: PRG0を増やすため実施しない
- 保留: init前段の範囲外property読込を根本的に避ける構造変更
- 必要な文書作業: 管理簿のanimation attr説明訂正
- 必要な検査: 現行完成形ROMのバイト列比較、実機表示、60F死亡、原作Fairy系副作用

---

## Bomber Ghost / Cannon Ghost

### 1. 基本情報

- 現在のID: Bomber Ghost `$86`、Cannon Ghost `$87`
- ID方式: 専用ID
- モデル敵: Ghost右・速度1 `$34`
- 現行方向: 両方とも右移動だけ
- 完成形に必要な種類: Bomber右・左、Cannon右・左の4種類
- 速度別ID: 不要
- 現在の判断: Ghost系として8連番を確保し、先頭4IDへBomber/Cannon、次の2IDへBack Fireを配置し、最後の2IDは未使用予約とする。8連番の開始IDは全体配置図まで保留する。
- 実装本体: `magatu_skc/core/ghost86_runtime.py`
- 共通分類: `magatu_skc/core/new_enemy_runtime.py`

### 2. ID配置の根拠

現行 `$86/$87` は、敵IDで移動方向を分けていない。

- `$86`: 右移動、下向き射撃
- `$87`: 右移動、上向き射撃

完成形では4連番を次の順序にする。

| 連番内offset | 種類 | 移動方向 | 射撃方向 |
|---:|---|---|---|
| `+0` | Bomber Ghost右 | 右 | 下 |
| `+1` | Bomber Ghost左 | 左 | 下 |
| `+2` | Cannon Ghost右 | 右 | 上 |
| `+3` | Cannon Ghost左 | 左 | 上 |

この並びなら、IDのbit 0をGhostの移動方向、bit 1をBomber/Cannonの射撃種別として扱える。4IDを個別比較するより、範囲判定後に下位2bitから初期behaviorと射撃方向を導出する方が単純である。

Bomber/Cannonの4IDとBack Fire右左の2IDで、実使用数は合計6IDになる。ただし6IDだけを詰めて確保せず、Ghost系全体へ8連続IDを割り当てる。

| 8連番内offset | 用途 | 使用状態 |
|---:|---|---|
| `+0` | Bomber Ghost右 | 使用 |
| `+1` | Bomber Ghost左 | 使用 |
| `+2` | Cannon Ghost右 | 使用 |
| `+3` | Cannon Ghost左 | 使用 |
| `+4` | Back Fire右 | 使用 |
| `+5` | Back Fire左 | 使用 |
| `+6` | 予約 | 未使用 |
| `+7` | 予約 | 未使用 |

8ID単位にする理由は次のとおりである。

- Bomber/Cannonの先頭4IDを、4ID単位のAI分類として完結させられる。
- Back Fireの右左を同じ連続範囲へ置き、Ghost系の方向bit規則を統一できる。
- 後続敵を6ID目の直後へ詰めて分類境界を分かりにくくしない。
- 最後の2IDは他の敵へ割り当てず、Ghost系8連番の未使用予約として明示できる。

ただし、8連番の開始IDはまだ確定しない。Ice Burn `$82`、後回しにしたSpark85、Neul88、Chaos Dragon、Phantom Bullet系などを含む全体配置で、8連続IDを衝突なく確保してから決める。

### 3. 新敵ID共通入口センター

現行 `$86/$87` の分類は次のとおりである。

| 入口 | 現行処理 | 完成形での方針 |
|---|---|---|
| AI | `$86` と `$87` を個別比較し、下撃ち／上撃ち入口へ分岐 | 4連番を範囲分類し、bit 1から射撃種別を導出する |
| setup | `$84-$87` の4B tableを参照し、両IDへgroup `$1A` を設定 | Ghost 4IDを同じgroup `$1A` として範囲分類する |
| init | `$86/$87` を個別比較し、共通initへ分岐 | 4連番を範囲分類し、bit 0からbehavior `$00/$01` を導出する |
| animation | 専用分類なし。原作 `$8789` を使用 | 専用分類なしを維持する候補 |

分類は共通入口センター内へ残す。最終ID確定時にAI/setup/init入口を一度で再構築し、4ID分の個別比較を並べない。

### 4. runtime処理

#### setup

- 現行はgroup `$1A`、原作Ghost右・速度1 `$34` と同じvisual/velocity classを使用する。
- `SETUP_GROUP_TABLE` はGhostだけでなくIce Burn `$84` とSpark85 `$85` のgroup値も同居させた4B tableである。
- Ice Burn移動やID再配置後もこの表をGhost本体へ置く理由はない。最終実装では入口センター側の分類へ整理する。

#### init

- status `$C0`、behavior `$00` を設定し、原作init writer `$9D1C` を呼ぶ。
- behavior `$00` はGhost右、`$01` はGhost左である。
- 現行は両IDとも `$00` 固定なので左向きが存在しない。
- sub-slot `[7]` を射撃cooldown `$80` で初期化する。
- 完成形では連番内bit 0からbehavior `$00/$01` を設定する。

#### AI

- `$86` は弾方向 `$03`、下向き射撃を選ぶ。
- `$87` は弾方向 `$02`、上向き射撃を選ぶ。
- `$2C-$2F` をstackへ退避してから原作Ghost AI `$ABF7` を呼び、復元する。
- 壁待ち・ブロック破壊状態では射撃しない。
- sub-slot `[7]` をcooldownとして使い、空きchild slotを探して弾を生成する。
- 初期値は `$80`、再装填値は `$C0`。最初の射撃は即時候補、その後は下位7bitを約64回減算して再射撃する。
- 原作Ghost AIの静的解析ではsub-slot `[7]` の使用は見つからず、現行cooldownとの競合は見つからない。

#### animation

- 専用animation runtimeはない。
- 原作animation updaterとGhost group `$1A` を使う現行右向き表示は成立済み実装である。
- 左向きはbehavior `$01` による反転を利用する設計だが、今回の実機検査は未実施である。

### 5. ROM/RAM使用

#### 現行Bomber/Cannon本体

- file: `0x6D98-0x6E15`
- CPU: `$ED88-$EE05`
- 使用量: 126B
- 内訳: setup group table 4B、init 22B、AI 100B
- 直前の現行runtime予約なし領域: `0x6D2D-0x6D97`、107B
- 直後の現行予約: Neul88 `0x6E16-0x6EB3`、158B

#### RAM

- 射撃cooldown: 親Ghostのsub-slot `[7]`、1B
- child slot番号: 親Ghostのsub-slot `[6]`
- 新規グローバルRAM: なし
- 4種類化でも新規RAMは不要な設計にできる。

### 6. 監査結果

#### 成立している点

- 原作Ghost AI `$ABF7` を再利用する構成は、横移動と壁反転を維持できる。
- Bomberの下撃ちとCannonの上撃ちは、同一射撃本体へ方向値だけ渡している。
- pointer退避・復元により、原作Ghost AI後も親・子slot処理を継続できる。
- 壁状態中の射撃抑止、cooldown、空きslot失敗時の再試行は設計上整合している。
- runtimeはステージ使用有無に関係なく完成形ROMへ毎回書かれる。

#### 明確な不足

- 現行はBomber/Cannonとも右移動しかなく、要求される左右4種類を満たしていない。
- `GHOST_UP_ID` / `GHOST_DOWN_ID` という内部名は、実際のBomber下撃ち／Cannon上撃ちと意味が逆向きに読める。実装時に役割名へ整理する必要がある。

#### 重複・無駄

- Back Fire `$8A` のAI 99Bは、Bomber/CannonのAI 100Bと、pointer保存、原作Ghost AI、壁状態判定、cooldown、空きchild slot検索、弾生成処理がほぼ同じである。
- Back Fire側のコードコメントにも、この重複と将来の共通射撃化が明記されている。
- Ghost AI 100BとBack Fire AI 99Bを別々に維持する必要はない。最終実装では「固定下」「固定上」「進行方向と逆」の射撃方向選択だけを分け、共通射撃本体へ合流させる候補とする。
- Back Fireも右左2IDが必要なので、Ghost系8連番の `+4/+5` に置き、Bomber/Cannonと同じ方向bit規則で設計するとinit処理も共通化しやすい。
- 8連番の `+6/+7` は使用ID数を埋めるための敵を作らず、未使用予約として残す。
- 現段階では共通化後の正確な使用量は未算出であり、削減量を確定値として扱わない。

#### 危険な前提・要実機確認

- 左向きbehavior `$01` 自体は原作解析でGhost左と確定しているが、追加IDの見た目、射撃位置、壁反転後の向きとの整合は未検査である。
- 射撃方向はBomber/Cannonでは上下固定なので、左右反転後も射撃方向を変えないことを確認する必要がある。
- child slot不足時、親死亡時、ブロック破壊中の弾残留は今回未検査である。

### 7. 鍵持ち判定

- Bomber/Cannon Ghostはダーナ火球で撃破可能な敵として扱う。
- 原作Ghost AIにはIce Burnのような落下死亡経路はなく、通常撃破は既存 `$C267` 鍵drop hookを通る想定である。
- したがって4種類とも鍵持ち敵として指定可能にする候補である。
- ただし4ID化後の火球撃破と鍵出現は実機未検査なので、現時点でOK扱いにはしない。

### 8. 検査状況

| 検査 | 状態 | 備考 |
|---|---|---|
| 現行ID・表示名確認 | 済み | `$86` Bomber、`$87` Cannon |
| 原作Ghost方向bit確認 | 済み | behavior 0=右、1=左 |
| 現行runtime静的解析 | 済み | 126B本体を確認 |
| 共通入口静的解析 | 済み | AI/setup/initあり、animation専用分類なし |
| Back Fire AI重複確認 | 済み | 99Bが同じ射撃骨格を重複 |
| 現行保存ROMの本体バイト列比較 | 未検査 | 現行完成形ROMを新規出力して比較が必要 |
| Bomber右・左実機 | 未作成・未検査 | 4ID化後に要確認 |
| Cannon右・左実機 | 未作成・未検査 | 4ID化後に要確認 |
| 壁反転・ブロック破壊中射撃 | 未検査 | 左右両方で確認する |
| child slot不足・親死亡 | 未検査 | 弾とslot参照の残留確認 |
| 火球撃破・鍵出現 | 未検査 | 4種類すべて確認する |
| 原作Ghost/Neul副作用 | 未検査 | 原作敵を残した比較ROMが必要 |

未検査項目はOK扱いにしない。

### 9. 現時点の最終判断

- 必要ID数: 4
- 種類: Bomber右、Bomber左、Cannon右、Cannon左
- 速度違い: 作らない
- 配置: Ghost系として8連番を確保する
- 連番内規則: 8連番の先頭4IDではbit 0=右左、bit 1=Bomber/Cannon。Back Fireの2IDもbit 0=右左
- 8連番内配置: `+0～+3` Bomber/Cannon、`+4/+5` Back Fire、`+6/+7` 未使用予約
- 開始ID: 全体配置図まで保留
- 現行 `$86/$87`: 完成形の4ID配置が決まるまで仮位置
- 入口センター: AI/setup/initを4ID範囲として分類、animation専用分類は不要候補
- runtime: 左右initを追加し、Bomber/Cannon/Back Fireの共通射撃本体を検討する
- Back Fire: 右左2IDが必要。Ghost系8連番内へ含め、ID配置と共通射撃設計へ影響する依存事項として扱う
- 鍵持ち敵仕様: 4種類とも指定可能候補。実機で火球撃破と鍵出現を検査する
- 実装状態: 未変更

---

## Neul Twin Cannon

### 1. 基本情報

- 現在のID: `$88`
- 現在の表示名: Neul Twin Cannon
- ID方式: 専用ID
- モデル敵: Neul上・速度1 `$30`
- 現行射撃: 左右へ1発ずつ、合計2発
- 完成形に必要な方向: 上・下
- 速度別・追加派生: 作らない
- 必要ID数: 2
- 現在の判断: 上下2連番へ再配置する。開始IDは全体配置図まで保留する。
- 実装本体: `magatu_skc/core/neul88_runtime.py`
- 共通分類: `magatu_skc/core/new_enemy_runtime.py`

### 2. ID配置の根拠

Neul Twin Cannonは移動方向だけを上・下で分ければ完結する。速度違い、射撃方向違い、追加派生を増やす予定はないため、2IDで十分である。

| 2連番内offset | 種類 | 初期behavior | 射撃 |
|---:|---|---:|---|
| `+0` | Neul Twin Cannon上 | 原作方向bit `$02` | 右・左の2発 |
| `+1` | Neul Twin Cannon下 | 原作 `$32` 相当の正方向Y速度 | 右・左の2発 |

原作配置敵ではNeul/Ghost共通AI `$ABF7` のbehavior下位2bitと移動軸に対応関係がある。ただし追加ID `$88` は原作type下位bitだけで初期化されず、setup group `$18` が先にNeul用Y速度を設定した後、専用initがbehavior `$00` を書く構成である。ユーザー実機確認では現行 `$88` は正しく上移動しているため、behavior値だけから現行方向を否定してはいけない。

原作 `$30` と `$32` は同じsetup group `$18` を使うが、group内の間接表がtype下位2bitを参照する。`$30` は速度index `$10` から負方向Y速度、`$32` は速度index `$0F` から正方向Y速度を得る。したがって下向き版はbehaviorだけを書き換えず、専用2IDを原作 `$30/$32` のsetup subtypeへ明示変換する。

仕様として必要なのは2IDである。ただし、ID領域も2IDだけに詰めるか、4ID境界や全体の余裕を考えて未使用枠を隣接させるかは、まだ決めない。開始位置と確保範囲は全敵の最終配置図で判断する。

### 3. 新敵ID共通入口センター

現行 `$88` は次の3入口で専用分類され、animationは原作処理を使用する。

| 入口 | 現行処理 | 完成形での方針 |
|---|---|---|
| AI | `$88` をNeul Twin Cannon AIへ分岐 | 上下2IDを範囲分類して同じAIへ分岐 |
| setup | `$88` をgroup `$18` 読込へ分岐 | 2IDを原作 `$30/$32` 相当へ変換してgroup `$18` を使う |
| init | `$88` を専用initへ分岐 | 上は方向bit `$02`、下は `$03` を明示する |
| animation | 専用分類なし。原作 `$8789` を使用 | 専用分類なしを維持する |

分類は共通入口センター内へ残す。上下を個別の長い比較列にせず、2ID範囲として扱う。

### 4. runtime処理

#### setup

- 上下ともgroup `$18` と原作Neulのvisual/velocity classを使用する。
- `+0` は原作 `$30` subtype、`+1` は原作 `$32` subtypeとして速度表を選ぶ。新ID自身の下位bitには依存しない。
- 原作 `$30/$32` のanimation番号はいずれも43なので、上下で専用animation runtimeを分けない。

#### init

- status `$C0` を設定し、原作init writer `$9D1C` を呼ぶ。
- sub-slot `[7]` を射撃cooldown `$80` で初期化する。
- 完成形では原作Neul/Ghost AIの方向定義に合わせ、`+0` はbehavior下位2bit `$02`（上）、`+1` は `$03`（下）を明示する。
- 現行 `$88` のbehavior `$00` は初期Y速度により見た目上は上移動するが、方向bit上はGhost右であり、完成形へ残さない。
- setupのY速度とbehavior方向を同じ上下へ揃える。これによりstate 0以降と天井・床接触後の反転も原作Neul経路へ一致させる。

#### AI

- `$2C-$2F` をstackへ退避して原作Neul/Ghost AI `$ABF7` を呼び、復元する。
- 壁待ち・ブロック破壊状態では射撃しない。
- sub-slot `[7]` をcooldownとして使う。
- cooldown到達時、右向きBullet `$00` と左向きBullet `$01` を順番に生成する。
- 1発目は右、2発目は左の順である。
- 初期値 `$80`、再装填値 `$C0` はBomber/Cannon/Back Fireと同じである。

#### animation

- 専用animation runtimeはない。
- 原作Neul animationを使用する。
- 上下で同じNeul animationを使う。上下2ID化後の表示と反転は実機未検査である。

### 5. ROM/RAM使用

#### 現行Neul Twin Cannon本体

- file: `0x6E16-0x6EB3`
- CPU: `$EE06-$EEA3`
- 使用量: 158B
- 内訳: setup 9B、init 22B、AI 127B
- 直前の現行予約: Bomber/Cannon Ghost `0x6D98-0x6E15`
- 直後の現行予約: Chaos Dragon `0x6EB4-0x6ED0`
- 本体前後の連続空き: 0B

#### RAM

- 射撃cooldown: 親Neulのsub-slot `[7]`、1B
- child slot番号: 親Neulのsub-slot `[6]`、1B
- 新規グローバルRAM: なし
- 上下2ID化でも新規RAMは不要な設計にできる。

### 6. 監査結果

#### 現行方向設定の訂正結果

- 現行initがbehavior `$00` を書くことだけを根拠に、Ghost右へ誤動作すると断定した先行監査は誤りだった。
- setup group `$18` がNeul用のY速度を設定し、ユーザー実機確認でも現行 `$88` は正しく上移動している。
- 現行上向きが画面上で成立する理由は、group `$18` の原作 `$30` 相当速度がY負方向だからである。
- ただしbehavior `$00` は原作定義では右であり、速度と方向bitが不一致である。現行表示を壊す即時バグではないが、上下2ID化では残してはいけない実装上の不整合と確定した。

#### 成立している点

- 原作Neul/Ghost AIを再利用し、射撃処理だけ追加する基本構成は妥当である。
- 左右2発の方向値はBulletの右 `$00`、左 `$01` と整合する。
- cooldownと壁状態中の射撃抑止はBomber/Cannon系と同じ構造である。
- runtimeはステージ使用有無に関係なく完成形ROMへ毎回書かれる。

#### 重複・最適化候補

- pointer退避、原作AI呼出し、壁状態判定、cooldown、空きchild slot検索、Bullet生成はBomber/Cannon/Back Fireと重複する。
- Neul Twin Cannonは1回のcooldownで `fire_one` を右・左の2回呼ぶ点だけが異なる。
- 最終実装ではGhost系共通射撃本体、または少なくともBullet 1発生成helperを共有できる候補である。
- 共通化後の正確なROM使用量は未算出なので、現時点では削減量を確定しない。

#### 左右2発とsub-slot `[6]` の確認結果

- 親sub-slot `[6]` は、Bullet生成時に空きslot indexを `$AE76` へ渡す一時的な受渡し欄として使われる。
- `$AE76` はそのindexから生成先main-slotを求め、Bullet type `$20`、方向、座標を書いた後、親sub-slot `[0]` の所有bit 0を解除する。
- 生成後のBulletは独立したAI `$AFBB` で移動・衝突判定・壁破壊・消滅を行う。親が2発分のindexを保持し続ける必要はない。
- そのため2発目がsub-slot `[6]` を上書きしても、1発目の移動や壁破壊は継続する。ユーザー実機確認でも左右両方の壁破壊が成立している。
- 原作Neul AIもsub-slot `[6]` を壁処理用の一時entityに使うが、追加射撃は原作AI実行後にbehavior state bits `$0C` が0の時だけ行う。原作側の壁処理state中は射撃しないため、同時所有の競合を避ける構造になっている。
- 空きslotが1つだけの場合は右弾だけが生成され、2発目の左弾が失敗してもcooldownが再装填される。この挙動はslot不足時の許容仕様として確定し、修正対象にしない。
- 親が撃破された後も生成済みBulletは独立entityとして継続する。親死亡時に左右弾を消す処理は追加しない。

### 7. 鍵持ち判定

- Neul Twin Cannonはダーナ火球で撃破可能な敵として扱う。
- 原作Neul/Ghost AIに落下死亡経路はなく、通常撃破は既存 `$C267` 鍵drop hookを通る想定である。
- 上下2種類とも鍵持ち敵として指定可能にする。
- ただし上下2ID化後の火球撃破と鍵出現は実機未検査なので、OK扱いにはしない。

### 8. 検査状況

| 検査 | 状態 | 備考 |
|---|---|---|
| 現行ID・名称確認 | 済み | `$88` Neul Twin Cannon |
| 原作方向bit確認 | 済み | `$02` 上、`$03` 下 |
| 現行runtime静的解析 | 済み | 158B本体を確認 |
| 現行上移動 | ユーザー実機確認済み | setup group `$18` と専用initの組合せで成立 |
| 共通入口静的解析 | 済み | AI/setup/initあり、animation専用分類なし |
| 左右2発の独立動作 | 静的確認＋ユーザー実機確認済み | `$AE76` 後は各Bulletが独立し、左右とも壁破壊 |
| 現行保存ROMの本体バイト列比較 | 未検査 | 現行完成形ROMを新規出力して比較が必要 |
| 現行上向き `$88` | ユーザー実機確認済み | group `$18` の原作 `$30` 相当Y負速度で上移動。behavior不一致は完成形で解消 |
| 新規下向き版 | 仕様確定・未実装 | 原作 `$32` 相当Y正速度＋behavior `$03`。表示、射撃、壁反転は実装後検査 |
| child slot不足時の右弾優先 | 仕様確定 | 空き1slotなら右弾だけ。修正しない |
| 親死亡時の左右弾 | 仕様確定 | 独立Bulletとして継続。連動消去は追加しない |
| 火球撃破・鍵出現 | 未検査 | 上下両方で確認する |
| 原作Neul/Ghost副作用 | 未検査 | 原作敵を残した比較ROMが必要 |

未検査項目はOK扱いにしない。

### 9. 現時点の最終判断

- 必要ID数: 2
- 種類: Neul Twin Cannon上、Neul Twin Cannon下
- 速度違い・追加派生: 作らない
- 配置: 2連番へ再配置する
- 連番内規則: 2連番を上・下の順にし、offset bit 0を原作 `$30/$32` subtypeへ明示変換する
- 開始ID: 全体配置図まで保留
- 確保範囲: 必要数は2ID。2IDだけ詰めるか未使用枠を隣接させるかは全体配置図まで保留
- 現行 `$88`: 完成形の2ID配置が決まるまで仮位置
- 入口センター: AI/setup/initを2ID範囲として分類し、animation専用分類は置かない
- runtime: 上=`$30`相当速度＋behavior `$02`、下=`$32`相当速度＋behavior `$03`。Ghost系との射撃共通化は実装時に判断する
- 2発child処理: sub-slot `[6]` は一時受渡しなので2発生成と矛盾しない。slot不足時の右弾優先は許容仕様
- 鍵持ち敵仕様: 上下とも指定可能。火球撃破と鍵出現は実装後に検査する
- 実装状態: 未変更

---

## Chaos Dragon

### 1. 基本情報

- 現在のID: `$89`
- ID方式: 専用ID
- モデル敵: Dragon右 `$68`
- 初期方向: 右
- 方向別ID: 作らない
- 速度別・追加派生: 作らない
- 必要ID数: 1
- 現在の判断: 単独1IDで確定する。最終IDは全体配置図まで保留する。
- 実装本体: `magatu_skc/core/flying_dragon89_runtime.py`
- 共通分類: `magatu_skc/core/new_enemy_runtime.py`

### 2. ID配置の根拠

Chaos Dragonは初期状態を右向きで開始するが、原作Dragon AIの壁判定、接近判定、state遷移によって短時間で左右反転する特殊な動きをする。

- 初期左向きIDを追加しても、AIによる方向変更後は右開始版との差が残らない。
- 配置時の初期方向を選択できることに実用上の意味がない。
- 速度違い、攻撃違い、追加派生も作らない。

したがって右開始の単独1IDだけを用意する。方向IDを揃えるためだけに左向きIDを追加しない。

単独IDの配置場所と隣接予約の有無は、全敵の最終配置図で決める。

### 3. 新敵ID共通入口センター

現行 `$89` は次の3入口で専用分類され、animationは原作処理を使う。

| 入口 | 現行処理 | 完成形での方針 |
|---|---|---|
| AI | `$89` をChaos Dragon AI入口へ分岐 | 単独ID比較を維持する候補 |
| setup | `$89` をDragon metadata読込へ分岐 | 単独ID比較を維持する候補 |
| init | `$89` を専用initへ分岐 | 単独ID比較を維持する候補 |
| animation | 専用分類なし。原作 `$8789` を使用 | 専用分類なしを維持する |

方向別分類は追加しない。最終IDが移動した場合はAI/setup/initの比較値だけを一括更新する。

### 4. runtime処理

#### setup

- setup/animation group `$34`、原作Dragon右 `$68` のvisual classを使用する。
- group `$34` を `$0E` へ保存し、原作animation setupがDragon metadataを使えるようにする。
- metadata読込自体はindex `$00` を使用し、初期Y速度を書かない構成である。

#### init

- 共通init入口がstackへ保存した、custom type `$89` 由来のbehaviorを破棄する。
- status `$C0`、無重力activeを設定する。
- main-slot `[5]` の初期Y速度を `$00` にする。
- behavior `$14`、Dragon state 5・右方向で原作init writer `$9D1C` へ接続する。

#### AI

- 専用処理は `JMP $A64A` の3Bだけで、原作Dragon AIをそのまま使う。
- Dragon state 5はDana接近判定、壁判定、移動阻害判定によってstateと方向を更新する。
- Chaos Dragonの頻繁な左右反転はこの原作AIによるものであり、方向別IDで制御する設計ではない。

#### animation

- 専用animation runtimeはない。
- 原作Dragon animationとgroup `$34` を使用する。

### 5. ROM/RAM使用

#### 現行Chaos Dragon本体

- file: `0x6EB4-0x6ED0`
- CPU: `$EEA4-$EEC0`
- 使用量: 29B
- 内訳: setup 10B、init 16B、AI 3B
- 直前の現行予約: Neul Twin Cannon `0x6E16-0x6EB3`
- 直後の現行予約: Back Fire `0x6ED1-0x6F52`
- 本体前後の連続空き: 0B

#### RAM

- 新規専用RAM: なし
- 原作Dragonが使うmain-slot/sub-slotだけを使用する。

### 6. 監査結果

#### 成立している点

- 右向きDragonの見た目と原作Dragon AIを最小runtimeで再利用している。
- status `$C0` とY速度 `$00` により、原作Dragonの通常出現降下を省いた飛行型として開始する。
- behavior `$14` により、出現stateを経由せずDragonの主行動state 5へ直接入る。
- 方向変更をAIへ任せるため、単独IDという仕様と実装が一致している。
- runtimeはステージ使用有無に関係なく完成形ROMへ毎回書かれる。

#### 明確なロジックミス

- 静的解析では見つかっていない。

#### 重複・最適化候補

- AI本体は3Bの原作AI jumpだけなので、削減対象となる重複はほぼない。
- setup 10Bとinit 16Bを入口センターへインライン化するとPRG1は減るが、PRG0入口センターが増える。
- PRG0を狭い通路として扱う方針では、現行の小さなPRG1本体を維持する方がよい候補である。
- 最終runtime再配置時は29Bを前後のruntimeと詰めるが、処理自体を複雑にして数B削る必要はない。

#### 要確認事項

- 原作Dragon AIには通常Dragonの落下・寿命消滅stateがある。
- Chaos Dragonは無重力かつstate 5から始まるため、その消滅stateへ実際に入るかは今回未検査である。
- ユーザー確認済みの頻繁な左右反転は仕様として扱うが、長時間動作、壁際、足場崩壊、Dana接近時の全state遷移は別途確認する。

### 7. 鍵持ち判定

- Chaos Dragonはダーナ火球で撃破可能な敵として扱うため、鍵持ち指定可能候補である。
- ただし原作Dragon AIの自然消滅stateへ入る場合、その経路は鍵drop hookを通らない可能性がある。
- 鍵持ち可否を最終確定する前に、Chaos Dragonが火球撃破以外で消滅する経路を実機確認する。
- 自然消滅しないことを確認できれば、通常火球撃破の既存 `$C267` 鍵drop hookだけでよい。

### 8. 検査状況

| 検査 | 状態 | 備考 |
|---|---|---|
| 現行ID・名称確認 | 済み | `$89` Chaos Dragon |
| 必要ID数 | 仕様確定 | 右開始の単独1ID |
| 現行runtime静的解析 | 済み | 29B本体を確認 |
| 共通入口静的解析 | 済み | AI/setup/initあり、animation専用分類なし |
| 左右反転仕様 | ユーザー実機確認済み | 方向別IDは不要 |
| 現行保存ROMの本体バイト列比較 | 未検査 | 現行完成形ROMを新規出力して比較が必要 |
| 長時間・壁際・足場崩壊 | 未検査 | 自然消滅stateへ入るか確認する |
| 火球撃破・鍵出現 | 未検査 | 鍵持ち可否の確定に必要 |
| 原作Dragon副作用 | 未検査 | 原作Dragonを残した比較ROMが必要 |

未検査項目はOK扱いにしない。

### 9. 現時点の最終判断

- 必要ID数: 1
- 初期方向: 右だけ
- 左向きID: 作らない
- 速度違い・追加派生: 作らない
- ID配置: 単独1ID。最終番号と隣接予約は全体配置図まで保留
- 入口センター: AI/setup/initの単独分類、animation専用分類なし
- runtime: 現行29Bを維持する候補
- 方向反転: 原作Dragon AIによる頻繁な左右反転を仕様として維持
- 鍵持ち敵仕様: 指定可能候補。自然消滅経路の有無を確認後に確定
- 実装状態: 未変更

---

## Phantom Bullet / Phantom Bullet Wave

### 1. 基本情報

- 現在のID: Phantom Bullet `$8B`、Phantom Bullet Wave `$8C`
- ID方式: 専用ID
- モデル敵: Bullet右 `$20`
- 完成形に必要な方向: 右・左・上・下
- 完成形に必要な速度枠: 2段階。各枠の実速度倍率はUIで指定する
- 種類: 通常、Wave
- 必要ID数: 4方向 × 2速度 × 2種類 = 16
- 現在の判断: Phantom Bullet系として16連番へ再配置する。開始IDは全体配置図まで保留する。
- 実装本体: `magatu_skc/core/bullet91_runtime.py`、`magatu_skc/core/bullet92_runtime.py`
- 共通分類: `magatu_skc/core/new_enemy_runtime.py`

### 2. 16ID配置

16連番を4ID単位の4グループとして使う。

| 16連番内offset | 種類 | 速度 | 方向 |
|---:|---|---|---|
| `+0` | Phantom Bullet | 速度枠1・UI設定値 | 右 |
| `+1` | Phantom Bullet | 速度枠1・UI設定値 | 左 |
| `+2` | Phantom Bullet | 速度枠1・UI設定値 | 上 |
| `+3` | Phantom Bullet | 速度枠1・UI設定値 | 下 |
| `+4` | Phantom Bullet | 速度枠2・UI設定値 | 右 |
| `+5` | Phantom Bullet | 速度枠2・UI設定値 | 左 |
| `+6` | Phantom Bullet | 速度枠2・UI設定値 | 上 |
| `+7` | Phantom Bullet | 速度枠2・UI設定値 | 下 |
| `+8` | Phantom Bullet Wave | 速度枠1・UI設定値 | 右 |
| `+9` | Phantom Bullet Wave | 速度枠1・UI設定値 | 左 |
| `+A` | Phantom Bullet Wave | 速度枠1・UI設定値 | 上 |
| `+B` | Phantom Bullet Wave | 速度枠1・UI設定値 | 下 |
| `+C` | Phantom Bullet Wave | 速度枠2・UI設定値 | 右 |
| `+D` | Phantom Bullet Wave | 速度枠2・UI設定値 | 左 |
| `+E` | Phantom Bullet Wave | 速度枠2・UI設定値 | 上 |
| `+F` | Phantom Bullet Wave | 速度枠2・UI設定値 | 下 |

方向順は原作Bulletのbehavior下位2bitと同じ、`0=右 / 1=左 / 2=上 / 3=下` とする。これにより下位2bitをそのまま方向として使える。

16連番内ではbit 2が速度設定枠、bit 3が通常/Waveを表す配置になる。4ID単位のAI分類とも一致し、各グループを個別ID比較せず扱える。bit 2は固定速度値そのものではなく、UIで個別設定する2つの速度枠を選ぶ。

必要数と確保数はともに16IDとし、Phantom系ブロック内に未使用IDは置かない。開始位置は他敵との全体配置で決める。

### 3. 新敵ID共通入口センター

現行 `$8B/$8C` は4入口すべてで専用分類される。

| 入口 | 現行処理 | 完成形での方針 |
|---|---|---|
| AI | `$8B/$8C` を個別比較し、通常/Wave本体へ分岐 | 16ID範囲を判定し、bit 3で通常/Waveを選ぶ |
| setup | `$8B/$8C` を個別比較し、Bullet group `$10` へ分岐 | ROM生成時に方向とUI速度設定を反映したsetupを用意する |
| init | `$8B/$8C` を個別比較し、右向き専用initへ分岐 | ROM生成時に4方向と各速度枠の即値を焼き込む |
| animation | `$8B/$8C` を個別比較し、専用palette処理へ分岐 | 16ID範囲を一度で分類して同じpalette処理を使う |

16IDを16回比較しない。共通入口センター内で連続範囲とbitを使って分類する。

### 4. 現行runtime処理

#### Phantom Bullet `$8B`

- setup group `$10`、原作Bullet右のvisual/velocity classを使う。
- status `$C0`、behavior `$00`、右向きで初期化する。
- 原作Bulletのstate 0とstate 1はそのまま使う。
- 飛翔state 2だけ専用RTSへ送り、原作の壁衝突、ブロック破壊、自身のdespawn処理を通さない。
- その結果、壁やブロックを破壊せず貫通して直進する。

#### Phantom Bullet Wave `$8C`

- Phantom Bulletと同じ壁抜けBulletを基礎にする。
- initでsub-slot `[6]` を `$FF` にし、最初のWave phase適用を強制する。
- `$043C` frame counterを1bit右shiftし、`& $3F` で64段階のphaseを作る。
- 同じphaseを1frame中に二重適用しないよう、最後のphaseをsub-slot `[6]` に保存する。
- 64Bの差分tableを現在のY座標へ加算する。
- 差分tableの1周期合計は0で、長期的に基準位置へ戻る。

#### animation/palette

- 原作animation updater `$8789` を実行する。
- attrへ `AND #$33 / ORA #$48` を適用し、flip bitを残してSPR #2 paletteへ変更する。
- UI picker側もpalette override 6を使う。

### 5. 16ID化で必要なruntime変更

#### 4方向

- 通常版は下位2bitをbehaviorへ設定し、原作Bulletと同じ右・左・上・下の速度方向を使う。
- Wave版も同じ方向規則を使う。
- setupとinitの両方で方向に対応したX/Y速度が一致することを確認する。

#### 2速度

- 現行は両方ともgroup `$10` の1速度だけである。
- 完成形では速度枠1と速度枠2を持つが、それぞれの速度倍率は固定仕様にしない。
- ユーザーはUI上で各速度枠へ `1/2`、`1/4` などの倍率を指定できるようにする。
- UI設定はROM作成時にX/Y速度の即値へ変換し、生成runtimeへ書き込む。NES実行中に倍率計算や設定値解釈を行わない。
- 方向によって絶対速度が変わらないよう、ROM生成側が右左ではX、上下ではYへ同じ速度量を符号違いで焼き込む。
- `$40` は速度更新skip markerなので、UI値から即値へ変換する時に生成してはいけない。
- UIでは選択可能な倍率と実際に書くNES速度byteの対応を日本語・英語の両方で分かるようにする。

#### Waveの方向別軸

- 現行Waveは常にY座標へ波形差分を加えるため、右・左では進行方向に対して垂直なWaveになる。
- 上・下へ同じ処理を使うと、Y進行方向そのものを加減速するだけで、左右へ揺れるWaveにならない。
- ユーザーはUI上でWaveの振幅、つまり中心線から左右または上下へどこまで深く振れるかを設定できるようにする。
- UI設定からROM生成側がWave差分tableを作り、完成したtable byte列をROMへ書く。NES実行中に振幅を計算しない。
- ROM生成側は右・左用runtimeではY座標へ、上・下用runtimeではX座標へ加算するコードをあらかじめ生成する。
- 「Y軸をX軸へ変換する」という汎用処理をNES runtimeへ追加しない。方向別に正しい座標offsetを使うバイト列をROM作成時に選ぶ。
- Wave周期は前進速度設定と一致させる。周期を独立したNES runtime設定として持たせない。
- 速度枠ごとに必要なphase進行またはtable配置をROM生成側で確定し、NES側には完成した即値とtableだけを置く。

#### UI設定とROM生成の責務

- 速度倍率、Wave振幅、方向別の加算軸はカスタマイザー側の設定・ROM生成責務とする。
- 設定値は保存対象のUI設定として日本語・英語両方の文言を用意する。
- ROM作成時に設定値を検証し、NES用の速度byte、座標offset、Wave差分tableへ変換する。
- NES runtimeは書き込まれた即値とtableを使うだけとし、倍率、振幅、軸変換の抽象設定を実行時に解釈しない。

### 6. ROM/RAM使用

#### 現行Phantom Bullet本体

- file: `0x6F53-0x6F73`
- CPU: `$EF43-$EF63`
- 使用量: 33B
- 内訳: setup 9B、init 11B、AI 13B

#### 現行Phantom Bullet Wave本体

- file: `0x6F74-0x6FFC`
- CPU: `$EF64-$EFEC`
- 使用量: 137B
- 内訳: setup 9B、init 22B、AIと64B Wave table 106B
- 直後の現行runtime予約なし領域: `0x6FFD-0x7004` / `$EFED-$EFF4`、8B
- その直後の現行予約: Solomon Seal block helper `0x7005-0x700F` / `$EFF5-$EFFF`、11B

#### RAM

- Phantom Bullet通常版の新規専用RAM: なし
- Wave phase記録: 各Wave Bullet自身のsub-slot `[6]`、1B
- Wave phase source: 既存frame counter `$043C`
- 新規グローバルRAM: なし
- 16ID化後も各entityのtype下位bitとsub-slotだけで分類できるため、新規RAMは不要な設計にできる。

### 7. 監査結果

#### 成立している点

- 原作Bulletの出現・寿命stateを再利用し、飛翔中の壁処理だけを差し替える構成は小さい。
- 通常版は33B、Wave版は137Bで役割が分離されている。
- Wave tableは1周期の差分合計が0で、累積位置が周期ごとにずれ続けない。
- outer enemy-loopのX registerをWave処理前後で保存・復元している。
- 同一phaseの二重加算をsub-slot `[6]` で防いでいる。
- runtimeはステージ使用有無に関係なく完成形ROMへ毎回書かれる。

#### 明確な不足

- 現行は通常版もWave版も右向き・1速度だけであり、要求される16種類を満たしていない。
- UI/config上は `$8B/$8C` の両方が同じPhantom Bullet名で、Waveを区別できない箇所がある。
- 速度枠1/2のUI、倍率からNES速度byteへの変換、即値書込経路がまだない。
- Wave上下版の垂直軸切替がない。
- Wave振幅のUI、差分table生成、ROM書込経路がまだない。

#### 重複・最適化候補

- 通常/Waveでsetup 9Bが重複し、init先頭のstatus/behavior初期化も重複する。
- AIのstate table先頭12Bも重複する。
- 16ID化では共通setup、共通init、共通state dispatchを1つにし、state 2だけbit 3で通常/Waveへ分けられる候補である。
- 64B Wave tableは全方向・両速度で1つを共有できる。
- 正確な削減量と追加量は、UI設定から生成する速度即値、方向別Wave処理、振幅tableのバイト列が決まるまで未算出とする。

#### 危険な前提・要検査

- Wave phaseは各弾の生成時刻ではなくグローバルframe counter基準なので、途中生成した弾はその時点のphaseからWaveを開始する。
- 複数Wave Bulletは同じframeでは同じphaseを使い、同期して揺れる。この挙動を現行仕様として維持する候補だが実機確認が必要である。
- 壁衝突despawnを飛ばすため、画面外へ出た後の共通despawn経路が4方向すべてで働くか確認する。
- Wave上下版でX座標へ差分を加えた際、画面端wrapや壁内位置からの復帰を確認する。

### 8. 鍵持ち判定

- Phantom Bullet系は通常敵ではなく、飛翔するBullet entityを配置敵として使う特殊敵である。
- ダーナ火球で撃破できるか、接触・画面外移動・寿命で先に消えるかを今回未検査である。
- 鍵持ち敵にした場合、撃破前に画面外へ抜けて鍵が出ない危険がある。
- したがって現時点では鍵持ち可とも禁止とも確定しない。16IDすべてについて火球衝突、寿命、画面外despawn、鍵dropを確認して決める。

### 9. 検査状況

| 検査 | 状態 | 備考 |
|---|---|---|
| 現行ID・runtime確認 | 済み | `$8B`通常33B、`$8C`Wave 137B |
| 必要ID数 | 仕様確定 | 4方向×2速度×2種類=16 |
| 16ID内offset | 仕様確定 | 方向bit、速度bit、Wave bitを割当 |
| 共通入口静的解析 | 済み | AI/setup/init/animationの4入口すべて必要 |
| 現行Wave table検査 | 済み | 64B、差分合計0 |
| 現行保存ROMの本体バイト列比較 | 未検査 | 現行完成形ROMを新規出力して比較が必要 |
| 速度枠1/2のUI | 未実装 | 倍率選択、NES速度byte変換、即値書込が必要 |
| Wave振幅UI | 未実装 | 振幅から64step差分tableを生成して書く |
| 通常4方向×2速度 | 未作成・未検査 | 8種類すべて確認する |
| Wave 4方向×2速度 | 未作成・未検査 | 8種類すべて確認する |
| Wave方向別生成 | 未作成・未検査 | 右左=Y、上下=Xのバイト列をROM生成側で作る |
| 複数Waveの同期 | 未検査 | global phase仕様を確認する |
| 火球撃破・鍵出現 | 未検査 | 鍵持ち可否を決める |
| 原作Bullet/Panel Monster副作用 | 未検査 | 原作敵を残した比較ROMが必要 |

未検査項目はOK扱いにしない。

### 10. 現時点の最終判断

- 必要ID数・確保数: 16
- 配置: 4IDグループを4組連続配置する
- `+0～+3`: Phantom Bullet速度1、右左上下
- `+4～+7`: Phantom Bullet速度2、右左上下
- `+8～+B`: Phantom Bullet Wave速度1、右左上下
- `+C～+F`: Phantom Bullet Wave速度2、右左上下
- bit割当: bits 0-1=方向、bit 2=UIで値を決める速度枠、bit 3=通常/Wave
- 開始ID: 全体配置図まで保留
- 入口センター: 16ID範囲を分類し、4入口すべて対応する
- runtime: 通常/Waveの共通部分を統合し、Wave tableは1つを共有する候補
- 速度設定: 各速度枠の倍率をUIで指定し、ROM生成時にNES速度即値として焼き込む
- Wave振幅: UIで指定し、ROM生成時に64step差分tableへ変換して焼き込む
- Wave方向: ROM生成側が右左用はY座標、上下用はX座標を使うバイト列を作る。NES実行時の軸変換は行わない
- Wave周期: 速度設定と一致させ、独立設定にはしない
- UI名称: 通常とWave、方向、速度枠を区別できる日本語・英語名称へ変更する
- 鍵持ち敵仕様: 未確定。火球撃破、寿命、画面外despawn、鍵dropを検査して決める
- 実装状態: 未変更

---

## Seraphic Radiance

### 1. 基本情報

- 現在のID: `$9D`
- UI名称: 熾天の眩光 / Seraphic Radiance
- ID方式: 専用ID
- 移動方向: 設置座標から自動決定
- 方向別ID: 作らない
- 速度別・追加派生: 作らない
- 必要ID数: 1
- 現在の判断: 単独1IDで確定する。最終番号は全体配置図まで保留する。
- 実装本体: `magatu_skc/core/seraphic_radiance9d_runtime.py`
- 共通分類: `magatu_skc/core/new_enemy_runtime.py`

### 2. ID配置の根拠

Seraphic Radianceは敵IDで初期方向を選ばない。生成時の設置座標を画面中心と比較し、内側へ向かう縦横方向を自動決定する。

- X座標が中心より右なら左、左なら右へ向ける。
- Y座標が中心より下なら上、上なら下へ向ける。
- 移動phaseがX/Yを交互に切り替える。
- 画面端で各方向bitを反転する。

同じIDをどこへ置くかで初期進行方向が変わるため、上下左右の方向別IDは不要である。単独1IDの配置場所と隣接予約は全体配置図で決める。

### 3. 新敵ID共通入口センター

Seraphic Radianceは4入口すべてに専用分類が必要である。

| 入口 | 現行処理 | 完成形での方針 |
|---|---|---|
| AI | `$9D` をphase切替・移動・衝突処理へ送る | 単独ID分類を維持 |
| setup | `$9D` をFairy group `$0E` の安全な無重力setupへ送る | 維持 |
| init | `$9D` を専用status・座標方向初期化へ送る | 維持 |
| animation | `$9D` を専用2frame animationへ送る | 維持 |

単独IDであっても4入口のどれも省略できない。分類は共通入口センター内へ維持する。

### 4. runtime処理

#### setup/init

- Fairy group `$0E` を使い、安全な無重力setupを得る。
- status `$C4`、active・visible・no gravity・fire immuneで初期化する。
- type `$9D` を維持し、原作init writer `$9D1C` を呼ぶ。
- main-slotのX/Y座標を画面中心 `$88/$78` と比較し、sub-slot `[7]` のbit 0へ縦方向、bit 1へ横方向を保存する。
- bit 2はX/Y移動phaseとして0から開始する。

#### phase/movement

- phase入口はsub-slot `[7]` のbit 2を毎回反転する。
- phaseにより縦移動または横移動を選ぶ。
- 縦方向はY `$21-$D0`、横方向はX `$09-$E8` の境界で反転する。
- 1回の選択軸で1pixel移動するため、X/Y交互の斜め移動になる。

#### collision

- 17個の敵main-slotを走査する。
- 非active slotと同じSeraphic Radiance type `$9D` を除外する。
- X/Yとも16pixel未満の重なりなら、対象main-slotと対応sub-slotのstatusを直接0へする。
- 原作の通常死亡、drop、score、鍵出現処理は呼ばない。
- 消去時に原作のblock removal soundを鳴らす。

#### animation

- global frame counter `$21` のbit 3で8frameごとに2frameを切り替える。
- tile `$B0/$B2` とpacked attr `$CE/$CF` をmain-slot `[17-$19]` へ直接設定する。

### 5. ROM/RAM使用

#### Seraphic Radiance本体

- file: `0x6C04-0x6D2C`
- CPU: `$EBF4-$ED1C`
- 使用量: 297B
- 予約capacity: 404B
- 現行本体後の予約内未使用量: 107B
- 内訳の主要部: setup 8B、phase 12B、collisionを含むAI 205B、init、animation
- 直後の現行runtime: Bomber/Cannon Ghost `0x6D98-0x6E15`

#### RAM

- 方向・phase: 自身のsub-slot `[7]`、1B
- 既存frame counter: `$21`
- pointer作業領域: 既存zero-pageを使用
- 新規グローバルRAM: なし

### 6. 再監査結果

#### 現状維持でよい理由

- 設置座標からの4象限方向生成、X/Y交互phase、画面端反転、17slot衝突走査、main/sub同時消去、専用animationという複数の独立処理が必要である。
- AI 205Bの大部分は17slot走査と16×16重なり判定であり、単純な重複で膨らんだ処理ではない。
- setup、init、phase、AI、animationの各責務が分かれており、明確に削除できる重複は見つからない。
- 既に成立確認を重ねた複雑な処理を、数Bのために再構成するとregister・pointer保護や衝突対象へ副作用を出す危険が高い。
- runtime本体は現行297Bを維持する方針とする。

#### 短縮しない項目

- 17slot走査を対象制限で短縮しない。
- main/subの両status clearを片方だけにしない。
- 方向生成や画面端反転を共通の原作AIへ置き換えない。
- animationを原作汎用処理へ戻さない。
- 4入口のいずれも削除しない。

#### 容量上の注意

- 現行予約capacity 404Bのうち、本体は297B、未使用は107Bである。
- 107Bは現行本体外であり、本体使用量として扱わない。
- 最終runtime再配置ではこの未使用量をそのまま緩衝として残すか、後続runtimeを詰めるかを全体配置で決める。
- 予約を縮小・移動する場合は、実装前に移動範囲、使用量、残り空きを提示する。

### 7. 鍵・drop・消去副作用

#### Seraphic Radiance自身

- status `$C4` でfire immuneであり、通常手段では撃破できない。
- 鍵持ち敵へ指定すると鍵を出現させられないため、明示的に鍵持ち対象外とする。
- UIと保存時検証の両方で鍵持ち選択を禁止する必要がある。

#### Seraphic Radianceが消す敵

- collision処理は対象敵を通常死亡経路へ通さず、main/sub statusを直接0へする。
- score、通常drop、鍵dropを発生させない。
- Seraphic Radianceが鍵持ち指定された別敵を消した場合、鍵が出ず進行不能になる可能性がある。
- 最終仕様では、鍵持ち敵を衝突対象から除外するか、Seraphic Radianceによる消去でも鍵を出すか、組合せ自体をUIで禁止するかを決める必要がある。
- この問題はruntime短縮とは別であり、現状維持方針でも未解決のゲーム進行副作用として残す。

### 8. 検査状況

| 検査 | 状態 | 備考 |
|---|---|---|
| 必要ID数 | 仕様確定 | 設置位置で方向決定する単独1ID |
| 現行runtime静的解析 | 済み | 297B本体、4入口を確認 |
| 方向・phase処理 | 静的確認済み | X/Y交互、画面端反転 |
| 17slot collision | 静的確認済み | 同type除外、main/sub直接clear |
| 明確な短縮余地 | なし | 現状維持を推奨 |
| 現行保存ROMの本体バイト列比較 | 未検査 | 現行完成形ROMを新規出力して比較が必要 |
| 四象限の初期方向 | 今回未検査 | 各象限と中心境界を確認する |
| 画面端反転・長時間移動 | 今回未検査 | 全方向を確認する |
| 複数Radiance相互非衝突 | 今回未検査 | 同type除外を確認する |
| 鍵持ち敵との衝突 | 未検査 | 鍵不出現と進行不能条件を確認する |
| 原作敵・drop・score副作用 | 未検査 | 直接clearの影響を確認する |

未検査項目はOK扱いにしない。

### 9. 現時点の最終判断

- 必要ID数: 1
- 方向別ID: 作らない
- 方向決定: 設置座標の四象限から内向きに自動決定
- 最終ID: 全体配置図まで保留
- 入口センター: AI/setup/init/animationの4入口すべて維持
- runtime: 現行297Bをそのまま維持する
- 短縮・再設計: 行わない
- 予約capacity: 404B。未使用107Bの扱いだけ全体runtime配置時に決める
- 鍵持ち敵仕様: Seraphic Radiance自身は明示禁止
- 未解決副作用: Seraphic Radianceが別の鍵持ち敵を直接消すと鍵が出ない可能性
- 実装状態: 未変更

---

## Back Fire

### 1. 基本情報

- 現在のID: `$8A`
- ID方式: 専用ID
- モデル敵: Ghost右・速度1 `$34`
- 現行方向: 右開始だけ
- 完成形に必要な方向: 右・左
- 速度別・追加派生: 作らない
- 必要ID数: 2
- 配置方針: Ghost系8連番の `+4/+5`
- 実装本体: `magatu_skc/core/afterburner90_runtime.py`
- 共通分類: `magatu_skc/core/new_enemy_runtime.py`

### 2. ID配置の根拠

Back Fireは現在の進行方向と逆向きへBulletを発射するGhost派生である。Bomber/Cannonと同じGhost移動AIを使うため、完成形では右開始・左開始の2IDを用意する。

| Ghost系8連番内offset | 種類 | 初期behavior | 射撃方向 |
|---:|---|---:|---|
| `+4` | Back Fire右 | `$00` | 現在X速度の逆、初期は左 |
| `+5` | Back Fire左 | `$01` | 現在X速度の逆、初期は右 |

壁反転後はIDの初期方向ではなく、毎回読み取る現在X速度に従って射撃方向も反転する。速度違いは作らない。

Ghost系8連番全体は、`+0～+3` Bomber/Cannon、`+4/+5` Back Fire、`+6/+7` 未使用予約とする。開始IDは全体配置図まで保留する。

### 3. 新敵ID共通入口センター

現行 `$8A` はAI/setup/initで専用分類され、animationは原作処理を使う。

| 入口 | 現行処理 | 完成形での方針 |
|---|---|---|
| AI | `$8A` をBack Fire AIへ分岐 | Ghost系8連番内 `+4/+5` を同じAIへ分類 |
| setup | `$8A` をGhost group `$1A` へ分岐 | Ghost系8連番と共通化 |
| init | `$8A` を右向き専用initへ分岐 | bit 0からbehavior `$00/$01` を設定 |
| animation | 専用分類なし。原作 `$8789` を使用 | 専用分類なしを維持 |

左右2IDを個別の長い比較列にせず、Ghost系8連番の範囲とoffsetで分類する。

### 4. runtime処理

#### setup/init

- setup group `$1A`、原作Ghost右・速度1 `$34` のvisual/velocity classを使用する。
- status `$C0`、active・no gravityで初期化する。
- 現行behaviorは `$00`、Ghost右である。
- sub-slot `[7]` をcooldown初期値 `$80` で初期化する。
- 完成形では `+4` に `$00`、`+5` に `$01` を設定する。

#### AI

- `$2C-$2F` をstackへ退避し、原作Ghost AI `$ABF7` を呼んで復元する。
- 原作Ghostの壁待ち・ブロック破壊state中は射撃しない。
- sub-slot `[7]` の下位7bitをcooldownとして減算する。
- 初期値 `$80` なので最初の射撃は即時候補、再装填は `$C0` で約64count後に再射撃する。
- 空きchild slotがなければcooldownを再装填せず、次frame以降に再試行する。
- main-slot `[8]` の現在X速度を `$40` と比較する。
- 右移動値ならBullet方向 `$01`、左移動値ならBullet方向 `$00` を選び、現在の進行方向と逆へ撃つ。
- Bullet生成後は `$AE76` により独立Bullet entityとして動く。

### 5. ROM/RAM使用

#### 現行Back Fire本体

- file: `0x6ED1-0x6F52`
- CPU: `$EEC1-$EF42`
- 使用量: 130B
- 内訳: setup 9B、init 22B、AI 99B
- 直前の現行予約: Chaos Dragon `0x6EB4-0x6ED0`
- 直後の現行予約: Phantom Bullet `0x6F53-0x6F73`
- 本体前後の連続空き: 0B

#### RAM

- 射撃cooldown: 親Back Fireのsub-slot `[7]`、1B
- Bullet生成slot受渡し: 親sub-slot `[6]`
- 新規グローバルRAM: なし
- 左右2ID化でも新規RAMは不要である。

### 6. 監査結果

#### 成立している点

- 射撃方向をIDやbehaviorの初期値で固定せず、現在X速度から毎回求めている。
- 右開始・左開始のどちらも、壁反転後を含めて常に後方射撃できる設計である。
- 原作Ghost AI、壁state抑止、cooldown、空きslot再試行は整合している。
- runtimeはステージ使用有無に関係なく完成形ROMへ毎回書かれる。

#### 明確なロジックミス

- 静的解析では見つかっていない。
- 現行は右開始1IDしかなく、要求される左開始版が不足している。

#### 重複・最適化候補

- Back FireのAI 99BはBomber/Cannon GhostのAI 100Bと、pointer保存、原作Ghost AI、壁state判定、cooldown、空きslot検索、Bullet生成がほぼ同じである。
- Back Fire側のコードコメントにも、初回実装ではBomber/Cannon処理を複製し、後で共通射撃化する予定が明記されている。
- 違いは射撃方向の準備だけである。Bomberは固定下、Cannonは固定上、Back Fireは現在X速度の逆を選ぶ。
- 最終実装ではGhost系8連番の共通setup、共通左右init、共通射撃本体へ統合する。
- Neul Twin CannonともBullet 1発生成helperを共有できる候補だが、無理に1本化して分岐を増やすかは最終バイト数で判断する。
- 正確な削減量は共通化後のバイト列が決まるまで未算出とする。

### 7. 鍵持ち判定

- Back Fireはダーナ火球で撃破可能なGhost派生として扱う。
- 原作Ghost AIに落下死亡経路はなく、通常撃破は既存 `$C267` 鍵drop hookを通る想定である。
- 右・左とも鍵持ち敵として指定可能候補である。
- 左右2ID化後の火球撃破と鍵出現は実機未検査なので、OK扱いにはしない。

### 8. 検査状況

| 検査 | 状態 | 備考 |
|---|---|---|
| 現行ID・名称確認 | 済み | `$8A` Back Fire |
| 必要ID数 | 仕様確定 | 右・左の2ID |
| 現行runtime静的解析 | 済み | 130B本体を確認 |
| 後方射撃判定 | 静的確認済み | 現在X速度の逆方向を選択 |
| 共通入口静的解析 | 済み | AI/setup/initあり、animation専用分類なし |
| Bomber/Cannon重複 | 済み | AI 99B/100Bがほぼ共通 |
| 現行保存ROMの本体バイト列比較 | 未検査 | 現行完成形ROMを新規出力して比較が必要 |
| 右開始・壁反転・後方射撃 | 今回未検査 | 現行版を確認する |
| 左開始・壁反転・後方射撃 | 未作成・未検査 | 追加IDで確認する |
| child slot不足時の再試行 | 未検査 | cooldown未再装填を確認する |
| 火球撃破・鍵出現 | 未検査 | 右左両方を確認する |
| 原作Ghost/Neul副作用 | 未検査 | 原作敵を残した比較ROMが必要 |

未検査項目はOK扱いにしない。

### 9. 現時点の最終判断

- 必要ID数: 2
- 種類: Back Fire右、Back Fire左
- 速度違い・追加派生: 作らない
- 配置: Ghost系8連番の `+4/+5`
- 方向規則: bit 0=初期右左
- 射撃規則: IDではなく現在X速度の逆方向
- 開始ID: Ghost系8連番の全体配置まで保留
- 入口センター: AI/setup/initをGhost系範囲として分類、animation専用分類なし
- runtime: Bomber/Cannonとの共通setup・init・射撃本体へ統合する
- 鍵持ち敵仕様: 右左とも指定可能候補。火球撃破と鍵出現を検査する
- 実装状態: 未変更

---

## Spark系24IDの確定仕様

Spark85と借用IDのSpark Ball variantsは別々に配置せず、Spark系の連続24IDとして一緒に監査する。

### 種類とID数

| 24連番内offset | 種類 | 速度 | 方向 | 現行実装との関係 |
|---:|---|---|---|---|
| `+00～+03` | 停止型Spark Ball | 速度1 | 右・左・上・下 | 現借用 `$6A/$6B` 系を4方向化 |
| `+04～+07` | 停止型Spark Ball | 速度2 | 右・左・上・下 | 現借用 `$6E/$6F` 系を4方向化 |
| `+08～+0B` | 透明型Spark Ball | 速度1 | 右・左・上・下 | 現借用 `$72/$73` 系を4方向化 |
| `+0C～+0F` | 透明型Spark Ball | 速度2 | 右・左・上・下 | 現借用 `$76/$77` 系を4方向化 |
| `+10～+13` | 停止後反転型Spark Ball | 速度1 | 右・左・上・下 | 現Spark85を4方向化 |
| `+14～+17` | 停止後反転型Spark Ball | 速度2 | 右・左・上・下 | 現Spark85へ速度2を追加 |

必要ID数は、3種類 × 4方向 × 2速度 = 24IDとする。

### 現行借用IDの制約

- 現行の停止型は借用範囲が4IDだけなので、速度1の上下2方向と速度2の上下2方向しか持てない。
- 現行の透明型も借用範囲が4IDだけなので、速度1の上下2方向と速度2の上下2方向しか持てない。
- 右・左がないのは仕様上不要だからではなく、借用できるID数が不足していたためである。
- 新規専用IDを取得する目的は、速度1/2を維持したまま各種類へ右・左・上・下の4方向を揃えることにある。

### 各種類の意味

- 停止型: UIで指定したLIFE百の位に達している間、停止する。
- 透明型: UIで指定した周期で表示・非表示を切り替える。
- 停止後反転型: 最初に停止条件へ入った時だけ進行方向を逆へ切り替え、そのdigitの間は停止する。別の指定digitへ後で入った時も停止はするが、同じentityを二度目は反転しない。現行Spark85のone-shot仕様を4方向へ拡張する。

### 方向と速度

- 各種類は右・左・上・下の4方向を持つ。
- 24連番内の方向順は `0=右 / 1=左 / 2=上 / 3=下` と確定する。
- 原作subtype対応は、速度1では右=`$28`、左=`$29`、上=`$2A`、下=`$2B`、速度2では右=`$2C`、左=`$2D`、上=`$2E`、下=`$2F` とする。
- Spark内部のsub-slot `[6]` は `0=下 / 1=上 / 2=左 / 3=右` である。したがってUI/ID offsetから `[6]` へは `右→3 / 左→2 / 上→1 / 下→0` と変換する。
- sub-slot `[7]` は単なる反対方向ではなく反射時の次方向予約である。初期化は方向値だけを自作せず、上記原作subtypeのsetup/init結果を一組で再現する。
- 速度1/2は別IDグループとして維持する。
- 速度1/2は原作AI `$A929/$A92D` と速度表 `$A9DF/$A9E7` の2系統を使う。既存のSpark移動速度UIはこの共通速度表を書き換えるため、原作Sparkと追加24IDの双方へ効く。
- NES実行中に速度設定値を解釈する処理は追加しない。

### ID配置方針

- Spark85 `$85` を単独IDとして維持しない。
- Dragon #2借用 `$6A/$6B/$6E/$6F` とGolem #2借用 `$72/$73/$76/$77` は、Spark専用24IDへ移行する方向で監査する。
- 24IDの開始番号、24IDだけ詰めるか32ID境界へ配置するか、隣接8IDを未使用予約にするかは全体配置図まで保留する。
- 借用解除後はDragon/GolemのAI tableを原作へ戻し、追加24IDの分類は共通入口センターへ統合する。

### runtime共通化方針

Spark系24IDは種類ごとに独立runtimeを3本作らず、共通部分を統合する。

#### 全3種類で共有する部分

- 24ID範囲の分類
- 4方向を原作 `$28-$2B` subtypeへ、速度1/2を `$A929/$A92D` へ対応させるsetup・init
- Spark Ball用propertyとanimation metadata
- 原作Spark Ball AIへの接続
- pointer・register保護
- UI設定から原作Spark速度表 `$A9DF/$A9E7` へ書いた速度値の使用

#### 停止型と停止後反転型で共有する部分

- LIFE百の位 `$0439` の読込
- UIで選択した最大4個の停止digitとの比較
- 停止条件で通常の速度commitを行わずRTSする処理
- 停止条件から外れた時に原作Spark移動へ戻る処理

両者の違いは、停止条件へ入った瞬間の処理だけである。

- 停止型: そのまま停止する。
- 停止後反転型: entityごとのone-shot flagを確認し、未反転ならsub-slot `[6]` と `[7]` を双方 `EOR #$01` して反対方向へ一度だけ反転してから停止する。Spark方向encodeでは上下 `0↔1`、左右 `2↔3` がともにXOR 1で反転する。

したがって共通の停止判定本体から、種類bitに応じて短い反転tailを通す構成を推奨する。

#### 透明型だけに必要な部分

- 原作描画後のOAM非表示判定
- UIで選択した透明化周期mask
- 透明phase中に2tileを `$F8` へする処理

透明型は停止判定を使わないが、setup・init・方向・速度・原作Spark AIは他2種類と共有する。

#### 統合時の注意

- 「統合」は1本の巨大routineへ無理に全分岐を詰め込む意味ではない。
- 共通入口、共通setup/init、共通Spark AI wrapper、共通停止判定を1つずつ持ち、反転tailと透明OAM処理だけを分ける。
- 現行Spark85 runtimeと借用variant runtimeに重複する停止判定を残さない。
- 共通化後の正確な使用量は、24ID分類と4方向初期化を組んだ最終バイト列で算出する。

### 現行分岐と完成形の確定

| 処理 | 現行 | 完成形 |
|---|---|---|
| AI | Dragon/Golem AI tableを借用ID用wrapperへ差替 | 24IDを入口センターで分類し、速度1=`$A929`、速度2=`$A92D`へ分岐 |
| setup/init | 借用元type下位bitとSpark85固定値に依存 | 24ID offsetから種類・速度・方向を算出し、原作Spark subtypeを再現 |
| 停止判定 | `$AB13`速度commit直前で借用停止型だけを判定 | 停止型と停止後反転型だけを共通停止判定へ通す |
| property | `$A2CC` global hookで借用8IDへ`$19`を返す | `$A2CC` hookは維持し、判定をSpark専用24IDへ変更。Panel/stock fallbackを維持 |
| animation | `$8B05` global hookで借用8IDを`$D35A`へ送る | animation入口で24IDを原作Spark metadataへ送る |
| 透明化 | `$85FA` global OAM hookでGolem借用4IDだけを判定 | global描画hookは必要だが、判定対象を透明型8IDだけに限定 |

停止型のdigit設定は最大4個で、現行defaultは `0/3/6/9`。一致中は `$AB13` のX/Y速度commitを行わず停止し、不一致なら原作commitへ戻る。透明型の周期maskは `$20/$30/$40/$60/$80` から選び、default `$40`。frame counter `$21` とのANDが0以外のphaseでOAM 2tileのYを `$F8` にする。

現行Spark85には明確な仕様不足が2点ある。停止digitが0固定でUIの4digit設定を共有せず、速度1 `$A929` しか持たない。完成形では前者を停止型と共通化し、後者を24ID内の速度groupで解消する。停止判定とpointer保護の重複も統合対象である。

### 副作用経路

| 経路 | 現行の危険 | 完成形での処置 |
|---|---|---|
| AI table `$A358/$A35A` | Dragon group全体がwrapperを経由 | 原作 `$A64A` へ戻す |
| AI table `$A35C/$A35E` | Golem group全体がwrapperを経由 | 原作 `$AD11` へ戻す |
| 速度出口 `$AB13` | 原作Spark全体の共通出口をJMPで置換 | 原作Sparkは無条件fall-through、追加の停止2種類だけ判定 |
| property `$A2CC` | Panel/stock selectorとのhook chain順に依存 | 借用8ID判定を24ID範囲判定へ置換し、Panel/stock fallback chainを維持 |
| animation `$8B05` | Panel animation hookとのfallback順に依存 | 借用判定を削除。24IDはanimation入口で処理し、Panel chainを維持 |
| OAM `$85FA` | 全entity描画がhookを通る | 透明型8ID以外は原作処理だけを実行 |
| 原作Dragon metadata | 過去の直接table差替を戻す処理が混在 | property `$A322/$A323` とanimation `$D4CA` を原作値のまま維持 |

副作用検査対象は、原作Spark `$28-$2F`、Dragon `$68-$6F`、Golem `$70-$77`、Panel Monsterのproperty/animation chain、透明型以外の全描画entityである。静的監査では経路を確定したが、実ROMのバイト列比較と実機副作用検査は24ID実装後まで未検査とする。

### 静的監査の結論

- 仕様は3種類×4方向×2速度の24IDで確定した。
- 方向順、原作subtype対応、Spark内部direction encode、速度AI分岐を確定した。
- 借用Dragon/Golem IDは解除し、原作AI/property/animationを維持する。
- 停止判定は停止型と停止後反転型で共有し、透明型はOAM処理だけを追加する。
- 正確なruntimeバイト数、共通化後の削減量、最終ROM配置は実装しながら確定する。ここでは未算出であり、空き容量確定値として扱わない。
- 実機検査は未実施なので、動作OK扱いにはしない。

---

## Gargoyle / 強化Gargoyle 2発variant

### 1. ID構成と最終判断

| 系統 | 親移動速度 | 右 | 左 | 弾設定 |
|---|---:|---:|---:|---|
| 通常Gargoyle | 1 | `$78` | `$79` | 原作1発・通常速度 |
| 強化Gargoyle | 1 | `$7A` | `$7B` | 2発・4ID共通設定 |
| 通常Gargoyle | 2 | `$7C` | `$7D` | 原作1発・通常速度 |
| 強化Gargoyle | 2 | `$7E` | `$7F` | 2発・4ID共通設定 |

現時点の判断は、原作Gargoyle速度2側を含む`$7A/$7B/$7E/$7F`の借用を維持する。強化4IDは親本体の移動速度と左右を原作IDから引き継ぐ一方、弾速、1発目と2発目の間隔、発射後クールダウンは1組の共通設定として扱う。

### 2. 現在の仕様

- 1回の発射機会でBulletを2発、時間差で発射する。
- 弾速は`通常 / 1/2 / 1/4`から選ぶ。デフォルトは`1/2`。
- 1発目から2発目までの間隔は`0-255F`で設定する。デフォルトは`12F`。
- 2発目後のクールダウンは`0-255F`で設定する。デフォルトは`120F`。
- 2発目の空きslotを確保できない場合は待ち続けず、2発目を省略してクールダウンへ移る。
- 通常Gargoyleの弾へ強化弾の速度markerを残さない。通常弾は子sub-slot `[7]`を`$00`へ明示初期化する。
- 強化弾の内部markerは、通常速度`$01`、1/2速`$89`、1/4速`$88`。1発目と2発目へ同じmarkerを書く。
- 通常Gargoyleの原作1発経路と、強化Gargoyleの2発経路をID判定で分離する。

### 3. 現在のruntime配置

現行実装は動作成立を優先し、次の2ブロックへ分けている。

| ブロック | file | CPU | 使用量 | 内容 |
|---|---:|---:|---:|---|
| 第1ブロック | `0x634F-0x63A7` | `$E33F-$E397` | 89B | 通常/強化ID判定、1発目生成、速度marker、state 3移行、通常/強化クールダウン |
| 第2ブロック | `0x6D2D-0x6D7F` | `$ED1D-$ED6F` | 83B | state 3待機、2発目slot確保、2発目生成、速度marker、クールダウン移行 |

主なhookは次の3箇所。

- `$AE6F`: 1発目materialize入口
- `$AE48`: 発射後クールダウン判定
- `$AE28`: Gargoyle state 3 dispatch先

現在の合計は172B。配置は完成形ではない。最終runtime配置では2ブロックを1つの連続ブロックへまとめ、hook先、定数、予約範囲、管理簿を同時に更新する。

### 4. runtime再整理で確認する項目

現在は挙動を成立させる実装を優先したため、最終実装前に入口から全分岐・全出口をもう一度監査する。

- 通常/強化のID判定と、1発目生成前後の共通処理を整理する。
- 1発目と2発目で重複するslot参照、`$AE76`呼出し、速度marker書込みを共通化できるか確認する。
- 通常速度marker `$01`、1/2速`$89`、1/4速`$88`の判定がBullet共通速度処理と重複していないか確認する。
- state 3の通常IDガード、待機中RTS、slot成功、slot失敗の各出口を確認する。
- 通常クールダウンと強化クールダウンの共通化範囲を確認し、通常Gargoyleへ強化設定が漏れないことを確認する。
- `A/X/Y`、carry、zero、negative、stack、`$00-$05`、`$2C/$2E`の入口契約と出口状態を命令単位で確認する。
- 即値位置を手計算へ依存させず、組立結果からoffsetを検証できる形へ整理する。
- 1ブロック化後の実使用量を再計測し、不要な旧分岐、重複signature、未使用helperを削除する。

### 5. 最終確認

- 通常Gargoyleが1発後に原作行動へ戻り、強化弾の速度を引き継がない。
- 強化Gargoyleが全速度設定で2発発射し、設定した間隔とクールダウンで復帰する。
- 右向き・左向き、親速度1・2の4IDで同じ弾設定が反映される。
- 2発目slot不足時に停止しない。
- 1ブロック化前後のruntimeバイト列とレジスタ保護差分を確認する。
- 通常Gargoyle、Panel MonsterのBullet速度処理、その他原作敵への副作用を実ROMで確認する。
- 実装、`RESERVED_SPANS`、ROM管理簿は最終配置と検査が確定した同じコミットで更新する。

---

## Saramandor / Saramandor #2 Bullet variant

### 1. ID構成と最終判断

| 系統 | 速度 | 右 | 左 | 用途 |
|---|---:|---:|---:|---|
| 通常Saramandor | 1 | `$5C` | `$5D` | 原作Flame |
| Saramandor #2 | 1 | `$5E` | `$5F` | Bullet variant |
| 通常Saramandor | 2 | `$60` | `$61` | 原作Flame |
| Saramandor #2 | 2 | `$62` | `$63` | Bullet variant |
| 通常Saramandor | 3 | `$64` | `$65` | 原作Flame |
| Saramandor #2相当 | 3 | `$66` | `$67` | Panel Monster 3-way上・下へ貸出済み |

- 通常Saramandorは3速度を維持する。
- 強化Saramandorは速度1/2だけで十分とし、速度3は作らない。
- `$66/$67`はPanel Monster 3-wayへの貸出を維持する。Panel Monster側も借用維持と確定しているため、双方のID方針は整合している。
- Saramandor #2 Bullet variantの4IDも借用維持とし、新規IDへ移さない。

### 2. runtimeの対象分類

現行runtimeは範囲 `$5E-$63` に入った後、bit 1が立つIDだけを対象にする。

- 対象: `$5E/$5F/$62/$63`
- 対象外: 通常Saramandor `$5C/$5D/$60/$61/$64/$65`
- 対象外: Panel Monsterへ貸出済み `$66/$67`
- 対象外: 同じ距離判定routineを共有するDragon

速度1/2の違いは親Saramandor本体の移動速度である。生成するBulletは両速度ともtype `$20` の通常Bullet速度を使い、Bullet側の速度違いは作らない。

### 3. runtime処理

#### spawn setup 47B

- 対象4IDでは子typeをFlame `$04` からBullet `$20` へ変更する。
- 子statusをFlame `$C6` から通常敵Bullet用 `$C0` へ変更する。
- 親behaviorのbit 0からBulletの右・左directionを設定する。
- 対象外は置換前の原作Flame setupをそのまま再現する。

#### child substatus 34B

- 原作 `$B0D9` で子statusを読む処理は維持する。
- Flameではstatusへbit 1を立てる原作処理を通す。
- Bullet variantではFlame固有の `ORA #$02` を行わず、Bullet自身のstatusをそのまま戻す。
- `PHA/PLA`は全分岐で釣り合っており、stack不整合はない。

#### Flame behavior bypass 20B

- Bullet variantではFlame子を消去・連鎖管理する原作 `$B05E` を呼ばずRTSする。
- 対象外は原作 `$B05E` へ戻す。
- Bulletの移動・寿命・消去はtype `$20` の原作Bullet AI `$AFBB`へ任せる。

#### reaction distance 64B

- 対象4IDだけDanaへの横反応距離を `$60`、縦反応距離を原作どおり `$10` にする。
- sub-slot `[5]` のX距離は原作更新済み値をASLして比較するため、`$60`は96px、6tileに相当する。
- 通常SaramandorとDragonは原作の横 `$14`、縦 `$10` をそのまま使う。

### 4. ROM/RAM使用

- runtime: file `0x63D9-0x647D` / CPU `$E3C9-$E46D`
- 使用量: 165B
- 内訳: spawn setup 47B、substatus 34B、Flame behavior bypass 20B、distance check 64B
- `RESERVED_SPANS`: 上記165Bを1本の連続範囲として予約
- runtime直後のfile `0x647E-0x6495`、24Bは現行予約なしの空きであり、本体予約へ含めない。
- 新規グローバルRAM: なし
- 親sub-slot `[7]` と既存child main-slot、原作Bullet entity fieldだけを使う。

### 5. 原作照合と監査結果

- 原作ROMの7か所、`$B105/$B0A9/$B0C6/$B121/$AFD1/$866D/$B1E9`は実装側の原作シグネチャと全て一致した。
- コメント付きASMでも、Saramandor Flame生成、child slot、Bullet type `$20`、方向behavior、共有距離判定の意味を照合した。
- 通常Saramandor/Dragonへ入るfallbackは原作命令列を再現している。
- 4routineは役割が異なり、現配置で明確な重複削減候補は見つかっていない。
- 静的解析上のstack不整合、対象ID漏れ、`$66/$67`巻き込み、通常敵巻き込みは見つかっていない。

#### 文書不一致

- `saramandor_variant.py`冒頭の「`$66/$67 -> reserved / unchanged for now`」は古い。
- 現在の正しい状態は「`$66/$67`はPanel Monster 3-way上・下として借用中」である。
- コードの対象判定自体は`$66/$67`を除外しているため正しく、今回コード変更は行わない。コメント修正は最終整理時に行う。
- `docs/borrowed_enemy_id_audit.html`のSaramandor #2を新規ID移行候補とする記述も、今回の借用維持判断より古い。

### 6. 検査状況

| 検査 | 状態 | 備考 |
|---|---|---|
| ID構成 | 確定 | 通常3速度、強化2速度、左右 |
| `$66/$67`貸出 | 確定 | Panel Monster 3-way上・下として維持 |
| runtime静的解析 | 済み | 165B、4routine |
| 原作ROMシグネチャ | 済み | 7か所すべて一致 |
| 原作ASM照合 | 済み | Flame/Bullet/child/distance経路 |
| 通常Saramandor/Dragon除外 | 静的確認済み | fallbackは原作しきい値と処理 |
| 速度1/2・左右の実機挙動 | 今回未検査 | 既存成立状態を新たにOK判定していない |
| Bullet生成・消滅・slot再利用 | 今回未検査 | 完成形ROMで再確認が必要 |
| 原作敵副作用 | 今回未検査 | 通常3速度とDragonを残した比較ROMが必要 |

### 7. 現時点の最終判断

- ID分類: **借用維持**
- 強化Saramandor速度3: 作らない
- `$66/$67`: Panel Monsterへ貸し出したまま維持
- runtime: 現行165Bを維持する
- 再構築・共通化: 不要
- 実装変更: なし
- 正式ROM/RAM管理簿更新: なし

---

## Panel Monster系 — 借用ID維持

### 1. 基本情報

Panel Monster系は次の24IDで構成する。

| 系統 | ID | 内容 |
|---|---|---|
| 原作 | `$24/$25/$26/$27` | 通常弾、右・左・上・下 |
| 2-way | `$52/$53/$56/$57` | 2方向弾、右・左・上・下 |
| 3-way | `$5A/$5B/$66/$67` | 3方向弾、右・左・上・下 |
| Variant C | `$31/$33/$35/$37` | 設定C、右・左・上・下 |
| Variant A | `$41/$43/$45/$47` | 設定A、右・左・上・下 |
| Variant B | `$49/$4B/$4D/$4F` | 設定B、右・左・上・下 |

追加機能が借用しているのは2-way/3-wayの8IDとA/B/Cの12ID、合計20IDである。

### 2. ID配置の判断

- 結論は20IDすべて借用維持とする。
- Panel Monster v2として、20個の非連続IDを一つの分類・射撃・Bullet速度処理へ既に統合している。
- 新規連続IDへ移す場合は20IDを新たに消費し、UI方向表、描画置換、AI/setup/init/animation分類、保存データ上の敵番号を全面的に移す必要がある。
- 移動によって得られるruntime削減は限定的であり、確立済みの借用構成を壊す費用の方が大きい。

#### 原作配置との衝突

- 借用20IDのうち、原作ステージへ直接配置されるのは `$4D` だけである。
- 原作Stage 29の座標 `(14,4)` と `(14,6)` に、Ghost右 speed 2 noslow #2として2体入っている。
- 日本版原作ROMを通常読込する時、既存の `_normalize_original_jp_enemy_data()` がこの2体だけを通常Ghost `$4C` へ正規化する。
- したがって通常の原作ROM入力ではGhost 2体を維持したうえで `$4D` をPanel Variant B上向きとして借用できる。
- この正規化を外す、または生の原作敵ID列を無変換で拡張ROMへ移す経路を追加すると、Stage 29の2体がPanel Monsterへ化ける。そのような経路を作らないことが借用維持の条件である。

### 3. runtime処理

- 通常Panel、2-way、3-way、A/B/Cは共通のfire dispatchと114Bのfire commonを使う。
- fire common内の入口だけを切り替え、marker tableで通常1発、2-way、3-way、A/B/Cの弾生成を分ける。
- A/B/Cのspeed/intervalは6Bの固定settings tableから読む。ステージに対象敵がいなくてもruntimeとtableは毎回同じ配置へ書く。
- 見た目判定は共通Panel type classifier、方向変換は共通animation direction helper、親速度・作業fieldの初期化も共通helperへ統合済みである。
- Bullet速度decode、追加移動step、Bullet entryもPanel Monster v2の共通処理へ統合済みである。

現時点では、さらに統合して明確に削除できる独立重複処理は見つかっていない。`panel_monster_variant.py` に旧2-way/3-way blob定義は残るが、完成形の書込みは `panel_monster_stage_variant.py` のPanel Monster v2が担当し、旧blobを別runtimeとして二重配置してはいない。

### 4. ROM/RAM使用と静的検査

- PRG0の主要runtimeはfile `0x6496-0x674F` に隙間なく分割配置されている。
- property/animation hook本体は続く `0x675A-0x677F` を使う。
- PRG0 settings tableはfile `0x62ED-0x62F2`、6Bである。
- PRG1 loader slotはfile `0x8A10-0x8A6F`、96Bである。
- gameplay flag helperはfile `0x8A76-0x8A8B`、22Bである。
- 現行`RESERVED_SPANS`内の重複はない。
- runtime本体の配置reportでも相互重複はない。
- 主要runtimeは既に実サイズで詰めて予約され、今回の文書監査でROM/RAM配置は変更しない。

### 5. 検査状況

| 検査 | 状態 | 備考 |
|---|---|---|
| 必要ID数 | 確定 | 原作4ID + 借用20ID |
| ID方針 | 確定 | 借用20IDを維持 |
| runtime共通化 | 静的確認済み | fire、分類、方向、速度、Bullet処理を統合済み |
| 配置重複 | 静的確認済み | runtime report / `RESERVED_SPANS`とも重複なし |
| 原作借用ID配置 | 確認済み | `$4D`だけStage 29に2体 |
| `$4D`原作敵維持 | コード確認済み | 原作ROM読込時に `$4C` へ正規化 |
| 73ケース保存検査 | 既存資料で確認済み | 全方向・混在・再保存同一性など |
| 今回の新規ROM出力・実機検査 | 未実施 | 文書監査のみ。新たなOK判定は出していない |

### 6. 現時点の最終判断

- ID分類: **借用維持**
- 新規ID取得: しない
- 既存20借用ID: 変更しない
- runtime再構築: 原則不要。最終全体配置へ詰める際も、成立済みPanel Monster v2を一まとまりとして維持する
- 追加条件: 日本版原作ROM読込時のStage 29 `$4D` → `$4C` 正規化を維持する
- 実装変更: なし
- 正式ROM/RAM管理簿更新: なし

---

## 次の敵で使う監査テンプレート

各敵は次の順番で記録する。

1. 基本情報
2. ID配置の根拠
3. 新敵ID共通入口センター
4. runtime処理
5. ROM/RAM使用
6. 監査結果
7. 文書不一致
8. 検査状況
9. 現時点の最終判断

各項目で、確定、推測、未検査を明確に分ける。
