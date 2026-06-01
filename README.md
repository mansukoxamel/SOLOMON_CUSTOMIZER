# SOLOMON_CUSTOMIZER

[日本語](#日本語) / [English](#english)

## 日本語

ファミコン版『ソロモンの鍵』を、ステージエディタの範囲を超えて改造できるカスタマイザーです。  
日本版ROMを mapper66 / wide-title 形式へ自動拡張し、ステージ配置だけでなく、敵AI、弾速、部屋別ルール、タイトル画面、パレット、テストプレイ用ROM生成までGUIから扱えます。

![SOLOMON_CUSTOMIZER main window](docs/images/readme_main_window.png)

## 目玉機能

- 日本版ROMを mapper66 / wide-title 形式へ自動変換して容量制約を広げる
- 全53ステージのブロック、アイテム、敵、鍵、扉、スタート位置をGUI編集
- 隠しアイテム、ブロック内アイテム、特殊メタ要素を見える形で配置
- 部屋ごとにBファイア禁止、A換石禁止、隠し扉、暗闇ステージを設定
- デーモンミラーの出現敵、出現スケジュール、敵寿命を詳細編集
- Panel Variant A/B/Cの弾速と発射間隔をステージごとに調整
- パネルモンスター弾の左右速度バグ修正と弾速プリセットを適用
- Spark Ball、Ghost/Neul、Golem/Dragon/Gargoyleなどの移動速度を調整
- 強化スパークボール、強化ガーゴイル、Demonheadなど敵AI拡張を設定
- 敵撃破時のドロップ内容と確率をテーブル編集
- ワープ羽の進行数、初期魔法、初期残数、制限時間、暗闇テンポを変更
- タイトル画面を別ROMから移植し、上部ロゴPNG読込/保存やタイトル色編集に対応
- メインパレットとステージ壁色を編集し、表示を即時プレビュー
- 全ステージ統計で重要アイテム、敵、ミラー敵、部屋フラグを一覧確認
- スプライト/キャラクタービューアでROM内フレームやCHRタイルを確認
- 現在ステージから始まる一時ROMを作って、そのままエミュレータでテストプレイ
- `.nes`、`.ips`、ステージデータ入り `.png`、設定 `.json` の出力

## 重要

- このリポジトリにROMデータは含まれません。
- 所有しているROMを読み込んで使う前提です。
- US ROMは通常編集対象ではなく、タイトル移植など限定用途の素材としてだけ扱います。
- 『ソロモンの鍵』および関連する名称・画像・ゲーム内容の権利は、テクモ / コーエーテクモゲームスおよび各権利者に帰属します。
- このツールは非公式のファン制作ツールです。権利上の問題や掲載内容への懸念がある場合は、GitHub Issues等でご連絡ください。確認次第、該当内容を修正または削除します。

## 起動

- Python 3.10 以上
- PyQt5

```bat
pip install -r requirements.txt
python SOLOMON_CUSTOMIZER.py
```

詳細な操作は [MANUAL.md](MANUAL.md) を参照してください。

## 参考・謝辞

SOLOMON_CUSTOMIZERの開発では、過去に作られたソロモンの鍵向け編集・解析ツールから多くの知見を参考にしています。

- BESK（Binary Editor for Solomon's Key）
- skedit
- skchain

これらのツールと作者の方々に感謝します。

## English

SOLOMON_CUSTOMIZER is a GUI customizer for the Famicom version of *Solomon's Key*.
It automatically expands the Japanese ROM to the mapper66 / wide-title format and lets you edit much more than stage layouts.

### Highlights

- Converts a Japanese ROM into the expanded mapper66 / wide-title format
- Edits all 53 stages: blocks, items, enemies, keys, doors, and start positions
- Configures room rules such as B-fire disable, A-button stone disable, hidden doors, and dark rooms
- Edits Demon Mirror enemy spawns, schedules, and enemy lifetimes
- Adjusts panel monster projectile timing/speed and applies projectile bug fixes
- Tunes enemy behaviors and speed values, including enhanced enemy variants
- Edits item drops, player starting values, timers, palettes, wall colors, and title-screen assets
- Exports `.nes`, `.ips`, stage-data `.png`, and settings `.json` files
- Builds a temporary test ROM from the current stage for emulator playtesting

### Important

- ROM data is not included in this repository.
- Use this tool with a ROM you own.
- US ROMs are not normal editing targets; they are only used as limited asset sources, such as for title-screen import.
- *Solomon's Key* and related names, images, and game content are owned by Tecmo / Koei Tecmo Games and their respective rights holders.
- This is an unofficial fan-made tool. If any rights holder has concerns about this project or its contents, please contact us through GitHub Issues so the relevant material can be modified or removed.

### Run

Requirements:

- Python 3.10 or later
- PyQt5

```bat
pip install -r requirements.txt
python SOLOMON_CUSTOMIZER.py
```

For detailed usage, see [MANUAL.en.md](MANUAL.en.md).

### Credits

SOLOMON_CUSTOMIZER was developed with reference to knowledge from earlier Solomon's Key editing and research tools:

- BESK (Binary Editor for Solomon's Key)
- skedit
- skchain

Many thanks to these tools and their authors.
