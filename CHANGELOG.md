# SOLOMON_CUSTOMIZER CHANGELOG

## v0.8.50 (2026-06-06) ステージPNG保存の隠し表示を切替可能に
- ステージ範囲選択の「すべてのステージ」右に「隠し表示」チェックを追加し、PNG保存時だけ隠しアイテム、隠し扉、特殊ブロックを画像へ表示するか選べるようにした。
- 既定はONにして従来互換を維持し、OFFでは友人へ渡すプレイ用PNGとして隠し要素を画像上に出さないようにした。
- OFF時はミラー識別用の赤/青枠も保存PNGへ出さないようにした。
- 表示オプションの「特殊処理マーカー表示」を「隠し要素強調」の直後へ移動した。
- 「隠し表示」ONかつ「特殊処理マーカー表示」ONのとき、現在ステージ/全ステージの保存PNGにも特殊処理マーカーを出すようにした。
- PNG内の埋め込みステージデータXMLはチェック状態に関係なく保持する。

## v0.8.49 (2026-06-05) 全ステージ読込後のサムネイル更新を修正
- 「すべてのステージ」でステージPNGを読み込んだ後、右側のステージ選択サムネイルを全再生成するようにした。
- 全ステージ読込で実際に1件以上読み込めた場合、変更あり状態として扱うようにした。

## v0.8.48 (2026-06-05) 16列目ロックをCtrl移動にも適用
- 「16列目を編集」がOFFのとき、Ctrl+左ドラッグ移動で16列目の要素を掴んだり、16列目へ移動したりできないようにした。
- 選択範囲のCtrl移動でも、内容物が16列目へ入る移動は部分貼り付けせず拒否するようにした。

## v0.8.47 (2026-06-04) 音楽データ表示を追加
- ROM内サウンドデータを読取専用で解析し、raw byte と C/D/E 表記の解釈を並べて表示する「音楽データ表示」を追加した。
- 実ASM `SUB_F190` / `SUB_F235` に基づき、`F4=RETURN`、`F5=LOOP_START`、`F6=LOOP_DEC_BNE`、`F8=DUTY`、`F9=CHANNEL_END` としてデコードするようにした。
- ユーザー提供MIDIとの照合で `sound id $01` の音程一致を確認し、`0x0C` は休符ではなくホールド/タイとして表示するようにした。
- `docs/sound_analysis.html` の古いコマンド説明とデュレーション説明を、再確認したASM解釈に合わせて更新した。

## v0.8.46 (2026-06-03) 保存ダイアログの初期フォルダを安定化
- ROM保存とIPS保存のダイアログにファイル名だけではなく初期フォルダ付きの保存候補パスを渡し、環境依存のカレントフォルダが開かないようにした。
- 保存成功後のフォルダを記憶し、次回保存時はそのフォルダを優先するようにした。
- 現在ステージのPNG保存はフォルダ自動作成をやめ、`level_XX_日時.png` を直接保存するダイアログにした。全ステージ保存は保存基準フォルダ配下に日時付きフォルダを作る。

## v0.8.45 (2026-06-03) 保存前チェック失敗表示を整理
- ROM保存、テストプレイ準備、IPS生成で保存用ROMを構築する際、どの保存工程で署名検証や予約領域検証に失敗したかを共通形式で表示するようにした。
- ユーザー向けダイアログは短い原因表示に抑え、巨大な署名バイト列などの詳細はログへ出すようにした。

## v0.8.44 (2026-06-03) 再保存時のPanel Variant loader署名エラー修正
- オリジナルROM読込後に保存したmapper66 ROMを続けて再保存すると、StageExt/Panel Monsterの短い旧runtimeとPanel Variantの長いruntimeが共有領域で混在し、Panel Variantの署名検証で保存失敗する問題を修正した。
- StageExt runtime loaderは予約済み96B全体をStageExt loader + 00埋めに、Panel Monster Bullet hookは予約済み81B全体を旧hook + EA埋めに正規化し、その後Panel Variantが必要な場合は従来どおり最終runtimeで上書きするようにした。

## v0.8.43 (2026-06-02) ミラー出現敵パネルの非出現表示を追加
- ミラー詳細設定の出現タイミングが全OFFのミラーは、下部のミラー出現敵セット行をグレーアウトするようにした。
- 敵セット自体は保持したまま、出現スケジュールが無効なため実際には出ない状態をメイン画面上で判別できるようにした。

## v0.8.42 (2026-06-02) 敵ドロップ編集に敵グラフィック表示を追加
- 敵ドロップ編集ダイアログの各行に、その行のドロップ設定が適用される敵グループをスプライト帯で表示するようにした。
- 敵グループ表示は既存の敵ピッカーと同じROM由来スプライトを使い、ツールチップで敵コードと名前を確認できるようにした。
- 敵ドロップ編集ダイアログ下部に「すべてなしにする」ボタンを追加し、全行の8枠を一括でドロップ無しへ変更できるようにした。

## v0.8.41 (2026-06-02) 33面以降のステージ設定読み出しを修正
- mapper66拡張ROMのStageExt runtime loaderで、33面以降のテーブル参照が1面側へ巻き戻る不具合を修正した。
- A禁止、B禁止、暗闇、鍵敵、火リセット、扉セルなどのStageExt由来設定が33面以降でも正しい面番号から読み込まれるようにした。
- Panel Variant使用時のcombined runtime loaderも同じ16bitポインタ計算へ修正し、17面以降のPanel Variant stage table参照も巻き戻らないようにした。

## v0.8.40 (2026-06-02) 敵配置数インジケータを追加
- キャンバス上の余白に、現在ステージの初期配置敵数を15枠のゲージで表示するようにした。
- 1-8体は緑、9-12体は黄色、13-15体は赤で表示し、敵配置数の上限に近い状態を視覚的に確認できるようにした。
- ゲージはステージ切替、配置、削除、Undo/Redo、ステージデータ読込後に現在の敵数へ追従するようにした。

## v0.8.39 (2026-06-02) ステージ貼り付け/入れ替え確認時の対象表示を追加
- ステージ貼り付け確認ダイアログの表示中に、コピー元と貼り付け先のサムネイルを一時ハイライトするようにした。
- ステージ入れ替え確認ダイアログの表示中に、入れ替え元と入れ替え先のサムネイルを一時ハイライトするようにした。
- ハイライトはスクロール位置を変えず、確認ダイアログを閉じたら元の表示へ戻すようにした。

## v0.8.38 (2026-06-02) ステージ一覧のショートカット操作を追加
- 右側のステージサムネイル一覧にフォーカスがある時だけ、Ctrl+Cで面コピー、Ctrl+Vで貼り付け、Ctrl+Xで面入れ替えを呼び出せるようにした。
- キャンバス側にフォーカスがある時は、従来どおり範囲編集のコピー/貼り付け/切り取りとして動作するようにした。

## v0.8.37 (2026-06-02) ステージ一覧の右クリック操作を追加
- 右側のステージサムネイルを右クリックした時に、面コピー、貼り付け、面入れ替えのコンテキストメニューを出すようにした。
- 右クリックしたステージを選択してから既存のステージ操作処理へ接続し、ボタン操作と同じ確認、Undo/Redo、読み取り専用制御を使うようにした。

## v0.8.36 (2026-06-02) ステージ入れ替え先をサムネイルで選択
- ステージ選択ペイン内に入れ替え先番号ボックスを出し、右側のステージサムネイルをクリックすると番号へ反映されるようにした。
- 入れ替え元ステージは最初に「面入れ替え」を押した時点のステージで固定し、選択中ステージを移動しても入れ替え元が変わらないようにした。
- 入れ替え実行前の確認を維持し、入れ替え先入力中は情報表示を「入れ替え元」に切り替えるようにした。
- Windows onedirビルドのEXEファイルアイコンに`docs/images/dana.ico`を指定するようにした。

## v0.8.35 (2026-06-02) ステージのコピー/貼り付け/入れ替えを追加
- 右側のステージ選択ペインへ、現在ステージを内部コピーし、別ステージへ貼り付ける操作を追加した。
- 現在ステージと指定ステージのデータ一式を入れ替える操作を追加した。
- ステージ操作は編集可能ROMだけで有効にし、読み取り専用ROMでは無効化するようにした。
- 入れ替えを1回のUndo/Redoで戻せるよう、複数ステージのスナップショット履歴に対応した。

## v0.8.34 (2026-06-02) Panel Variant final splitの署名確認を強化
- `panel_monster_stage_variant.apply_final_split_test_candidate()` がROMへ書き込む前に、hookサイト、AI table、各小routine配置先、PRG1 loader/tableをまとめて検証するようにした。
- 署名不一致時は書込み前に中止し、ROMが半端に変更されないようにした。
- 既存のStageExt loader、旧Panel Variant prototype、適用済みfinal splitは正規の移行元/再適用元として受け入れるようにした。

## v0.8.33 (2026-06-01) US/skchain ROMを読み取り専用で受け入れ
- skchain US66 mapper66 ROMを厳密署名で判定し、閲覧/ステージ出力専用で読み込めるようにした。
- US/JP mapper3改造ROMも通常編集から分離し、読み取り専用ならステージ表示/出力できるようにした。
- 読み取り専用ROMはROM情報欄に赤字で「編集不可」を表示し、保存・編集・hack・インポート系操作を無効化した。

## v0.8.32 (2026-06-01) 通常編集ROMの入口をJP系に限定
- メインROM読込で、通常ROMは確認済みの日本版オリジナルCRC3件だけを受け付けるようにした。
- 日本版mapper66拡張ROMは、SOLOMON_CUSTOMIZERのメタデータを持つ保存済みROMだけ再読込対象にした。
- mapper66変換入口も確認済み日本版オリジナル通常ROM専用にし、US/EU版やCRC未確認のJP改変ROMから内部変換へ進めないようにした。

## v0.8.31 (2026-05-31) PickupDrop自動パッチを停止
- v0.8.29で追加した共通物理Y高位更新フックと`Y=$D0`下端クランプを撤回。
- さらに`$14-$17` PickupDrop床接触位相緩和 (`$A3FD: CMP #$10`) も停止し、保存時にPickupDrop系ROMバイトを一切変更しないようにした。
- 敵撃破直後のドロップアイテムが、生成位置ではなく最下段床へ瞬間移動したり空中で停止したりする副作用を避けるようにした。

## v0.8.30 (2026-05-31) Stage 20/30の原作bitmapアイテム再注入を停止
- 原作ROM読込時だけ、Stage 20のBat SymbolとStage 30のBlue Opalを24byte bitmapから通常ステージデータへ変換するようにした。
- 変換後はROM側にコピーされたbitmap配置バイトをクリアし、キャンバスで削除したアイテムが保存後の再読込や実機処理で復活しないようにした。
- 既にmapper66拡張済みのROMを開く場合は、m66ステージデータを正として扱い、原作bitmapを再度重ねないようにした。

## v0.8.29 (2026-05-31) ドロップアイテムの下端ラップを防止
- `$14-$17`のPickupDrop向けに、共通物理のY高位更新で下端の危険域または下端から上端へ巻き戻る直前のガードを追加。
- ゴーレムなど敵由来のドロップが混雑時に`Y=$FE->$00`で天井側へ出るケースを、PRG0内の小片フックで下限停止するようにした。
- ラップ直前だけでなく`Y>=$D8`でも停止し、床下へ大きく沈んでから戻る表示を抑えるようにした。
- 下限停止後はX座標更新へ途中復帰せず、共通境界処理へ戻すことで別フィールド参照による瞬間移動を避けるようにした。
- 同日テスト中の旧PickupDrop下端ガード小片が入ったROMも、再保存時に新しい危険域ガードへ置換できるようにした。
- v0.8.12の床接触位相緩和は残し、床判定遅延対策と下端ラップ対策を別レイヤーとして併用するようにした。

## v0.8.28 (2026-05-31) 16x16ピクセル編集にUndo/Redoと反転を追加
- 16x16ピクセル編集へ`元に戻す`/`やり直し`を追加し、`Ctrl+Z`、`Ctrl+Y`、`Ctrl+Shift+Z`へ対応した。
- ペン/右クリック消去のドラッグ操作を1ストローク単位でUndoできるようにした。
- 画像取込、クリア、左右反転、上下反転を1操作として履歴へ積むようにした。
- 16x16ピクセル編集へ`左右反転`/`上下反転`を追加し、選択範囲がある場合は範囲内、ない場合は16x16全体を反転するようにした。

## v0.8.27 (2026-05-31) 16x16ピクセル編集に範囲選択とスポイトを追加
- 16x16ピクセル編集キャンバスで、`Shift+左ドラッグ`による矩形範囲選択を追加した。
- 選択範囲を緑のオーバーレイで表示し、情報欄へ座標とサイズを表示するようにした。
- 16x16ピクセル編集キャンバスで、`Alt+左クリック`したピクセルのパレットインデックスを現在のペンへ取り込めるようにした。
- 通常の左クリックで選択範囲を解除し、選択中の`Esc`でも範囲解除できるようにした。

## v0.8.26 (2026-05-31) ビューア起点の編集動線へ整理
- ROMフレーム一覧のダブルクリックで開く16x16ピクセル編集をモーダル表示から通常ウィンドウ表示へ変更し、ビューアを開いたまま続けて操作できるようにした。
- 同じCHR bank/tile/attrの編集画面を重複起動せず、既存ウィンドウを前面化するようにした。別対象は複数開ける。
- 16x16ピクセル編集側の「一覧を開く」ボタンを削除し、一覧から編集へ進む動線に一本化した。
- ビューアから開いた編集画面のROM書込を即時通知し、ビューア再描画とメイン画面側のCHR再構築へ反映するようにした。

## v0.8.25 (2026-05-31) ピクセル編集から開いた一覧の破棄処理を修正
- 16x16ピクセル編集の「一覧を開く」で表示したビューアを閉じる時、参照クリア用lambdaが`NameError`になる不具合を修正。
- ビューア破棄時の後始末を、編集ダイアログ本体を強参照しない弱参照コールバックへ変更した。

## v0.8.24 (2026-05-31) スプライトビューアとピクセル編集を接続
- スプライト/キャラクタービューアのROMフレーム一覧で、セルをダブルクリックすると該当16x16をピクセル編集で開けるようにした。
- 16x16ピクセル編集からスプライト/キャラクタービューアを開ける「一覧を開く」を追加した。
- ビューア経由でCHRを書き換えた場合も、メイン画面側で変更を検出してレンダラ/表示/サムネイルを再構築するようにした。

## v0.8.23 (2026-05-31) ROM由来16x16表示を一本化
- スプライト/キャラクタービューアの「キャラクター (組み立て)」から、ROMフレームデータと重複していた「ROM由来 全キャラ(組立16x16)」カテゴリを削除。
- ROM由来の16x16確認は「ROMフレームデータ (全網羅 16x16)」へ一本化した。
- 「キャラクター (組み立て)」は`skc_config.xml`由来のアイテム/敵/メタ/全tile_def確認用に整理した。

## v0.8.22 (2026-05-31) ROMフレーム重複参照を統合表示
- スプライト/キャラクタービューアのROMフレーム16x16表示を、既定では同じ`left/right/attr`の編集対象ごとに統合して表示するようにした。
- 必要な場合だけ全フレーム参照を確認できる「重複参照も表示」を追加した。
- 16x16ピクセル編集のフレーム選択も同じ重複統合を既定にし、各編集対象の参照数を表示するようにした。

## v0.8.21 (2026-05-31) スプライトビューアの色順を修正
- スプライト/キャラクタービューアのROMフレーム16x16表示で、スプライトパレットの4バイト目をCHR色3として扱っていた不整合を修正。
- ROM由来16x16組立表示と生CHR表示のSPRパレットも、CHR色0=透明、CHR色1-3=ROMパレット先頭3色として表示するようにした。
- Danaなどのスプライト一覧がピクセル編集と同じ色順で表示されるようにした。

## v0.8.20 (2026-05-31) CHRバンク切替に対応
- 16x16ピクセル編集へCHRバンク選択を追加し、bank 0-3の同じROMフレームtile番号を切り替えて確認・編集できるようにした。
- スプライトビューアのROMフレーム表示で、画面上のCHRバンク選択が実描画に反映されずbank 2固定になっていた不整合を修正。
- スプライトビューアのROM由来16x16組立表示にもCHRバンク選択を追加した。

## v0.8.19 (2026-05-31) ピクセル編集のスプライト色順を修正
- 16x16ピクセル編集で、ROMパレットテーブルの4バイト目をCHR色3として扱っていた不整合を修正。
- CHRピクセル値0を透明、1-3をROMスプライトパレット先頭3色として表示・画像取込・PNG保存するようにした。
- Danaなどのスプライト色がステージ表示と同じ色順で編集できるようにした。

## v0.8.18 (2026-05-31) 16x16ピクセル編集を追加
- 編集ツールへ「16x16ピクセル編集」を追加し、ROMフレーム由来の16x16スプライトを1ピクセル単位で編集できるようにした。
- 16x16画像を取り込み、現在のスプライトパレットに近い4色インデックスへ変換して作業バッファへ反映できるようにした。
- 書き込み後はCHRレンダラ、ピッカーアイコン、ステージ表示、サムネイルを再構築し、保存対象ROMへ反映されるようにした。

## v0.8.17 (2026-05-31) 土色特殊壁を追加
- ピッカーへ「すり抜ける土色壁」と「壊せない土色壁」を追加。
- mapper66セル`$A3/$A4`を土色表示用に使い、描画後のruntime scannerで`$A3->$10`、`$A4->$F8`へ変換するようにした。
- XML、範囲コピー/削除/反転、スポイト、キーボード配置、ROM保存/読込へ対応。

## v0.8.16 (2026-05-31) 共通設定項目を棚卸
- ゲーム挙動改造/敵設定の共通設定JSONについて、UI値・インポート値・実適用処理の対応を棚卸。
- パレット編集側へ移ったステージ壁色12バイトが共通設定では空扱いになっていたため、実ROMテーブル値を保存/復元するようにした。
- 画面に出しておらず、現在のSaramandor #2常時パッチでは実適用もしない旧サラマンダー反応距離キーを共通設定の保存/読込対象から外した。
- v0.8.14/v0.8.15で追加したメタ項目座標とボーナスステージテーブルが共通設定に含まれることを再確認。

## v0.8.15 (2026-05-31) 共通設定にボーナスステージテーブルを保存
- 共通設定JSONにボーナスステージの配置32バイトとアイテム種類16バイトを保存するようにした。
- 共通設定インポート時、現在ROMのリージョンに合わせたボーナステーブル位置へ復元し、ボーナス面表示も再同期するようにした。

## v0.8.14 (2026-05-31) 共通設定にメタ項目座標を保存
- 共通設定JSONに、ROM直書きの`level_meta_item`座標としてソロモンの紋章とPage of Space/Timeを保存するようにした。
- 共通設定インポート時、既存の面定義は変えずに同じ`no`/`level_no`の座標バイトだけを復元するようにした。
- マイティボンジャックや静的メタ項目は対象外とし、座標復元対象を必要なROM-backed項目に限定した。

## v0.8.13 (2026-05-31) ミラー出現パターン一覧と簡易設定を拡張
- ミラー詳細設定の出現タイミング簡易設定に`4空け`、`5空け`、`6空け`を追加。
- ミラー詳細設定から、全ステージのミラー敵セット、TTL、Phase1/Phase2の64tick出現パターンを読取専用で確認できる`ミラー出現一覧`を開けるようにした。
- 一覧では`X`を出現、`.`を非出現、`-`をゲーム側で無視される先頭tickとして表示するようにした。

## v0.8.12 (2026-05-31) ヌエル大量配置時のドロップ床抜けを抑制
- `$14-$17`のドロップAIで、床接触後のY位相判定が遅延した時だけ着地を拒否して再落下する原作処理を緩和。
- 敵や床判定そのものは変えず、底面衝突を検出した時に低位相8-Fでも停止できるようにした。
- 大量敵/複数ドロップでAI更新が間引かれ、最初の床接触サンプルが遅れた場合の床抜けを回避するための最小1バイトパッチを保存時に自動適用するようにした。

## v0.8.11 (2026-05-31) ステージPNGの単体ドラッグ読込に対応
- キャンバスへ単体PNGをドラッグ&ドロップした時、SOLOMON_CUSTOMIZERの`msc_level`メタデータ入りPNGだけを現在ステージへ読み込むようにした。
- 複数ファイルや通常PNGは受け付けず、誤読込を防ぐようにした。
- 既存の「現在ステージへPNG読込」処理と同じ経路を使い、Undo/dirty/サムネイル更新も行うようにした。

## v0.8.9 (2026-05-31) ミラー出現タイミングの簡易設定を追加
- ミラー詳細設定のスケジュール操作ボタンを`全ON`/`全OFF`へ短縮。
- 出現タイミングを`1空け`、`2空け`、`3空け`で一括設定できるボタンを追加。
- 先頭2tickはゲーム側で無視されるため、簡易設定ではtick 2からパターンを開始するようにした。

## v0.8.8 (2026-05-30) Saramandor #2のSP3配置を禁止
- Saramandor #2 (`$5E/$5F`) のSP3選択を無効化し、Panel Monster 3-way用ID `$66/$67`へ変換されないようにした。
- `$66/$67`はピッカー上のPanel Monster 3-way (up/down) からのみ配置する扱いに整理。

## v0.8.7 (2026-05-30) Panel Variantキャンバス表示修正
- Panel Variant A/B/Cをキャンバスへ配置した時、借用元の通常敵ではなくPanel Monster方向グラフィックで描画するように修正。
- キャンバス上のPanel Variant A/B/Cにも青いtintを重ね、通常Panel Monsterと見分けられるようにした。

## v0.8.6 (2026-05-30) 読込元ROM CRCを表示
- ROM情報欄のCRC32表示を、ボーナスステージ補正やmapper66/wide-title自動変換後のメモリ上ROMではなく、最初に読み込んだ元ROMバイトのCRC32に変更。
- JP ROMの既知CRCをヘッダ違いの3種類に更新し、正常なJP ROMを`正規`として表示できるようにした。

## v0.8.5 (2026-05-30) パッケージ版で同梱アイコンを解決
- PyInstaller向けに、書き込み可能なアプリルート設定パスと同梱データパスを分離。
- 相対アセットパスは`_internal`の同梱データディレクトリへフォールバックするようにし、
  パッケージ済みonedirビルド内で`docs/images/dana.png`を解決できるようにした。

## v0.8.4 (2026-05-30) Danaアイコンを既定アセット化
- `docs/images/dana.png`を既定のウィンドウアイコンパスにした。
- 設定済みの相対パスをプロジェクトルートから解決するようにし、絶対ローカルパスなしで同梱アイコンが動くようにした。

## v0.7.169 (2026-05-30) hackインポート後にパレット同期
- ゲーム/敵設定ダイアログ経由で変更されたメインパレットバイトを検出。
- 共通設定インポートがパレットを変更した場合、通常のパレット同期経路でエディタ描画、ピッカーアイコン、サムネイルを更新するようにした。

## v0.7.168 (2026-05-30) 共通インポート警告をファイル選択前へ移動
- 取り消せない共通設定インポートの警告をファイルピッカー表示前に出すようにし、ファイルを選ぶことがインポート続行を意味することを明確化。
- インポート補助コメントを更新し、ROM由来データはインポート中に即時書き込まれることを明記。

## v0.7.167 (2026-05-30) Panel Variantアイコンの色付けを簡素化
- Panel Variant A/B/Cのピッカーアイコンから青いハッチオーバーレイを削除。
- 単純な青 tint により、Panel Variant A/B/Cアイコンを黄色の強化敵と見分けられる状態は維持。

## v0.7.166 (2026-05-30) 共通設定インポート前に警告
- 一部のROM由来データは即時適用されUndoできないため、共通設定インポート前に明示的な確認を追加。
- インポート完了メッセージを更新し、即時適用されたROM由来データと、ApplyまたはOKがまだ必要な設定を区別。

## v0.7.164 (2026-05-30) 保存前にconfigディレクトリを作成
- fresh cloneで無視対象の`config/`ディレクトリが存在しない場合でも、アプリ設定保存時に作成するようにした。
- ROM履歴保存時も、書き込み前に親ディレクトリを作成するようにした。

## v0.7.163 (2026-05-30) ミラー寿命UIをミラー詳細へ移動
- 左側ステージ設定からミラー敵寿命コントロールを削除。
- ミラー詳細ダイアログの寿命コントロール横に、リアルタイム秒数表示を追加。

## v0.7.162 (2026-05-30) 配置拒否時にクリーン状態を保持
- クリック配置が検証ルールで拒否された場合、直前のUndo、Redo、dirty状態を復元。
- 敵の上にブロックを置くなどの失敗配置で、データが変わっていないのにステージがdirty扱いになる問題を防止。

## v0.7.161 (2026-05-30) 空削除/空ドラッグでdirtyにしない
- 右クリック削除、右ドラッグ消去、Ctrlドラッグ開始では、実際の対象が見つかるまでUndoスナップショット作成を遅延。
- 空の右クリック、空の右ドラッグ消去、空のCtrlドラッグ試行でステージがdirty扱いになる問題を防止。

## v0.7.160 (2026-05-30) お気に入りドラッグのデバッグ出力を削除
- お気に入りドラッグ&ドロップ処理に残っていたデバッグprintを削除。

## v0.7.159 (2026-05-30) ミラースケジュール操作を調整
- ミラースケジュールのクイックボタンを入れ替え、「全ON」を左、「全クリア」を右に配置。
- ダークUIで未チェック時のスケジュールチェックボックスが見えるよう、チェックボックスインジケータに明示的な境界線を追加。

## v0.7.158 (2026-05-30) Panel Variantピッカーアイコン修正
- Panel Variant A/B/Cのピッカーアイコンを、借用元敵グラフィックではなく正しいPanel Monster方向グラフィックで表示。
- Panel Variant A/B/Cアイコンに、他の強化敵で使う黄色オーバーレイとは別の青いハッチオーバーレイを付与。

## v0.7.157 (2026-05-30) 範囲操作で16列目を保護
- 範囲選択、範囲削除、範囲移動、貼り付けが`16列目を編集`ロックを尊重するようにし、ロック中は右端列を変更しないようにした。

## v0.7.156 (2026-05-30) ステージ選択を目立たせる
- 右側ステージ選択をテストプレイボタンと同系色にしつつ、元のスピンボックス挙動を維持。
- 右ペインから常時表示のサムネイル再生成ボタンを削除。必要時のサムネイル自動再生成は継続。

## v0.7.155 (2026-05-30) ステージ選択を強調
- 右側ステージ番号コントロールを拡大・太字化し、より強い緑枠を付けて、ダークUI上で現在のステージ選択が目立つようにした。

## v0.7.154 (2026-05-30) 右側テストプレイショートカット追加
- 右側Panel Variantコントロールの下へ2つ目の緑色テストプレイボタンを追加し、ピッカー/ステージ編集の作業導線からテストプレイへ届きやすくした。
- 2つのテストプレイボタンは、どちらも同じ現在ステージテストプレイ処理を呼ぶ。

## v0.7.153 (2026-05-30) アプリUIをダークグリーンテーマへ変更
- グローバルQtスタイルシートを作り直し、黒ベースに緑の文字、境界線、タブ、コントロール、選択色を使うようにした。
- ダークテーマ向けに設定の明るさコントロールを更新し、旧ライトグレー設定値を新しいダーク既定値へマップ。

## v0.7.152 (2026-05-30) Panel Variant間隔をフレーム数表示
- 右側Panel Variantの間隔コントロールを16進`$xx`表示から10進フレーム数へ変更し、原作既定値が`$C0`ではなく`192`として見えるようにした。

## v0.7.150 (2026-05-30) Panel Variant間隔の既定値を原作クールダウンへ
- Panel Variant A/B/Cの発射間隔が欠落/既定の場合は`192`にし、明示的なA/B/C間隔データがないステージでは原作Panel Monsterのクールダウン閾値を使うようにした。

## v0.7.149 (2026-05-30) Panel Variant ID分類を厳格化
- A/B/Cグループオフセットhelperを変更し、`LSR`のcarryを即時チェックするようにした。偶数IDは`X=$FF`を返すため、A/B/C runtime速度/間隔バイトを読めない。
- `$66/$67`を最終Panel runtime有効化条件へ追加し、Saramandor-IDの3方向Panel Variantが親速度ガードの対象範囲と一致するようにした。
- A/B/C Panel Variantの敵ドロップは、元のドロップ処理が`type >> 2`でインデックスするため、意図的に借用元敵IDの行に従う。
- 保存適用順序をPanel Variant runtime契約として固定。`panel_monster_stage_variant`は選択されたhook/loaderを意図的に置き換えるため、base PanelとStageExt書き込みの後に実行する必要がある。
- 現在のfinal split runtime向けにPanel Monsterクールダウン書き込みを修正。`$A575`が`JSR $BE62`へ置き換わった後、UIは`0x258A`のNOPを壊すのではなく、file `0x3E82`の実際のthreshold operandを読み書きするようになった。
- final split runtimeが間隔helperを再注入する時に現在のグローバルPanel Monsterクールダウンを保持し、保存によってthresholdが`$C0`へ戻らないようにした。
- Panel Bullet左右速度修正は共有Bullet速度テーブルを更新するため、Bullet弾を撃つ全ての敵へ影響する、というUI注記を追加。
- Panel Monsterの「キビキビ動作」UI/設定/ROM writerを削除。古い発射前待ちoffsetは、final Panel Variant runtimeでは`0x409D`がA/B/C Bullet速度マーカー比較の一部になっているため安全ではない。

## v0.7.148 (2026-05-30) 借用Panel親の速度再初期化をガード
- `$866D`親速度ガードの奇数IDチェックは維持。これは既に`LSR`直後に偶数IDでexitする。
- final split Panel runtime有効化条件を広げ、ROM内にA/B/C IDが存在しない場合でも、古い2-way/3-way借用Panel ID `$52/$53/$56/$57/$5A/$5B`が移設済み共有wrapperを有効化するようにした。
- これにより、2-wayのみのステージでは借用元敵の移動を継承せず、parent-field clear pathを使える。
- `$866D`親速度ガードを`$E7A4`へ移動し、繰り返し実行される`$8AC0`速度初期化が、A/B/Cと借用Panel ID `$52/$53/$56/$57/$5A/$5B/$66/$67`について`main+5/main+6/main+8/main+9`をクリアするように拡張。
- 再保存時には、古い`$E876`と新しい`$E7A4`のPanel speed guard hookの両方を受け入れるようにした。`$866D`を共有するSaramandor署名チェックも含む。

## v0.7.147 (2026-05-30) A/B/C RAM分類をPanel見た目分類から分離
- A/B/C専用group offset helperを追加し、Panel Variant速度/間隔設定を`$31/$33/$35/$37`、`$41/$43/$45/$47`、`$49/$4B/$4D/$4F`だけが読むようにした。
- グラフィック/property routing用には広いPanel visual classifierを維持したが、`$0740-$0745` runtime設定offsetの決定には使わないようにした。
- これにより、古い2-way/3-way Panel Monster variantがA/B/C速度または発射間隔バイトを読む問題を防止。

## v0.7.146 (2026-05-30) Panel Variant方向と2-way drift分離を修正
- A/B/C Panel Variant AI tailを修正し、共有Panel方向setterへ入る前にparent velocity/subpixel clearを行っても、decode済み方向が保持されるようにした。
- Panel Variant共有Demonhead-ID wrapperを別の00-fill gapへ移動し、A/B/C runtime有効時は`$52/$53/$56/$57/$5A/$5B`をそこへrouting。
- 2-way借用Panel MonsterとA/B/C variantが借用元敵の移動を継承しないよう、共有parent-field clear helperを追加。
- 古いcarry状態に依存せず、共有Panel classifierを中心にA/B/C RAM offset helperを再構築。

## v0.7.145 (2026-05-30) オブジェクト削除時に16列目ロックを尊重
- `オブジェクト削除`を変更し、`16列目を編集`がOFFの間は、`すべて削除`、ブロックのみ、アイテムのみ、モンスターのみの削除が16列目を触らないようにした。

## v0.7.144 (2026-05-30) 再保存時にPanel Variant速度ガードを許可
- `$866D`のSaramandor variant署名チェックを更新し、現在のPanel Variant親速度ガードhookを受け入れるようにした。
- Saramandor patch byteを変更せず、既にPanel Variant A/B/C runtimeを含むROMを再保存できるように修正。

## v0.7.143 (2026-05-30) Panel Variant helperをGargoyle領域から分離
- Panel Variantのステージdispatch helper、AI dispatch entry、AI dispatch Panel tail、親速度ガード、fire marker tableを、それぞれ検証済みの別gapへ移動。
- 親速度ガードを厳格化し、採用済みのA/B/C ID範囲だけをクリアし、放棄済みの`$39/$3B/$3D/$3F`範囲は対象外にした。
- Panel Variant A/B/C split runtimeをRoomFlag cave verifierの許可リストへ追加し、既にパッチ済みのA/B/Cバイトを再保存時に拒否しないようにした。
- Gargoyle 2-shot runtimeとの偶発的な重複を除去。残るPanel Variantの重複は、古いPanel Monster共有runtimeを意図的に置き換えるものだけ。

## v0.7.142 (2026-05-30) Panel Variant A/B/CでPanel Bullet対称性を強制
- Panel Variant A/B/C適用時、既存のPanel Bullet左右速度バグ修正も`$3F/$41`プリセットでROMへ適用するようにした。
- A/B/C Panel Variant runtimeが有効な同じROM内で、通常Panel Monsterに右/左タイミング不一致が出ないようにした。

## v0.7.141 (2026-05-30) Panel Variantの2x/3x Bullet追加ステップを有効化
- 最終Panel Variant Bullet extra-step helperを`$E823`へ追加。
- 統合Bullet hookはvelocity table writerを直接呼ぶのではなくwrapper helperを呼ぶようにした。プリセット`2x`は追加の移動変換パスを1回、`3x`は2回実行し、各追加パス後にBullet衝突を確認し、原作state2衝突パスが着弾を処理する前に停止する。
- `1/4`、`1/2`、高速プリセットで使うbase velocity用として、既存の`$C088`速度テーブルwriterは維持。

## v0.7.140 (2026-05-30) 古いPanel Variant Bullet速度マーカーをクリア
- 最終Panel Variant fire共通パスを変更し、速度マーカーを持たないべきBulletではchild sub-slot `+7`を明示的にクリアするようにした。
- 通常Panel MonsterのBulletが、以前Panel Variant A/B/Cで使われたchild slotを再利用した時に、古い`$88-$8B`速度マーカーを継承する問題を防止。

## v0.7.139 (2026-05-30) 新旧VariantでPanel見た目分類を共有
- `$BFBA`に分割共有Panel type classifierを追加し、tail codeを`$DAB9`へ配置。既存の強化Panel Monster ID（`$52/$53/$56/$57/$5A/$5B/$66/$67`）と新しいPanel Variant A/B/C IDの両方をPanel visualsとしてマークする。
- initial-magic/livesまたはGargoyle領域を使わないよう、dynamic Bullet speed marker helperを`$BFBA`から元の00-fill gapである`$E89C`へ移動。
- 最終`$DBDF` property hookと`$C0C2` animation hookを、新A/B/C IDだけを認識するのではなく、そのclassifierを呼ぶように変更。Panel Variant A/B/C有効時に、既存の強化Panel MonsterがDemonhead/Saramandorグラフィックへ戻る問題を防ぐ。

## v0.7.138 (2026-05-30) Panel Variant A/B/CでSpark hookを保持
- 最終Panel Variant A/B/C runtimeを変更し、`$A556`ではPanel fire jumpを維持しつつ、`$A559`のSpark property hook bodyを保持するようにした。
- `$A2CC`と`$8B05`はSpark dispatch hook経由のままにし、その後Panel property/animation hookへfall throughする形を維持。最終Panel VariantパスがSpark Ball挙動を消してしまう問題を防ぐ。
- `panel_monster_stage_variant.RESERVED_SPANS`を古いprototype範囲から、最終runtimeで使う現在のsplit-placement範囲へ更新。

## v0.7.137 (2026-05-30) Panel Variant速度ガード分類を修正
- `$BD40` Panel Variant速度ガードを変更し、原作`$8AC0` initializer後に`($08)+1`からactive parent IDを読むようにした。以前の`$05`チェックはこの時点では古く、`$8689`がPanel Variant親を動かす前に`main+5/main+8`をクリアできていなかった。

## v0.7.136 (2026-05-30) 採用済みPanel Variant no-drift方式に合わせる
- 以前の`$8670` common-physics skip案を、局所的な`$866D -> $BD40` speed-initializer guardに置き換え。
- ガードはまず原作`$8AC0` initializerを実行し、その後、奇数`$30-$4F` Panel Variant親の`main+5/main+8`だけをクリアする。元の`$DBB5-$DBDE`敵速度テーブルをグローバルにゼロ化せず、採用済みNoDrift挙動に従う。

## v0.7.135 (2026-05-30) Panel Variant親でcommon physicsをスキップ
- `$8670 -> $BD40`にPanel Variant親専用ガードを追加。奇数`$30-$4F` Panel Variant親IDは原作`$8689` common physics stepをスキップし、通常敵は元のA値を復元して`$8689`へジャンプする。
- 既存の`$BD17` AI-entry velocity clearは維持し、アプリruntimeが借用ID由来の移動継承と共有ループdrift pathの両方を止めるようにした。

## v0.7.134 (2026-05-30) Panel Variant親を静止させる
- 共有方向setterへジャンプする前に、`$BD17` dispatch helper内でPanel Variant専用の親velocity/subpixel byteクリアを復元。A/B/C親が借用元Ghost/Neul移動を継承するのを防ぎつつ、`$C146` Demonhead path上の直接Demonhead呼び出しは残す。

## v0.7.133 (2026-05-30) Panel Variant AI経路でDemonhead wrapperを保持
- `$C146`の統合Panel Variant A/B/C AI wrapperを変更し、直接Demonhead-ID variant呼び出しはPanel Variant親扱いではなくDemonhead routing logicを実行するようにした。
- Panel Variant奇数IDは引き続き`$BD17` dispatch helperから入り、Demonhead entry pointではなく共有方向setterを使う。
- `$A575`発射間隔hookをガードし、奇数Panel Variant IDだけがステージ別`$0740`間隔cacheを読むようにした。stock/even IDは元の`CMP #$C0`タイミングへ戻る。

## v0.7.132 (2026-05-30) 原作敵速度テーブルの上書きを停止
- 統合Panel Variant A/B/Cによる`$DBB5-$DBDE`書き込みを削除。この範囲はGolemやDemonheadなどの原作敵が使う原作敵速度テーブルであり、クリアするとPanel Variant runtimeへ入らない敵を壊す可能性がある。

## v0.7.131 (2026-05-30) 原作敵をPanel Variant dispatchから除外
- 統合Panel Variant A/B/C dispatchを修正し、奇数variant IDだけが新Panel runtimeへ入るようにした。
- 同じ`$30-$37`および`$40-$4F`テーブル範囲の偶数IDについて、原作AI、property、animation処理を復元し、既存Ghost/Golem系の敵がPanel Monster扱いされないようにした。
- 偶数IDを原作AI routineへ戻す前に元のA/Yレジスタ状態を保持し、原作敵の移動挙動を維持。
- Panel fire dispatchも同様に分割。`$34/$36`など既存の偶数Panel IDは通常発射パスを維持し、奇数A/B/C IDは新しいstage-variant発射パスを使う。
- Panel Variant AI dispatch helperを、既存Saramandor-ID AI wrapperに属する`$BC5B`から、古いprototype gapである`$BD17`へ移動。

## v0.7.130 (2026-05-30) Panel Variant A/B/Cをエディタへ接続
- 12個のPanel Variant A/B/C IDをモンスターピッカーへ追加: `$31/$33/$35/$37`, `$41/$43/$45/$47`, `$49/$4B/$4D/$4F`。
- 右側ピッカー領域に、A/B/CのBullet速度と発射間隔を設定するステージ別Panel Variantコントロールを追加。
- A/B/C速度と間隔値をstage XMLおよびPanelVariantStageTableへ永続化し、A/B/C ID使用時に採用済みfinal split runtimeを適用するようROM保存を接続。
- 当時のNoDrift candidateを統合保存パスへ接続したが、`$DBB5-$DBDE`が共有の原作敵速度データだと確認されたため、v0.7.132で取り消した。

## v0.7.118 (2026-05-29) Spark Ball variant判定を圧縮
- 採用済みID集合を変えずに、Spark Ball借用IDチェックを短縮。Dragon-ID wrapperは`AND #$FE`でphase-normalizeし、pause hookは正規化後に`$6A/$6E`をチェックし、property/animation hookはcompact offset ruleで`$6A/$6E/$72/$76`を分類する。
- Spark Ball variant PRG0 codeを合計26B削減。
- Panel Monsterの`$A556`署名ガードを更新し、圧縮後の現在Spark Ball property selectorを受け入れるようにした。

## v0.7.110 (2026-05-27) 専用マーカーでPanel Bullet offsetをゲート
- 安全でないSaramandor child-marker cleanup案を削除。
- Panel Monster斜めBullet markerをbit7付き値へ変更し、Bullet hookはtagなし`sub+7`値を無視するようにした。
- Panel Monster斜めoffsetを動作させたまま、Saramandor #2 BulletがPanel Bulletと誤認されるのを防ぐ。

## v0.7.107 (2026-05-27) Saramandor #2の反応範囲を6タイルに
- Saramandor #2 ID `$5E/$5F/$62/$63`向けに`$B1E9`距離チェックhookを追加。
- 強化Saramandor IDはX反応threshold `$60`（6タイル）を使うようにした。stock SaramandorとDragonは元の共有`$14` thresholdを維持。
- 古いUI側の共有Saramandor/Dragon距離書き換えは適用停止し、この範囲変更をvariant専用にした。

## v0.7.106 (2026-05-27) Saramandor低速Bulletを削除
- Saramandor #2の1/4速度Bullet overrideを削除。`$5E/$5F`と`$62/$63`はいずれも通常速度Bulletを生成する。
- 現在のpatch pathから、有効な`$B121`、`$AFD1`、`$866D`のslow-Bullet marker/speed hookを削除。

## v0.7.105 (2026-05-27) Panel Monster fire dispatchを圧縮
- parent typeを`AND #$FE`でpair-normalizeし、採用済みbase ID 4種だけと比較することで、Panel Monster fire dispatchを45Bから31Bへ削減。
- `$BCF1-$BCFE`を新しい14B bank0 cave gapとして回収。

## v0.7.104 (2026-05-27) Panel Bullet速度対称化修正を追加
- Panel Monster敵設定に「弾の左右速度バグ修正」を追加。
- このオプションは右、左、上、下のPanel shot向け原作Bullet velocity table entryだけを書き換えるため、ROM cave領域を消費しない。
- `$40`境界を挟む方向別`$30/$50`および`$3F/$41` selector pairを追加。生の`$41`は右/下shotには書き込まない。

## v0.7.103 (2026-05-27) Panel Monster fire caveを圧縮
- 個別のPanel Monster normal / 2-way / 3-way fire bodyを、`$BD88`の1つの共有marker-table fire loopへ置き換え。
- それらの正確なlegacy byteが存在する場合、古いnormal fire copy `$BFB9-$BFD7`と古い2-way cave `$C088-$C0C1`を回収。

## v0.7.100 (2026-05-26) 敵設定を視覚的にグループ化
- Enemy設定ダイアログをモンスター系統ごとに並べ替え、関連コントロールを近くに配置。
- ROM rendererが利用可能な場合、Enemy設定グループへモンスタースプライトを追加。

## v0.7.99 (2026-05-26) variant patchでGargoyleキビキビ待ちを許可
- 強化Gargoyle patch検証を修正し、アプリ自身のsnappy Gargoyle `$AF2B`待ち値`$01`を受け入れるようにした。
- 古いrapid-fire実験hookを削除する場合以外は、強化Gargoyle patchが`$AF2B`を`$68`へ戻さないようにした。

## v0.7.98 (2026-05-26) Gargoyle速度調整UIを削除
- runtime値が信頼できるユーザー向け速度設定ではないため、強化Gargoyle 2発目速度コントロールを削除。
- 強化Gargoyle 2発目位置コントロールは維持し、内部2発目velocity補正を標準値で適用。

## v0.7.97 (2026-05-26) Gargoyle 2-shot gate branch修正
- 強化Gargoyle `$7A/$7B/$7E/$7F` gateを修正し、一致IDが原作materialization tailへ入らず2-shot routineへジャンプするようにした。

## v0.7.96 (2026-05-26) 強化Gargoyle調整を追加
- 強化Gargoyle 2発目offsetと2発目速度の敵UIコントロールを追加。
- ROM保存中にvariant patchが再適用される時、custom強化Gargoyle調整を保持。

## v0.7.95 (2026-05-26) Gargoyle 2-shot speed 2を追加
- 強化Gargoyle 2-shot speed-2 ID `$7E/$7F`を追加。ピッカー速度切替、敵ラベル、保存検出、runtime gateを含む。

## v0.7.94 (2026-05-26) panel hackとsparkのhybrid状態を検出
- Panel Monster挙動コントロール検出を更新し、variant patchが扱うstock-panel/current-Spark hybrid状態と同じ状態を受け入れるようにした。これにより、そのROM状態でEnemyダイアログがPanel Monsterコントロールを無効化しなくなった。

## v0.7.93 (2026-05-26) orig-panel spark hybrid状態を許可
- Panel Monster variant検証を修正し、原作Panel fire code headが`$A556`に残り、現在のSpark property hook bodyが`$A559`から始まるROMを受け入れるようにした。保存/テストパイプラインがSpark再適用前にPanel dispatchを復元できる。

## v0.7.92 (2026-05-26) panelとspark hookの重複を許可
- Panel Monster variant検証を修正し、`$A556`のPanel fire dispatch jumpと`$A559`開始のSpark Ball property hookが共存する現在layoutを受け入れるようにした。

## v0.7.91 (2026-05-26) 非表示の挙動ダイアログwidgetを修正
- hidden behavior-dialog groupを生存させ、Enemy-only viewを開いても、共有apply/export codeが読む可能性のあるwidgetを削除しないようにした。

## v0.7.90 (2026-05-26) 強化Spark Ball調整を追加
- 強化Spark Ball pause digitと透明Spark Ball blink mask調整の敵UIコントロールを追加。
- ROM保存中にvariant patchが再適用される時、custom強化Spark Ball調整を保持。

## v0.7.89 (2026-05-26) Salamander挙動グループを非表示化
- 表示中の敵挙動UIからSalamander behavior groupを削除。

## v0.7.88 (2026-05-26) Salamander Y toleranceを非表示化
- 表示中の敵挙動UIからSalamander Y toleranceコントロールを削除。

## v0.7.87 (2026-05-26) 敵挙動入口を分離
- ゲーム挙動編集の横にトップレベルのEnemyボタンを追加し、敵AI設定を一般ゲーム挙動ダイアログから分離。

## v0.7.86 (2026-05-26) 挙動ダイアログlayoutをフラット化
- ゲーム挙動ダイアログのタブを削除し、敵設定と敵以外の設定が一緒に表示されるようにした。特殊処理ビューアもダイアログ内へ移動。

## v0.7.85 (2026-05-26) 関連編集ボタンを移動
- 敵ドロップ、デモ入力、クリアメッセージ編集をゲーム挙動ダイアログへ移動し、それらのボタンを左編集ツールパネルから削除。

## v0.7.84 (2026-05-26) フォント設定を即時適用
- 設定ダイアログのフォント変更を修正し、編集したspin-box値がcommitされ、OK/Apply直後に既存ウィンドウへフォントが再適用されるようにした。

## v0.7.83 (2026-05-26) ステージ選択ペイン切替を追加
- 右側ステージ選択ペインの表示/非表示を切り替える表示オプションを追加し、小さい画面でスペースを確保できるようにした。

## v0.7.82 (2026-05-26) 表示上のステージ表記を統一
- プレイ可能なステージを指すUI表記を、レベル/Levelからステージ/Stageへ統一。内部名は変更なし。

## v0.7.81 (2026-05-26) グローバル時間設定を改名
- 挙動ダイアログのグローバルtime-rateセクション名を`ステージ制限時間`へ変更。

## v0.7.80 (2026-05-26) 制限時間秒数を丸める
- level time selector表示を`制限時間`へ改名し、推定秒数を整数へ丸めた。

## v0.7.79 (2026-05-26) ミラー寿命ヒントを移動
- ミラー敵寿命の秒数見積もりを2行目へ移動し、フィールドラベルをコンパクトに保つようにした。

## v0.7.78 (2026-05-26) time-rate秒数を表示
- level time decreaseヒントを、現在ROMのtime-rate tableから計算した推定秒数表示へ置き換え。

## v0.7.77 (2026-05-26) ミラー寿命秒数を表示
- ミラー敵寿命ラベルを更新し、値の変更に合わせて概算秒数をリアルタイム表示するようにした。

## v0.7.76 (2026-05-26) テストプレイボタンを強調
- ファイルパネル内でplayback actionとして目立つよう、テストプレイボタンを大きく緑色にした。

## v0.7.75 (2026-05-26) ウィンドウタイトルを改名
- メインウィンドウタイトルを`MAGATU_SOLOMON_CUSTOMIZER`から`SOLOMON_CUSTOMIZER`へ変更。
- Windows AppUserModelIDを`Chaos.MAGATU.SOLOMON_CUSTOMIZER`から`Chaos.SOLOMON_CUSTOMIZER`へ変更。
- mapper66 ROM metadata magicを`MAGATU_SC_META`から`SOLOMON_CUSTOMIZER_META`へ変更。
- セッションログヘッダを`SOLOMON_CUSTOMIZER セッションログ`へ変更。
- PNG埋め込みXML rootを`magatu_solomon_customizer`から`solomon_customizer`へ変更し、それに合わせてformat-version定数を改名。

## v0.7.72 (2026-05-26) 特殊ブロックをm66 cell IDとして保存
- mapper66特殊ブロックをステージmap cellへ直接保存するように変更: `0xF9`壊せる白、`0xFA`通過可能白、`0x40`透明solid、`0x50`透明壊せる。
- 古い32-byteの`$0740-$075F` runtime block override listを、描画後にそれらのdirect cell IDを変換する`$0304` grid scannerへ置き換え。
- 古いPRG1 runtime block override copyを無効化し、保存時にlegacy per-room cell tableをクリアするようにした。

## v0.7.70 (2026-05-26) module別ROM書き込みを棚卸し
- Transparent Spark Ball Golem-ID AI wrapperを`$8BE2`からoriginal `00` fillの`$E80C`へ移動し、`$8BE2-$8BFD`をinitial magic/lives用に残した。

## v0.7.67 (2026-05-26) ローカルfile dialog依存を削除
- machine-localな`file_dialog` importを、リポジトリ内の`QFileDialog`互換wrapperへ置き換え。
- machine-local helper directory向けのhard-coded startup `sys.path` entryを削除。
- fresh checkoutが外部`PyQt5`依存を宣言するよう、`requirements.txt`を追加。

## v0.7.66 (2026-05-25) 縦Panel Monster spread軸を修正
- Panel Monster 2-way/3-way spreadを修正し、縦variantではbullet Xをoffsetし、横variantでは引き続きbullet Yをoffsetするようにした。
- Mesen logで問題を確認。`PM3_DOWN` shotがまだ`$BF69` spread hookに到達し、`$BF98`で`ptr2E+7/Y`を書いていた。
- Panel Monster bullet hookを70Bから74Bへ拡張し、normal fire copyと重複せず、小さな`$BFAF-$BFB8` gapから4Bを消費。

## v0.7.61 (2026-05-25) 元ROM CRCを記録
- 後から再構築に使ったsource ROMを識別できるよう、ROM保存global sidecarへ`original_rom_crc32`と`original_rom_size`を追加。
- これらのfieldはmetadataのみで、import/rebuild logicは依存しない。

## v0.7.60 (2026-05-25) global byte dataを圧縮
- global sidecarのbyte-table fieldを長い10進配列からcompactな大文字hex stringへ変更: `main_palette_hex`, `demo_input_wait_hex`, `demo_input_joy_hex`, `enemy_drop_c278_hex`, `enemy_drop_c293_hex`, `clear_message_hex`。
- importは新しいhex-string fieldだけを期待するようにし、短期間だけ存在したdecimal-array形式への互換pathは持たない。

## v0.7.59 (2026-05-25) 不足していたglobal byte tableを追加
- ROM save sidecarがlevel以外の編集をより多く保持できるよう、common settings JSONへROM-backed global tableを追加: `main_palette_bytes`, `demo_input_wait_bytes`, `demo_input_joy_bytes`, `enemy_drop_c278_bytes`, `enemy_drop_c293_bytes`, `clear_message_bytes`。
- common settings importはそれらのbyte tableを直接復元し、不正な長さでは古い形式互換を試さず失敗するようにした。
- Game Behavior settings exportを再確認。combo値はUI labelではなくnumeric dataまたはstable idとして保存される。

## v0.7.58 (2026-05-25) clear-screen presetをidで保存
- ユーザーが互換baseline versionを明示するまでは後方互換を意図的に無視する、というプロジェクトルールを追加。
- global settings JSONの`clear_screen_preset`をUI label textから`fairy_original`などのstable internal idへ変更。
- Clear-screen presetのUI labelを変更しても、保存済みJSON値が変わらないようになった。

## v0.7.57 (2026-05-25) ROMと一緒にproject dataを保存
- ROM保存時、保存済みROMの隣に再現可能なproject sidecarも書き出すようにした: `<rom>_global_settings.json`と`<rom>_stage_data/level_01.png`から`level_53.png`。
- stage PNG fileは既存の埋め込みXML形式を再利用し、JSON fileは保存ROM名、stage-data folder名、現在のtitle extra textを含めた既存common-settings export形式を再利用。
- ROM file書き込み後にsidecar exportが失敗した場合、ROM file自体が失敗したかのように扱わず、アプリは警告する。

## v0.7.56 (2026-05-25) 保存時に空タイトル文字を刻印
- ROM data保存時、title extra-text行を確認するようにした。空の場合、保存出力に`BUILD YYYYMMDD HHMMSS` timestampを入れ、ゲームのタイトル画面からbuildを識別できるようにした。
- 既存のtitle extra textは変更せず保持。

## v0.7.55 (2026-05-25) 保存整合性を検証
- 鍵持ち敵について、保存時のlevel整合性検証を追加。ステージの初期敵数がN未満なのにkey enemy #Nを選んでいる場合、保存を停止するようにした。
- ROM/IPS保存データは出力書き込み前に一時ROM copy上で構築するようにし、検証失敗や後続保存エラーで開いているROM dataが部分的に変更されたままにならないようにした。

## v0.7.54 (2026-05-25) テストプレイ専用fast-startを追加
- 確認済みraw-JPの3-byte title skipと3つのstart-screen wait skipに基づく、F9 testplay-only title/start-screen shortcutを追加。
- shortcutは一時testplay ROMにだけ適用し、その直後に`rom.data`から復元するため、通常ROM保存やIPS出力にはfast-start patchが入らない。

## v0.7.53 (2026-05-25) 透明Spark Ball variantを追加
- 借用Golem #2 ID上に透明Spark Ball variant `$72/$73/$76/$77`を追加。
- それらのIDを確認済みSpark Ball移動routineへroutingし、採用済みslow blink effect向けにOAM post-draw hide hookを追加。
- 新runtime codeは確認済みEA padding spanにだけ配置し、上書きするとステージグラフィックを壊す`0x500C` data areaを回避。
- 新variant向けに敵ピッカー/config labelと速度mappingを更新。

## v0.7.52 (2026-05-24) Spark BallとDemonhead設定を移動
- Spark Ball速度とDemonhead snappyコントロールを敵設定タブへ移動。
- ROM patch挙動の変更はなし。

## v0.7.50 (2026-05-24) Demonhead調整をJP66専用に維持
- shifted US-style編集サポートを維持するのではなく、Demonhead snappy wait patchをcustomizerで使うJP bank0 layoutへ戻した。
- US assetはタイトル素材として使用できるが、US ROMは通常編集対象ではない、という扱いに統一。

## v0.7.49 (2026-05-24) Demonhead snappy turn waitを追加
- post-spawn/post-turn startup waitを`$0F`から`$01`へ最小化するDemonhead snappy設定を追加。
- patchはDemonhead wait命令列を動的に探すため、JP address `$B2A7`とshifted US-style layoutで動作する。

## v0.7.48 (2026-05-24) Spark Ball速度倍率を追加
- 専用`$A9DF/$A9E7` signed delta table向けに、Spark Ball移動速度倍率設定を追加。
- 設定はspeed 1とspeed 2の両方向を更新し、stock Spark Ballと`$A929/$A92D`へ入るDragon-ID Spark Ball variantに影響する。

## v0.7.47 (2026-05-24) Panel Monster snappy variant保存を修正
- snappy発射前delayが既に`$A55B`を`$10`から`$01`へ変更している場合に、Panel Monster借用ID variant適用が失敗する問題を修正。
- variant hook導入後、snappy delayをPanel Monster normal/2-way/3-way cave routineへ伝播し、保存/testplay準備後も設定が効き続けるようにした。

## v0.7.46 (2026-05-24) NeulとGhost速度設定を追加
- Ghost X速度とNeul Y速度へ1つの倍率を適用する「ゴースト＆ヌエル移動速度」敵AI設定を追加。
- 設定はSP1とSP2のspeed-table pair両方を更新するため、通常版とnoslow variantがピッカー速度システムと整合する。
- 倍率由来の速度byteを計算する時、engineのspeed-update skip markerである`$40`を避け、負速度は検証済み`$41-$7F`範囲に保つ。

## v0.7.45 (2026-05-24) Panel Monster cooldownを常時編集
- 追加のPanel Monster cooldown-enableチェックボックスを削除。frame値そのものを設定とし、原作192Fを既定として表示。
- 非常に短いcooldown値への警告を明確化。リスクは17個の共有sub-slotを使い切ることで、複数の発射敵がいる部屋では発射失敗やbullet生成不整合を引き起こす可能性がある。

## v0.7.44 (2026-05-24) Panel Monsterのキビキビ発射待ちを追加
- `$A55B`の発射前waitを`$10`から`$01`へ変更するPanel Monster「キビキビ動作」設定を追加。
- 既存のPanel Monster intervalコントロールをcooldownへ改名し、UIは`$A57A`をframe単位で直接編集するようにした。
- cooldown復元はsnappy toggleから分離し、各設定を独立して変更できるようにした。

## v0.7.43 (2026-05-24) 共有モンスター速度をGolem外へ移動
- 共有Golem/Dragon/Gargoyle s0 walk-speedコントロールをGolemグループ内ではなく、独立した敵AIグループへ移動。
- 共有速度とGolem固有速度の混同を避けるため、当面はGolem-only walk-speedとcharge-speedコントロールをダイアログから削除。
- この設定について、ダイアログ適用時は共有s0 walk-speed pair `0x5BE0/0x5BE2`だけを変更するようにした。

## v0.7.42 (2026-05-24) 共有モンスター歩行速度を分離
- 旧Golem walk-speedコントロールを、Golem/Dragon/Gargoyle向け共有s0 walk speedと、別のGolem s1 walk speedへ分割。
- Golem charge speedは独立したs1-only controlとして維持。
- global settings export/importに共有monster walk speedを別項目として含めるよう更新。

## v0.7.41 (2026-05-24) Dragonキビキビ動作を追加
- Dragon専用の攻撃前waitを`$A693` / file `0x26A3`で`$01`へ最小化するDragon「キビキビ動作」global設定を追加。
- 共有Saramandor flame startup wait `$B0E8`は変更せず、Saramandor timingを変えずにDragon自身のwaitだけに効くようにした。
- 新Dragon設定をglobal settings export/importおよびresetに含めた。

## v0.7.40 (2026-05-24) Gargoyle cooldown設定を分離
- Gargoyleのpre-materialize wait `$AE6C`を「キビキビ動作」toggleへ追加し、snappy設定がcooldown以外のwait 3箇所を最小化するようにした。
- object-pool floodingを避けるため、`$AE49`向けGargoyle post-shot cooldownコントロールを別に追加し、1-frame snappy toggleから外した。
- cooldown値をglobal settings export/importおよびresetへ含めた。

## v0.7.39 (2026-05-24) キャンバス上端枠を非表示化
- 左と下の装飾壁は維持しつつ、エディタ専用の上端装飾壁行をlevel canvas描画から削除。
- 新しいborder layoutに合わせてobject label位置を更新し、ラベルがずれないようにした。

## v0.7.38 (2026-05-24) Gargoyleキビキビ動作を追加
- 確認済みGargoyle wait threshold 2箇所を`$01`へ書く、Gargoyle「キビキビ動作」global設定を追加。
- 無効時は元の`$68/$18`値を復元し、借用ID Gargoyle two-bullet variantとは分離して保持。
- 新設定をglobal settings export/importとreset処理へ含めた。

## v0.7.37 (2026-05-24) デモステージ設定を簡素化
- game-behaviorダイアログから追加の「change demo stage」チェックボックスを削除。
- demo stage spinboxはROMの現在値を既定にするようにし、未改造ROMでは6面ではなく原作3面を表示。
- ダイアログ適用時は選択したdemo stageを直接書き込む。3面を選べば自然に原作値へ復元される。

## v0.7.36 (2026-05-24) attract demo前にwide titleをクリア
- title-timeout専用hookを`$CB9E`へ追加し、原作attract-demo action `$18`を予約する前に、古いwide-title nametableを`$CC18`でクリアするようにした。
- 9-byteの`$BC0E-$BC16` / file `0x3C1E-0x3C26` stubを使い、room flagやkey-enemy runtimeと衝突しないようにした。
- 既存の現行wide-title ROMは保存時にcleanup hookを受け取り、新規wide-title正規化では即時書き込む。

## v0.7.35 (2026-05-24) wide-title RAM trampolineを移動
- 静的解析により`$03C0-$03DF`がroom block grid `$0304-$03E3`内だと確認されたため、mapper66 wide-title RAM trampolineを`$03C0-$03CD`から`$072C-$0739`へ移動。
- 古い`$03C0` bootstrapをまだ含む、正規化済みinternal wide-title ROM向けに保存時migrationを追加。
- `$072C-$0739`を予約し、古いblock grid重複を禁止領域として扱うようにした。

## v0.7.34 (2026-05-24) CHR0 wide-title returnを取り消し
- テストにより、wide-title trampolineを`PRG0+CHR0`へ戻すと後続のゲーム/スタート画面が壊れることが分かったため、v0.7.33を取り消し。
- 以前の`PRG0+CHR3` return byteを復元し、自動CHR0正規化を削除。

## v0.7.33 (2026-05-24) wide titleをCHR0へ戻す
- mapper66 wide-title RAM trampolineのreturn bankを`PRG0+CHR3`から`PRG0+CHR0`へ変更し、タイトル描画後にdemo pre-start、start、clear screenでCHR bank3が選択されたままにならないようにした。
- 古い`PRG0+CHR3` return byteをまだ含むalready-wide ROM向けに、load/save正規化を追加。

## v0.7.32 (2026-05-24) title idle demo cleanup patchを取り消し
- action `$18` demo cleanup rerouteと`$BC0E` stubを削除。これらがdemo以外の画面遷移とclear screenの描画を不正にしていたため。
- 新規wide-title正規化/保存では、原作`$CBBB` attract-demo entryを変更しない形へ復元。

## v0.7.31 (2026-05-24) title cleanup後もattract demo modeを維持
- v0.7.30の直接`$CBB3` action-table routeを、`$BC0E` / file `0x3C1E`の6-byte stubへ置き換え。このstubは`JSR $CC18`だけを実行し、その後原作`$CBBB` attract-demo entryへ戻る。
- SHRINE/ROOM画面前にwide-title nametable残りをクリアしつつ、title-idle demo playbackが通常auto-startに変わらないようにした。

## v0.7.30 (2026-05-24) wide-title demo開始cleanupを修正
- title-idle demo actionを、手動Startで使うのと同じ`$CBB3` start-screen cleanup pathへroutingし、wide-title nametable残骸がSHRINE/ROOM demo pre-start画面へ漏れないようにした。
- 既にinternal wide-title形式だったROMも含め、JP mapper66 ROMのload/save時に修復を適用。

## v0.7.29 (2026-05-24) title top PNG palette importを分離
- 4-color Top PNG importを変更し、importしたPNG色を、import top band外では未使用のtitle palette slotにだけ割り当てるようにした。
- universal background colorと既存lower title palette使用は触らず、top-only importで山/神殿領域が再着色されないようにした。

## v0.7.28 (2026-05-24) 4-color title top PNG importを修正
- 既存title attribute palette経由で再量子化するのではなく、PNG色をtitle CHR pixel indexへ直接mappingする専用4-color Top PNG import pathを追加。
- importerはtitle palette #0を更新し、保存済みtop title attributeをpalette #0へ強制するため、cleanな4-color 256x64 title artが保たれる。

## v0.7.27 (2026-05-24) 壁色をパレットエディタへ移動
- 4-stage wall colorコントロールをgame-behaviorダイアログからpalette editorへ移動し、同じ64-color picker workflowを使うようにした。
- Palette Applyはcanvas上のwall-color previewを更新し、level thumbnailを再生成する。

## v0.7.26 (2026-05-24) 同梱palette fileに合わせる
- 共有NES RGB paletteを、192-byte palette reference fileの正確なraw RGB値へ置き換え。
- binary検証で以前の手入力palette tableがpalette fileと一致しないことが分かったため、これにより旧tableを置き換えた。

## v0.7.25 (2026-05-24) Mesen NES paletteを使用
- 共有NES RGB paletteを、emulator dataから提供されたMesen palette値へ置き換え。
- canvas、picker、palette editor、sprite viewer、title preview、wall-color swatchで、palette依存previewが同じ色基準を使うようになった。

## v0.7.24 (2026-05-24) ステージ壁色をpreview
- stage wall color数値fieldをNES color swatch selectorへ置き換え。
- game-behavior変更適用後、編集済みwall colorをmain canvasと右側level thumbnailへ同期。

## v0.7.23 (2026-05-24) ステージ壁色table editorを追加
- ROM `$9122` / file offset `0x1132`の通常ステージwall color table entry 12個向けに、game-behaviorコントロールを追加。
- editorは1〜48面を4ステージ単位で変更し、末尾の`$80/$80`特殊ステージmarkerは意図的に触らない。

## v0.7.22 (2026-05-24) キャンバスlabel overlay配置を修正
- object label背景矩形がscene/local座標混在で配置され、黒いlabel boxがtextからずれて見える問題を修正。
- 同じtile上に重なるlabelのspacingを詰めた。

## v0.7.21 (2026-05-24) object labelをUI overlayとして描画
- canvas object labelを焼き込みimage textからQGraphicsView overlay textへ変更し、level canvas拡大縮小時もlabelが鮮明に残るようにした。
- pixelated textを避けるため、内部image-rendered label pathを削除。

## v0.7.20 (2026-05-24) ミラー敵row labelに色付け
- ピッカー内のmirror enemy row labelに色を付けた。M1は赤、M2は青。

## v0.7.19 (2026-05-24) キャンバスobject labelを追加
- アイテム、敵、鍵、扉、ミラー、スタート位置、星座、特殊meta itemなどのcanvas objectに短いlabelを重ねる表示オプションを追加。
- 表示オプションが有効な場合、現在levelおよび全level PNG exportにもobject labelを含める。

## v0.7.18 (2026-05-24) タイトル文字入力を制限
- 長すぎるtextをUIで入力または貼り付けできないよう、タイトル追加文字ダイアログの入力fieldを32文字に制限。

## v0.7.17 (2026-05-24) US66タイトル素材判定を修正
- mapper66拡張US ROMがタイトルimport中にJP66として検出され、import title previewが誤ったnametable layoutを使う問題を修正。
- 拡張ROMのregion検出では、共有mapper66 loader markerより先にoriginal PRG JP/US signatureを優先するようにした。

## v0.7.16 (2026-05-24) legacyタイトル画像ボタンを削除
- title migration dialogから古いfull-screen title image save/import buttonを削除。絞り込んだTop PNG controlは引き続き利用可能。

## v0.7.15 (2026-05-24) level別time-rate selectorを制限
- 3以上の値は有効なtable selectorではないため、level別time decrease selectorを0〜2に制限。

## v0.7.14 (2026-05-24) time-rate duration見積もりを表示
- game-behaviorダイアログ内の3つのglobal LIFE decrease table値の横に、リアルタイムduration見積もりを追加。

## v0.7.13 (2026-05-24) 共通time decrease table改造を追加
- fast、normal、slowの3つのglobal LIFE decrease table値向けにgame-behaviorコントロールを追加。
- コントロールはPRG0 cave領域を使わず、原作`$9942` tableを直接編集する。

## v0.7.12 (2026-05-24) time decreaseヒントlabelを分割
- level settings formが横に伸びないよう、time decrease rate値ガイドを2行目へ移動。

## v0.7.11 (2026-05-24) time decrease rate labelを明確化
- level setting labelを更新し、time decrease値の意味を表示。0はfast、1はnormal、2はslow。

## v0.7.10 (2026-05-24) 統計のlifetime列lookupを修正
- enemy lifetime列headerの改名後に内部column lookupを更新していなかったことで発生していた、全level統計ダイアログcrashを修正。

## v0.7.9 (2026-05-24) game-hackダイアログtabを簡素化
- game behavior hackダイアログを5タブから2タブへ削減。enemy設定とnon-enemy設定に分けた。
- 既存enemy/AIコントロールはenemy tabへ表示し、その他の全コントロールはnon-enemyにまとめた。

## v0.7.8 (2026-05-24) ミラー敵寿命unitを明確化
- level settingsとmirror detail labelを更新し、敵寿命がおおよそ設定値×0.5秒であることを表示。
- 実測例付きtooltipを追加し、stats文言も調整。

## v0.7.5 (2026-05-24) 調整可能なグレーUI設定を追加
- アプリ全体のグレーUI tone向けに設定コントロールを追加。
- gray toneはapp configに保存され、settings dialogから即時適用される。

## v0.7.4 (2026-05-24) 柔らかいグレーUIテーマを追加
- editor canvasは変更せず、既定の白いUI surfaceを柔らかいgray paletteへ変える共有Qt stylesheetを追加。

## v0.7.3 (2026-05-24) level情報をsettingsへ統合
- separate level-info groupを削除し、残るsummaryをlevel-settings groupへ移動。
- key position、door position、start position、key-enemy number textは他の場所で編集または表示されるため、summaryから冗長表示を隠した。

## v0.7.2 (2026-05-24) 読み込みROMのmetadata versionを表示
- metadata stampを既に含むROMを読み込んだ時、ROM info panelに埋め込みMAGATU_SOLOMON_CUSTOMIZER versionを表示。

## v0.7.1 (2026-05-24) key enemy selectorを制約
- 鍵持ち敵selectorを、選択中ステージに現在配置されている敵数までに制限。
- 敵削除により保存済みkey enemy numberが無効になった場合、範囲外targetを残さず、設定をクリアして警告を表示。

## v0.7.0 (2026-05-24) 最小機能マイルストーン
- 最初の0.7 releaseを、現在の最小target feature setが揃ったmilestoneとしてマーク。
- このreleaseには、採用済みステージ設定基盤、鍵持ち敵サポート、ステージ開始時fire reset、stage-start announcement、現行強化敵variantが含まれる。

## v0.6.173 (2026-05-24) 鍵持ち敵announcementのgate分岐を修正
- `$B3C0`のstage-start announcement key-enemy gateを修正。no-key branchはroutine `RTS`の1byte後ではなく、routine `RTS`そのものへ着地するようになった。
- announcement overlayが導入済みで、現在roomにkey enemyがいない場合にroom 4以降のtest playがstart screenでfreezeする問題を修正。

## v0.6.171 (2026-05-24) start announcementのmain caveを移動
- stage-start announcement main routineを`0x0BF2 / $8BE2`から`0x63CC / $E3BC`へ移動し、mask tableを`0x60CC / $E0BC`へ分割。
- これにより`$8BE2`のinitial magic routineとの重複を除去。この重複はstage-start initializerを壊し、announcement flagがないroomでもroom 4以降のtest playをfreezeさせていた。

## v0.6.168 (2026-05-24) Golem charge dash boostを削除
- Golem charge-only dash boost moduleとhack-dialog controlを削除。
- PRG0 overlap ledgerからGolem charge dash予約spanを削除。採用済みGargoyle 2-shot caveが、それらの占有範囲をmutual-exclusion warningなしで所有するようになった。
- Saramandor `$866D` hook互換チェックを、active slow-Bullet wrapper pathへ単純化して戻した。

## v0.6.165 (2026-05-24) announcement描画loop indexを修正
- labelごとの`$915E`呼び出しを`$9471`風PPU script wait helperへ置き換え、stage-start announcement flag branchを修正。
- 各label描画中にcallerの`X` registerを保持し、room-flag announcement loopが5つのflag entryを超えて走らないようにした。
- v0.6.164 announcement hookで保存されたROM向けにmigration toleranceを追加。

## v0.6.164 (2026-05-24) stage-start announcement順序を修正
- custom labelを描いてからstock `$915E` intro updateへ戻るようstage-start announcement hookを修正し、採用済みtest-ROMの呼び出し順に合わせた。
- shrine markerとannouncement labelが表示されずstart screenでfreezeしていたv0.6.163の問題を修正。

## v0.6.163 (2026-05-24) stage-start announcementを追加
- intro screen上にactive level settingsを表示するstage-start announcement overlayを追加。採用済み2-column layoutで`DARK ROOM`, `FIRE LOSS`, `KEY ENEMY`, `HIDDEN DOOR`, `FIRE SEALED`, `SPELL SEALED`を表示。
- bank 0/1/2のtile byte `$25`と`$27`へ、不足していた`K`と`P`文字用custom gameplay CHR tileを導入。
- 新しいステージ別UI fieldを追加せず、既存room flag、fire-reset状態、key-enemy設定からROM保存時にoverlayを接続。

## v0.6.162 (2026-05-23) Gargoyle 2-shot variantを追加
- 借用Gargoyle ID `$7A/$7B`向けに、採用済み`$AE6F` two-Bullet materialization routineを追加。
- two-shot bodyの前にtype gateを追加し、stock Gargoyle `$78/$79`は原作single-Bullet pathに残した。
- stageまたはmirror enemy dataに`$7A/$7B`が存在する時、Gargoyle variantをROM保存へ接続し、新しい2-shot Gargoyle entry向けにpicker/config labelを更新。
- Golem charge dash hackが既に適用済みのGargoyle 2-shot ROMを黙って上書きしないようguardを追加。

## v0.6.160 (2026-05-23) 壊れたGargoyle rapid-fire patchを無効化
- 検証によりGargoyle bulletのmaterializeを妨げ、item pickup処理へ干渉し得ることが分かったため、v0.6.159 Gargoyle rapid-fire runtime hookを通常ROM保存から無効化。
- firing pathの再確認が済むまで、`$7A/$7B`敵ピッカー説明を中立的なGargoyle #2 labelへ復元。

## v0.6.159 (2026-05-23) Gargoyle rapid fireを追加
- `$7A/$7B`向けにGargoyle speed1 #2 rapid-fire variantを追加。1発目はattack stateをactiveに保ち、stock resetが再開する前に2発目が短時間後に続く。
- Saramandor Bullet state0 cave後の未使用paddingを回収し、新しいGargoyle reset wrapperをkey-enemy split chunkより前の`$BEC7-$BEF2`へ配置。
- `$7A/$7B`の敵ピッカーlabelを更新し、rapid-fire Gargoyle variantを説明するようにした。

## v0.6.158 (2026-05-23) key enemyとgap_fixの重複を解消
- key-enemy initial-slot binderを`$C000`から、回収済みPRG0 tail領域`$C1D6`へ移設。
- key-enemy defeat dropperを小さな検証済みPRG0 cave gapへ分割し、entryを`$C029`から`$BE2F`へ移動。migration中に古い`$C000/$C029` byteをクリア。
- `gap_fix` `$C000-$C087`との残りPRG0重複を削除し、鍵持ち敵とhorizontal-gap stabilization patchが共存できるようにした。

## v0.6.157 (2026-05-23) room flag dataをPRG1へ移動
- mapper66 runtime room flagとhidden-door cell dataをPRG1 StageExt tableへ移動し、mapper66 loader tail中に`$0778`と`$077C`へコピーするようにした。
- 古いDoorCellTable/RoomFlagTable役割からPRG0 `$C180-$C1FF`を解放し、key-enemy dropped-key handlerを`$C0F0`から`$C180`へ移設。
- `$C0F0-$C155`をruntime block override caveへ戻し、鍵持ち敵とspecial block/dark-room runtime処理の衝突を除去。

## v0.6.156 (2026-05-23) fall key drop entryを修正
- fall-death key handlerを修正し、古い`$C024` entryではなく、移設後key-drop bodyの`$C02C`を呼ぶようにした。以前のv0.6.155 layoutでは、敵が落下死した時にfire-defeat-onlyの`$9D1C` setupへfall throughしてcrashする可能性があった。

## v0.6.155 (2026-05-23) key enemy落下死dropを追加
- key-carrying initial enemy向けにfall-deathサポートを追加。選択されたinitial enemyはroom enemy load中に既存のfall-death replacement flagを受け取り、足場を落とすとkey pathを発火できる。
- 原作fall-fairy replacement entryをhookし、設定keyをspawnしてから落下敵を通常どおりdespawnするようにした。active key targetがないroomでは原作fairy replacement挙動を保持。
- fall-death flagging logic用の余地を作るため、key enemy defeatとdoor-light helper caveを移動し、保存時にv0.6.153-v0.6.154 cave layoutからのmigrationを追加。

## v0.6.154 (2026-05-23) key enemy slot hook stackを均衡化
- production key-enemy initial-slot binderを成功したv12実験に合わせて修正。全branchがreturn前に、保存したX registerを正確に1つのPLAで均衡させる。
- targetではないinitial enemyがroom setup中にstack byteを1つずつ漏らす問題を防止。これは敵が複数いるステージで即クリアやstartup flow破壊を起こし得た。
- 以前のv0.6.153 key-enemy binderで保存されたROMを、次回保存時に修正版binderで上書きできるようにした。

## v0.6.153 (2026-05-23) key enemy entry clearを修正
- 設定されたkey-carrying initial enemy slotを、dropped-key runtime stateから分離。StageExt slotはRAM `$072B`に置き、`$0723`はdropped-key active/tile marker専用のままにした。
- 設定enemy numberがactive dropped keyとして誤読され、ステージ開始時に即key/clear処理へ流れ込むbugを修正。

## v0.6.152 (2026-05-23) key enemy runtimeを接続
- ステージ別key-carrying initial enemy向けproduction runtime patchを追加。Mapper66 stage loadはStageExt key enemy slotをRAMへコピーし、そのinitial placement numberをruntime enemy slotへbindし、その敵撃破時にkeyをdropする。
- 生成されたkeyがDemon Mirror spawn敵を再利用せず、通常key flowでdoorを開くよう、dropped-key pickup処理を追加。
- key runtime cave span向けにROM/RAM overlap guardを追加。patchは無関係の非empty codeを黙って衝突上書きせず拒否する。

## v0.6.151 (2026-05-23) key enemy UIを追加
- tile hover/status-barの敵textに`敵#N`として敵順番号を追加し、canvas上からinitial placement indexを識別できるようにした。
- 既存stage extension key-enemy slot fieldへ書き込む、level別`鍵持ち敵 (#)`設定を追加。`0`はなし、`1-15`は初期配置敵順に対応。
- key-enemy enable/read/write処理向けにstage extension helper accessorを追加。

## v0.6.150 (2026-05-23) borrowed-IDの見た目metadataを分離
- v0.6.121のPanel Monster group-wide property/animation書き換えをtype-specific hookへ置き換え、借用Panel IDだけがPanel metadataを受け取るようにした。
- Spark Ball property/animation hookをPanel selector経由でchainし、2つのborrowed-ID systemが互いを戻さず共存するようにした。
- 元の共有Demonhead/Saramandor group metadataを復元し、`$50/$51`などのstock Demon Mirror spawnがPanel Monster metadataを継承しないようにした。

## v0.6.146 (2026-05-23) post-HUD fire reset hookを取り消し
- stage-start挙動を悪化させ、Demon Mirror spawningも復元しなかったため、v0.6.145の`$90E6` post-HUD hookを取り消し。
- Demon Mirrorとの相互作用は別途調査しつつ、v0.6.144型のloader-based fire reset実装を復元。

## v0.6.145 (2026-05-23) fire resetをstage setup後へ移動
- per-stage fire reset runtimeを`$9071` level-loader caveから外した。loaderは再び`ROOMFLAGS` cacheとhidden door処理だけを担当。
- `$90E6`からhookされる新しい`$C0C2` post-HUD caveを追加。level ready、enemy placement、HUD buffer setup後に実行され、`ROOMFLAGS` bit4がsetされている時に`$042E/$042F`をclearしHUDを再描画する。これによりDemon Mirror setupの中断を避ける。

## v0.6.144 (2026-05-23) per-stage fire reset対象を修正
- stage fire reset runtimeを修正し、`$042B`をclearしないようにした。このbyteは持ち越しstockだけでなくHUD/max/cursor状態の一部であり、clearすると不可能なscroll-count表示挙動を起こしていた。
- resetは`$042E/$042F`だけをclearし、すぐに`$A1CC`を呼んで新ステージのfire stock HUDを再描画するようにした。

## v0.6.143 (2026-05-23) per-stage fire resetを追加
- ステージ開始時に持ち越しfire / super-fire stockをresetするステージ設定を追加。UIは設定を`StageExtTable`へ保存し、runtimeはそれを`RoomFlagTable` bit4へmirrorするため、bank0 stage-load codeがPRG bank switchingなしで適用できる。
- `$BBE0` room loader caveを37Bから55Bへ拡張。current roomでbit4がsetされている場合、loaderはplay開始前に`$042B/$042E/$042F`をclearする。

## v0.6.142 (2026-05-23) StageExtTable基盤を追加
- PRG1 `0x8800-0x8A0F`へ`StageExtTable`を追加。16B header + 64 rooms x 8B。将来のfire reset、鍵持ち敵、stage-start announcement機能向け共有per-stage settings基盤。
- mapper66拡張とmapper66保存がtableを保持し、XML export/importが新per-level fieldを保持するよう、read/write配管を追加。

## v0.6.141 (2026-05-23) Panel Monster fire tailを共有
- 2-wayと3-way fire cave間で、同一のPanel Monster marker-write helperとfire-exit tailを共有。2-way caveは3-way caveのcommon tailへジャンプし、local ready-timer RTSだけを保持する。
- Panel Monster borrowed-ID予約をさらに27B削減。Borrowed-ID runtime予約は合計819B、bank0 cave fragmented free totalは238B、最大fragmentは46B。

## v0.6.140 (2026-05-23) 未使用Borrowed-ID予約を解放
- Borrowed-ID runtime span listから、未使用の`$BF50-$BF68` NOP-only Saramandor variant予約を削除。Saramandor、Panel Monster、Spark Ball挙動を変えず、PRG0 bank0 caveで25Bを解放。
- Panel Monster bullet hookとnormal fire copy予約を分割し、`$BFAF-$BFB8`の未使用10B gapを占有扱いしないようにした。

## v0.6.139 (2026-05-23) PRG1 wide-title reserveを分割
- wide-title PRG1予約を`0x80D0-0xBB95`から`0x80D0-0x87FF`へ削減し、1,840Bのtitle workspaceを残した。確認済みimport titleは589Bを使用。
- `0x8800-0xBB95`を、将来のstage-load-time tableおよびnon-gameplay-screen code/data向け13,206B PRG1 general reserveとして再分類。

## v0.6.137 (2026-05-23) Spark Ball variant caveをgap_fixから移動
- Dragon-ID Spark Ball variant runtime caveを`$C000-$C087` gap_fix cave範囲外へ移設。Spark Ball variantは`$BD26`, `$BE62`, `$BEEA`, `$BFD8`, `$CFDE`, `$EFC4`の小さなPRG0 free fragmentを使うようになった。
- gap_fixとSpark Ball variantを、予約PRG spanの重複なしで同時適用できることを検証。

## v0.6.136 (2026-05-23) 通常animation table lookupを保持
- animation metadata hookの通常pathを復元し、`$D0E8/$D0E9`を読む前に元のtype-group indexをreloadするようにした。Spark Ball variant type check後に、非variant characterが誤ったanimation metadataを使う問題を防ぐ。

## v0.6.135 (2026-05-23) Spark Ball variant animation検出を修正
- Dragon-ID Spark Ball animation hookを修正し、animation state scratch値ではなくactive main slotからentity type byteを読むようにした。通常DragonはDragonとして描画しつつ、`$6A/$6B/$6E/$6F`はSpark Ballとして描画できる。

## v0.6.134 (2026-05-23) 通常Dragon描画を復元
- Dragon-ID Spark Ball variantを作り直し、共有Dragon groupを変更するのではなく、type-specific hook経由で`$6A/$6B/$6E/$6F`にSpark Ball propertyとanimation metadataを与えるようにした。
- 共有Dragon propertyおよびanimation table byteを復元し、通常Dragon `$68/$69/$6C/$6D`がSpark Ball化しないようにした。

## v0.6.133 (2026-05-23) Spark Ball pause方向labelを修正
- Dragon-ID Spark Ball pause variantのpicker/config labelを確認済み挙動に合わせて更新。`$6A/$6E`は上、`$6B/$6F`は下。

## v0.6.132 (2026-05-23) Spark Ball pause検出用にDragon IDを保持
- Dragon-ID Spark Ball variantを変更し、AIをstock Spark Ball routineへroutingしつつ、元の`$6A/$6B/$6E/$6F` type byteを保持するようにした。pause hookが確認できる安定IDを残す。
- sub-slot `+3` marker checkを、`$AB13` Spark Ball speed commitでの直接main-slot type checkへ置き換え。stock `$28-$2F` Spark Ballはpause hook pathを迂回する。

## v0.6.131 (2026-05-23) Spark Ball pause variantを分離
- Dragon-ID Spark Ball variant向けにmarker-based `$AB13` pause hookを追加。wrapperはsub-slot `+3`を`$A6`でmarkし、markされた敵だけがLIFE百の位mod3停止挙動を使う。
- 大きくなったmarker-aware wrapper同士が重ならないよう、fast Dragon-ID wrapperを`$C008`へ移動し、pause hookを`$C038`へ配置。
- `$6A/$6B/$6E/$6F`のpicker/config labelを「Spark Ball pause」へ復元。

## v0.6.130 (2026-05-23) Dragon-ID Spark Ball variantを安定化
- 借用Dragon `$6A/$6B/$6E/$6F` group向けに、不足していたSpark Ball propertyとanimation metadata patchを追加。確認済みtest ROM setupにより近くなり、借用IDが無関係な敵として初期化/描画される問題を防ぐ。
- 確認済みmarker-free hookは原作`$28-$2F` Spark Ballも変更してしまうため、LIFE百の位pause hookはいったん無効のままにした。
- 停止挙動をきれいに分離できるまで、picker/config labelを「pause」から「variant」へ改名。

## v0.6.129 (2026-05-23) 危険なSpark Ball variant markerを削除
- 安全でないSpark Ball pause marker実験を削除。main-slot `+2`とsub-slot `+2`のどちらも、借用Dragon-ID Spark Ball variantを壊す可能性があった。
- Dragon-ID Spark Ball variantは、`$6A/$6B/$6E/$6F`を確認済みstock Spark Ball phaseへ変換するだけになった。global `$AB13` pause hookはもう適用されないため、原作`$28-$2F` Spark Ballは触られない。

## v0.6.128 (2026-05-23) Spark Ball variant markerをsub-slotへ移動
- 敵の見た目/初期化へ影響し得るmain-slot `+2`から、Spark Ball pause variant markerを外した。
- Dragon-ID Spark Ball variantは代わりにsub-slot `+2`をmarkし、原作`$28-$2F` Spark Ballは引き続きpause hookを迂回する。

## v0.6.127 (2026-05-23) Spark Ball pause variantを分離
- Dragon-ID Spark Ball pause variantが選択可能なmonster entryとして出るよう、敵ピッカーを修正。
- LIFE百の位mod3停止を適用する前にborrowed-ID markerを確認するよう、Spark Ball pause hookを変更。原作`$28-$2F` Spark Ballはstock movementを維持。

## v0.6.126 (2026-05-23) Dragon-ID Spark Ball variantを追加
- 採用済みDragon #2 ID `$6A/$6B/$6E/$6F`向けに、always-on Spark Ball variant patchを追加。
- `$6A/$6E`はstock Spark Ball up phaseへ入り、`$6B/$6F`は採用済みright-hand/down phaseへ入る。slow/fast pairは確認済みstock Spark AI entry pointを使う。
- Spark Ball position commitへLIFE百の位mod3 pause hookを追加し、再利用Dragon IDがエディタ内でSpark Ball pause variantとして表示されるよう敵定義を更新。

## v0.6.124 (2026-05-23) 不安定なPanel Monster velocity-sync実験を取り消し
- v0.6.123のPanel Monster斜めBullet velocity-sync変更を取り消し。これはdemon mirror spawnを含むspawned-enemy挙動を壊し、Panel Monsterの発射/向きを不安定にしていた。
- v0.6.122の「移動時だけ有効になるBullet Y hook」を復元。生成済みBullet速度やmirror spawn flowに触れず、口元drift修正の挙動を保つ。

## v0.6.123 (2026-05-23) Panel Monster斜めBulletにY velocityを使用
- Bullet AI hookから手動でYを動かすのではなく、spawned BulletのY velocityを設定するようPanel Monster variantの斜めshotを作り直した。
- 共有diagonal velocity helperで採用済み2-way/3-way spawn patternを保ちながら、stock Bullet AI entry `$AFBB`を復元。
- 斜め移動をstock entity physics pathへ結びつけ、enemy load変更時のangle driftを減らした。

## v0.6.122 (2026-05-23) Bullet移動でPanel Monster斜めY移動をゲート
- production Panel Monster variant Bullet hookを修正し、stock Bullet movement routineがactive motionを報告した時だけ斜めY移動を適用するようにした。
- 新規spawnされたPanel Monster Bulletが、水平移動開始前に口元で待機している間に縦方向へdriftするのを防ぐ。

## v0.6.121 (2026-05-23) Panel Monster 2方向/3方向variantを追加
- `$52/$53/$56/$57`を2-way diagonal shot panel、`$5A/$5B/$66/$67`を3-way shot panelとして、always-on Panel Monster borrowed-ID patchを追加。
- patchはborrowed ID自体を保持しつつ、AIをPanel Monster wrapperへroutingし、Panel Monster init property/animationを適用し、採用済み斜め挙動向けにPanel Bullet Y移動をhookする。
- borrowed IDがDemonhead/Saramandor entryではなくPanel Monster variantとして表示されるよう、敵ピッカーと敵定義を更新。

## v0.6.120 (2026-05-23) CustomizerへGolem charge dash boostを追加
- `core/golem_charge_dash.py`とGolem charge dash boost selectorをgame behavior dialogへ追加。selectorはOFF/2x/3x/4x/5xを提供し、5xは採用済みtest挙動に一致。
- production patchは既存Saramandor speed wrapper経由でchainし、Saramandor bullet variantとGolem charge boostが共存できるようにした。
- boost対象は確認済みGolem rush speed `$26/$5A`だけ。通常歩行速度は既存Golem speed設定で制御される。

## v0.6.105 (2026-05-22) export dataとmapper66 ROMへapp versionを刻印
- runtime block override tableの後、copy済みvectorの前にあるfree areaを使い、PRG bank1 file `0xFF00-0xFF3F`へmapper66 ROM metadata stampを追加。
- ROM保存時、拡張mapper66 ROMだけに現在の`MAGATU_SOLOMON_CUSTOMIZER` app versionをそのmetadata slotへ書き込むようにした。
- 互換性のためlegacy `app_version="1.1"`値を保持しつつ、既存level XML exportへ`customizer_app_version`を追加。
- MAGATU PNG埋め込みstage XMLとglobal settings JSONは既に`app_version`を持っていることを確認。この変更でそれらの経路もversion付きに保たれる。

## v0.6.103 (2026-05-22) animation timer再利用で低速Saramandor bulletを維持
- Mesen loggingによりmain-slot `+12`はpersistent storageではなくstock Bullet animation timerだと確認されたため、v0.6.102 slow-bullet修正を修正。
- `$866D` wrapperは、後続Bullet behavior reinitialization中に、fresh-spawn marker（`+12=$A5`）または既にoverride済みの1/4速度X velocity（`Xv=$10/$F0`）のどちらかでslow Bulletを認識するようになった。
- `+12`のpersistent marker状態への依存を停止。slow-speed wrapper caveは`$BF00-$BF4F`に広がり、未使用fillerを`$BF50`へ移動。

## v0.6.102 (2026-05-22) reinit後も低速Saramandor bulletを低速維持
- Bullet state0がbehaviorを変更し、generic entity loopが`$8AC0`を2回目に呼ぶことで、Saramandor #2 speed 2 bulletが通常速度へ戻る可能性を修正。
- `$866D` wrapperは各slow Bullet speed init後にslow markerを再保存するようになり、後続Bullet reinitializationでも1/4速度overrideを維持する。
- cave spanは`$BF00-$BF3F`内に収まり、次の登録済みSaramandor variant caveである`$BF40`より前で終わる。

## v0.6.101 (2026-05-22) Salamander/Dragon反応距離labelを明確化
- `SUB_B1E9`をROM byteおよび`SUB_A134` distance updaterと照合し直した。
- `$B1F3` / file `0x3203`がX反応threshold、`$B1FF` / file `0x320F`がY許容thresholdであることを確認。
- game-behaviorダイアログの文言をfiring rangeからreaction distanceへ更新し、preset labelを明示的なpixel/tile値へ変更。

## v0.6.100 (2026-05-22) legacy toggleなしでSalamander距離調整を維持
- Salamander/Dragon X/Y reaction distanceコントロールの適用を復元。
- 削除済みlegacy global fireball/despawnチェックボックスは戻さず、2つのdistance byteだけを書き込む。
- UIが古いglobal Salamander fireball patchを呼ばないよう、distance-only core helperを追加。

## v0.6.99 (2026-05-22) 古い共通Salamander bullet toggleを削除
- game behaviorダイアログから、廃止済みglobal Salamander fireball enable/despawnチェックボックスを削除。
- 現在実装はglobal toggleではなくSaramandor #2 enemy IDを使うため、古い2項目は混乱を招き、legacy patchを書き込み得た。
- 共通設定のexport/importは、削除済みの古いkeyを無視するようにした。

## v0.6.98 (2026-05-22) Saramandor #2の低速markerを速度初期化まで保持
- v0.6.97の低速Bullet runtime漏れを修正。main-slot `+2`は`$8AC0`前にentity loopで上書きされるため、低速markerをmain-slot `+12`へ移動した。
- `$866D`速度wrapperは、原作`$8AC0`が`+12`を消す前にone-shot markerを確認し、marker付きの`$62/$63` Bulletだけを1/4速度へ上書きするようにした。
- wrapperは`$8AC0`へ入る前のA/Y入力を保持するようにした。`$8AC0`はこれらのregisterに依存するため、先に触ると通常entity初期化が壊れていた。
- 通常Saramandor #2 speed 1（`$5E/$5F`）と通常ゲームBulletはmarkerなしのまま変更しない。

## v0.6.97 (2026-05-22) Saramandor #2低速Bullet速度修正
- Saramandor #2 speed 2（`$62/$63`）のBulletが通常Bullet速度のままになる問題を修正。
- patchはSaramandor #2 speed 2が作ったchild sub-slotだけをmarkし、原作entity速度初期化`$866D`をwrapするようにした。`$8AC0`が通常Bullet速度を読み込んだ後、markされたBullet entityを1/4速度（`Xvel=$10/$F0`）へ上書きする。
- 通常Bullet、Panel Monster Bullet、Saramandor #2 speed 1（`$5E/$5F`）は変更しない。

## v0.6.96 (2026-05-22) ミラーピッカーで敵速度を適用
- ミラー敵のドラッグ&ドロップを修正し、敵をミラー出現slotへ落とす時に現在の敵速度radio buttonを適用するようにした。
- これによりSaramandor #2 speed 2はslotを`$5E/$5F`のままにせず、`$62/$63`を配置するため、1/4速度Bullet variantが実際に選ばれる。

## v0.6.95 (2026-05-21) Saramandor #2 Bullet variantを追加
- 未使用のSaramandor #2 ID向けに常時適用ROM patchを追加。
- `$5E/$5F`は通常速度Bullet entityを生成し、`$62/$63`は1/4速度Bullet entityを生成する。`$66/$67`は予約のまま変更しない。
- Saramandor #2右/左entryをモンスターピッカーと速度radio mapping（`5E/62/66`, `5F/63/67`）へ追加。
- Saramandor variant cave範囲をRoom Flag cave verifierへ登録し、隠し扉、暗闇、壊せる白壁、gap-fix patchと共存できるようにした。

## v0.6.94 (2026-05-21) ROM読み込み時にroom flagを復元
- 改造済みROM読み込みで、Room Flag Tableを各`Level.room_flags`へ復元するようにした。
- patch済みROMを再度開いた時、隠し扉、Bファイア禁止、Aストーン禁止、暗闇などの部屋別設定がlevel settings checkboxへ再表示される。
- 既存の壊せる白壁/透明壊せるcell復元はそのまま維持。

## v0.6.93 (2026-05-21) 共通設定import/export
- game behavior/global settingsダイアログへJSON export/importボタンを追加。
- exportは、開始/continueステージ、ワープ羽、初期魔法/残機、プレイヤー速度、敵挙動調整、clear-screen character、gap fix、暗闇テンポなど、共有ROM挙動設定の現在のダイアログ値を保存する。
- importはダイアログcontrolだけを更新する。ROMは他のダイアログ操作と同じく`Apply`または`OK`を押した後に変更される。

## v0.6.92 (2026-05-21) Top PNGをpixelから再構築
- `Top PNG読込`は同名JSON sidecarのlayout dataを無視するようにした。
- 読み込んだPNGを256x64 top bandの正本として扱い、同一8x8 tileは共有し、異なる8x8 tileには別のtitle tile IDを割り当て、そのband向けにwide-title streamを再構築する。
- PNGが別の絵に編集された時、古いtile共有関係を保持してしまう問題を防ぐ。

## v0.6.91 (2026-05-21) カラーTop PNG round-trip
- `Top PNG保存`はtitle top bandを4段階グレースケールへ潰さず、color RGB PNGとしてexportするようにした。
- PNG importは各pixelを、そのcellの実際のtitle palette/attribute context内で最も近い有効色へ戻すようにし、複数paletteのtitle artを全体一律で平坦化せず保持する。
- 描画済みtitle imageを全960 tile pixel patternへ戻すround-tripで、color export/import logicの不一致が0件であることを確認。

## v0.6.90 (2026-05-20) title palette Applyボタンを追加
- title palette editorへ`OK / Cancel / Apply`挙動を追加。
- `Apply`はダイアログを閉じずに、選択したtitle色を書き込みpreviewを更新する。
- `Cancel`はtitle palette editorを開いた時点の色へ戻す。

## v0.6.89 (2026-05-20) title palette editorを追加
- title migrationダイアログへ`タイトル色...`ボタンを追加。
- ダイアログはROMのtitle palette script経由でPPU `$3F00-$3F0F`へ書かれるtitle BG palette byteを編集する。
- 実効NES color numberが変わるslotだけを書き戻すため、`$FF`のような等価な既存byteを不要に正規化しない。

## v0.6.88 (2026-05-20) title previewのPPU attribute対応
- color title previewで誤っていた`$24` clear-tile特別扱いを取り消した。`$24`はPPUと同じく実際のCHR tile、attribute、palette pathで描画される。
- JP title後半のhardcoded attribute write（`$2BEA`, `$2BF0-$2BF6`, `$2BF8-$2BFF`）をpreview attribute mapへ追加し、previewが最終title attribute状態により近くなるようにした。

## v0.6.87 (2026-05-20) title preview背景色修正
- color title previewで、clear/background cell（`$24`）を通常CHR tile artとして扱わず、title backdropとして描画するように修正。
- title attribute previewは、21-byte title attribute table適用前に原作`$FF` attribute fillから開始するようにした。

## v0.6.86 (2026-05-20) color title preview
- title migrationダイアログのpreviewを、固定グレースケールではなくtitle paletteとattribute dataで描画するようにした。
- PNG export/import pathは既存の4段階グレースケールrendererを使い続けるため、このpreview改善で編集round-tripは変わらない。

## v0.6.85 (2026-05-20) Top PNG sidecar layout
- `Top PNG保存`はtimestamp付き既定file名を使い、同名`.json` sidecarを書き出すようにした。
- `Top PNG読込`はsidecarが存在する場合にそれを読み、pixel適用前にtitle top-band layoutを復元する。
- fresh-JPの`377 cells`とimport済みarcadeの`386 cells`の差で、Top PNG round-tripが噛み合わない問題を修正。

## v0.6.84 (2026-05-20) 重複したPage位置controlを削除
- game behaviorダイアログから52/53 Page position spin boxを削除。
- 同じJP ROM offset（`0x35D9` / `0x35DD`）はcanvas meta-item drag pathで既に編集されるため、両方のUIを残すとdrag済み位置を古いダイアログ値で上書きする可能性があった。
- `page_pos.py`は低レベルROM helperとして残すが、ユーザー向け操作はcanvas drag workflowに統一。

## v0.6.83 (2026-05-20) game behavior設定を整理
- game behaviorダイアログを`基本`、`プレイヤー`、`敵・AI`、`画面・演出`、`保守・特殊`のcategory tab構成へ作り直した。
- UI整理だけで、patch logicとROM formatはv0.6.82から変更なし。

## v0.6.82 (2026-05-20) 初期残機設定を追加
- game behaviorダイアログへDanaのglobal初期残機設定を追加。
- patchは小さな`$8BF4` routineを入れて`$0452`だけを変更し、`X=$03`で戻るため、原作`$042B` fire-scroll setupを誤って変更しない。
- 設定は原作の`3` livesへきれいに復元できる。

## v0.6.81 (2026-05-20) 初期魔法UIを調整
- game behaviorダイアログの初期魔法controlを、より分かりやすいtooltipとhelp textで改善。
- 初期魔法patchのapply log messageを日本語のユーザー向け文言へ変更。
- ROM patch formatはv0.6.80から変更なし。

## v0.6.80 (2026-05-20) 初期魔法routineでAを保持
- v0.6.79で入った、shrine intro中にscore/status areaが壊れる副作用を修正。
- `$9144` call siteは復帰直後に`A=0`であることを期待し、その値で`$78-$7C`をclearする。custom `$8BE2` routineは`PHA/PLA`で書き込みをwrapし、Xは触らないままAを保持するようにした。
- Aを保持しないroutineが入ったv0.6.79 test ROMは、設定を再適用した時に受け入れ、18-byteの安全なroutineへ書き直す。

## v0.6.79 (2026-05-20) 初期魔法hookをnew-game setupへ移動
- 初期魔法patchを再修正。v0.6.78の`$B606` hookは読み違いで、`$B604`は通常ステージ開始ではなくSolomon room / ending pathだった。
- patchはnew-game setup内のCPU `$9144`（`STX $042B`）と、後続stage-start initializer内のCPU `$C9E3`（`STX $042B`）をhookするようにした。どちらも同じ`$8BE2` routineを呼び、`$042B/$042E/$042F`を書き、Xを保持する。
- 誤ったv0.6.78 `$B606` hookを受けたROMは、設定適用または復元時にclean upされる。

## v0.6.78 (2026-05-20) 初期魔法の後段resetを修正
- 初期魔法patchが実際のステージ開始で効かない問題を修正。
- v0.6.77はCPU `$C9E3`をhookしたが、後続stage-build pathのCPU `$B604`が`$042E/$042F`を再度clearしていた。patchはCPU `$B606`（`STA $042E`）も`JSR $8BE2`へ置き換え、直後の原作`$B609: STA $042F`は残す。custom routineは`A=hi`で戻るため、原作`$B609` storeが意図したhigh byteを再度書く。
- 既定設定は両hookと`$8BE2` NOP bandを復元する。

## v0.6.77 (2026-05-20) 共通初期魔法設定を追加
- game behaviorダイアログへglobalな「初期魔法」設定を追加。
- 古いBESKのdemo/start/continue 3行拡張modelは採用せず、共通stage-start magic max（`$042B`）と初期F/S stock（`$042E/$042F`）を制御する。
- patchは検証済み`$8BE2` NOP bandを使い、CPU `$C9E3`（`STX $042B`）だけを`JSR $8BE2`へ置き換える。`$042C/$042D` fire elapsed-counter clearは残し、「zero-clear全体を消す」危険なshortcutを避ける。
- 既定max `3` + 空stockは原作hookとNOP bandを復元する。

## v0.6.76 (2026-05-20) ワープ羽の0ステージ進行を許可
- ワープ羽の進行ステージ設定を`0-53`へ拡張。
- `0`はoperand `$FF`としてencodeされ、通常のstage-clear `+1`と合成されて同じroomへwrapする。これにより「羽を取って同じステージへ戻る」挙動が可能になった。

## v0.6.75 (2026-05-20) ワープ羽進行設定を追加
- game behaviorダイアログへglobalな「ワープ羽」設定を追加。
- 設定はCPU `$C6A0`（file `0x46B0`）の検証済みJP/JPN66 operandを編集する。原作operand `$05`は通常stage-clear incrementと合成され、原作の6ステージ進行を作る。
- patchは署名検証され、既に変更済みの値も再編集できる。

## v0.6.73 (2026-05-20) 星座背景のミラー配置を修正
- 通常ステージの星座背景グラフィックについて、選択範囲の左右/上下反転を修正。星座背景は3x2の背景オブジェクトなので、左端cellを1点として扱うのではなく、3cell幅の左上位置を中心基準でミラーするようにした。
- その他のmeta位置、アイテム、敵、デーモンミラー、壊せる白壁marker、透明壊せるmarkerのミラー挙動は従来どおり維持。

## v0.6.72 (2026-05-20) title文字overlay編集を改善
- titleの「追加文字...」ダイアログは、固定のversion文字列を常に表示するのではなく、現在のoverlay行をwide-title streamから読み戻して初期編集文字列に使うようにした。
- title overlay textでcomma、period、double quoteを使えるようにした。これらの記号glyphはROM既存の低位font tileを再利用し、未使用の高位CHR tile slotへコピーするため、原作title text routineは触らない。
- Room Flag bank0 cave帯を変更せず、`VERSION 0.6.72, TEST`と`DARKNESS MIRROR "A"`のような反復編集を確認。

## v0.6.71 (2026-05-20) wide-title stream経由のtitle文字overlayを追加
- title画面へ、中央揃え1行のA-Z / 0-9 / space textを書き込む「追加文字...」操作を追加。原作のPUSH START / TECMO text routineを変更せず、内部wide-title stream経由で描画する。
- wide streamが`$00-$2F`をcontrol byteとして予約していても安全に描画できるよう、ROM font glyphを未使用の高位CHR tile IDへコピーした。
- mapper66 loader codeが実際には`0x8010-0x80C5`を占有するため、wide-title bank1 workspace開始位置を`0x80A8`から`0x80D0`へ移動した。

## v0.6.70 (2026-05-20) F1ショートカットhelpを更新
- F1ショートカット/helpダイアログを、基本キー、mouse操作、hover quick placement、item flag、selection editing、file loadingの分かりやすいsectionへ再構成。
- block quick placement、透明壊せる壁、完全なmirror挙動、現在の`SOLOMON_CUSTOMIZER.py` command line entry pointに合わせて古い記述を更新。

## v0.6.69 (2026-05-20) ステージmeta itemをミラー反転
- 選択範囲の反転で、Solomonのseal markerやJP Page of Time/Space markerなど、ROM-backed位置byteを持つ`level_meta_items`もミラーするようにした。
- 反転時はeditorが使うmemory上のmarker位置と、各`rom_offset`にある元ROM位置byteの両方を更新する。

## v0.6.68 (2026-05-20) 選択範囲ミラー挙動を完成
- 選択範囲の左右/上下反転を拡張し、start、key、door、constellation panel、demon mirrorなどのstage meta位置も対象にした。
- 左右反転では、速度variantを可能な範囲で保持しつつ、左右向きの敵variantも入れ替えるようにした。
- 既存の選択反転は地形、アイテム、敵、壊せる白marker、透明壊せるmarkerに対応済みだったため、部屋全体を選択して`F`を押す全体ミラー編集が実用的になった。

## v0.6.67 (2026-05-19) 透明壊せる壁の配置を堅牢化
- 通常のblock変更時に古い透明壊せるmarkerを先にclearし、UIが意図的に再追加する前の古いmarker残りを消すようにした。

## v0.6.66 (2026-05-19) 透明壊せる壁markerを追加
- 部屋map上では空白に見えるが、runtimeでは通常の壊せる石へ変換される透明壊せる壁をeditor block typeとして追加。
- v0.6.65のbank1 breakable-cell tableと`$0760-$076F` runtime listを再利用し、白い壊せる壁と透明壊せる壁が同じ安全な保存経路を共有するようにした。新しいbank0 dataは追加しない。
- 透明壊せるcellをXMLとROM read/writeで永続化。editorでは編集表示時だけ黄色の内枠で示す。
- runtime上のsolid判定に合わせ、透明壊せるcell上にはitemやenemyを配置できないようplacement guardを更新。

## v0.6.65 (2026-05-19) 壊せる白壁dataをbank0外へ移動
- 壊せる白壁cell保存先を、bank0 RoomFlag cave領域からPRG bank1拡張data file `0xF860-0xFBAF`（bank1上の`$F850-$FB9F`）へ移動。
- mapper66 loaderは現在roomの16-byte breakable-white listをRAM `$0760-$076F`へcopyするようにした。NMI runtimeは部屋描画後、そのRAM listを読み、選択された`$0304` cellへ`$90`を書き込む。
- 古いbank0 `0x3D00-0x40FF` breakable-white tableとbit1 room flagを削除し、`0x4010-0x4097`の`gap_fix`との衝突を解消。
- editor `(3,8)`をruntime `$93`として読み戻せること、`gap_fix`とbreakable-white runtimeが重ならないことを確認。

## v0.6.64 (2026-05-19) US title import後もJP66を維持し、壊せる白壁を部屋単位でgate
- USまたはpatched US title ROMからtitle/CHRを置き換えたJP mapper66 ROMのregion検出を修正。弱いUS66 markerより先にJP66 loader markerを確認するようにし、JP拡張ROMが`JP66`のまま残るようにした。
- 壊せる白壁cell用の内部room flag bitを追加。現在roomに壊せる白壁cellがない場合、runtimeのbreakable-white routineは即returnするようにし、空tableの部屋に誤って見えない`$90`blockが出るのを防止。
- v0.6.63のgateなしbreakable-white routineで保存済みのROMも、既存のmarked cellを復元できるようreadback互換を維持。

## v0.6.63 (2026-05-19) 壊せる白壁の起動regressionを修正
- v0.6.62で発生したboot hang/green-screen regressionを修正。breakable-white runtime routineは`$BF50`から`$C0F0`へ移動していたが、dark-stage NMI caveが古い`$BF50` addressを呼び続けていた。
- dark-stage caveを`$C0F0`呼び出しへ更新し、breakable-white処理がtable dataへ飛び込まず、新しい16-cell対応routineから実行されるようにした。

## v0.6.62 (2026-05-19) 壊せる白壁の容量を拡張
- 壊せる白壁の容量を1部屋8cellから16cellへ増やした。
- runtime table形式をcount+cellsから`$FF`埋め16-byte room slotへ作り直した。これによりDoorCellTable/RoomFlagTableと重ならず、既存bank0予約領域内に収める。
- runtime routineをindexed pointer readerへ置き換え、2page目以降の部屋が8-bit absolute-X table前提に依存しないようにした。

## v0.6.61 (2026-05-19) 壊せる白壁のeditor対応
- 壊せる白壁をblock pickerへ追加。editorでは白壁として描画しつつ、緑のoutlineで示す。
- 壊せる白壁cellをXMLとROM save dataへ永続化。ROM出力では見た目のcellは白のままにし、one-shot NMI routineで部屋がactiveになった後、選択された`$0304` cellを`$90`へ変更する。
- 実装は既存のroom flag基盤を共有し、title wide bank0 cave衝突を避ける。この時点の上限は1部屋8個。
- editor座標をruntime `$0304` gridへ変換し、editor上のcellとゲーム内の壊せるcellが正しく対応するようにした。
- JP66 ROM検出を修正。拡張済みJP test ROMがUS66 markerだけでplain `JP`として検出され、アプリが再度拡張しようとしていた。plain JP判定より先にJP66を検出するようにした。

## v0.6.60 (2026-05-19) 暗闇ステージtempo既定値を45/100へ変更
- global dark-stage tempoの既定値を、明45frame、暗100frameへ変更。保存ROM byteは2byte目が合計周期（`light + dark`）のため`[45, 145]`になる。
- hack dialogのreset/default値とhint textも合わせて更新。
- 未初期化tempo領域と`[45,145]`のどちらでも`room_flags.get_tempo()`が`(45, 100)`を返すようにした。

## v0.6.59 (2026-05-19) Top PNG cropの縦offsetを修正
- 256x64 Top PNG export/import bandが1pixel上にずれていた問題を修正。title preview imageには1pixelの縦表示補正があるが、Top PNG cropは補正前の`y=48`を使っていた。
- Top PNGは表示補正後の`y=49..112`を使うようになり、上端の空行が消え、下端pixel rowも切れなくなった。

## v0.6.58 (2026-05-19) arcade title固定banner stripを取り込み
- importしたUS arcade title bannerで下側stripが欠けていた問題を修正。patched US titleは2つのstream blockに加え、code（`$CBC3`, PPU `$29A6`, tiles `$63-$74`）から18cellを書き込む。
- US arcade import pathは、その固定stripをblock AへmergeしてからJP内部wide-title streamへ変換するようにした。
- patched US arcade importは、完全な`$63-$74` stripを含む386cellを書き込むようになり、gridが正確に一致する。

## v0.6.57 (2026-05-19) patched US arcade title ROMのimportを修正
- 既知の「Title Screen v1-1 / arcade」patched US ROMからのtitle importを修正。これはstock US title streamではないため、stock decoderがtitle dataをgarbageとして解釈し、previewが崩れていた。
- patched US arcade title decoderを`$CBA6`で検出し、2つのarcade形式stream（`$CD5F`と`$CDF5`）をdecodeしてから、JP内部wide-title bank1 streamへ書き込むようにした。
- そのarcade sourceでは、signatureが一致する場合だけarcade attribute table `$CCAF -> $CD58`をcopyし、既知のJP側color調整を適用する。
- clean JP loadからauto mapper66/wide normalize後、patched US arcade titleをimportしても、targetは`JP66`を維持し、Room Flag bank0 caveを触らない。

## v0.6.56 (2026-05-19) US title import後もJP wide targetをJPのまま維持
- US titleを一度importした後のtitle importを修正。US title CHRをJP wide-title ROMへcopyすると、generic binary region detectorが`US66`と判定し、その後JP raw ROMからimportしようとすると`title import target must be JP/JP66 (target=US66)`で失敗していた。
- `title_screen._verify()`は、CHR由来のregion検出よりもcustomizer内部のJP wide-title bootstrap signatureを強い不変条件として扱うようにした。そのsignatureを持つmapper66 ROMは`JP66`に分類される。
- clean JP load、clean US title import、clean JP title再importの順でも成功し、targetはJP wideのまま残る。

## v0.6.55 (2026-05-19) JP load時のwide-normalization regressionを修正
- `MainWindow.load_rom()`のregressionを修正。古いlog block整理中にmapper66 expansion呼び出しが誤って削除され、clean JP ROMがmapper3のまま残り、title importが「target ROM is not in the internal wide-title format」で失敗していた。
- 読み込み順序を復元。元のraw ROM byteを保存し、mapper3 JP ROMをmapper66へ拡張してから、JP wide-title normalizationを実行する。

## v0.6.54 (2026-05-19) 設計安全性を見直し
- 現在のload pathではmapper66拡張後にJP ROMを正規化するにもかかわらず、title wide normalizationが無効だと表示していた古いload-time log blockを削除。
- 古い実験的な`apply_wide_arcade_title()` APIを無効化。v9 recipeはbank0 Room Flag caveへ書き込むため、統合customizerでは安全ではない。対応pathは`normalize_title_to_wide()` + `transcode_title()`とし、Room Flag caveを触らない。

## v0.6.53 (2026-05-19) layout復元guardを追加
- 復元されるwindow sizeとsplitter sizeにguardを追加。別monitorや大きすぎるdesktopで保存された設定により、中央のlevel editorが使えないほど狭く潰れないようにした。
- 復元window sizeは利用可能screen内にclampし、実用的な最小値を持たせた。splitter復元も、panelが小さすぎる場合や中央editorが圧迫される場合は安全なpanel幅へfallbackする。
- side panelに最大幅を設定し、level editorには最小幅を設定。長いlabelやtool groupが中央editorを細い帯まで押し潰すのを防ぐ。

## v0.6.52 (2026-05-19) title上部PNG限定編集
- title-screenダイアログに上部title graphic band向けボタンを追加。
  - `Top PNG保存...`: `x=0..255, y=48..111`を256x64 grayscale PNG/BMPとしてexport。
  - `Top PNG読込...`: 256x64 imageを同じbandへimportし、下側の山/神殿部分は触らない。
- 編集対象はNES tile row 6..13で、title logo/banner領域を含み、下側の圧縮された風景領域を避ける。

## v0.6.51 (2026-05-19) ユーザー所有ROMからJP wide titleをimport
- 公開build方針として、third-party US title-screen IPSやROMは同梱しない。ユーザーが所有するROMを選択する。US titleが欲しい場合はclean US ROMを選び、個人的にIPS適用済みUS ROMを持っている場合はそれも選択できる。
- mapper66 JP wide-title形式向けに`title_screen.transcode_title()`を作り直した。stock PRG title blockをbank0へcopyするのではなく、source titleをdecodeし、target JP wide-title bank1 workspaceへtitle streamを再encodeする。
- title importはRoom Flag bank0 cave帯`0x3BEE-0x4210`を触らない。targetはmapper66 wide-titleのまま残る。

## v0.6.50 (2026-05-19) JP wide title自動正規化のtest pathを修正
- JP wide title自動正規化を、mapper66拡張後の実アプリ読み込み経路で実行するように修正。
- `m66_expander.change_mapper()`だけでは固定m66 level data area（`0xC010-0xF510`）が埋まらず、ステージデータがzero-fillになる問題を避けるため、`load_all_levels()`、`m66_expander.expand_rom()`、`normalize_title_to_wide()`の順序を使う。
- `main_window.py`でmapper66拡張後にJP load-time title normalizationを再有効化し、適用できない場合はfail-safe loggingで読み込みを継続するようにした。

## v0.6.49 (2026-05-19) ★JP wide タイトル RAM-trampoline 機構 (再設計・実装)
- ★v0.6.48 で無効化した「読込時タイトル自動wide正規化」を、
  bank0 cave を一切使わない新機構で ★再実装 (US は対象外=JP専用)。
- 機構: ★RAM-trampoline + PRG bank1。decoder本体+blockA/B stream
  を mapper66 拡張の bank1 空き (file 0x80A8〜) に配置。$CC4F=
  bootstrap → RAM($03C0) の小型stub → PRG bank1 切替($BB86 bus
  競合・bank0=$FF不変ROM定数/bank1=予約$FF) → bank1 decoder →
  bank0 復帰 → RTS (純サブルーチン・スタック不可侵)。RAM 実行ゆえ
  PRG bank 切替の影響を受けない (定石)。
- ★twin-stub 案は破棄: bank1 の CPU $CC4F 像 = expander level
  data ゆえ同番地 stub 不可。既存loader相当処理も実は PRG 非切替
  (bank0[$8011]=$AD で $13 AND=$01) と判明し、RAM-trampoline に収束。
- ★Room Flag/暗闇/隠し扉/gap_fix と ★完全共存 (静的検証: 
  normalize↔Room Flag↔gap_fix 全順序で RoomFlagError 無し・
  Room Flag 占有帯 file 0x3BEE-0x4210 が素拡張とバイト完全一致)。
- 視覚完全同一: $CD58/palette/CHR bank3/色/bank0 cave ★非改変。
  round-trip 377セル一致で stock と同一描画を自己検証。
- 安全: 署名10点 (stock $CC4F/$CCB6/$CE08/$CEA3/$CD80 caller-B/
  SW両bank/bank1域全0/l_a2・vector/Room Flag帯非交差)、不一致は
  TitleScreenError で ★out 無改変中止 (フォールバック/部分書込禁止)。
- ★bugfix: bootstrap copy-loop の BPL 変位 0xF6→0xF7。v1 は分岐先が
  LDX 即値オペランドにずれループ後ゴミ実行→★起動不可 (ユーザー報告
  「うごかない」)。6502 実行シミュレーションで copy14B+JMP$03C0 実証。
- ★未完: 実機(Mesen)で v2 の trampoline 実行・タイトル表示・Room
  Flag 併用テストプレイ を要確認。確認が通って初めて load時自動
  正規化フックを再有効化する。

## v0.6.48 (2026-05-18) ★リグレッション修正
- ★重大: v0.6.47 の読込時タイトル自動wide正規化が、bank0 cave
  ($BBDE-$C200) を ★Room Flag 機能群 (LOADER$BBE0/MAGICGATE
  $BC20/DOORPREDRAW$BC40/DARK$BC80/gap_fix) と奪い合い、
  clean JP 読込→テストプレイで RoomFlagError(別改造競合)発生。
- 修正: ★読込時の自動正規化を一時無効化 (load_rom のフックを
  no-op化)。clean JP 読込は従来どおり stock のまま=cave非妨害=
  ★テストプレイ復旧 (bank0 cave帯が plain拡張と完全一致を検証)
- ★訂正: 「Phase A 完了」は誤り。標準build_TitleWide_JP_v9 が
  実機OKだったのは Room Flag 未適用の単体ROMだったため。
  Customizer ではテストプレイが Room Flag を当てる→cave衝突。
  真の修正 = 山streamを ★bank0 cave不使用 で stock タイトル
  自身の領域 $CE08..$CF9A(402B) に in-place で収める
  (現エンコーダは stock JP で +9B 超過→エンコーダ圧縮改善が
  必要)。これが出来てから自動正規化 再有効化 & Phase B
- core の wide 系関数 / build script は保持 (再設計の土台)

## v0.6.47 (2026-05-18)
- ★ROM読込時 タイトル内部自動正規化 (方針: アプリ内部処理)
  - clean JP 読込 → (既存)mapper66拡張 → ★自動で当方wide形式へ
    正規化 (確認UIなし・外部ROM不要・ユーザー操作不要)。★見た目
    は元タイトルのまま (視覚同一: 描画377セル完全一致を round-
    trip 検証。プレビューも画素完全一致を確認)
  - 二重適用防止 (is_wide_normalized で判定→既wideはskip)。
    US/unknown/改造済/内部例外 は ★skip し ★読込は絶対壊さない
    (try/except・level編集等に影響なし)
  - decode_title_grid を wide 対応化 (正規化後 ROM のプレビュー
    が正しく表示)。core: is_wide_normalized 追加
  - 私の二転三転で混入した orphan ボタン(_on_wide_arcade 参照)を
    除去しダイアログ構築クラッシュを修正
  - ★未完(次スライス・正直申告): 「別ROMから移植」「PNGから
    取り込む」等はまだ stock 形式前提 → 正規化後(wide)ROMでは
    要 wide 対応化。US の wide 正規化も未実装(現状US読込はskip
    =stockのまま)。これらは継続作業

## v0.6.46 (2026-05-18)
- タイトル移植ダイアログから「広域arcadeタイトル移植(JP)」と
  「独自形式に正規化(見た目そのまま)」の2ボタン+ハンドラを
  ★削除(ユーザー判断)。「正規化」は押しても見た目不変=UXとして
  無意味/混乱、「広域arcade」はGUI露出が特殊(外部arcade ROM必須)
  - core の apply_wide_arcade_title / normalize_title_to_wide は
    ★検証済 Phase2 API として保持(解析R201/memory/build script
    群が参照・無害な不使用ライブラリ。GUI非露出)。広域arcade
    再現は build_TitleWide_JP_v9.py で恒久・独立に可能
  - 残ボタン: 画像保存 / PNG取込 / 別ROMから移植 / 取消 / OK等

## v0.6.45 (2026-05-18)
- 「独自形式に正規化(見た目そのまま)」を追加(タイトル移植ダイアログ)
  - ★JP/JP66専用・外部ROM不要・★明示操作(load時自動書換はしない=
    合意どおり)。この ROM 自身の stock タイトルを ★視覚を変えず
    当方wide形式へ正規化 → 以後アプリ内でタイトル編集が統一・容易
  - core.title_screen.normalize_title_to_wide。stock $CC4F で
    自タイトルを decode→当方arcade形式へ re-encode、decoder@
    $CC4F + block1@$CEA3 + block2@JP cave + $CCB6→cave。
    ★attribute($CD58)/palette/CHR は ★一切非改変=視覚同一
  - ★round-trip 自己検証: 正規化後の描画セルが元 stock と完全
    一致(clean JP 377セル一致)を確認、不一致なら中止(視覚が
    変わる改変は出さない・フォールバック禁止)
  - 全署名二重検証。clean JP/把握済stock JP のみ。改造済/別版/
    US/再適用 は安全に中止。拡張ROM(mapper66)対応(PRG offset
    不変・CHR非改変)

## v0.6.44 (2026-05-18)
- 「広域arcadeタイトル移植(JP)」を追加(タイトル移植ダイアログ)
  - ★JP ROM 専用。所有する arcade版バナー適用済 ROM から、
    広域タイトル(当方arcade形式 6502デコーダ@$CC4F + banner
    +$CBC3固定帯@$CEA3 + 山@JP cave + $CCB6 ptr→cave +
    CHR bank3 + $CD58←arcade$CCAF + 色4点)を移植
  - core.title_screen.apply_wide_arcade_titleを追加。
  - 全パッチ ★before署名二重検証・不一致は中止(フォールバック
    禁止)。region gate=JP/JP66のみ(US$9604相当をJP同番地に
    当てると破壊ゆえ US 不可)。改造済/別版/非arcade source/
    再適用 は全て安全に中止
  - 拡張ROM(mapper66)対応: PRG patch は file offset 不変、
    CHR bank3 のみ動的算出
  - ★著作権: arcade の CHR/stream/attribute は ★ユーザー所有
    ROM から抽出(ツール非埋込)。埋め込みは当方デコーダ+色
    patch定数のみ

## v0.6.43 (2026-05-18)
- Phase2 基盤(UI未接続): arcade形式 広域タイトル stream の
  codec を core に追加 (decode_arcade_stream /
  encode_arcade_stream)。$30-$FF タイル規則・$2F終端を強制
  - 実 arcade ROM ストリームで ★往復完全一致を検証
    (135 writes ⇄ 再エンコード、PPUADDR $28C5..$2997、118タイル)

## v0.6.42 (2026-05-18)
- タイトル画像 位置補正の縦方向を修正: 「上1px→下」ではなく
  ★「下1px→上」が正しい (横8px→左は変更なし)。出力/取り込み
  両方の縦符号を反転。往復は画素完全一致を維持(0/61440・CHR0)

## v0.6.41 (2026-05-18)
- タイトル画像の位置補正 (出力/入力時のみ・ROM内部ロジック不変)
  - 出力(プレビュー/画像保存): 右8px を左へ巡回 + 上1px を
    下へ巡回 → 実画面と整列(バナー/神殿が中央に来る)
  - 取り込み(PNGから取り込む): 上記の逆を適用
  - export→import の往復は画素完全一致を維持(0/61440・CHR0)
  - ※デコード/移植/CHR再構築等の内部処理は一切変更なし

## v0.6.40 (2026-05-18)
- タイトル移植ダイアログ: 「PNGから取り込む」を追加(exportの逆)
  - 画像(PNG/BMP)を 256x240 / 4階調へ自動量子化し、各マスの
    8x8 を 2bpp 化して CHR bank3 を再構築
  - ★nametable(配置)は不変方式: RLE 再圧縮しないので圧縮枠
    超過の危険なし・往復が厳密一致(画素完全一致を検証)
  - core に apply_title_image / _encode_2bpp 追加。同一タイル
    番号を使う複数マスで絵が食い違う場合は最多パターン採用
    +個数を報告(export画像をそのまま編集すれば食い違い無)
  - 検証(描画目視+画素比較): JP export→import→再export が
    画素完全一致(0/61440)・CHR変化0。US画像→JP取り込みで
    「SOLOMON'S KEY」正しく描画
  - 自由レイアウト(配置自体を画像で変える)取り込みは RLE
    エンコーダが要るため将来拡張。v1 は絵の再構築(配置不変)

## v0.6.39 (2026-05-18)
- タイトル移植ダイアログ: デフォルト表示倍率を x3 → ★x2 に変更

## v0.6.38 (2026-05-18)
- タイトル移植ダイアログ: プレビューを ★実タイトル画面の合成
  表示に変更 (従来は CHR 素タイル並びだった)
  - core に decode_title_grid 追加: $CC4F デコーダを 6502 命令
    忠実に再現 (PPUADDR の ROR キャリーまで) し nametable を復元
  - CHR bank3 上位256タイル + 暗背景4階調で 256x240 合成。
    開いた瞬間に「今読み込んでいる ROM のタイトル画面」が
    そのまま見える。移植後は結果が即プレビュー反映
  - 画像保存も実タイトル 256x240 を出力
  - 検証: JP=「ソロモンの鍵」/ US=「SOLOMON'S KEY」/ US→JP
    移植後=JP に SOLOMON'S KEY が正しく合成 (バラバラ解消) を
    描画目視で確認。各 377 セル(=144+233)完全一致
  - ※色は未確定ゆえ白黒4階調 (形は正確、色精緻化は後日)

## v0.6.37 (2026-05-18)
- 「タイトル移植 (US↔JP)」: 配置も含む完全移植に進化(解析 R198)
  - タイトル= RLE 圧縮ピースの集合と解明。デコーダ $CC4F(JP)/
    $CBA6(US) は同一エンジン → ★ピース単位 verbatim コピーで
    US↔JP 相互移植 (コードは一切改変しない)
  - 移植ピース: nametable(配置 402B) + attribute(色区分 21B) +
    CHR bank3(絵 8192B)。JP/US でピース長が完全同一ゆえ安全
  - 「バラバラになる」を解消: 絵だけでなく配置(nametable)も
    各版の対応位置へ移すため正しく表示される
  - core に _TITLE_PIECES(JP/US offset表) + transcode_title 追加。
    リージョン自動判定・CRC不要・位置+署名二重検証・長さ不一致は
    中止(フォールバック禁止)
  - ダイアログのボタンを「別ROMからタイトルを移植」に更新
  - ※色(パレット)は v1 では移植先のまま (配置・絵は移植済、
    パレット片が散在し全特定が未完のため色精緻化は後日)
  - 解析知見は asm $CC4F 注記 / 解析CHANGELOG R198 /
    memory に恒久保存 (前回のタイトルメモ紛失の再発防止)

## v0.6.36 (2026-05-18)
- 「タイトルグラフィック移植」に方針変更・簡素化(編集ツール)
  - タイトル画像= CHR bank3 (8KB) を別 ROM から ★まるごと
    取り込む単純ブロックコピーに一本化。IPS でも CRC 一致
    要求でもない (既知ブロックcopyゆえ CRC は無関係)
  - JP/US 自動判定。CHR は両版同 offset(0xE010、本アプリ拡張
    ROM では 0x16010 を動的算出)ゆえ ★US↔JP どちらの向きも可
  - 配置/色 (PRG 側 nametable/attribute/palette) は各版のまま
    = 将来拡張 (今回は画像のみ)。core に import_chr_bank3 追加
  - UI 簡素化: 旧「別ROMから差替(PRG込)」「IPS+原本差替」を
    撤去し「別ROMからタイトル画像を取り込む」1本に。位置+署名
    二重検証で両 ROM 確認、不一致は中止(フォールバック禁止)
  - プレビュー(グレー4階調)/画像保存(PNG/BMP)/取り消しは継続
  - 解析 R197: 既存タイトル系 IPS は US 版専用(JPに当てると
    タイトル描画コード破壊で起動不可)。本機能は IPS を使わず
    CHR ブロックコピーゆえ region 非依存で安全

## v0.6.35 (2026-05-18)
- 「タイトル画面 抽出/差替」を追加(編集ツール)
  - タイトルのロゴ絵(CHR bank3, 512タイル)をグレー4階調で
    プレビュー / 128x256 PNG・BMP で保存
  - 「別ROMから差し替え」: 所有する別 ROM(.nes/.zip)の
    タイトル領域(CHR bank3 + 描画/nametable/attr/palette)を複写
    (例: 所有 US 版から英語ロゴを移植)
  - 「IPS+原本ROMから差替」: 所有の未改造 ROM に .ips を当て
    そのタイトルだけ取り込む安全二段方式
  - core/title_screen.py 新規 / core/ips.py に apply_ips_patch 追加
    / ui/title_screen_dialog.py 新規
  - ★著作権配慮: 画像も IPS の中身もツールに埋め込まない。
    ユーザー所有 ROM からの抽出/差替/適用のみ
  - ★読込時の mapper66 自動拡張に対応: CHR/タイトル位置を iNES
    ヘッダから動的算出し生/拡張どちらでも正しい位置を扱う。
    raw用 IPS の現ROM直接適用(破損経路)は二段方式で排除
  - 位置+署名 二重検証 / 両ROM一致時のみ差替 / 不一致は中止
    (フォールバック禁止・JP/US 専用)。解析 R196
  - ※実機確認推奨。色精密描画・別region描画コード差替は今後

## v0.6.34 (2026-05-18)
- クリア画面メッセージ編集: 「字数」列を追加し入力中の文字数を
  リアルタイム表示(現在 / 最大)。上限到達=赤・空=灰で視認性UP

## v0.6.33 (2026-05-18)
- 「クリア画面メッセージ編集」を追加(編集ツール)
  - おめでとう画面3行(THANK YOU DANA / YOU RELEASED THIS ROOM /
    TRY NEXT ROOM)を編集。R135/R194確定の PPU script を ★同字数
    置換(安全方式)。英大文字A-Z+スペース、原作と同字数まで
    (超過不可・不足はスペース詰め)
  - core/clear_message.py 新規 + ui/clear_message_dialog.py 新規
  - 位置+署名(各行ヘッダ3byte+終端$00+現tile妥当) 二重検証。
    不一致は中止(US版/拡張別配置/改造/破損=自動安全停止、JP前提)
  - 「原作に戻す」/OK/キャンセル/適用。ヘッダ・終端は不変で安全

## v0.6.32 (2026-05-18)
- Page面対応ラベル訂正(ユーザー100%確定): skc_config.xml の
  level_meta_item を **面52=Page of Space / 面53=Page of Time** に
  (旧ラベルは逆だった。JP/US66 両方)。page_pos/HackDialogの呼称
  (52=空間/53=時)は元から正しく整合。asm/解析CHANGELOG R190 記録

## v0.6.31 (2026-05-18)
- ゲーム挙動改造に「呪文(Page)の出現位置」を追加
  - 52面 空間の呪文 / 53面 時の呪文 を単純X/Yで変更(ROM直接書換)
  - core/page_pos.py 新規: R188/R189確定の特殊処理スクリプト
    LDX #$XX オペランド (file 0x35D9/0x35DD) を書換
  - 位置+シグネチャ ダブル検証(SIG_OFF基準、item$21=$21含む
    不変パターン)。不一致は例外で中止(フォールバック禁止)。
    US/US66 はoffset未トレース→シグネチャ不一致で自動無効化
  - 範囲ガード(grid内 X0-15/Y0-12)。原作値=52面(7,2)/53面(7,9)
  - キャンバスのPageマーカードラッグ(v0.6.30)と同一ROM箇所、併用可

## v0.6.30 (2026-05-18)
- Page of Time/Space (item$21) を決め打ち→★実ROM読みに変更
  - skc_config.xml level_meta_item no=12/13 (JP): position直書きを
    やめ offset 化。$B5C9=file 0x35d9(面52)/$B5CD=file 0x35dd
    (面53)=R188特殊処理スクリプトの LDX #$XX オペランドを読む
  - 効果: 改造ROMでも正しい位置を表示(ハードコード排除)＋
    rom_offset≥0 になり★ドラッグ移動可(書戻し=LDXオペランド
    書換=実機R188機構で実際に面内Page位置が動く。round-trip検証済)
  - US/US66 は当該offset未トレースゆえ従来 position 据置
    (既存 Solomon's seal meta と同じ region 分割方式・JP優先)

## v0.6.29 (2026-05-18)
- ★アイテム名を単一ソース化 (2重管理禁止) — 0x21修正が全UIに
  伝播しなかった根本原因を解消
  - 正本 = skc_config.xml item_definitions (cfg.item_desc) のみ
  - element_picker.ITEMS_LIST / stats_dialog.IMPORTANT_ITEMS を
    ★コード一覧のみ(どれを/順序)に変更。名前は保持しない
  - 名前解決は item_name(code, config) 1関数に集約 (ピッカー本体/
    ボーナスパネル/レベル設定数字キー/全レベル統計 すべて経由)
  - 効果: 今後アイテム名は skc_config.xml 1箇所修正で全UI反映
  - 回帰確認: ITEMS_LIST全46件が item_desc と一致・敵0x21無事
  - 注: ENEMIES_LIST(敵名)は同型の2重管理だが今回スコープ外(別途)

## v0.6.28 (2026-05-18)
- アイテム名訂正(ユーザー確定): skc_config.xml の `0x21` を
  "Egyptian Head" → **"Page of Time / Space"**(0x31 は
  "Egyptian Head" のまま確定)。config自身の level_meta_item
  (Page of Time/Space を面52/53に配置, animation=30)とも整合
  - 注: stats_dialog.py IMPORTANT_ITEMS の 0x21 ハードコードは
    別系統で未変更(指示「ここだけ・まず」に従い flag のみ)

## v0.6.27 (2026-05-18)
- キャンバスのホバー情報(ステータスバー)に★アイテム番号を表示
  - `アイテム:0xXX 名前[タグ]` 形式。base コード(item_desc準拠)を併記
  - 隠し/ブロック内など flag 付きは `0xXX(raw 0xYY)` で実バイトも併記

## v0.6.26 (2026-05-18)
- 左パネルを2列化(縦長を圧縮)
  - ファイル: 「改造ROMとして保存」「IPSパッチ出力」を横2列に
  - 編集ツール: 7ボタン+レベルクリアを 4行×2列グリッドに
    (列幅均等)。機能・接続・ツールチップは不変

## v0.6.25 (2026-05-18)
- ★暗闇面バグ修正: 妖精取得音($0F)が無限ループする副作用を解消
  - 原因: room_flags の ROOMFLAGS/暗闇フェーズカウンタが $0460/$0461
    に在ったが、ここはサウンドドライバ ch0 状態RAM($0456+$10*N の
    ch0 +$0A/+$0B)。暗闇面で毎NMI $0461 を踏み、数フレーム継続する
    妖精音の再生状態を壊して終われなくなっていた(実機 PC=$F2F7 で
    サウンドが $0461 を書込むのを確認)
  - 対策: ROOMFLAGS=$0778 / 暗闇フェーズ=$0779 へ移設(LOADER/
    MAGICGATE/DOORPREDRAW/DARK 全cave)。$0778/$0779 は entity 21slot
    終端 $0722 の後ろにある安全域を使う
  - 隠し扉/B火球禁止/A換石禁止/暗闇 すべて同一移設で継続動作

## v0.6.24 (2026-05-18)
- 全レベル統計に3列追加: 「タイル」(tileset_no)/「時間減少」
  (time_decrease_rate)/「敵寿命」(spawn_enemy_lifetime)。
  レベル設定パネルと同一データ源、敵数の右に配置・中央寄せ
- 内部改善: 列インデックスをCOLUMNSのヘッダ名から解決する方式に
  変更(列追加・並べ替えで他処理が壊れないよう堅牢化)

## v0.6.23 (2026-05-18)
- 全レベル統計「敵種類」列を2列に分離 (すっきり表示)
  - 「配置敵」= 面に配置された敵 (実数 ×N)
  - 「ミラー敵」= デーモンミラーから出る敵 (種類のみ presence=1、
    無スケジュールのミラーは除外)
  - CSV出力も配置敵/ミラー敵を別カラムで出力

## v0.6.22 (2026-05-18)
- 全レベル統計「敵種類」: デーモンミラーから出る敵も集計対象に
  - 配置敵に加え、各ミラーの敵セットを読み出して加算
  - 出現数は不明なため presence=1 (基底名で重複排除し各 +1)
  - ★スケジュール(出現タイミング)に1つもチェックが無いミラーは
    実際には出ないので除外 (先頭2tickのゲーム無視分を考慮)
  - 読出経路は main_window._sync_enemy_codes_from_rom /
    MirrorDialog._read_schedule と同一 (m66 layout、rom を受領)

## v0.6.21 (2026-05-18)
- 全レベル統計「敵種類」: 方向/速度違いを同一モンスターとして合算
  - グループキー = enemy_desc の基底名(括弧 "(...)" 以降と末尾
    " #N" を除去)。代表 element_no のスプライトを表示し ×N で合計
  - 例: `Gargoyle(right)×4 / Gargoyle(left)×4` → `Gargoyle×8`

## v0.6.20 (2026-05-18)
- 全レベル統計
  - 「重要アイテム」から Star Coin/Star Coin(W)/Bell/Diamond青/
    Diamond橙/Scroll の6件を除外 (13件に整理)
  - 「敵種類」列を新設: 出現する敵をスプライト表示(個数 ×N、
    hoverで名前内訳、CSV出力対応)。element_picker と同一ルート
    (config.enemy_map → TileRenderer)を流用

## v0.6.19 (2026-05-18)
- 全レベル統計の列構成見直し
  - 座標表示を全廃 (鍵・星座は名前/状態のみ)
  - ミラー列を撤去
  - 部屋フラグ4列を追加: A禁止 / B禁止 / 暗闇 / 隠し扉
    (lv.room_flags を参照、ONは ● + 薄い着色で一目表示)

## v0.6.18 (2026-05-18)
- 全レベル統計の表示改善
  - 「…」省略を全廃 (ElideNone)。鍵/ミラー/星座などを全文表示
    (改行を空白区切りの1行に統一して全部見えるように)
  - 列幅を保存/復元 (config: stats_dlg_col_w)。ヘッダで自由に
    リサイズ可、次回起動時に復元
  - ミラー列の「同位置かどうか」判定(●同位置マーク/着色)を撤去。
    位置を `m1 / m2` でそのまま表示

## v0.6.17 (2026-05-18)
- 全レベル統計の改善
  - ウィンドウのサイズ/位置を復元 (HackDialog と同一方式、
    config: stats_dlg_x/y/w/h)
  - 「重要アイテム」列はスプライトのみ表示に変更(文字を撤去)。
    内訳テキストは hover ツールチップ + CSV出力で保持(情報落ち無し)

## v0.6.16 (2026-05-18)
- 全レベル統計: 「重要アイテム」列をスプライト表示化
  - element_picker と同一の実証ルート (config.item_map →
    TileRenderer.get_tile_image) を流用してアイコン描画
  - 各アイテムを横並びサムネイル帯で表示。状態を枠色で表現
    (隠し=黄/ブロック内=緑/通常のみ=灰)、複数個は ×N
  - 元のテキスト内訳はツールチップ＋CSV出力用に保持(情報落ち無し)
  - 列幅はスプライト帯の最大幅に自動追従

## v0.6.15 (2026-05-18)
- デモ操作編集に編集上の注記を追加(簡潔): 最後に死ぬ動きは不要、
  34ステップ使い切りでデモ終了(ダイアログ説明)

## v0.6.14 (2026-05-18)
- デモ操作編集 (attract mode 入力データ) を追加
  - 「デモ操作編集...」ボタン → 34ステップ固定の表で各ステップの
    入力(A/B/上下左右チェック)＋継続フレーム数を編集
  - 録画不要・原作の記述方式そのまま手入力。原作値を初期表示、
    「原作に戻す」で完全復元
  - $CF9A(wait)/$CFBC(joy) を同サイズ上書き(cave不要)。実効フレーム
    =wait+1 のため UI「Nフレーム」→ wait=N-1 で書込(asm R183)
  - Start/Selectはデモ中断判定のため選択不可(書込時$30強制除去)
  - core/demo_input.py 新規: 位置+署名($CBEC 26B)二重検証、不一致は
    DemoInputError で中止。デモ領域は US 再配置ゾーン=JP専用
    (US は署名不一致で安全中止)。標準/拡張ROM共通(自動テスト確認)

## v0.6.13 (2026-05-18)
- ゲーム挙動改造ダイアログのサイズ/位置を記憶・復元
  - 閉じる時に サイズ/位置 を config に保存、次回開いた時に復元
  - 保存はコンフィグファイル (config/magatu_skc_config.json、
    レジストリ不使用)。hack_dlg_x/y/w/h を DEFAULT_CONFIG に追加
  - done() で OK/キャンセル/Esc/×閉じ すべての経路をカバー

## v0.6.12 (2026-05-18)
- ゲーム挙動改造ダイアログを 2列グリッド + 縦スクロール化
  - 項目増で縦長になり画面に収まらない問題を解消
  - グループ群を2列(均等)・縦スクロール領域に配置。冒頭説明は上、
    「オリジナル値に戻す」/OK/キャンセル/適用 は下に常時固定
  - 呼び出し側(各 layout.addWidget)は非改変、収集→組立方式で最小差分
  - 既定サイズ 940x720

## v0.6.11 (2026-05-17)
- 暗闇面 (明滅) を Room Flag Table に統合
  - レベル設定パネルに「この画面を暗闇にする (明滅・敵とDanaのみ)」
    追加 = $0428 部屋別 ON (bit3=BIT_DARK)。XML永続化済
  - ゲーム挙動改造に「暗闇テンポ (全体共通)」明/暗フレーム設定追加
    (60フレ≒1秒、既定 明30/暗180≒0.5s見え3s暗、必ず明から開始)
  - 実装: NMI PPUMASK 書込点 $8055 を独立フック (LOADER非改変)。
    DARK cave $BC80(53B): ROOMFLAGS bit3 & Dana実プレイ($057F>=$C0)
    の時だけ位相カウンタ $0461 を進め、テンポ $BCD0/$BCD1 で
    明($0301)/暗(PPUMASK bit3クリア=BG-off)を明滅。非該当は
    $0461=0 リセット→暗闇面は必ず明から。タイトル/紹介/クリア/
    非暗闇面は通常表示
  - $0461 は $0460(確定空き)隣接・asm 静的参照ゼロで確定使用
  - 位置+署名($804B)二重検証、暗闇面なし時は $8055 非フック
    (NMI完全無影響)。gap_fix と双方向 非破壊 共存(自動テスト確認)
  - core/room_flags.py 拡張 (BIT_DARK/DARK_CAVE/get_tempo/
    set_tempo)、main_window/hack_dialog UI、標準/拡張ROM共通

## v0.6.10 (2026-05-17)
- ゲーム挙動改造に「原作バグ回避: 落下中の横穴侵入を安定化」を追加
  - ソロモンの鍵 積年の謎「落下中に左/右で横穴に入れる/入れないが
    運任せ」を機構解明(Mesen実機解析 asm R182)→回避。サブピクセル
    位相依存の col bit0(左)/bit1(右)を、横穴開口がある時だけ
    クリアして除去。通常の壁・歩行・着地は原作どおり(副作用なし、
    実機v8で確認済・左右対応・ソフトロック無し)
  - core/gap_fix.py 新規: 位置+署名($877F)二重検証、cave $C000
    (136B、room_flags予約帯内の非使用中間帯)、apply/restore、
    不一致は GapFixError で中止(フォールバック禁止)
  - room_flags._verify を更新し gap_fix cave span を許容→両機能を
    同時適用可能(拡張ROM・双方向で非破壊を自動テスト確認)
  - ゲーム挙動改造ダイアログに ON/OFF チェックボックス追加
  - 標準/拡張ROM共通(cave は bank0 verbatim 領域 file 0x4010)

## v0.6.9 (2026-05-17)
- 敵ドロップ編集: 効果名をユーザー実機知識で確定 + 未確定値を検証用に開放
  - $02 = 「マガドラの壺」/ $03 = 「ライラックの鐘」(ユーザー一次情報)
  - $01 / $07 を「未確定$01/$07」として選択可能に (実機確認用。
    $A373/$A41D の <8値経路に乗るのでテスト可。推測命名はしない)

## v0.6.8 (2026-05-17)
- 敵ドロップ効果表エディタ (グローバル) を新設
  - 「敵ドロップ編集...」ボタン → ダイアログで $C293 (10行×8枠) を
    効果コンボで編集。確率(枠数/8)と「その行を使う敵」を各行表示
  - 設定可能値は実機確定の14効果のみ (なし/特殊/$042B++/ファイア
    距離+/妖精予約/1UP/スコア+10〜+2000)。★$06=1UP であって鍵では
    ない (拾得AIのドロップ効果値であり通常item IDではない=R180)
  - 行は複数の敵グループで共有 (Neul各系/Saramandor+Dragon等)。
    UIに使用敵を明示
  - core/enemy_drop.py 新設: 位置+署名($C248/$C20F)ダブル検証、
    不一致/不正値は EnemyDropError で中止 (フォールバック禁止)、
    「原作に戻す」で完全復元。
  - ROM直書き(既存挙動改造hackと同様、project非依存)。標準/拡張
    ROM共通 (table は bank0 verbatim 領域 file 0x4288/0x42A3)
  - 通常アイテムを落とさせるには別途 code-cave 変換層が必要(非対応)

## v0.6.7 (2026-05-17)
- アイテムピッカーの不足を解消
  - skc_config.xml <item_definitions> を正本に自前抽出した「配置可能」
    46件へ ITEMS_LIST を拡張 (旧36件)。追加=$05 Demon Mirror /
    $09・$0A・$0B・$0D・$0F modifiable系 / $21 Egyptian Head /
    $37 Mini-Dana / $38・$39 Tecmo Bunny の10件
  - glitch/garbage/Nothing 18件は配置で壊れ得るため従来どおり非表示
  - カテゴリ追加なし・既存 _populate_all パイプラインそのまま (UX非破壊)

## v0.6.6 (2026-05-17)
- Room Flag Table 拡張: A換石(石作成)禁止 (bit7) を追加
  - レベル設定パネルに「この画面でA換石(石作成)禁止」を追加。
    Bファイア禁止とは独立トグル (A+B 任意の組合せ可)
  - MAGICGATE cave 拡張 (21B→34B): SE id $08 で判別、
    bit2&$08==$13(B火球) / bit7&$08==$11(A換石) を各々却下
  - cave 再配置: MAGICGATE 34B 化に伴い DOORPREDRAW を $BC50 へ、
    $91CC フックを "20 50 BC" に変更 (非重複を自動検証)
  - ※A禁止は階段が作れず進行不能になり得る独立option (tooltip警告)
  - 自己テスト: A/B/A+B 全組合せで apply・冪等・原作復元 OK

## v0.6.5 (2026-05-17)
- Room Flag Table 拡張 — ステップ2: 隠し扉 (bit0) を統合
  - レベル設定パネルに「この画面の扉を隠す (石を壊すと出現)」を追加
  - エディタの扉位置(fixed_door_pos)をそのまま使用。扉を動かせば追従
  - 統合cave化: $9071 LOADER を拡張し、面ロード後に
    DoorCellTable[room] が指す扉マス($0304+扉位置byte)へ隠しフラグ
    $40 を付与。$91CC(扉先行描画=R179確定)を新フックし、隠し扉の
    部屋は開始前画面の扉インジケータを抑止
  - cave 再配置 (LOADER 32B→$BBE0 / MAGICGATE→$BC20 /
    DOORPREDRAW→$BC40 / DoorCellTable→$C180 / RoomFlagTable→$C1C0)。
    全て bank0 空き $BBDE-$C1FF 内、非重複を自動検証
  - 原作復元はフック3点($9071/$8326/$91CC)のみ戻す死にコード方式
  - $91C1 署名検証を追加 (位置+署名トリプル検証)
  - 実機実証済みの隠し扉機構を部屋別へ一般化

## v0.6.4 (2026-05-17)
- Room Flag Table 拡張 (画面ごとの挙動改造) を本編に統合 — ステップ1
  - レベル設定パネルに「この画面でBファイア禁止 (A換石は可)」を追加
  - 部屋ごと(レベル単位)に挙動フラグを設定。原作 level data は非破壊
  - ROM保存/テストプレイ時、bank0 のコードケーブへ自動注入
    ($9071 ローダフック + $C1C0 RoomFlagTable 64B + $0460 ROOMFLAGS
     + $8326 MAGICGATE。bit2=B火球禁止、A換石は常に可)
  - 位置+署名ダブル検証付き、不一致時 RoomFlagError で保存中止
    (フォールバック禁止)。全画面OFF=原作フック復元
  - 標準ROM/拡張ROM(mapper66)共通。expander が bank0 を verbatim
    コピーするため file offset 不変
  - プロジェクトXMLに room_flags 属性を永続化 (後方互換: 既定0)
  - core/room_flags.py 新規、level.py / xml_io.py / saver.py /
    ui/main_window.py 拡張
  - 隠し扉(bit0)は同 RoomFlagTable のステップ2で実装予定

## v0.6.3 (2026-05-16)
- 設定画面(F9)にフォント設定を実装
  - フォントファミリー(QFontComboBox)+「既定に戻す」ボタン
  - 太字(チェックボックス)
  - 既存のフォントサイズと合わせ MAGATU標準3項目が完成
  - 空ファミリー/サイズ0=アプリ標準。アプリ全体に即時反映
  - settings_dialog.py / main_window._apply_font_size 拡張
  - 「今後追加予定」からフォント設定を削除

## v0.6.2 (2026-05-16)
- ゲーム挙動改造に「デモプレイのステージ」追加
  - タイトル放置で流れるデモ(既定3面)を任意の面に変更
  - 3面以上のみ(内部のX連鎖制約。$CBC0 LDX operandを共用)
  - stage = operand + 2。OFFで3面復元、冪等
  - ROM解析(asm Round 113/135)で確定。デモコードはJP/US再配置
    ゾーン($C400-$CFFF)のため位置はJP/US個別特定
    (JP file 0x4BD1 / US 0x4B20)。位置+シグネチャ ダブル検証
  - core/demo_stage_hack.py 新規、hack_dialog に項目追加
  - 副作用: $0433/$80/残機/$0452 連動するがデモ(attract)では無害

## v0.6.1 (2026-05-16)
- ゲーム挙動改造に「クリア画面のキャラ」追加
  - おめでとう画面(THANK YOU DANA)の左右2体を差し替え
  - プリセット: Fairy(原作)/Golem/Gargoyle速/Gargoyle遅/
    Demonhead/Saramandor (全て beh=/usr/bin/bash0 速度ゼロ=落下せず置物表示)
  - ROM解析(Round 110/128/131/132)で確定。type=0x0FBC /
    state base=0x0F6D。位置+シグネチャ ダブル検証、改造ROM再適用可
  - core/clearscreen_hack.py 新規、hack_dialog に項目追加


## v0.6.0 (2026-05-16)
- スプライトビューアに「★ROMフレームデータ」モード追加(既定)
  - 検証済み $D0E8 機構(group表→metadata→frame data 3byte)で
    ROMから全1391フレームを直接抽出・16x16描画
  - NES 8x16スプライト方式(left=tile1/right=tile2)で本来の姿
  - CHRバンク/SPRパレット(attr&3自動)/拡大 切替
  - skc_config(tile_def約105)に依存しない=editor用configを
    壊さずビューアの抜けを構造的に解消(主人公死亡/しゃがみ等
    従来欠落フレームも表示)
  - ラベル gGGsSSfF (group/state/frame)
  - 検証用スタンドアロン 解析資料/gen_sprite_sample.py も同梱
  - キャラクターモードに「★ROM由来 全キャラ(組立16x16)」カテゴリ
    追加(既定): 全1391キャラを$D0E8由来で組み立て、CHRバンク自動
    補正+group意味名(妖精/Demonhead/Saramandor等)付きで表示。
    editor用 skc_config.xml は不変=編集機能無傷で組立表示を全網羅
  - [要Mesen] attr の palette/flip bit 正確な意味は未確定


## v0.5.0 (2026-05-16)
- スプライト/キャラクタービューア追加（読込専用）
  - **キャラクターモード**: skc_config のメタタイル定義で組み立てた
    実キャラを名前付き一覧（アイテム/敵/メタ/全メタタイル）。
    生8x8タイルでなく組み上がった姿で表示。tileset/拡大切替
  - **★全網羅カテゴリ**: 全 tile_def(105) × 全 tileset(15) = 1575枚
    をフィルタ無しで列挙（curated map に載らない物も漏れなく表示）。
    既定カテゴリに設定
  - tileset「全部(網羅)」+「背景不透明」追加: 透過/誤パレットで
    見えず抜けて見える問題を解消（不透明灰背景で必ず可視化）
  - **生CHRタイルモード**: CHR-ROM の 8x8 を素のまま一覧
    （バンク・パレット・拡大・グリッド線、上級者向け）
  - iNESヘッダからCHR位置自動算出（JP: 0x8010 / 2048タイル / 4バンク）
  - 拡張ROM(m66)はヘッダ不正時に残り全域をCHR扱いでフォールバック
  - 編集機能の左ペインに「スプライトビューア...」ボタン追加
  - ROM未読込時は無効、読込で有効化

## v0.4.6 (2026-05-16)
- ゴーレムグループに「歩行速度」「特攻速度」倍率を追加 (0.5〜3.0x)
  - Mesen実機ブレークポイント解析で真のレバーを特定（静的解析3連敗後）
  - 速度テーブル本体 $DB99 は JP/US 同一 file offset（再配置されない）
  - s1歩行 $DBC8/$DBCA, s1特攻 $DBD4/$DBD6, s0歩行 $DBD0/$DBD2
  - 歩行倍率はs0+s1両方、特攻倍率はs1に適用。1.0xで原作厳密復元
  - 実効上限±2.0px/f (V*8/256符号拡張の限界)
  - $40 (速度更新スキップマーカー) を逆引きから除外（敵停止バグ回避）
- 新モジュール `core/golem_speed.py`: 位置+シグネチャ ダブル検証
  - $DB99先頭8B シグネチャでJP/US判定（同一offset・一意確認済）
  - 速度→バイト逆引きは全256値スキャンで実効速度最近接（$40除外）
- 教訓: 過去3連敗の真因はGolem s0(type$70-73)を弄っていたが検証面のGolemは
  s1(type$74)で別speed-indexだったこと。Mesen実機解析(ユーザー操作)で解決

## v0.4.5 (2026-05-16)
- ゲーム挙動改造ダイアログに「ゴーレム」グループ追加
  - 「キビキビ動作」ON/OFFチェックボックス1個
  - ON=State遷移待ち4箇所($AD33/$AD41/$AD90/$AE0A)を$01に、OFF=原作復元
  - 実機検証で正常動作・劇的に機敏を確認
- 新モジュール `core/golem_hack.py`: 位置+シグネチャ ダブル検証
  - AI_GOLEM $AD11 dispatch シグネチャ(待ちバイト不含)でJP/US自動判定
  - US=JP+$140。検証失敗時 GolemHackError でパッチ中止
- 【重要】Golem 移動速度は $AD5F/$AD95/$AE0F の #$01 が速度値兼behaviorビット
  マスクのため変更不可($02で無限ループ)。ROMバイト検証で確定。
  速度UPは別アプローチ(speed-index表/速度表)が必要、別途調整予定

## v0.4.4 (2026-05-16)
- ゲーム挙動改造ダイアログに「パネルモンスター発射間隔」を追加
  - 秒指定スピンボックス (0.8〜4.5秒、0.1刻み) + ON/OFFチェック
  - OFFで原作(約3.47秒)復元
  - ROMバイト検証で確定: 周期=(しきい値$A57A+発射ディレイ$10)/60秒
  - 設定式 しきい値=round(秒*60)-16、安全下限$20でclamp
- 新モジュール `core/panel_monster_hack.py`: 位置+シグネチャ ダブル検証
  - threshold直後の安定領域でJP/US自動判定 (US=JP+$140, JSR先差で別sig)
  - 検証失敗時 PanelMonsterHackError でパッチ中止 (フォールバック禁止)
  - Panel Monster ($24-$27, AI $A54C) 専用、他AI非影響

## v0.4.3 (2026-05-16)
- サラマンダー火球化に「ダーナ被弾」を追加（実機検証で完成）
  - ROMバイト検証: ダーナ被弾判定 SUB_81B1 は status & $03 != 0 を除外
  - status $C6→$C0 (file 0x311A/$B10A): $C0&$03=0 で被弾有効化
  - $B0AC ORA #$02 → ORA #$00 (file 0x30BD/$B0AD): bit1再セット抑制で被弾を維持
  - これらを火球化ON時に必須セット、OFFで原作復元
  - US offset: status JP+$140=0x325A, ora02 JP+$140=0x31FD
- 【バグ修正】検証シグネチャ sig1 が status バイトを含んでいた問題
  - 火球化(status→$C0)するとsig1不一致でdetect_region失敗→復元不能だった
  - 改造対象を一切含まない安定領域へ変更 (JP $B0FE / US 同+$140、一意確認済)
- 確定改造7バイト: type$20 / dir$04 / despawn NOP / status$C0 / ORA#$00 / X$50 / Y$10

## v0.4.2 (2026-05-15)
- 【重要修正】サラマンダー改造の X/Y 距離しきい値が逆だったのを訂正
  - SUB_A134 実コード検証で sub-slot[4]=Y距離 / sub-slot[5]=X距離 と判明
    (解析資料 Round 67 のコメントが X/Y 逆で誤っていた → asm も訂正)
  - SUB_B1E9 しきい値A ($B1F3 file 0x3203) = X距離ゲート (原作$14)
  - SUB_B1E9 しきい値B ($B1FF file 0x320F) = Y距離ゲート (原作$10)
  - `salamander_hack.py` の xdist/ydist offset を入替修正 (JP/US 両方)
  - 発射距離プリセット刷新: X=原作/4/5/6マス、Y=同高さ限定/やや甘い
  - 誤った $40 禁止チェック削除 (SUB_B1E9 に特別禁止値なし)
  - ⚠ SUB_B1E9 は Dragon State5 ($A669) も共有 → 距離変更は Dragon にも影響
    (サラマンダー専用化は専用routine差替が必要、将来課題)

## v0.4.1 (2026-05-15)
- ゲーム挙動改造ダイアログに「サラマンダー強化（火球発射化）」を追加
  - 火球発射化 ON/OFF（口から1マス火 → 水平に火球$20を発射）
  - 強制消滅除去 ON/OFF（弾が壁まで飛び続ける / 時間で消滅）
  - 発射距離X（原作=隣接 / 遠距離=最大約5マス）※非線形のため2択
  - 発射許容Y（標準 / 緩め）
  - OFF で全バイト原作復元
- 新モジュール `core/salamander_hack.py`: 位置 + シグネチャ ダブル検証方式
  - 安定シグネチャ2点（spawn部 $B107 + SUB_B1E9 $B1E9）で JP/US 自動判定
  - US版はサラマンダーが再配置ゾーン (JP +$140) のため別オフセットを内蔵
  - 検証失敗時は SalamanderHackError でパッチ中止（フォールバック禁止）
  - 実機検証済: type$04→$20 / 方向$05→$04 / despawn JSR→NOP / X距離 $10↔$FF

## v0.4.0 (2026-05-15)
- ゲーム挙動改造ダイアログに「ダーナ歩行速度」を追加
  - プリセット: 0.5x / 1.0x(原作) / 1.25x / 1.5x / 2.0x / 2.5x / 3.0x
  - 地上歩行・空中横移動の左右4方向すべてに適用 ($DBA6/$DBA8/$DBAA/$DBAC)
  - 原作 1.0x = 0.75 px/frame (実機検証済 R107)
- 新モジュール `core/walk_speed.py`: 位置 + シグネチャ ダブル検証方式
  - 速度テーブル先頭 ($DB99) の13バイトシグネチャで改造ROM/異版/破損を検出
  - 検証失敗時は WalkSpeedError でパッチ中止 (フォールバック禁止)
  - $40 (速度更新スキップマーカー) を使用値から除外
  - JP/US 共通アドレス (ゲーム本編領域なので両リージョン完全同一)

## v0.3.3 (2026-05-15)
- 対応リージョンを JP / US のみに整理（EU版は完全に非対応として明示）
  - `region.py`: EU専用エラーパス削除、対応外ROMは統一エラーメッセージへ
  - `special_process.py`: EU未確認コメント削除
  - `skc_config.xml`: `<region name="EU">` 削除、EU専用 offset 行削除、複合 region 属性から `EU` を除去（22箇所）
  - XML 構文・JP/US の参照は無変更（XML パース確認済み）

## v0.3.2 (2026-05-13)
- パレット編集ダイアログ: BGパレット(#0〜#3)にもプレビューアイコンを追加
  - BG#0=白壁, BG#1=茶ブロック, BG#2=ファイアジャー青, BG#3=ファイアジャーオレンジ
  - パレット色変更時にBGアイコンもリアルタイム再描画

## v0.3.1 (2026-05-13)
- ソロモンの紋章（六芒星）をキャンバス上でCtrl+ドラッグ移動可能に
  - MetaItemDefにrom_offsetを保持、ドラッグ終了時にROMへ書き戻し
  - 位置はROMから動的に読み込み（ステージ割り当ては固定）
- バグ修正: PNG埋め込みステージデータにミラー敵セットの実データが含まれていなかった
  - DemonMirrorにenemy_codesフィールド追加
  - エクスポート時: ROMからenemy_codesを取得してXMLに含める
  - インポート時: enemy_codesをDemonMirrorに復元しROMに書き戻す
  - これにより他のステージのミラー設定をPNG経由でインポートした時に敵セットも正しく反映される
- バグ修正: JP版拡張ROM(JP66)でソロモンの紋章がキャンバスに表示されなかった
  - config_loader._load_meta_items() のregionフィルタにbase_regionフォールバックが無かった

## v0.3.0 (2026-05-12)
- ピッカーを4カテゴリに分割: ブロック / キャラ / アイテム / モンスター
  - カテゴリラベル付きで視認性向上
  - スクロールエリア内に縦配置
  - カテゴリ間の排他選択（1つ選ぶと他カテゴリの選択が解除）
- ミラーのキャンバス表示を改善: 数字テキスト → 色枠（1=赤, 2=青）

## v0.2.9 (2026-05-12)
- ミラーダイアログ: ドロップスケジュール先頭2tickをグレーアウト
  - ゲーム側6502コードの初期化処理で先頭2tickが「処理済み」判定されスキップされる仕様
  - チェックボックスを無効化し、ツールチップで理由を表示
- ミラーダイアログから敵セット編集コードを完全削除（メインウィンドウに一本化）
- 特殊処理ビューアのサブルーチン注釈を追加・修正
  - $B4F4(JP)/$B924(US): 敵リスト1体目 落下死→妖精出現フラグ有効化
  - $B500(JP)/$B930(US): マイティボンジャック出現処理
  - 全既存エントリの説明文を改善

## v0.2.8 (2026-05-12)
- ゲーム挙動改造ダイアログの整理
  - BESK方式ステージセレクトを廃止（簡易3バイト方式に統一）
  - 開始ライフポイント変更機能を削除
- パレット編集の強化
  - パレットプリセット保存/読込機能（JSON形式）
  - スプライトパレットにキャラクター名ラベル追加（主人公/サラマンダー/ガーゴイル/ゴブリン）
  - スプライトパレット行にキャラクタープレビューアイコン表示
- hack_data.pyからBESK関連コード・開始ライフ関連を削除

## v0.2.7 (2026-05-12)
- ボーナスステージ(Level 51)テーブル編集ダイアログを実装（BESK hidden.cs互換）
  - 出現アイテム16種をコンボボックスで編集（アイコン付き）
  - 出現位置32箇所をX/Y座標スピンボックスで編集
  - OK/キャンセル/適用ボタン、リージョン別ROMアドレス対応
  - Level 51表示時のみ「ボーナスステージ編集...」ボタンが有効化
- Level 51表示時、ピッカー下部をボーナスアイテム16種パネルに切替
  - アイテムピッカーからD&Dでアイテムを直接入れ替え可能
  - 変更は即座にROMに反映、キャンバスも再描画
  - 他のレベルでは通常のお気に入りバーを表示

## v0.2.6 (2026-05-11)
- 星座とタイルセットの排他制御を実装（BESK互換）
  - 星座パネルがある場合: タイルセットは星座グループに強制決定、spinboxをグレーアウト
  - 星座パネルなしの場合: タイルセットは自由選択可
  - 星座選択時にタイルセットを連動更新（グループ0=tileset0, グループ1=tileset1, グループ2=tileset2）
  - タイルセット変更時の星座グループ連動も実装（グループ内相対位置保持）

## v0.2.5 (2026-05-11)
- EU版ROM非対応を明確化
  - EU版を読み込んだ場合「ヨーロッパ版は非対応です」とエラー表示
  - リージョン判定を US / JP / US66(拡張) の3種に限定
  - EU関連のROMオフセット・パッチアドレスを削除

## v0.2.4 (2026-05-11)
- ROM拡張(mapper 66)のリージョン対応（JP版修正）
  - `change_mapper()` のパッチアドレスがUS版ハードコードだった問題を修正
  - JP版: NOP x3 → offset 6162、サブルーチン注入 → offset 6534（US比 delta -125）
  - サブルーチン1内の絶対アドレス($9A00)をリージョン別に動的計算
  - EU版は未対応（パッチアドレス特定が必要）

## v0.2.3 (2026-05-11)
- ボーナスステージ(51面)のアイテム表示に対応
  - ROM内の専用テーブル(位置32箇所 + アイテム16種)を読み込みキャンバスに描画
  - ROM 0x1955: アイテム出現位置テーブル(32byte)
  - ROM 0x1975: アイテムIDリスト(16byte)
  - サムネイル・PNGエクスポートにも反映

## v0.2.2 (2026-05-11)
- レベルビューに装飾ボーダー追加（上・下・左に壊せない白ブロック）
  - 実機と同様にレベルがブロック枠で囲まれた見た目に
  - 右辺は既存の16列目が担当、3辺を追加
  - ボーダー部分は編集不可（クリック・ホバー無反応）

## v0.2.1 (2026-05-11)
- Pキーでテストプレイ（エミュレータ起動）のショートカット追加
- F1キーマップにPキーの説明を追加
- XML・PNG出力先を `exports/ROM名_YYYYMMDD_HHMMSS/` フォルダに変更
  - XML出力時のファイルダイアログを廃止（即座に出力）
  - 出力先パスをスクリプト基準の絶対パスに修正（CWD依存を排除）
- F9設定画面にフォントサイズ設定を追加（0=デフォルト、「適用」で即時反映）
- レベル選択スピンボックスの上下矢印をサムネイル順に合わせて反転
- IPS出力: 原本ROM（市販吸出し）を毎回選択する方式に変更
  - 改造ROM→改造ROMの無意味な差分ではなく、ピュアな原本からの完全な差分を生成

## v0.2.0 (2026-05-11) ★ マイルストーン

- **コア機能完成版として v0.2.0 を確定**
- v0.1.x からの累積成果:
  - レベル編集（タイル/敵/アイテム/メタ/ミラー/星座）
  - ROM自動拡張 (mapper 3 → mapper 66)
  - パレット編集（NES 64色ピッカー）
  - 特殊処理ビューワ + Canvas上のマーカー表示（壊せる隠しブロック・トリガー・MBJ）
  - 全53レベルのSP解析（条件付きブロック・テーブル参照・分岐対応）
  - item_bitmasks サポート（Lv20 Bat Symbol・Lv30 Opal の一括配置）
  - noslowフラグ解析完了（ピッカー登録済み）
  - サムネイル付きレベル選択・お気に入りバー・パレット編集
  - テストプレイ連携・IPS出力
  - 既存改造ROM 10作品で動作検証済
  - BROWN_WHITE廃止整理（実機で意味なしと確定）
- **検証済み互換性**: 既存改造ROM全10作品で正常動作

### 今回の変更
- バージョン 0.1.99 → 0.2.0

## v0.1.99 (2026-05-11)

### 仕様変更（廃止）
- **BROWN_WHITE (壊せる白ブロック) を廃止**
  - ユーザー検証により実機で「壊せない白壁」と完全に同じ挙動と判明
  - 両ビットONでも brown bit による破壊判定は発動しない（白bitが優先）→ 冗長表現
  - 10作品の既存改造ROMでも使用されていない死にスペック
- **変更内容**
  - `Level._walls_to_wall_type`: 両ビットON時 BROWN_WHITE → WHITE へ正規化
  - `LevelRenderer`: 青フィルター除去、WHITE と同等に描画
  - `stats_dialog`: 「壊白」列を削除（列インデックス前倒し）
  - `main_window`: ホバー表示の「壊せる白」表記を削除、m66展開後コメント整理
- `element_picker`: 既に v0.1.x で削除済みのまま維持
- 互換性: 過去データに BROWN_WHITE があっても WHITE として扱われる（情報落ち＝挙動上は等価）

## v0.1.98 (2026-05-11)

### 追加
- **ピッカーにnoslow版Neul/Ghost (0x40-0x4F) を追加**
  - ピッカー `ENEMIES_LIST` に Ghost(right/left, noslow)・Neul(up/down, noslow) 4種を追加
  - `ENEMY_SPEED_TABLE` も拡張: 0x40/0x42/0x44/0x46 をbase codeとして sp1/sp2 を選択可能に
  - 既存の通常版0x30-0x3F 4種と並んで合計8種選択可能（×sp1/sp2 = 実質16種）

## v0.1.96 (2026-05-11)

### 修正
- **item_bitmasks 読み出しバグ修正**（Level 20/30 でアイテムが表示されない問題）
  - 拡張ROM変換後の `rom.data` を参照していたため bitmap バイトがゼロクリアされ取得失敗していた
  - `original_rom_data`（変換前バイト列）から bitmap を読むよう修正
  - JP ROM の region フィルタ修正: 拡張後 `JP66` でも XML 側 `region="JP"` にマッチするよう `base_region` で補助判定
  - 検証: US/JP どちらも Lv20=129個・Lv30=34個 の bit を正しく取得

## v0.1.95 (2026-05-11)

### 追加
- **item_bitmasks のサポート**（Level 20: Bat Symbol、Level 30: Opal の一括配置）
  - 既存形式と同じ仕組み: 24バイト (16×12 ビット) の bitmap で同種アイテムを多数配置
  - 標準ROMの容量節約のための仕組み（通常のアイテムストリームでは入りきらないため）
  - `SkcConfig` に `item_bitmasks` 属性を追加、XML から読み込み
  - `MainWindow._apply_item_bitmasks()` で ROM data の bitmap を解読し、各レベルの items に追加
- Level 20 に約 129個の Bat Symbol、Level 30 に約 34個の Opal が表示されるように
- JP/USA 両方対応（オフセットが異なるが XML の region 設定で自動切替）

## v0.1.94 (2026-05-11)

### 修正
- **MBJ 位置検出を X2 (内部状態用) から X1 (叩く場所 = 出現位置) に変更**
  - BESK互換の仕様では「X1 = 叩く場所の座標 / X2 = 出現する場所の座標」
  - 実機検証では MBJ は X1 の位置に出現するため、X1 を使う
  - X1 は通常のアイテムバッファ形式 `y = (b >> 4) - 1` で復元できるシンプルな式
- ハードコードオーバーライドテーブルを撤廃、純粋な解析ロジックに戻した
- 検証:
  - Level 17 X1=$7E → (14, 6) ✓
  - Level 39 X1=$56 → (6, 4) ✓

## v0.1.93 (2026-05-11)

### 修正
- **MBJ位置をユーザー実機検証に基づくオーバーライドテーブルで指定**
  - `$91A3` で計算した座標が `$A2B8` 内の `STY $04` で再上書きされるため、簡単な式で復元不可能と判明
  - 実機検証ベースの対応表で固定:
    - $36 → (6, 4) (Level 39)
    - $6E → (14, 6) (Level 17)
  - 未知のバイト値は暫定計算式 (`y = high_nibble + 1`) でフォールバック

## v0.1.92 (2026-05-11)

### 修正
- **MBJ位置のデコード式が間違っていたのを修正**
  - $91A3 ルーチン (MBJ表示処理) を逆解析した結果、MBJ の位置バイトはアイテムバッファとは違うエンコーディングだった
  - アイテムバッファ: `y = (b >> 4) - 1` (基底 $0304+P 用)
  - **MBJ ($91A3経由)**: **`y = (b >> 4) + 1`** ← こちらが正しい
  - 修正結果:
    - Level 17: (14, 5) → **(14, 7)** に訂正
    - Level 39: (6, 2) → **(6, 4)** に訂正

## v0.1.91 (2026-05-11)

### 修正
- マイティボンジャック隠し配置の描画順を改善
  - 旧仕様: MBJスプライト(不透明) → 白壁(55%)上書き → 結果: 白く曇って MBJ が見えにくい
  - 新仕様: 既存白壁(不透明) → MBJスプライト(55%)上書き → 結果: 白壁の中に MBJ が透けて見える
  - その位置が白壁でない場合は白壁を下地として補完描画

## v0.1.90 (2026-05-11)

### 追加
- **マイティボンジャック（MBJ）出現位置を可視化** (Level 17, 39)
  - 検出パターン: `A9 XX 85 88 4C YY ZZ` (LDA #pos; STA $88; JMP $B500/B930)
  - JP: JMP $B500 / USA: JMP $B930 両方対応
- **描画**: MBJ スプライト (enemy 0x18) + 半透明白壁オーバーレイ + 黄色枠
  - 既存の隠しアイテム表現と同じスタイル
- 検出結果:
  - Level 17: (14, 5)
  - Level 39: (6, 2)

## v0.1.89 (2026-05-11)

### 追加
- **特殊処理トリガー検出**を実装（待機パターン認識）
  - `A5 7E C9 XX D0 -k` (LDA $7E; CMP #$XX; BNE) 検出
  - `A6 7E E0 XX D0 -k` (LDX $7E; CPX #$XX; BNE) 検出
  - トリガー位置 → 条件付き壊せる位置 の対応を抽出
- **マーカー種別を拡張**:
  - 緑実線: 即壊せる (無条件)
  - **緑点線: 条件付き壊せる**
  - **ピンク: トリガー位置（プレイヤーアクション待機点）**
- **トリガー→ターゲット間に点線**で対応関係を可視化
- 検証結果:
  - Level 49: (13,9)→(2,7), (7,4)→(5,5)
  - Level 50: (12,5)→(9,5)
  - Level 52, 53: (1,9)→(7,11)

## v0.1.87 (2026-05-11)

### 修正・追加
- **特殊処理マーカー検出を大幅強化** (Level 52 のユーザー報告 (6,3)(7,3)(8,3) が見落とされていたため)
  - **前方分岐 (BEQ/BNE/BPL/BMI/BCC/BCS) を追跡**: RTS の先にあるコードでも分岐で到達するなら検出
  - **範囲配置 (`STA $03YY,X`) を認識**: `LDX #N; ...; STA $03YY,X; DEX; BPL -k` パターン
  - **位置テーブル経由配置 (`LDY $XXXX,X; STA $0304,Y`) を認識**: テーブル先頭のRAMアドレスをROM変換して該当バイト列を読み取り、各 X について Y を取得して位置展開
- 検出範囲拡大: BinaryDistSpecial の長さ制限を撤廃、最大512バイトまで分岐追跡

### 検証結果（修正後の検出位置）
- Level 49: 14箇所（左列5+右列5+中央2+直接配置2）
- Level 50 SOLOMON: 4箇所
- Level 52, 53: 5箇所（うち (6,3)(7,3)(8,3) はユーザー報告と一致）

## v0.1.86 (2026-05-11)

### 変更
- 特殊処理マーカーから「強制白 (white_forced)」検出を廃止（既存白壁とノイズになるため）
- 「強制空 (empty_forced)」を黄→水色に変更
- 結果として2種類のみ: **緑=壊せるブロック / 水色=強制クリア**

## v0.1.85 (2026-05-11)

### 変更
- 特殊処理マーカーの「破/白/空」ラベルバッジを廃止、色枠のみ表示
  - 色で種類を区別: 緑=壊せる / 水色=強制白 / 黄=強制空

## v0.1.84 (2026-05-11)

### 追加
- **Level 50 SOLOMON の壊せる隠し壁などを編集画面で可視化**（Phase 1.5）
  - 表示オプションに「特殊処理マーカー表示」チェックボックス追加（デフォルトON）
  - レベルの特殊処理ROMコードから動的配置マスを自動抽出:
    - 緑[破] = 壊せるブロック (LDA #$90; STA $03XX)
    - 水色[白] = 強制白壁 (LDA #$F8; STA $03XX)
    - 黄[空] = 強制クリア (LDA #$10; STA $03XX)
  - 例: Level 50 SOLOMON の (7,1), (12,7), (3,3), (9,5), (10,5) 等が緑[破]として表示される
- 新機能: `special_process.find_marks()` / `find_marks_for_level()`
- 検出: `LDA #$XX` の直近 A 値を追跡しながら `STA $03YY` を解釈

## v0.1.83 (2026-05-11)

### 削除
- **エディタ画面の BROWN_WHITE 青フィルター描画を削除**
  - 「壊せる白壁」は実は特殊処理ROM側で実現されており、レベルデータの BROWN_WHITE は実ゲームで意味を持たない
  - 青フィルター表示はミスリーディングだったため廃止
  - BROWN_WHITE データは引き続き白として描画（区別なし）

## v0.1.82 (2026-05-11)

### 削除
- **「壊せる白ブロック (BROWN_WHITE)」をピッカーから削除**
  - 自動拡張ROM運用では普通の白ブロック (0xf8) に圧縮されるため、配置しても効果なし
  - 「白く見えて壊せる」効果は実は **Level 50 特殊処理ROM** 側で実現されている（レベルデータ機構ではない）
  - 既存データ (Level 41/47/48) の読込・表示は引き続き level_renderer 側で対応（青フィルター表示）

## v0.1.81 (2026-05-11)

### 修正
- **JP ROM 読込時に特殊処理ビューアが「未対応」表示になる**不具合修正
  - 原因: m66_expander が `rom.region = "US66"` をハードコードしていたため、JP源泉ROMでも `base_region()` が "US" を返していた
  - 修正: ソースリージョンに応じて `"US66"` / `"JP66"` / `"EU66"` に設定
  - `region.is_expanded()` / `base_region()` を新 region に対応
  - `Rom.is_expanded()` も汎用化（hardcoded "US66" → `region_mod.is_expanded()`）
- これで JP ROM の特殊処理ビューアが JP のテーブル位置 (0x3404) を参照するようになる

## v0.1.80 (2026-05-11)

### 追加
- **特殊処理ビューア (Phase 1, 読込専用)** を実装
  - 編集ツールに「特殊処理ビューア...」ボタン追加
  - 各レベルの ROM ハードコードルーチンを表示
    - 生バイト (アドレス付き)
    - 擬似アセンブラ（既知サブルーチンに日本語注釈）
  - 全53レベルの一覧 + サイズ別カテゴリ (empty / JMP only / 短い / 中 / ★大規模)
  - 対応リージョン: **JP (0x3404), USA (0x3834)** — EU は未対応
- BESK を逆コンパイルして得た解析データを実装に反映
- 新ファイル:
  - `magatu_skc/core/special_process.py` (ディスパッチ計算 + 6502長さ + 注釈)
  - `magatu_skc/ui/special_process_dialog.py` (ビューアUI)

### 注意
- Phase 1 は読込専用。編集は Phase 2 (プリセット投入) / Phase 4 (拡張ROM対応) で実装予定
- Phase 3 (自由バイト編集) は需要次第で後回し

## v0.1.79 (2026-05-11)

### 修正
- **壊せる白ブロック (BROWN_WHITE) がエディタに表示されない不具合**を修正
  - 原因: 自動拡張変換後の再パースで BROWN_WHITE が WHITE に変質していた
  - 通常ROMでは BROWN/WHITE のビットマップ独立で BROWN_WHITE 表現可能
  - 拡張ROM (mapper 66) は 1バイト/マスのグリッドフォーマットで `0x90`(brown)/`0xf8`(white) のみ
  - `save_level_m66` は BROWN_WHITE を `0xf8` (普通の白) として書き出すため、再パースで情報消失していた
  - 修正: 自動拡張変換後の再パースを廃止し、通常ROMから読んだ `levels` をそのまま使用
  - これによりエディタ上で BROWN_WHITE が青フィルター付きで正しく表示される
- 既知の制約: 改造ROM保存時、拡張形式に書き出す段階で BROWN_WHITE は普通の白 (0xf8) になる
  - 既存形式でも同じ制約あり。拡張ROMフォーマットでの BROWN_WHITE 表現は未解明
  - 解析タスクとして 9-14 にロードマップ追加予定

## v0.1.78 (2026-05-11)

### 変更
- **敵スピードをフラグ化**（アイテムフラグ Hidden/InBlock と同形式の UI）
  - ピッカーに「敵スピード (対応する敵のみ)」の SP1 / SP2 / SP3 ラジオを追加
  - `ENEMIES_LIST` を sp1 ベースのみに整理（重複バリアント削除）
  - 敵配置時にベースコード + 選択中スピード → 実コードに変換
    - Demonhead/Saramandor: SP1/2/3 すべて対応
    - Dragon/Golem/Gargoyle/Fireball/Neul/Ghost: SP1/2 対応
    - Mighty Bomb Jack/Bullet/Panel Monster/Fairy/Flame: スピード無関係（無視）
  - スピード非対応 sp が選ばれた場合、一段下のスピードへフォールバック
- スポイト (Alt+Click) で敵を取った時、ベースコード+スピードを逆引きしてピッカーに反映

### 内部
- `element_picker.py` に `ENEMY_SPEED_TABLE`, `apply_enemy_speed()`, `base_code_from_actual()` を新設
- `ElementPicker.get_enemy_speed()` / `set_enemy_speed()` API追加

## v0.1.77 (2026-05-11)

### 修正・追加
- ミラー詳細設定ダイアログの Phase 1 / Phase 2 のチェックボックス位置ずれを修正
  - ラベル幅を 110px に固定して桁を揃える
- 敵リスト (`ENEMIES_LIST`) に以下を追加:
  - **Fireball sp2** (0x2C-0x2F, 4方向)
  - **Demonhead sp2/sp3** (0x54-0x55, 0x58-0x59)
  - **Saramandor sp2/sp3** (0x60-0x61, 0x64-0x65)
  - **Dragon sp2** (0x6C-0x6D)
  - **Bullet** (0x20-0x23, 4方向)
- これによりピッカー・ミラー詳細設定の両方で選択可能に

## v0.1.76 (2026-05-11)

### 追加
- レベル画面のミラーアイコンに **番号ラベル ("1" / "2")** を重ね描き
  - 黒縁取り + 黄色文字で視認性確保
  - 「ミラー詳細設定」ダイアログのミラー1/ミラー2と対応がつくように

## v0.1.75 (2026-05-11)

### 追加
- **ミラー詳細設定ダイアログ** (Phase 2-4 / 2-5 / 4-7 を統合)
  - 「レベル設定」グループに「ミラー詳細設定...」ボタンを追加
  - 1ダイアログ内で 2ミラー分まとめて編集:
    - **出現タイミング**: 64ビット = Phase 1 (32) + Phase 2 ループ (32) のチェックボックス
    - **出現する敵**: 最大7体ぶんのコンボボックス（敵アイコン + 名前）
    - **クイック操作**: スケジュール全クリア/全ON、敵セットクリア
  - スポーン敵の生存時間 (Saramander/DemonHead 用 TTL) スピンボックス
- 16進数を見ずに編集可能なUIにした
- 拡張ROM (mapper 66) のレイアウトに直接読み書き

### 内部
- 新ファイル: `magatu_skc/ui/mirror_dialog.py`

## v0.1.74 (2026-05-11)

### 修正
- 敵配置上限の不整合を解消
  - `ENEMY_COUNT_MAX` を 16 → **15** に変更（拡張ROM運用に統一）
  - 旧仕様: 16体まで配置できるが保存時に SaveError、もしくは編集中に16体目以降がサイレント無視
  - 新仕様: 16体目を置こうとした時点でステータスバーに「敵は1レベル 15 体まで（拡張ROM形式の制限）」と表示
  - `Level.add_enemy` が bool を返すようになり、上限到達を呼出側で検知可能に
- アイテムは引き続き上限なし（マップ192マスが事実上の上限）

## v0.1.73 (2026-05-11)

### 修正
- パレット編集 Apply 後、エディタ画面の色がおかしくなる不具合を修正
  - 原因: ROMの 4バイト `[c1, c2, c3, separator]` をそのまま XML 形式に流していた
  - XML 形式は 3バイト `[c1, c2, c3]` で `SubPalette` が先頭に 0x0F (透明) を補完する仕組み
  - 4バイト渡すと色が1スロットずれて表示されていた
  - 修正: ROM の先頭3バイトのみを XML に流す
- ダイアログの「リセット」ボタンが現在のROM値に戻していた不具合を修正
  - 起動時のスナップショットを保存し、Apply済みでもそこに戻れるように

## v0.1.72 (2026-05-11)

### 追加
- パレット編集 Apply 後、エディタ画面に **リアルタイム反映**
  - ROM 0xED4 の 32バイトを `config.palettes` (XML由来の40パレット) に同期
  - 5グループ (red/cyan/purple/dgreen/gray) のうち:
    - BGパレット slot 0 はグループ固有なので red のみ更新
    - BGパレット slot 1/2、SPRパレット全色は全グループ共通として全部更新
  - `tile_renderer.clear_cache()` + `picker._populate_all()` + `_refresh_view()` で
    メイン画面・ピッカー両方を再描画
  - レベル選択サムネイルは手動再生成ボタンから更新可能

## v0.1.71 (2026-05-11)

### 追加
- **パレット編集機能** を新設（試作）
  - 編集ツール群に「パレット編集...」ボタンを追加
  - ROM offset `0xED4` の 32バイト = 8パレット (背景4 + スプライト4) を編集可能
  - 各パレット: 編集可能な色3スロット (4バイト目はセパレータ 0x0F/0x00 で維持)
  - NES 64色から色選択（4×16グリッドのカラーピッカー）
  - リセットボタンでダイアログ起動時の値に戻せる
  - 主人公の色は SPR #0〜#3 のいずれか（テストプレイで確認しながら特定）
- 新ファイル: `magatu_skc/ui/palette_dialog.py`

### 注意
- パレット変更は ROMバイトに直接書き込み、テストプレイ/保存で反映
- エディタ画面（マップ表示）のパレットは XML設定ベースなのでリアルタイム反映はされない

## v0.1.70 (2026-05-11)

### 追加
- **セッション操作ログ**を実装
  - 主要操作をメモリに蓄積し、アプリ終了時に `logs/session_YYYYMMDD_HHMMSS.log` へ保存
  - 記録対象:
    - セッション開始/終了
    - ROM読込（自動拡張変換の有無を含む）
    - ROM保存 / IPS保存 / XML出力(現在/全) / XML読込(現在/全)
    - 編集開始（クリーン→ダーティに変わった瞬間 + 対象レベル）
    - レベルクリア（モード別）
    - ゲーム挙動改造（HACK ダイアログでROMが変わったとき）
    - テストプレイ起動
    - 各種失敗時のエラー情報
- 何も操作がないセッション（開始/終了のみ）はファイル出力しない

### 内部
- `_session_log: list[str]`、`_log(msg)`、`_save_session_log()` を新設

## v0.1.69 (2026-05-11)

### 修正
- 自動拡張時の `Too many enemies in mirror enemy set 1 (42 >= 8)` エラー修正
  - 通常ROMのミラーデータはポインタテーブル経由（lo/hi 各17バイト → RAMアドレス → ROMオフセット）で読む構造だった
  - C++ `SKC_Config::get_offset_generic_data` を `_resolve_table_entry` として移植
  - `parse_drop_schedules_std` / `parse_enemy_sets_std` を書き直し

## v0.1.68 (2026-05-11)

### 追加
- **ROM読込時の自動拡張変換 (mapper 3 → 66)**
  - 通常ROMを読み込むと自動的に拡張ROM形式 (96KB, mapper 66) に変換される
  - 容量制約 (敵726バイト / アイテム1402バイト) が事実上無くなる（1レベル=256バイト固定 × 53レベル）
  - `change_mapper / patch_mirror_*` 相当の処理を実装
  - `core/m66_expander.py` 新設
- **ROM情報表示**: 自動変換時に「⚙ 拡張ROMに自動変換 (mapper 66)」を表示
- **IPS出力を拡張ROMでも有効化**:
  - 旧仕様: 拡張ROMだとIPSボタン無効化
  - 新仕様: `original_rom_data` (変換前=通常ROM) を基準にIPS生成。配布の唯一の手段なので残す
  - `core/ips.py` の `create_ips_patch` をサイズ拡張対応に更新（modified が original より大きくてもOK）

### 内部
- `MainWindow.load_rom` で `m66_expander.expand_rom(rom, levels)` 呼び出し
- 変換後 `load_all_levels(rom)` で拡張ROM形式から再パース
- `_auto_expanded` フラグを保持

## v0.1.67 (2026-05-11)

### 修正
- テストプレイ時の例外（`SaveError` 等）を `QMessageBox` で表示するよう修正（無言クラッシュ防止）

## v0.1.66 (2026-05-11)

### 追加
- **エミュレータ連携 / テストプレイ機能**
  - F9設定画面に「外部連携 → エミュレータ」項目を追加（参照ボタンで.exe選択）
  - 左ペインに「▶ テストプレイ (現在レベル)」ボタンを追加
  - 動作:
    1. 現在の編集中レベル群をROMデータに反映
    2. ステージセレクトパッチを現在レベルに設定（BESK利用可ならBESK、不可なら簡易方式）
    3. 一時ROMを `%TEMP%/magatu_skc_testplay/testplay.nes` に書き出し
    4. 設定したエミュレータをそのROMを引数にして起動
  - rom.dataは作業後に元の状態に復元（テストプレイ用の改変は永続化しない）

## v0.1.65 (2026-05-11)

### 修正（D&D問題完全解決）
- お気に入りへのD&Dが効かない問題を最終解決:
  - **MainWindow**: 内部D&D(`PICKER_MIME`)を `dragEnterEvent` で accept するよう修正（旧: URL以外を ignore してウィンドウ侵入を阻止していた）
  - **ElementPicker**: 親ウィジェットでドロップを受けて、ドロップ位置がお気に入りバーの矩形内なら `FavoritesBar.handle_drop()` に手動振り分け
  - **DraggablePickerList**: `startDrag()` + `mouseMoveEvent` の二重経路で確実にドラッグ起動
  - **FavoritesBar**: 各スロットに明示的な `setSizeHint` でアイコン全体を表示
- 高さを 86px → 92px に微調整（2行 + マージン）

### 内部
- デバッグ用 print を削除

## v0.1.60 (2026-05-11)

### 修正（再）
- お気に入りへのD&Dが効かない不具合を修正
  - 前回(v0.1.58)のマウスイベントオーバーライド方式は、QAbstractItemViewの選択処理と競合して動作しなかった
  - **`startDrag()` メソッドのオーバーライド方式に変更**
    - `setDragEnabled(True)` + `setDragDropMode(DragOnly)` でフレームワークの標準ドラッグ起動経路を使う
    - フレームワークが startDrag を呼んだ瞬間にカスタムMIMEで `QDrag.exec_()`
  - これがQtの正規ルートで最も確実

## v0.1.59 (2026-05-11)

### 追加
- **ウィンドウ状態の保存・復元**
  - 終了時に以下を `magatu_skc_config.json` に保存:
    - ウィンドウ位置 (X, Y)
    - ウィンドウサイズ (幅, 高さ)
    - 最大化状態
    - 4ペインのスプリッター幅 (`[LEFT, CENTER, PICKER, LEVEL_SELECT]`)
  - 起動時に自動復元
  - 画面構成変更時（モニター切替等）に画面外に出ないよう簡易チェックあり
  - 最大化状態のサイズは記録せず、復元時は最大化フラグのみ反映

## v0.1.58 (2026-05-11)

### 修正
- お気に入りへのD&Dが効かない不具合を修正
  - QListWidget標準のstartDragはモード設定との相互作用で発動しないことがある
  - 明示的にマウスイベントを処理してQDragを発動する `DraggablePickerList` を新設
  - カスタムMIMEタイプ `application/x-magatu-picker-item` で確実に受信側へ伝達

## v0.1.57 (2026-05-11)

### 追加
- **ピッカーお気に入り機能**を新設（10スロット）
  - メイングリッドからD&Dで登録
  - **1〜9 / 0 キーでクイック選択**（旧「ホバー位置に配置」機能を置換）
  - スロット選択時、メインリスト側も同期して選択状態に
  - **お気に入りはJSON永続化** (`magatu_skc_config.json`)
  - 選択中スロットで Del/BackSpace → スロットクリア
  - タイルセット変更時はお気に入りアイコンも自動更新

### 変更
- ピッカーのアイコン間スペースを大幅圧縮（`setGridSize` で密に配置）
- メイングリッドはドラッグソース（DragOnly）として動作
- お気に入りバーは2行分の固定高さ

### 内部
- `FavoritesBar`(QListWidget) クラスを `element_picker.py` に新設
- `ElementPicker.trigger_favorite_key(n)`, `get_favorites()`, `restore_favorites()` API追加
- `core/config.py` の `DEFAULT_CONFIG` に `picker_favorites` 追加

## v0.1.56 (2026-05-11)

### 変更
- **要素ピッカーを統合グリッド化**
  - ブロック / メタ（鍵・扉・スタート・ミラー）/ アイテム / 敵を **1つのIconModeグリッド**にまとめて表示
  - 各アイコンは画像のみ・テキストなし、説明はマウスホバーの**ツールチップ**
  - 「編集対象」ラジオボタン群（ブロック/アイテム/敵/鍵扉スタート）を**廃止**
    - アイコンクリックで自動的にモードが切り替わる（UserRoleに `(mode, value)` を格納）
  - **配置フラグ（通常/隠し/ブロック内）は常時表示**に変更（旧: アイテムモード時のみ）
  - 一覧性が大幅向上（モード切替なしで全要素にアクセス可能）

### 内部
- `ElementPicker._populate_all()` 新設、旧 `_populate_blocks/items/enemies/meta` と `_on_mode_changed` を統合
- `_set_picker_value(value, mode=...)` でモード指定検索可能に（スポイト機能用）

## v0.1.55 (2026-05-11)

### 変更
- レベル選択リストを **画像のみ表示**（IconMode + ラップ）に変更
  - 「Level N」のテキストラベルは削除
  - レベル番号はマウスホバーで **ツールチップ表示**
  - グリッド状に並ぶので一覧性アップ

## v0.1.54 (2026-05-11)

### 追加
- **サムネイル付きレベル選択ペイン**を実装（Phase 4-8）
  - レイアウト変更: `LEFT（諸々）| CENTER（メイン）| ピッカー | レベル選択（最右）`
  - レベル選択リスト（QListWidget）の各行にレベル画像のサムネイル（160×120px）を表示
  - レベル選択グループは左ペインから最右ペインへ移動
  - サムネイル生成タイミング:
    - **ROM読込時**: 全53レベルを一括生成（`_generate_all_thumbnails`）
    - **レベル切替時**: 「離れる側」のサムネだけ更新（`_refresh_thumbnail`）
    - **手動再生成ボタン**: 念のため全レベル再生成可能
  - 編集中の現在レベルはリアルタイム更新せず、別レベルへ移動した瞬間に反映 → 軽量

### 変更
- スプリッタを3ペイン → 4ペイン構成に変更（初期サイズ `[280, 700, 250, 220]`）

## v0.1.53 (2026-05-11)

### 追加
- **F9 設定画面**を新規実装（Phase 3-1 部分着手）
  - 設定ダイアログ `magatu_skc/ui/settings_dialog.py`
  - 設定永続化 `magatu_skc/core/config.py` → `magatu_skc_config.json`
  - 現状の設定項目:
    - **未保存マーク**（プリセット: ●/*/[未保存]/♦/•/✱/[edited] + 自由入力）
  - OK / Apply / Cancel ボタン（Applyは閉じずに即時反映）
  - 今後追加予定: フォント、アイコンパス、通知音、クラウドバックアップ等（プレースホルダ表示）

## v0.1.52 (2026-05-11)

### 追加
- **未保存マーク + 終了時確認** (Phase 4-14)
  - 編集すると **タイトルバーに ● マーク** が表示される
  - ROM/IPS/XML 保存で消える
  - ROM ロード時もリセット（読込直後はクリーン）
  - **ウィンドウ閉じる時、未保存があれば確認ダイアログ**
    - 「本当に終了しますか？」 Yes/No、デフォルトはNo
  - ゲーム挙動改造ダイアログでROMバイト変更があった場合も dirty 化

## v0.1.51 (2026-05-11)

### 修正
- Ctrl+ドラッグでブロックを移動した際、通り過ぎたタイルの既存ブロックが消える不具合を修正
  - 原因: 「現在の描画位置」をNONEで上書きしてから新位置に置く実装で、通り過ぎたタイルが他のブロック持ちだった場合にそれを破壊していた
  - 修正: 各タイルの「元の壁」を保存し、ドラッグが離れる際に復元するように変更

## v0.1.50 (2026-05-11)

### 追加
- **選択範囲のドラッグ移動**
  - 選択範囲の内側で **Ctrl+左ドラッグ** すると、範囲全体（ブロック/アイテム/敵）が追従移動
  - 元の位置は空白に、新位置に貼り直し
  - 選択枠も新位置に同期
  - Undo は1ストロークで1エントリ
- 内部リファクタ: `_build_clipboard_from_selection` / `_paste_clipboard_at` を切り出し、
  コピペとドラッグ移動でロジック共有

## v0.1.49 (2026-05-11)

### 追加
- **選択範囲操作 一式実装**
  - **Ctrl+C** コピー（ブロック/アイテム/敵 まとめて）
  - **Ctrl+V** ペースト（選択範囲の左上 or ホバー位置 を起点）
  - **Ctrl+X** 切り取り（コピー+削除）
  - **Delete** 範囲一括削除（範囲なしならホバー位置の従来動作）
  - **F** 左右反転
  - **Shift+F** 上下反転
  - 全操作 Undo 対応
  - F1ヘルプも更新

## v0.1.48 (2026-05-11)

### 修正
- 範囲選択中とリリース後にマウスを動かすと選択枠が消えるバグを修正
  - 原因: `_on_tile_hovered` 内の軽量再描画で `selection_rect` を渡していなかった
  - これでドラッグ中の選択範囲も滑らかに更新される

## v0.1.47 (2026-05-11)

### 追加
- **Shift+左ドラッグで矩形範囲選択**
  - 黄色の点線枠＋半透明黄色フィルで範囲をハイライト
  - ステータスバーに範囲座標と幅×高さ表示
  - **Esc** で選択解除
  - 通常の左クリックでも選択解除
  - 選択範囲を使った操作（コピー/ペースト/反転/削除等）は今後追加予定

## v0.1.46 (2026-05-11)

### 追加
- **Ctrl+ドラッグでブロックも移動可能に**（実装漏れ対応）
  - 茶ブロック / 白ブロック / 壊せる白ブロックを掴んでドラッグ可能
  - 移動優先順: アイテム > 敵 > メタ要素 > **ブロック**（最後）
  - 元位置は移動開始時に空白化、ドラッグ中は新位置に追従
  - Undoで一発戻し

## v0.1.45 (2026-05-11)

### 追加
- 🎯 **スポイト機能** (Alt+左クリック)
  - その位置の要素をピッカーに取り込む
  - 優先順: 敵 > アイテム > メタ要素 > ブロック
  - アイテムの場合はフラグ（隠し/in_block）も自動反映
  - 編集モードも該当モードへ自動切替
  - ステータスバーで通知

## v0.1.44 (2026-05-10)

### 修正
- **スタート位置・扉位置にブロックが置けてしまう不具合を修正**
  - スタート位置にブロック → 主人公が埋まってクリア不能
  - 扉位置にブロック → 出られなくてクリア不能
  - どちらも配置を拒否、ステータスバーで通知

## v0.1.43 (2026-05-10)

### 追加
- **ピッカー選択中のアイコンをマウスカーソル形状に表示**
  - レベルビュー上のカーソルが、ピッカーで選んだアイテム/敵/ブロックの絵に変わる
  - 32x32 ピクセル、ホットスポット中央
  - 選択変更で即座にカーソル更新
  - レベル切替時もタイルセット色に追従して再描画

## v0.1.42 (2026-05-10)

### 追加
- **ステータスバーにマウス下部のタイル情報を常時表示**
  - 右側固定エリアに専用ラベル
  - 表示内容:
    - 座標 `(x, y)`
    - ブロック種類（茶/白/壊せる白）
    - アイテム名 + フラグ（隠し/in_block）
    - 敵名（同位置複数なら全部）
    - メタ要素（スタート/鍵/扉/ミラー1/ミラー2）
    - 星座
  - ステータスバー左の `showMessage()` とは独立（操作通知に上書きされない）

## v0.1.41 (2026-05-10)

### 追加
- **ドラッグ塗り** & **ドラッグ消し**
  - **左ボタン押しっぱなし＋移動** = 連続配置（ドラッグ塗り）
  - **右ボタン押しっぱなし＋移動** = 連続削除（ドラッグ消し）
  - 既存の Ctrl+左ドラッグ（要素移動）と共存
- Undo は1回のドラッグ全体で**1エントリ**にまとめる
  - 押下時に1回だけスナップショット → Ctrl+Zで全戻し
  - `_suppress_next_undo` フラグで実装
- F1ヘルプにドラッグ系の操作を追記

## v0.1.40 (2026-05-10)

### 追加
- アイテムフラグ切替のショートカット追加
  - **N**: 通常 (0x00)
  - **H**: 隠し (0x40)
  - **B**: ブロック内 (0x80)
  - 押下するとピッカーのラジオボタンが切替＋ステータスバー表示
- F1ヘルプにフラグ切替も追記

## v0.1.39 (2026-05-10)

### 追加
- **キーボードショートカットでホバー位置にクイック編集**
  - **Delete / Backspace**: ホバー位置の要素削除
  - **0-9 数字キー**: モードに応じて配置
    - BLOCK: 0=消去 / 1=茶 / 2=白 / 3=壊せる白
    - ITEM: 1-9 = ITEMS_LIST 先頭から N 番目のアイテム / 0 = 既存削除
    - ENEMY: 1-9 = ENEMIES_LIST 先頭から N 番目の敵 / 0 = 既存削除
    - META: 1=スタート 2=鍵 3=扉 4=ミラー1 5=ミラー2
  - 配置時はピッカーの選択も自動で同期（次回の左クリック配置にも反映）
- F1ヘルプにキーバインド一覧を追記

## v0.1.38 (2026-05-10)

### 追加
- ブロック × アイテムの配置レギュレーション実装
  - **白ブロック (壊せない) 内アイテム**: **禁止**（取れなくなるため）
    - アイテム配置時に白ブロックタイル → 拒否
    - 白ブロック配置時にアイテムあり → 拒否
  - **茶ブロック / 壊せる白ブロック + アイテム**: **自動で in_block フラグ付与**
    - アイテム配置時に該当タイル → ピッカー選択に関わらず in_block 強制
    - ブロック配置時にアイテムあり → 既存アイテムを in_block に自動変換
    - ステータスバーで通知
  - 壊せる白ブロックは原作には無いが、ユーザーがアイテム配置できるように許可

## v0.1.37 (2026-05-10)

### 追加
- **敵 × ブロック同位置の配置禁止**（原作USA ROMで事実上皆無の組み合わせ）
  - 敵がいる位置にブロック（茶/白/壊せる白）配置 → ステータスバー警告 + 配置キャンセル
  - ブロックがある位置に敵を配置 → 同様に警告 + キャンセル
  - 「消去」（ブロック削除）は許可（敵は残る）
  - 誤って積んだUndo履歴も自動で取り消し

## v0.1.36 (2026-05-10)

### 修正
- 16列目非表示時の左右非対称な見た目を改善
  - 右に黒列がある分、**左にも同じ幅の黒パディング**を追加（17列幅のキャンバス）
  - クリック・ホバー座標は LevelView 側で自動補正（画像幅から推定）
  - これでプレイ画面のように上下中央＋左右対称に表示される

## v0.1.35 (2026-05-10)

### 修正
- 16列目を非表示にしてもマウスホバーで再描画した瞬間に復活する不具合を修正
  - ホバー再描画ルートが `show_col15` を渡していなかった

## v0.1.34 (2026-05-10)

### 追加
- **16列目（右端列）の表示・編集ON/OFFオプション**
  - 表示オプションに「16列目を表示・編集」チェックボックス追加
  - **デフォルトOFF**（実画面に出ない列なので非表示）
  - OFF時: 16列目は黒で塗りつぶし、クリック編集も無効化
  - ON時: 通常表示・編集可能

## v0.1.33 (2026-05-10)

### 修正
- **コンティニュー上限のアドレスが USA で間違っていた不具合を修正**
  - 旧: USA/JP 共通で 0x4A58 を使用 → USAでは別のデータ位置（値=2）を読んでた
  - 新: リージョン別アドレス
    - USA: ROM 0x4958 (LDX #$28; CPX $0428; BCS のパターンで特定)
    - JP : ROM 0x4A58
  - `get_continue_max_offset(region)` ヘルパー関数を追加

### 検証
- USA ROM ロード時: コンティニュー上限が「41」と正しく表示される
- JP ROM ロード時: 同じく「41」

## v0.1.32 (2026-05-10)

### 変更
- ゲーム挙動改造ダイアログを**完全に数字入力のみ**に整理
  - 「おおよそ」プレビューラベル削除
  - 開始ステージ: 「面目」サフィックス削除、純粋な数字 1〜53
  - コンティニュー上限: ドロップダウンを廃止、**スピンボックス 1〜53** に統一
  - 補足説明文（「※ステージ1を選べば〜」等）も削除
  - 全項目が **数字スピンボックスだけ** のシンプル構成

## v0.1.31 (2026-05-10)

### 変更
- アイコン読込優先順を **PNG → ICO** に変更
  - `assets/dana.png` (64×64) が存在すれば優先使用
  - ICO は低解像度だったため、ユーザーが任意のPNGに差し替え可能
  - `assets/` フォルダにファイル名 `dana.png` で置けば自動採用

## v0.1.30 (2026-05-10)

### 追加
- **アプリアイコンを設定** — `assets/dana.ico`
  - JP ROM の CHR-ROM からダーナ（主人公）スプライトを直接抽出
  - 16×16〜256×256 の複数解像度を埋込
  - タスクバー・ウィンドウタイトル両方に反映（マルチモニタ対策の AppUserModelID も既設定済）
  - ライセンス的にクリーン（自分のROMから自分で抽出した素材）

## v0.1.29 (2026-05-10)

### 変更
- 開始LIFE スピンボックスの範囲を **0〜9 → 1〜9** に変更（即死 0 を除外）
- 表示を「約 N 万」形式に変更（実機検証で約+5,000のオフセットがあるため）
  - 例: 設定 7 → 「約 75,000」
- USA/JP 実機検証で動作確認済み

## v0.1.28 (2026-05-10)

### 変更
- **開始ライフポイントの実装を全面刷新**
  - 旧: Game Genie由来のプリセット（3000/40000/330000）— 不正確、JPで効かない
  - 新: **10000の位 (0〜9) のスピンボックス** — 1バイト改造で確実に動作
  - **リージョン別アドレスに対応**:
    - USA: ROM 0x1835 (LDX #$01 即値)
    - JP: ROM 0x17B8 (USA 等価位置)
  - 設定値プレビュー表示（例: 9 → 「90,000」）
  - 0 を選ぶと「0（即死）」表示で警告
- 古い hack_data.py の `starting_life_points` (誤った 0x1839) は廃止し、
  リージョン別の `starting_life_10k_digit_USA` / `_JP` に置換
- `get_life_10k_offset(region)` ヘルパー関数を追加

### 検証
- USA ROMで KAXOOEVE 改造値（0x8C → ライフ40,000）と一致するメカニズムを解析
- 10000の位の値（ROM 0x1835/0x17B8）がそのままLIFE表示の万の位として反映されることを確認

## v0.1.27 (2026-05-10)

### 修正
- ゲーム挙動改造ダイアログのコンボボックス表示を改善
  - 「カスタム値（現在のROM値を保持）」等の曖昧な表記を廃止
  - **コンティニュー上限**: ROMの現在値がプリセット外なら **「ステージNまで」** と具体的に表示
  - **開始ライフ**: プリセット外なら **「その他の設定 (値 N)」** と表示
  - 常に現在のROM状態が一目で分かるように

## v0.1.26 (2026-05-10)

### 変更
- 「ステージセレクトを有効化」チェックボックスを **削除**（UI簡素化）
  - 代わりに **開始ステージのスピンボックス値だけで挙動が決まる**
  - **ステージ1**: パッチなし（原作通り）→ 既存パッチがあれば自動的に元に戻す
  - **ステージ2〜53**: ハック自動適用（BESK方式 or 簡易方式）
  - スピンボックスの上限を50→**53**に拡張（PRINSESS/SOLOMON/HIDDEN/空間の間/時間の間 まで指定可）

## v0.1.25 (2026-05-10)

### 修正
- **JPでBESKパッチ済みROMを読み込んだ際に「副作用あり」警告が誤表示される不具合を修正**
  - 原因: `has_besk_free_space()` が「領域が0xEA連続か」のみ判定していたため、既にパッチ済みROMだと False を返していた
  - 対応: 「BESKパッチが既に適用済」のケースも判定に追加（領域が `BESK_STAGE_SUBROUTINE` と `BESK_STAGE_TABLE` のパッチ内容と一致すれば True）

### 変更
- 「家族の呪い解除」「鬼畜仕様」等の煽り表現を全廃
  - UI: コンボボックス見出しを「コンティニュー上限」に変更
  - 機能名は事実ベースのニュートラルな表現に統一

## v0.1.24 (2026-05-10)

### 追加
- **コンティニュー制限解除（コンティニュー上限拡張）** ハックを実装 🌟
  - 原作の「ステージ42以降コンティニュー不可」鬼畜仕様の正体を解明
  - **ROM 0x4A58 のたった1バイト**を変更するだけで上限を最終ステージ(53)まで拡張可能
  - ゲーム挙動改造ダイアログにコンボボックス追加:
    - 41まで（原作デフォルト）
    - 42 / 48 / PRINSESS / SOLOMON / HIDDEN まで
    - **時間の間まで（全ステージ・最終）**
  - JP/USA/EU 全リージョン共通で動作（基本ゲームロジック領域）

## v0.1.23 (2026-05-10)

### 変更
- **ステージ選択をBESK方式に置き換え**（副作用なし、JP版で完全動作）
  - 旧: 0x1145 + 0x1149/0x114B のみ書換 → スコア・残機等が未初期化
  - 新: BESKが採用する**完全パッチ方式**を実装
    - 0x1145: ステージ番号
    - 0x1149-0x1157 (15B): 初期化コード差替
    - 0x0BF2-0x0C0A (25B): カスタムサブルーチン挿入
    - 0x5BEF-0x5BFB (13B): ステージ別初期値テーブル
  - JP版で BESK 出力と**バイト単位で完全一致**を確認
  - 「ステージセレクト無効化」で全パッチを元に戻す機能も実装
- **Resume (擬似セーブ) 機能を削除**
  - 0x1146 の編集を取りやめ、UIから関連コンボボックスを除去
- USA/EU 等の未使用領域がない ROM では従来の簡易方式にフォールバック（警告表示）
- `magatu_skc/core/hack_data.py` に BESK 方式パッチデータと `apply_besk_stage_select()` / `revert_besk_stage_select()` / `has_besk_free_space()` 関数を追加

## v0.1.22 (2026-05-10)

### 変更
- ROM/IPS 保存ダイアログのデフォルトファイル名を **「元ROM名_YYYYMMDD_HHMMSS.拡張子」** 形式に変更
  - 旧: `modified.nes` / `patch.ips`
  - 新: `Solomon's Key (USA)_20260510_193857.nes` / `.ips`
  - 上書き事故防止 + 改造履歴の自然な記録
  - ZIP内ROMの場合は内部ファイル名（"xxx.nes"部分）から派生

## v0.1.21 (2026-05-10)

### 変更
- ゲーム挙動改造ダイアログのUI改善（16進数表示を全廃）
  - 開始ライフポイント: 生バイト入力を削除、**プリセットドロップダウンのみ**（デフォルト/40,000/330,000）
  - 開始ステージ: 「書込み値」プレビューラベル削除（1〜50面表示で十分）
  - Resume挙動: 16進バイト値を非表示、わかりやすい説明に変更
    - 「無効 (常に最初から)」
    - 「前回到達ステージから再開（擬似セーブ）」
    - 「前回の次のステージから再開（擬似セーブ）」
  - Resume下に補足説明「電源OFFで初期化される擬似セーブ機能」を追記
  - 適用結果メッセージも数字ベースのわかりやすい表記に変更

## v0.1.20 (2026-05-10)

### 追加
- **ゲーム挙動改造ダイアログ** を実装 (Phase 9-1, 9-2 / B-1, B-2)
  - 編集ツールに「ゲーム挙動改造...」ボタン追加
  - **B-1: 開始ライフポイント変更** (ROM 0x1839)
    - プリセット: デフォルト3000 / 40000 (0x8C) / 330000 (0x83)
    - 生バイト値スピンボックスで自由設定 (0x00〜0xFF)
  - **B-2: 開始ステージ変更** (ROM 0x1145 + 0x1149 + 0x114B)
    - 「ステージセレクト有効化」チェックボックスで 0x1149/0x114B を切替
    - 1〜50面のスピンボックスで開始面選択
    - 0x1146 (Resume挙動) のドロップダウン: デフォルト/前回到達ステージ/次ステージ
  - 「オリジナル値に戻す」ボタンでデフォルト復元
  - OK/Apply/Cancel ボタン（Applyは閉じずに適用）
  - 適用結果を箇所別にメッセージ表示
  - ROM保存（改造ROMとして保存）するまでは未永続化、再読込で復元可

### 注意
- ROMバイナリを直接書き換えるため、Undo履歴とは別系統
- 改造ROMとして保存しないとファイルには反映されない

## v0.1.19 (2026-05-10)

### 変更
- **壊せる白ブロック (BROWN_WHITE) の表示を青フィルター方式に変更**
  - 旧: 白ブロック描画 + 緑枠ハイライト（隠し強調ON時のみ）
  - 新: 白ブロック描画 + **青フィルター半透明レイヤーを常時重ねる**
  - 緑枠は廃止
  - ピッカーアイコンも同じ青フィルターを適用 → 配置時とアイコンで完全一致

## v0.1.18 (2026-05-10)

### 追加
- **ホバーハイライト** (Phase 4-4): マウス位置のタイルを白枠で強調
- **レベル設定UI** (Phase 2-7, 2-8, 2-6):
  - **タイルセット切替** スピンボックス (0-2)
  - **時間減少率** スピンボックス (0-15)
  - **敵寿命** スピンボックス (0-255)
  - **星座** ドロップダウン + 位置スピンボックス（X/Y）
  - 全項目が**Undo対応** (Ctrl+Z で戻せる)
  - レベル切替時に自動でUI同期

## v0.1.17 (2026-05-10)

### 変更
- 「隠し要素強調 (黄色枠)」チェックボックスのデフォルトを **OFF** に変更（旧: ON）

## v0.1.16 (2026-05-10)

### 追加
- **全レベル統計** ダイアログを実装
  - 編集ツールに「全レベル統計」ボタン追加
  - 53レベル分を1表で一覧:
    - アイテム数（通常/隠し/in_block）
    - 敵数 / 壊せる白ブロック数
    - 鍵の状態と位置
    - ミラー位置（同位置なら●強調）
    - 星座
    - **重要アイテム一覧** (Bell, ソロモンの紋章, Warp, Shrine#1〜4, Star Coin系, Origami Swan, Demonhead Coin, Sphinx, Egyptian Head, Magic Lamp, E-bottle, Modifiable系)
  - 雑魚アイテム（Coin/Opal/Jewels/Hourglass等）は除外
  - セルダブルクリックでそのレベルへジャンプ
  - **CSV出力**ボタンで集計結果をエクスポート
  - 状態別に色付け（隠し=黄, in_block=緑, ミラー同位置=青）

## v0.1.15 (2026-05-10)

### 追加
- **レベルクリア（ブランクキャンバス）機能** を実装 (Phase 4-6)
  - 左パネルに「編集ツール」グループ追加、ドロップダウン式の **「レベルクリア ▼」** ボタン
  - 4種類のクリアモード:
    - **すべてクリア**（ブロック+アイテム+敵を一括削除、鍵/扉/スタート/ミラー/星座は保持）
    - **ブロックのみクリア**
    - **アイテムのみクリア**
    - **モンスターのみクリア**
  - 削除前に確認ダイアログ
  - Undo履歴に積むので **Ctrl+Z で戻せる**

## v0.1.14 (2026-05-10)

### 追加
- **Undo / Redo** 機能を実装 (Phase 4-1)
  - キーバインド:
    - **Ctrl+Z** = Undo（編集取り消し）
    - **Ctrl+Y** または **Ctrl+Shift+Z** = Redo（やり直し）
  - 履歴上限: **50件**（古いものから自動破棄）
  - レベル単位のスナップショット (deepcopy) 方式
  - 対象操作: 左クリック配置 / 右クリック削除 / Ctrl+ドラッグ移動 / 単一XML上書き読込
  - ドラッグ移動は drag_start で1回だけ履歴を積む（drag_move では積まない）
  - Undo/Redoで他レベルの状態も復元される（自動でレベル切替）
  - ROM/XML一括読込時はUndo履歴をクリア
  - ステータスバーに残履歴件数を表示

## v0.1.13 (2026-05-10)

### 追加
- **既存形式互換 XML 入出力** を実装
  - 新規モジュール `magatu_skc/core/xml_io.py`
  - 4ボタン追加（ファイル欄）:
    - **XML出力(現在)**: 現在のレベルを既存形式XMLとして保存
    - **XML出力(全)**: 全53レベルを `level-NN.xml` ファイル群でフォルダ保存
    - **XML読込(現在)**: XMLから読み込んで現在のレベルに上書き
    - **XML読込(全)**: フォルダから `level-NN.xml` を一括読み込み
  - 既存XMLフォーマット互換（相互運用可能）
  - 53レベル全てで round-trip 完全一致を検証済み

## v0.1.12 (2026-05-10)

### 追加
- ピッカーのアイテム一覧に **不足していた12種類**を追加
  - 0x08 Diamond (blue, modifiable)
  - 0x0c Diamond (orange, modifiable)
  - 0x0e Scroll (modifiable)
  - 0x11 Timebottle (half)
  - 0x1c Shrine #1
  - 0x1d Shrine #2
  - 0x1e Shrine #3
  - 0x1f Shrine #4
  - 0x26 Double Coin (silver)
  - 0x29 Double Coin (gold)
  - 0x2d Opal (dark orange)
  - 0x2f Demonhead Coin
  - 0x30 Sphinx, 0x31 Egyptian Head（拡充）
  - これでUSA ROM原作で使われている全実用アイテムを網羅（合計36種類）
  - L36の Shrine #1 等、原作にあるのにピッカーから配置できなかった問題を解消

## v0.1.11 (2026-05-10)

### 追加
- ファイル欄に **「再読込」** ボタンと **「履歴」** ボタンを追加
  - 再読込: 現在のROMを再ロード（編集を破棄、初期状態に戻す）
  - 履歴: 最近開いたROM最大15件のメニューを表示。クリックで読み込み。「履歴をクリア」あり
  - 履歴は `rom_history.json` に永続保存

## v0.1.10 (2026-05-10)

### 変更
- **敵 × 敵 の同位置重複を許可**（USA ROM検証で原作に8件あり、意図的な配置と確認）
  - 旧: 同位置に既存の敵がいると上書き削除
  - 新: 上書きせず追加。複数体が同じマスに置ける
  - ステータスバーに「このマスに{N}体」と表示
- アイテム × アイテム の重複は引き続き禁止（原作0件、レギュレーション準拠）
  - 既存アイテムを置き換える際にステータスバーで通知
- 右クリック削除はループで全要素削除するため、同マスに複数の敵があっても一括で消せる

### 検証データ
USA ROM 全53レベルの重複パターン調査:

| パターン | 件数 | 対応方針 |
|---|---:|---|
| アイテム × アイテム | 0 | 禁止（既存削除→置換） |
| 敵 × 敵 | 8 | **許可（重複OK）** |
| アイテム + 敵 | 6 | 自由配置可能 |
| 白ブロック内アイテム | 0 | 暗黙ルール |

## v0.1.9 (2026-05-10)

### 追加
- アイテム配置時のフラグ選択UIを追加
  - ピッカー上部に **「通常 / 隠し (0x40) / ブロック内 (0x80)」** のラジオボタン
  - 「アイテム」モード時のみ表示（他モードでは非表示）
  - 配置時に選択中のフラグを `element_no` に OR して書き込み
  - **配置レギュレーション自動適用**: 隠し専用アイテム（Warp/Origami Swan/Demonhead Coin/Sphinx/Egyptian Head/Magic Lamp）を選択すると **自動で「隠し」ラジオに切替**
  - 既存アイテムのフラグ変更UIは無し（削除→再配置 or 上書き配置で対応）

## v0.1.8 (2026-05-10)

### 変更
- 右クリック削除を**編集モード非依存**に変更
  - 旧: 「アイテム」モードのときはアイテムしか消えない / 「ブロック」モードのときはブロックしか消えない
  - 新: モード関係なく、その位置にある **アイテム/敵/ブロック を全て削除**
  - メタ要素（鍵/扉/スタート/ミラー）は移動が原則のため削除対象外
  - 削除内容をステータスバーに表示

## v0.1.7 (2026-05-10)

### 追加
- ピッカーの「ブロック」モードに **「壊せる白ブロック (見た目=白/実体=壊せる)」** を追加
  - `Wall.BROWN_WHITE` (茶＋白の両ビットON) を配置可能に
  - 描画は通常の白ブロックだが、隠し要素強調 (G で切替) 時に**緑枠**で強調表示
  - 緑枠＝「ブロック系の罠的要素」、黄色枠＝「アイテム系の隠し」と色で区別
  - USA ROMで10件存在（L47に3個集中、その他は右端列の壁が大半）

## v0.1.6 (2026-05-10)

### 変更
- Ctrl+左クリック移動を「2回クリック方式」から「ドラッグ&ドロップ方式」に変更
  - **Ctrl押下しながら左ボタンで掴む** → そのままマウス移動で要素が追従 → **Ctrl解放 or ボタン解放で確定**
  - 直感的でシンプルな操作にした
  - 旧方式（2回クリック）は廃止

## v0.1.5 (2026-05-10)

### 追加
- **Ctrl+左クリックで要素移動**機能を追加
  - 1回目のCtrl+クリック: その位置の要素を掴む（アイテム/敵/鍵/扉/スタート/ミラー1/ミラー2）
  - 2回目のCtrl+クリック: 移動先タイルへドロップ（隠し/ブロック内フラグ等は保持）
  - 通常の左クリック / 同じ位置をCtrl+クリック で移動操作キャンセル
  - 移動先に既存アイテムや敵がある場合は中止（誤上書き防止）
  - ステータスバーに状態表示

## v0.1.4 (2026-05-10)

### 修正
- メタアイテム（ソロモンの紋章/テクモバニー等）の隠し/in_block 描画処理を追加
  - 該当位置に茶色ブロックがある → in_block 表現（アイテム → 半透明ブロックを上に重ねる）
  - ブロックなし & `transparent="true"` → 半透明アイテム（隠し表現）
  - 隠し要素強調（黄色枠）にも対応
  - 通常アイテムと同じ「いつもの形」に統一

## v0.1.3 (2026-05-10)

### 修正
- ピッカー（編集対象リスト）のアイテム/敵アイコンの色がおかしい不具合を修正
  - 原因1: `mask_brick_color=True` がスプライトの本体色（palette index 1）まで透明化していたため、本体ピクセルが消失して全アイテムが青っぽく/スカスカに見えていた
  - 原因2: ピッカーのアイコンが常にタイルセット0で描画されていた
  - 対応: マスク廃止 + `tile_renderer.get_tile_image()` を経由して描画。`set_current_tileset_no()` を追加し、レベル切替時にアイコンを現在レベルのタイルセットで再描画するように変更
  - 結果: 配置時とピッカーの色が完全一致

## v0.1.2 (2026-05-10)

### 修正
- メタアイテム（ソロモンの紋章＝六芒星パネル、ボムジャック、テクモバニー、Page of Time/Space）が表示されない不具合を修正
  - 原因: `level_meta_items` の読み込み・描画処理が未実装だった
  - 対応: `config_loader.py` に `MetaItemDef` を追加し、リージョンごとに ROM オフセットから位置をデコード。`level_renderer.py` で該当レベルにのみ描画
  - 確認: JP版で14個のメタアイテムが正常に配置される（六芒星×8、ボムジャック×2、テクモバニー×2、Page×2）

## v0.1.1 (2026-05-10)

### 修正
- BESK等の旧エディタで改造されたROMが「Unknown ROM region」で読み込めない不具合を修正
  - 原因: BESKがリージョン判定オフセット (0x0bf2) も上書きするため、ルールベース判定が外れる
  - 対策: ルールが外れた場合、CHR-ROM の CRC32 によるフォールバック判定を追加（CHR-ROM はエディタが触らないので信頼できる）
  - 既知CHR CRC32: US=`FAD8A464`, JP=`EBCA054B`（EU は未確認）

## v0.1.0 (2026-05-10)

初回リリース。主要なROMエディタ機能をPythonで実装。

### 機能
- ROM読み込み (US / JP / EU / 拡張ROM US66 自動判別)
- 全53レベル解析・表示
- レベル可視化 (ブロック・アイテム・敵・鍵・扉・スタート位置・ミラー・星座背景)
- ブロック編集 (左クリックで配置、右クリックで削除)
- アイテム配置 (主要20種)
- 敵配置 (主要20種)
- 鍵/扉/スタート/ミラー位置の変更
- 通常ROM保存 (.nes)
- IPSパッチ生成 (.ips)
- 単一レベル / 全レベル PNG エクスポート
- グリッド表示切替
- 隠し要素オーバーレイ表示
- 既存形式の `skc_config.xml` を利用

### キーバインド
- F1: ヘルプ
- F9: 設定画面 (未実装)
- PageUp/Down: レベル切替
- G: グリッド表示切替

### 既知の制限
- 拡張ROM(US66)の保存は未対応
- 設定画面 (F9) 未実装
- アイテムの「隠し」「ブロック内」フラグの編集UI未実装
- デーモンミラーのドロップスケジュール・敵セット編集UI未実装
- アイテム/敵の選択UIが英語表記のみ
- 起動時自動バックアップ未実装
