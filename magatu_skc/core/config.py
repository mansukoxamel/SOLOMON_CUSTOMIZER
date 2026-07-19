"""アプリケーション設定の保存/読込

設定ファイル: プロジェクトルートの config/magatu_skc_config.json
"""
import json
from json import JSONDecodeError
import os
import sys
import tempfile
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
DEFAULT_LANGUAGE = "ja"
SUPPORTED_LANGUAGES = {"ja", "en"}
DEFAULT_PANEL_VARIANT_SETTINGS = {
    "a_speed": 0,
    "a_interval": 0xC0,
    "b_speed": 1,
    "b_interval": 0xC0,
    "c_speed": 2,
    "c_interval": 0xC0,
    "d_speed": 3,
    "d_interval": 0xC0,
}
DEFAULT_EMULATORS = []

SHORTCUT_DEFINITIONS = [
    ("help", "ショートカットヘルプ", "F1"),
    ("open_rom", "ROMを開く", "Ctrl+O"),
    ("save_rom", "ROM保存", "Ctrl+S"),
    ("save_stage_png", "現在ステージのステージデータPNG保存", "Ctrl+E"),
    ("stage_jump", "ステージ番号ジャンプ", "Ctrl+L"),
    ("show_stats", "全ステージ統計", "Ctrl+I"),
    ("open_binary_editor", "バイナリエディタで開く", "Ctrl+B"),
    ("test_play", "テストプレイ", "P"),
    ("stage_prev", "前のステージ", "PgUp"),
    ("stage_next", "次のステージ", "PgDown"),
    ("stage_compare_edit_start", "比較編集開始", "Ctrl+Q"),
    ("stage_compare_edit_orientation", "比較編集の縦横切替", "Q"),
    ("settings", "設定", "F9"),
    ("grid", "グリッド表示切替", "G"),
    ("undo", "Undo", "Ctrl+Z"),
    ("redo", "Redo", "Ctrl+Y"),
    ("redo_alt", "Redo代替", "Ctrl+Shift+Z"),
    ("select_all", "編集エリア全体を選択", "Ctrl+A"),
    ("clear_selection", "選択解除", "Ctrl+D"),
    ("copy_selection", "コピー", "Ctrl+C"),
    ("paste_selection", "ペースト", "Ctrl+V"),
    ("cut_selection", "切り取り", "Ctrl+X"),
    ("item_replace", "オブジェクト一括置換", "Ctrl+H"),
    ("item_flag_toggle", "ホバー位置のアイテム状態切替", "Tab"),
    ("item_flag_toggle_reverse", "ホバー位置のアイテム状態逆切替", "Shift+Tab"),
    ("delete_hover_or_selection", "ホバー/選択範囲を削除", "Delete"),
    ("delete_hover_or_selection_alt", "ホバー/選択範囲を削除 代替", "Backspace"),
    ("clear_selection_escape", "選択解除(Esc)", "Esc"),
    ("flip_horizontal", "選択範囲を左右反転", "F"),
    ("flip_vertical", "選択範囲を上下反転", "Shift+F"),
    ("favorite_1", "お気に入りスロット1", "1"),
    ("favorite_2", "お気に入りスロット2", "2"),
    ("favorite_3", "お気に入りスロット3", "3"),
    ("favorite_4", "お気に入りスロット4", "4"),
    ("favorite_5", "お気に入りスロット5", "5"),
    ("favorite_6", "お気に入りスロット6", "6"),
    ("favorite_7", "お気に入りスロット7", "7"),
    ("favorite_8", "お気に入りスロット8", "8"),
    ("favorite_9", "お気に入りスロット9", "9"),
    ("favorite_0", "お気に入りスロット0", "0"),
    ("hover_enemy_left", "ホバー敵を左向きに変更", "Left"),
    ("hover_enemy_right", "ホバー敵を右向きに変更", "Right"),
    ("hover_enemy_up", "ホバー敵を上向きに変更", "Up"),
    ("hover_enemy_down", "ホバー敵を下向きに変更", "Down"),
    ("hover_enemy_speed", "ホバー敵スピード循環", "S"),
    ("hover_enemy_enhance", "ホバー敵の強化/別版切替", "K"),
    ("hover_info", "ホバー情報表示切替", "I"),
    ("hover_item_normal", "ホバー位置を通常に変更", "N"),
    ("hover_item_hidden", "ホバー位置を隠しに変更", "H"),
    ("hover_item_in_block", "ホバー位置をブロック内に変更", "B"),
    ("hover_item_white_in_block", "ホバー位置を白ブロック内に変更", "W"),
    ("hover_item_visible_in_block", "ホバー位置を透明ブロック内に変更", "T"),
    ("hover_item_cracked_in_block", "ホバー位置をひび割れブロック内に変更", "C"),
]
DEFAULT_SHORTCUTS = {key: default for key, _label, default in SHORTCUT_DEFINITIONS}


def shortcut_display_label(action: str, fallback: str = "") -> str:
    from .i18n import t
    return t(f"shortcut.label.{action}", fallback or str(action))

GAMEPAD_BUTTON_OPTIONS = [
    ("", "未割当"),
    ("A", "A"),
    ("B", "B"),
    ("X", "X"),
    ("Y", "Y"),
    ("Back", "Back/View"),
    ("Start", "Start/Menu"),
    ("LB", "LB"),
    ("RB", "RB"),
    ("LStick", "左スティック押し込み"),
    ("RStick", "右スティック押し込み"),
    ("DPadUp", "十字 上"),
    ("DPadDown", "十字 下"),
    ("DPadLeft", "十字 左"),
    ("DPadRight", "十字 右"),
]
DEFAULT_GAMEPAD_SHORTCUTS = {
    key: "" for key, _label, _default in SHORTCUT_DEFINITIONS
}
DEFAULT_GAMEPAD_SHORTCUTS.update({
    "test_play": "Start",
    "stage_prev": "LB",
    "stage_next": "RB",
})


def normalize_int_setting(value, default: int, minimum: int, maximum: int) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        n = int(default)
    return max(int(minimum), min(int(maximum), n))


def normalize_shortcuts(value) -> dict:
    shortcuts = dict(DEFAULT_SHORTCUTS)
    if isinstance(value, dict):
        for key, _label, default in SHORTCUT_DEFINITIONS:
            raw = value.get(key, default)
            if raw is None:
                raw = default
            shortcuts[key] = str(raw).strip()
    return shortcuts


def normalize_gamepad_shortcuts(value) -> dict:
    valid = {button for button, _label in GAMEPAD_BUTTON_OPTIONS}
    shortcuts = dict(DEFAULT_GAMEPAD_SHORTCUTS)
    if isinstance(value, dict):
        for key, _label, _default in SHORTCUT_DEFINITIONS:
            raw = str(value.get(key, shortcuts.get(key, "")) or "").strip()
            shortcuts[key] = raw if raw in valid else shortcuts.get(key, "")
    return shortcuts


def normalize_panel_variant_settings(value) -> dict:
    settings = dict(DEFAULT_PANEL_VARIANT_SETTINGS)
    if isinstance(value, dict):
        for key in ("a_speed", "b_speed", "c_speed", "d_speed"):
            settings[key] = normalize_int_setting(
                value.get(key),
                DEFAULT_PANEL_VARIANT_SETTINGS[key],
                0,
                3,
            )
        for key in ("a_interval", "b_interval", "c_interval", "d_interval"):
            settings[key] = normalize_int_setting(
                value.get(key),
                DEFAULT_PANEL_VARIANT_SETTINGS[key],
                1,
                255,
            )
    return settings


def normalize_language(value) -> str:
    lang = str(value or DEFAULT_LANGUAGE).strip().lower()
    if lang in SUPPORTED_LANGUAGES:
        return lang
    return DEFAULT_LANGUAGE


def config_has_language_setting() -> bool:
    p = get_config_path()
    if not p.exists():
        return False
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return False
    if not isinstance(data, dict):
        return False
    lang = str(data.get("language", "") or "").strip().lower()
    return lang in SUPPORTED_LANGUAGES


def normalize_emulators(value) -> list[dict]:
    emulators = []
    seen_ids = set()
    if isinstance(value, list):
        for i, raw in enumerate(value, 1):
            if not isinstance(raw, dict):
                continue
            path = str(raw.get("path", "") or "").strip()
            emu_id = str(raw.get("id", "") or "").strip() or f"emu_{i}"
            base_id = emu_id
            suffix = 2
            while emu_id in seen_ids:
                emu_id = f"{base_id}_{suffix}"
                suffix += 1
            seen_ids.add(emu_id)
            name = str(raw.get("name", "") or "").strip()
            if not name:
                name = Path(path).stem if path else f"エミュレータ {len(emulators) + 1}"
            emulators.append({
                "id": emu_id,
                "name": name,
                "path": path,
            })
    return emulators


DEFAULT_CONFIG = {
    # 表示
    "dirty_mark": "●",
    "language": DEFAULT_LANGUAGE,
    # 外部連携
    "emulators": DEFAULT_EMULATORS,
    "default_emulator_id": "",
    "binary_editor_path": "",
    "test_play_quick_start": True,
    "stage_png_show_secrets": True,
    "developer_mode": False,
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
    "settings_dialog_x": -1,
    "settings_dialog_y": -1,
    "settings_dialog_w": 700,
    "settings_dialog_h": 780,
    "settings_dialog_tab": 0,
    "splitter_sizes": [240, 740, 250, 220],  # [LEFT, CENTER, PICKER, LEVEL_SELECT]
    "stage_thumbnail_width": 160,
    "picker_icon_size": 36,
    "enemy_count_meter_slot_size": 18,
    "last_session_restore_kind": "",
    "last_readonly_rom_path": "",
    "last_readonly_rom_level_no": 0,
    "last_file_dialog_dirs": {},
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
    # スプライト/キャラクタービューア サイズ/位置 (-1 = 未保存=既定)
    "sprite_viewer_x": -1,
    "sprite_viewer_y": -1,
    "sprite_viewer_w": -1,
    "sprite_viewer_h": -1,
    # 16x16ピクセル編集 サイズ/位置 (-1 = 未保存=既定)
    "pixel_editor_x": -1,
    "pixel_editor_y": -1,
    "pixel_editor_w": -1,
    "pixel_editor_h": -1,
    # 各種編集/表示ダイアログ サイズ/位置 (-1 = 未保存=既定)
    "palette_dlg_x": -1,
    "palette_dlg_y": -1,
    "palette_dlg_w": -1,
    "palette_dlg_h": -1,
    "enemy_drop_dlg_x": -1,
    "enemy_drop_dlg_y": -1,
    "enemy_drop_dlg_w": -1,
    "enemy_drop_dlg_h": -1,
    "demo_input_dlg_x": -1,
    "demo_input_dlg_y": -1,
    "demo_input_dlg_w": -1,
    "demo_input_dlg_h": -1,
    "clear_message_dlg_x": -1,
    "clear_message_dlg_y": -1,
    "clear_message_dlg_w": -1,
    "clear_message_dlg_h": -1,
    "title_screen_dlg_x": -1,
    "title_screen_dlg_y": -1,
    "title_screen_dlg_w": -1,
    "title_screen_dlg_h": -1,
    "special_process_dlg_x": -1,
    "special_process_dlg_y": -1,
    "special_process_dlg_w": -1,
    "special_process_dlg_h": -1,
    "sound_viewer_dlg_x": -1,
    "sound_viewer_dlg_y": -1,
    "sound_viewer_dlg_w": -1,
    "sound_viewer_dlg_h": -1,
    "mirror_dlg_x": -1,
    "mirror_dlg_y": -1,
    "mirror_dlg_w": -1,
    "mirror_dlg_h": -1,
    "mirror_overview_dlg_x": -1,
    "mirror_overview_dlg_y": -1,
    "mirror_overview_dlg_w": -1,
    "mirror_overview_dlg_h": -1,
    "bonus_stage_dlg_x": -1,
    "bonus_stage_dlg_y": -1,
    "bonus_stage_dlg_w": -1,
    "bonus_stage_dlg_h": -1,
    "item_replace_dlg_x": -1,
    "item_replace_dlg_y": -1,
    "item_replace_dlg_w": -1,
    "item_replace_dlg_h": -1,
    "keyboard_map_dlg_x": -1,
    "keyboard_map_dlg_y": -1,
    "keyboard_map_dlg_w": -1,
    "keyboard_map_dlg_h": -1,
    "rom_diff_dlg_x": -1,
    "rom_diff_dlg_y": -1,
    "rom_diff_dlg_w": -1,
    "rom_diff_dlg_h": -1,
    "rom_diff_dlg_splitter": [],
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
    "panel_variant_settings": DEFAULT_PANEL_VARIANT_SETTINGS,
    "shortcuts": DEFAULT_SHORTCUTS,
    "gamepad_shortcuts": DEFAULT_GAMEPAD_SHORTCUTS,
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
            if not isinstance(cfg.get("developer_mode"), bool):
                cfg["developer_mode"] = DEFAULT_CONFIG["developer_mode"]
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
            cfg["language"] = normalize_language(cfg.get("language"))
            cfg["shortcuts"] = normalize_shortcuts(cfg.get("shortcuts"))
            cfg["gamepad_shortcuts"] = normalize_gamepad_shortcuts(
                cfg.get("gamepad_shortcuts")
            )
            cfg["emulators"] = normalize_emulators(cfg.get("emulators"))
            valid_emu_ids = {emu["id"] for emu in cfg["emulators"]}
            if cfg.get("default_emulator_id") not in valid_emu_ids:
                cfg["default_emulator_id"] = (
                    cfg["emulators"][0]["id"] if cfg["emulators"] else ""
                )
            cfg["panel_variant_settings"] = normalize_panel_variant_settings(
                cfg.get("panel_variant_settings")
            )
            return cfg
        except JSONDecodeError as e:
            cfg = dict(DEFAULT_CONFIG)
            cfg["_config_load_error"] = str(e)
            cfg["_config_load_error_line"] = int(getattr(e, "lineno", 0) or 0)
            cfg["_config_load_error_column"] = int(getattr(e, "colno", 0) or 0)
            cfg["_config_path"] = str(p)
            return cfg
        except Exception:
            cfg = dict(DEFAULT_CONFIG)
            cfg["_config_load_error"] = "unknown"
            cfg["_config_path"] = str(p)
            return cfg
    cfg = dict(DEFAULT_CONFIG)
    cfg["shortcuts"] = normalize_shortcuts(cfg.get("shortcuts"))
    cfg["gamepad_shortcuts"] = normalize_gamepad_shortcuts(
        cfg.get("gamepad_shortcuts")
    )
    cfg["language"] = normalize_language(cfg.get("language"))
    cfg["emulators"] = normalize_emulators(cfg.get("emulators"))
    cfg["panel_variant_settings"] = normalize_panel_variant_settings(
        cfg.get("panel_variant_settings")
    )
    return cfg


def save_config(cfg: dict):
    """設定を保存"""
    if isinstance(cfg, dict) and cfg.get("_config_load_error"):
        return False
    p = get_config_path()
    temp_path = None
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{p.name}.",
            suffix=".tmp",
            dir=str(p.parent),
        )
        temp_path = Path(temp_name)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(
                {k: v for k, v in cfg.items() if not str(k).startswith("_config_")},
                f,
                ensure_ascii=False,
                indent=2,
            )
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, p)
        temp_path = None
        return True
    except Exception:
        return False
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except Exception:
                pass
