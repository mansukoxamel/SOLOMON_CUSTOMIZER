"""アプリケーション設定の保存/読込

設定ファイル: プロジェクトルートの config/magatu_skc_config.json
"""
import json
import sys
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parent.parent.parent
APP_ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else SOURCE_ROOT
DATA_ROOT = Path(getattr(sys, "_MEIPASS", APP_ROOT)).resolve()
DEFAULT_ICON_PATH = "docs/images/dana.png"
DEFAULT_AUTOSAVE_KEEP_COUNT = 10
MIN_AUTOSAVE_KEEP_COUNT = 1
MAX_AUTOSAVE_KEEP_COUNT = 999
DEFAULT_UNDO_LIMIT = 200
MIN_UNDO_LIMIT = 1
MAX_UNDO_LIMIT = 999
DEFAULT_HOVER_INFO_POPUP_FONT_SIZE = 16
MIN_HOVER_INFO_POPUP_FONT_SIZE = 10
MAX_HOVER_INFO_POPUP_FONT_SIZE = 40


def normalize_int_setting(value, default: int, minimum: int, maximum: int) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        n = int(default)
    return max(int(minimum), min(int(maximum), n))


DEFAULT_CONFIG = {
    # 表示
    "dirty_mark": "●",
    # 外部連携
    "emulator_path": "",
    # ピッカーのお気に入り（10スロット, [mode, value] or null）
    "picker_favorites": [None] * 10,
    "picker_block_order": [
        "none",
        "brown",
        "white",
        "breakable_white",
        "invisible_breakable",
        "passable_white",
        "invisible_solid",
        "passable_brown",
        "solid_brown",
    ],
    # ウィンドウ状態
    "window_x": -1,           # -1 = 未保存（デフォルト位置）
    "window_y": -1,
    "window_w": 1400,
    "window_h": 800,
    "window_fullscreen": False,
    "window_maximized": False,
    "splitter_sizes": [280, 700, 250, 220],  # [LEFT, CENTER, PICKER, LEVEL_SELECT]
    "stage_thumbnail_width": 160,
    "picker_icon_size": 36,
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
    "icon_path": DEFAULT_ICON_PATH,
    "font_family": "",
    "font_size": 0,
    "font_bold": False,
    "theme_gray": 18,
    "marker_overlay_scale": 3,
    "bonus_marker_color": "#FFC800",
    "hidden_marker_color": "#FFDC00",
    "breakable_white_marker_color": "#50E65A",
    "invisible_breakable_marker_color": "#FFDC28",
    "passable_marker_color": "#50BEFF",
    "solid_marker_color": "#FF78DC",
    "breakable_white_marker_shape": "rect_large",
    "invisible_breakable_marker_shape": "rect_small",
    "passable_marker_shape": "cross_medium",
    "solid_marker_shape": "ellipse_small",
    "mirror1_marker_color": "#FF3C3C",
    "mirror2_marker_color": "#3C78FF",
    "special_empty_marker_color": "#B4C8FF",
    "special_trigger_marker_color": "#FF64C8",
    "special_link_marker_color": "#FFC864",
    "selection_marker_color": "#FFE600",
    "hover_marker_color": "#FFFFFF",
    "notification_sound_path": "",
    "notification_sound_volume": 1.0,
    "cloud_backup_path": "",
    "autosave_keep_count": DEFAULT_AUTOSAVE_KEEP_COUNT,
    "undo_limit": DEFAULT_UNDO_LIMIT,
    "hover_info_popup_enabled": False,
    "hover_info_popup_font_size": DEFAULT_HOVER_INFO_POPUP_FONT_SIZE,
}


def resolve_project_path(path_value: str | Path) -> Path:
    """設定内の相対パスをアプリ/同梱データ基準に解決する。"""
    p = Path(path_value)
    if p.is_absolute():
        return p
    app_path = APP_ROOT / p
    if app_path.exists():
        return app_path
    return DATA_ROOT / p


def get_config_path() -> Path:
    """設定ファイルのパス"""
    return APP_ROOT / "config" / "magatu_skc_config.json"


def load_config() -> dict:
    """設定を読み込む（無ければデフォルト）"""
    p = get_config_path()
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            cfg = dict(DEFAULT_CONFIG)
            cfg.update(data)
            if not cfg.get("icon_path"):
                cfg["icon_path"] = DEFAULT_ICON_PATH
            cfg["autosave_keep_count"] = normalize_int_setting(
                cfg.get("autosave_keep_count"),
                DEFAULT_AUTOSAVE_KEEP_COUNT,
                MIN_AUTOSAVE_KEEP_COUNT,
                MAX_AUTOSAVE_KEEP_COUNT,
            )
            cfg["undo_limit"] = normalize_int_setting(
                cfg.get("undo_limit"),
                DEFAULT_UNDO_LIMIT,
                MIN_UNDO_LIMIT,
                MAX_UNDO_LIMIT,
            )
            cfg["hover_info_popup_font_size"] = normalize_int_setting(
                cfg.get("hover_info_popup_font_size"),
                DEFAULT_HOVER_INFO_POPUP_FONT_SIZE,
                MIN_HOVER_INFO_POPUP_FONT_SIZE,
                MAX_HOVER_INFO_POPUP_FONT_SIZE,
            )
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
