# SOLOMON_CUSTOMIZER

ファミコン版『ソロモンの鍵』向けのROMカスタマイズツールです。  
既存ROMを読み込み、ステージデータや一部のゲーム挙動を編集して、改造ROM・IPSパッチ・ステージPNGデータとして保存できます。

## 重要

- このリポジトリにROMデータは含まれません。
- 利用者が所有しているROMを読み込んで使う前提です。
- 現在の通常編集ターゲットは、日本版ROMをアプリ内で mapper66 / wide-title 形式へ拡張したものです。
- US ROMは通常編集対象ではなく、タイトル移植など限定用途の素材として扱います。

## 必要環境

- Python 3.10 以上
- PyQt5

```bat
pip install -r requirements.txt
```

## 起動

```bat
python SOLOMON_CUSTOMIZER.py
```


## 主な機能

- 全53ステージの表示・編集
- ブロック、アイテム、敵、メタ要素の編集
- 日本版ROMの mapper66 / wide-title 形式への自動変換
- グローバル設定の編集
- ROM保存時のステージPNGデータとグローバル設定JSONの同時保存
- テストプレイ用のタイトル/開始演出短縮
- IPSパッチ出力

## 出力

- `.nes`: パッチ済みROM
- `.ips`: 元ROMとの差分パッチ
- `.png`: METAデータにステージデータを埋め込んだ画像
- `.json`: グローバル設定

詳細な操作は [MANUAL.md](MANUAL.md) を参照してください。
