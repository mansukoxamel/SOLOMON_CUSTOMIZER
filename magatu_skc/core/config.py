"""アプリケーション設定の保存/読込

設定ファイル: プロジェクトルートの config/magatu_skc_config.json
"""
import json
from pathlib import Path


DEFAULT_CONFIG = {
    # 表示
    "dirty_mark": "●",
    # 外部連携
    "emulator_path": "",
    # ピッカーのお気に入り（10スロット, [mode, value] or null）
    "picker_favorites": [None] * 10,
    # ウィンドウ状態
    "window_x": -1,           # -1 = 未保存（デフォルト位置）
    "window_y": -1,
    "window_w": 1400,
    "window_h": 800,
    "window_maximized": False,
    "splitter_sizes": [280, 700, 250, 220],  # [LEFT, CENTER, PICKER, LEVEL_SELECT]
    # ゲーム挙動改造ダイアログ サイズ/位置 (-1 = 未保存=既定)
    "hack_dlg_x": -1,
    "hack_dlg_y": -1,
    "hack_dlg_w": -1,
    "hack_dlg_h": -1,
    # 全レベル統計ダイアログ サイズ/位置 (-1 = 未保存=既定)
    "stats_dlg_x": -1,
    "stats_dlg_y": -1,
    "stats_dlg_w": -1,
    "stats_dlg_h": -1,
    "stats_dlg_col_w": [],   # 全レベル統計 列幅 ([] = 未保存=自動)
    # SOLOMON_CUSTOMIZER標準（今後実装予定）
    "icon_path": "",
    "font_family": "",
    "font_size": 0,
    "font_bold": False,
    "theme_gray": 18,
    "notification_sound_path": "",
    "notification_sound_volume": 1.0,
    "cloud_backup_path": "",
}


def get_config_path() -> Path:
    """設定ファイルのパス"""
    return Path(__file__).parent.parent.parent / "config" / "magatu_skc_config.json"


def load_config() -> dict:
    """設定を読み込む（無ければデフォルト）"""
    p = get_config_path()
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            cfg = dict(DEFAULT_CONFIG)
            cfg.update(data)
            return cfg
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)


def save_config(cfg: dict):
    """設定を保存"""
    p = get_config_path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
