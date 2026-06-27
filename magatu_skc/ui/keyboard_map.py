"""
keyboard_map.py - ショートカットキーMAP 共通コンポーネント

MAGATUシリーズ共通モジュール。config モジュールの KEY_* 変数を自動収集し、
キーボードの物理配列に色分け表示する。

使い方:
    from keyboard_map import KeyboardMapDialog, save_keyboard_map_image
    import config

    # ダイアログ表示
    KeyboardMapDialog.show_from_config(parent, config, title="ショートカットMAP")

    # PNG画像として保存
    save_keyboard_map_image(config, "shortcuts.png")
"""

import os
import re
import json
import inspect
from pathlib import Path
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QPushButton,
    QLabel, QDialogButtonBox, QScrollArea, QSizePolicy, QToolTip,
    QComboBox, QSpinBox
)
from PyQt5.QtGui import QPainter, QColor, QFont, QImage, QPen, QFontMetrics, QFontDatabase, QPalette
from PyQt5.QtCore import Qt, QRectF, QSize, QPointF

from ..core.i18n import t


# ===== カテゴリ色定義 =====
CATEGORY_COLORS = {
    "navigation": "#4a90d9",   # 青: ナビゲーション
    "display":    "#e8a838",   # オレンジ: 表示切替
    "file_op":    "#4caf50",   # 緑: ファイル操作
    "ui":         "#9c5ec0",   # 紫: ブラウザ/UI
    "system":     "#c0392b",   # 赤: システム
    "other":      "#607d8b",   # 青灰: その他
}

CATEGORY_LABELS = {
    "navigation": "ナビゲーション",
    "display":    "表示切替",
    "file_op":    "ファイル操作",
    "ui":         "ブラウザ/UI",
    "system":     "システム",
    "other":      "その他",
}

# 未割当キーの色
UNBOUND_COLOR = "#3a3a3a"
UNBOUND_TEXT_COLOR = "#888888"
BOUND_TEXT_COLOR = "#ffffff"
KEY_BORDER_COLOR = "#555555"
BG_COLOR = "#1e1e1e"

# キーボードマップ専用フォント（親アプリに依存しない）
_KB_FONT_FAMILY = "Yu Gothic UI"

# アプリ間共有データファイル（各アプリのバインディングを保存）
try:
    from ..core.config import get_config_path
    _SHARED_DATA_PATH = str(get_config_path().parent / "keyboard_map_apps.json")
except Exception:
    _SHARED_DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_keyboard_map_apps.json")

# ===== KEY_名 → カテゴリ判定 =====
_CATEGORY_KEYWORDS = {
    "navigation": ["NEXT", "PREV", "BOOK", "PARENT", "WHEEL"],
    "display":    ["TOGGLE", "LAYOUT", "FULLSCREEN", "FIT", "RTL", "SORT",
                   "ROTATE", "METADATA", "INFO", "CUSTOM", "CUT", "STRETCH"],
    "file_op":    ["COPY", "CONVERT", "SEND", "ADD", "SEARCH", "IMAGE",
                   "FAVORITE", "MASTURBATION", "EDITOR"],
    "ui":         ["BROWSER", "QUICK", "CLONE", "HISTORY", "RUN", "WINDOW"],
    "system":     ["HELP", "EXIT", "SETTINGS", "RESTART", "BACKUP"],
}


def _categorize_key_name(key_name):
    """KEY_名からカテゴリを判定"""
    upper = key_name.upper()
    for category, keywords in _CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in upper:
                return category
    # OPEN は file_op だが "OPEN" だけだとファイル操作
    if "OPEN" in upper:
        return "file_op"
    return "other"


# ===== KEY_名 → 短縮ラベル自動生成 =====
_WORD_MAP = {
    "NEXT": "次", "PREV": "前", "TOGGLE": "切替", "LAYOUT": "配置", "SETTINGS": "設定",
    "RESTART": "再起動", "BACKUP": "BUP",
    "OPEN": "開", "COPY": "コピー", "CONVERT": "変換", "SEND": "送信",
    "FULLSCREEN": "全画面", "SINGLE": "1枚", "DOUBLE": "見開",
    "TRIPLE": "3枚", "HELP": "ヘルプ", "EXIT": "終了",
    "BROWSER": "ブラウザ", "CLONE": "複製", "WINDOW": "窓",
    "BOOK": "本", "PARENT": "親", "ONE": "1枚",
    "INFO": "情報", "RTL": "右開", "FIT": "表示", "SORT": "並替",
    "AUTO": "自動", "ROTATE": "回転", "METADATA": "メタ",
    "IMAGE": "画像", "SEARCH": "検索", "EDITOR": "編集",
    "FOLDER": "フォルダ", "QUICK": "クイック", "ADD": "追加",
    "FAVORITE": "お気入", "CUSTOM": "カスタム",
    "CUT": "カット", "STRETCH": "伸縮",
    "UP": "↑", "DOWN": "↓",
    "TO": "", "EEE": "EEE", "PROMPT": "プロンプト", "PNG": "PNG", "INPUT": "入力",
    "GRID4": "2x2", "GRID8": "2x4", "H4": "4横",
    "HISTORY": "履歴", "RUN": "起動", "FEMALE": "FI",
    "INDEX": "INDEX", "MASTURBATION": "M履歴",
    "KEY": "",
}


def _key_name_to_label(key_name):
    """KEY_NEXT_BOOK → '次本' のように短縮ラベルを生成"""
    name = key_name
    if name.startswith("KEY_"):
        name = name[4:]

    words = name.split("_")
    parts = []
    for w in words:
        mapped = _WORD_MAP.get(w)
        if mapped is not None:
            if mapped:
                parts.append(mapped)
        else:
            # 未知の単語: 先頭3文字
            parts.append(w[:3])
    label = "".join(parts)
    return label[:8]  # 最大8文字


# ===== Qt.Key → 表示ラベル変換 =====
_QT_KEY_LABEL = {
    Qt.Key_Escape: "Esc", Qt.Key_Tab: "Tab", Qt.Key_Backspace: "BS",
    Qt.Key_Return: "Enter", Qt.Key_Enter: "Enter",
    Qt.Key_Insert: "Ins", Qt.Key_Delete: "Del",
    Qt.Key_Home: "Home", Qt.Key_End: "End",
    Qt.Key_PageUp: "PgUp", Qt.Key_PageDown: "PgDn",
    Qt.Key_Left: "←", Qt.Key_Right: "→", Qt.Key_Up: "↑", Qt.Key_Down: "↓",
    Qt.Key_Space: "Space",
    Qt.Key_CapsLock: "Caps",
    Qt.Key_Shift: "Shift", Qt.Key_Control: "Ctrl", Qt.Key_Alt: "Alt",
    Qt.Key_NumLock: "Num",
    Qt.Key_F1: "F1", Qt.Key_F2: "F2", Qt.Key_F3: "F3", Qt.Key_F4: "F4",
    Qt.Key_F5: "F5", Qt.Key_F6: "F6", Qt.Key_F7: "F7", Qt.Key_F8: "F8",
    Qt.Key_F9: "F9", Qt.Key_F10: "F10", Qt.Key_F11: "F11", Qt.Key_F12: "F12",
    Qt.Key_Minus: "-", Qt.Key_Plus: "+", Qt.Key_Asterisk: "*",
    Qt.Key_Slash: "/", Qt.Key_Period: ".",
    Qt.Key_At: "@", Qt.Key_BracketLeft: "[", Qt.Key_BracketRight: "]",
    Qt.Key_Semicolon: ";", Qt.Key_Colon: ":", Qt.Key_Comma: ",",
    Qt.Key_Equal: "=", Qt.Key_Backslash: "\\",
    Qt.Key_QuoteLeft: "`", Qt.Key_Apostrophe: "'",
}

def _qt_key_to_label(qt_key):
    """Qt.Key_* を表示用ラベルに変換"""
    if qt_key in _QT_KEY_LABEL:
        return _QT_KEY_LABEL[qt_key]
    # 文字キー (A-Z, 0-9)
    if Qt.Key_A <= qt_key <= Qt.Key_Z:
        return chr(qt_key)
    if Qt.Key_0 <= qt_key <= Qt.Key_9:
        return chr(qt_key)
    return f"?{qt_key}"


# ===== キーボード物理配列データ =====
# (qt_key, label, x, y, w, h, is_numpad)
# x, y はグリッド単位。1単位 = 標準キー1個分
# _GAP はスペーサー用（描画しない）

def _build_layout():
    """キーボードレイアウトを構築して返す"""
    keys = []
    _K = lambda qt_key, label, x, y, w=1.0, h=1.0, numpad=False: \
        keys.append((qt_key, label, x, y, w, h, numpad))

    # === Row 0: Function keys (y=0) ===
    y = 0
    _K(Qt.Key_Escape, "Esc", 0, y, 1.5)
    for i, fkey in enumerate([
        Qt.Key_F1, Qt.Key_F2, Qt.Key_F3, Qt.Key_F4,
        Qt.Key_F5, Qt.Key_F6, Qt.Key_F7, Qt.Key_F8,
        Qt.Key_F9, Qt.Key_F10, Qt.Key_F11, Qt.Key_F12,
    ]):
        gap = 0.5 if i in (0, 4, 8) else 0
        x = 2.0 + i + (0.5 if i >= 4 else 0) + (0.5 if i >= 8 else 0)
        _K(fkey, f"F{i+1}", x, y)

    # === Row 1: Number row (y=1.5) ===
    y = 1.5
    _K(None, "半/全", 0, y)
    for i, digit in enumerate("1234567890"):
        qt_key = getattr(Qt, f"Key_{digit}")
        _K(qt_key, digit, 1 + i, y)
    _K(Qt.Key_Minus, "-", 11, y)
    _K(Qt.Key_Equal, "=", 12, y)
    _K(None, "\\", 13, y)
    _K(Qt.Key_Backspace, "BS", 14, y, 1.5)

    # === Row 2: QWERTY (y=2.5) ===
    y = 2.5
    _K(Qt.Key_Tab, "Tab", 0, y, 1.5)
    for i, ch in enumerate("QWERTYUIOP"):
        qt_key = getattr(Qt, f"Key_{ch}")
        _K(qt_key, ch, 1.5 + i, y)
    _K(Qt.Key_At, "@", 11.5, y)
    _K(Qt.Key_BracketLeft, "[", 12.5, y)
    # Enter (L字の上部分)
    _K(Qt.Key_Return, "Enter", 13.5, y, 2.0, 2.0)

    # === Row 3: Home row (y=3.5) ===
    y = 3.5
    _K(Qt.Key_CapsLock, "Caps", 0, y, 1.75)
    for i, ch in enumerate("ASDFGHJKL"):
        qt_key = getattr(Qt, f"Key_{ch}")
        _K(qt_key, ch, 1.75 + i, y)
    _K(Qt.Key_Semicolon, ";", 10.75, y)
    _K(Qt.Key_Colon, ":", 11.75, y)
    _K(Qt.Key_BracketRight, "]", 12.75, y)

    # === Row 4: Shift row (y=4.5) ===
    y = 4.5
    _K(Qt.Key_Shift, "Shift", 0, y, 2.25)
    for i, ch in enumerate("ZXCVBNM"):
        qt_key = getattr(Qt, f"Key_{ch}")
        _K(qt_key, ch, 2.25 + i, y)
    _K(Qt.Key_Comma, ",", 9.25, y)
    _K(Qt.Key_Period, ".", 10.25, y)
    _K(Qt.Key_Slash, "/", 11.25, y)
    _K(Qt.Key_Backslash, "\\", 12.25, y)
    _K(Qt.Key_Shift, "Shift", 13.25, y, 2.25)

    # === Row 5: Bottom row (y=5.5) ===
    y = 5.5
    _K(Qt.Key_Control, "Ctrl", 0, y, 1.25)
    _K(None, "Fn", 1.25, y)
    _K(Qt.Key_Meta, "Win", 2.25, y, 1.25)
    _K(Qt.Key_Alt, "Alt", 3.5, y, 1.25)
    _K(Qt.Key_Space, "Space", 4.75, y, 5.0)
    _K(Qt.Key_Alt, "Alt", 9.75, y, 1.25)
    _K(Qt.Key_Meta, "Win", 11.0, y, 1.25)
    _K(None, "Menu", 12.25, y, 1.25)
    _K(Qt.Key_Control, "Ctrl", 13.5, y, 2.0)

    # === Navigation cluster (右上) ===
    nx = 16.0
    _K(Qt.Key_Print, "PrtSc", nx, 0)
    _K(Qt.Key_ScrollLock, "ScrLk", nx + 1, 0)
    _K(Qt.Key_Pause, "Pause", nx + 2, 0)

    _K(Qt.Key_Insert, "Ins", nx, 1.5)
    _K(Qt.Key_Home, "Home", nx + 1, 1.5)
    _K(Qt.Key_PageUp, "PgUp", nx + 2, 1.5)
    _K(Qt.Key_Delete, "Del", nx, 2.5)
    _K(Qt.Key_End, "End", nx + 1, 2.5)
    _K(Qt.Key_PageDown, "PgDn", nx + 2, 2.5)

    # Arrow keys
    _K(Qt.Key_Up, "↑", nx + 1, 4.5)
    _K(Qt.Key_Left, "←", nx, 5.5)
    _K(Qt.Key_Down, "↓", nx + 1, 5.5)
    _K(Qt.Key_Right, "→", nx + 2, 5.5)

    # === Numpad ===
    px = 19.5
    _K(Qt.Key_NumLock, "Num", px, 1.5, numpad=True)
    _K(Qt.Key_Slash, "/", px + 1, 1.5, numpad=True)
    _K(Qt.Key_Asterisk, "*", px + 2, 1.5, numpad=True)
    _K(Qt.Key_Minus, "-", px + 3, 1.5, numpad=True)

    _K(Qt.Key_7, "7", px, 2.5, numpad=True)
    _K(Qt.Key_8, "8", px + 1, 2.5, numpad=True)
    _K(Qt.Key_9, "9", px + 2, 2.5, numpad=True)
    _K(Qt.Key_Plus, "+", px + 3, 2.5, 1, 2, numpad=True)

    _K(Qt.Key_4, "4", px, 3.5, numpad=True)
    _K(Qt.Key_5, "5", px + 1, 3.5, numpad=True)
    _K(Qt.Key_6, "6", px + 2, 3.5, numpad=True)

    _K(Qt.Key_1, "1", px, 4.5, numpad=True)
    _K(Qt.Key_2, "2", px + 1, 4.5, numpad=True)
    _K(Qt.Key_3, "3", px + 2, 4.5, numpad=True)
    _K(Qt.Key_Enter, "Enter", px + 3, 4.5, 1, 2, numpad=True)

    _K(Qt.Key_0, "0", px, 5.5, 2, 1, numpad=True)
    _K(Qt.Key_Period, ".", px + 2, 5.5, numpad=True)

    return keys


KEYBOARD_LAYOUT = _build_layout()

# レイアウト全体のサイズ（グリッド単位）
LAYOUT_WIDTH = 23.5
LAYOUT_HEIGHT = 6.5


# ===== config ソースからコメント（説明文）を抽出 =====

def _extract_key_comments(config_module):
    """config モジュールのソースコードから KEY_* 変数のコメントを抽出する。
    例: KEY_NEXT = [Qt.Key_Right]  # 次のページ  → {"KEY_NEXT": "次のページ"}
    """
    try:
        source = inspect.getsource(config_module)
    except (TypeError, OSError):
        return {}

    comments = {}
    for line in source.split('\n'):
        stripped = line.strip()
        if not stripped.startswith('KEY_') or '=' not in stripped:
            continue
        var_name = stripped.split('=')[0].strip()
        if '#' in stripped:
            comment = stripped.split('#', 1)[1].strip()
            if comment:
                comments[var_name] = comment
    return comments


# ===== config モジュールから KEY_* を収集 =====

def collect_keybindings(config_module, label_overrides=None):
    """
    config モジュールから KEY_* 変数を読み取り、バインディング情報を返す。

    戻り値: {
        (modifier, qt_key, is_numpad): {
            "label": "次ページ",
            "key_name": "KEY_NEXT",
            "category": "navigation",
            "color": "#4a90d9",
        },
        ...
    }

    modifier: "" (なし), "ctrl", "shift", "alt"
    is_numpad: True/False
    """
    bindings = {}
    overrides = label_overrides or {}

    # ソースコードのコメントからツールチップ用説明文を抽出
    key_comments = _extract_key_comments(config_module)

    for attr_name in dir(config_module):
        if not attr_name.startswith("KEY_"):
            continue

        value = getattr(config_module, attr_name)
        if not isinstance(value, list):
            continue

        category = _categorize_key_name(attr_name)
        color = CATEGORY_COLORS.get(category, CATEGORY_COLORS["other"])
        label = overrides.get(attr_name, _key_name_to_label(attr_name))
        # ツールチップ用: コメントがあればそれを使用、なければ自動生成ラベル
        description = key_comments.get(attr_name, label)

        for item in value:
            modifier = ""
            qt_key = None
            is_numpad = False

            if isinstance(item, tuple) and len(item) == 2:
                mod_str, qt_key = item
                if mod_str == "numpad":
                    is_numpad = True
                    modifier = ""
                else:
                    modifier = mod_str  # "ctrl", "shift", "alt"
            elif isinstance(item, int):
                qt_key = item
            else:
                continue

            if qt_key is None:
                continue

            binding_key = (modifier, qt_key, is_numpad)
            bindings[binding_key] = {
                "label": label,
                "key_name": attr_name,
                "category": category,
                "color": color,
                "modifier": modifier,
                "description": description,
            }

    return bindings


# ===== アプリ間レジストリ =====

def _extract_app_name(title):
    """タイトル文字列からアプリ名を抽出（例: 'MAGATU_VIEWER v1.0 ショートカットMAP' → 'MAGATU_VIEWER'）"""
    match = re.match(r'(MAGATU_\w+)', title)
    if match:
        return match.group(1)
    name = title.replace("ショートカットMAP", "").strip()
    name = re.sub(r'\s*v[\d.]+\s*$', '', name).strip()
    return name or title


def _bindings_to_save_dict(bindings):
    """内部バインディング形式 → 保存用辞書に変換"""
    result = {}
    for (modifier, qt_key, is_numpad), info in bindings.items():
        key_label = _qt_key_to_label(qt_key)
        if is_numpad:
            key_str = f"Numpad{key_label}"
        else:
            key_str = key_label
        if modifier:
            key_str = f"{modifier.capitalize()}+{key_str}"
        result[key_str] = {
            "description": info.get("description", info.get("label", "")),
            "category": info.get("category", "other"),
        }
    return result


def _save_app_data(app_name, title, save_dict):
    """アプリのバインディングをJSONファイルに保存"""
    app_data = _load_app_data()
    app_data[app_name] = {
        "title": title,
        "bindings": save_dict,
    }
    try:
        Path(_SHARED_DATA_PATH).parent.mkdir(parents=True, exist_ok=True)
        with open(_SHARED_DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(app_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[keyboard_map] 共有データ保存エラー: {e}")


def _load_app_data():
    """アプリ間共有JSONファイルを読み込む"""
    if not os.path.exists(_SHARED_DATA_PATH):
        return {}
    try:
        with open(_SHARED_DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


# ===== フォント設定 =====

def _load_font_settings():
    """キーボードマップのフォント設定を読み込む"""
    app_data = _load_app_data()
    settings = app_data.get("_font_settings", {})
    return {
        "family": settings.get("family", _KB_FONT_FAMILY),
        "pixel_size": settings.get("pixel_size", 14),
    }


def _save_font_settings(family, pixel_size):
    """キーボードマップのフォント設定を保存"""
    app_data = _load_app_data()
    app_data["_font_settings"] = {"family": family, "pixel_size": int(pixel_size)}
    try:
        Path(_SHARED_DATA_PATH).parent.mkdir(parents=True, exist_ok=True)
        with open(_SHARED_DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(app_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[keyboard_map] フォント設定保存エラー: {e}")


# ===== 描画エンジン =====

def _render_keyboard(painter, rect, bindings, title="", key_rects=None, font_family=None):
    """
    QPainter を使ってキーボードMAPを描画する。

    painter: QPainter (QWidget.paintEvent 内、または QImage 用)
    rect: QRectF - 描画領域
    bindings: collect_keybindings() の戻り値
    title: タイトル文字列（空文字なら非表示）
    key_rects: リスト（省略可）。渡すと各キーの (QRectF, key_label, bound_entries) を追記。
               ツールチップ用のヒットテストに使う。
    font_family: フォントファミリー名（Noneならデフォルト使用）
    """
    if font_family is None:
        font_family = _load_font_settings().get("family", _KB_FONT_FAMILY)
    # マージン
    margin = 10
    title_h = 40 if title else 0
    legend_h = 40

    # キーボード描画領域を計算
    kb_rect = QRectF(
        rect.x() + margin,
        rect.y() + margin + title_h,
        rect.width() - margin * 2,
        rect.height() - margin * 2 - title_h - legend_h
    )

    # 1グリッド単位のピクセルサイズ
    unit_w = kb_rect.width() / LAYOUT_WIDTH
    unit_h = kb_rect.height() / LAYOUT_HEIGHT
    unit = min(unit_w, unit_h)

    # キーボード全体を中央配置
    total_w = LAYOUT_WIDTH * unit
    total_h = LAYOUT_HEIGHT * unit
    offset_x = kb_rect.x() + (kb_rect.width() - total_w) / 2
    offset_y = kb_rect.y() + (kb_rect.height() - total_h) / 2

    # 背景
    painter.fillRect(rect, QColor(BG_COLOR))

    # タイトル
    if title:
        painter.setPen(QColor("#ffffff"))
        title_font = QFont(font_family)
        title_font.setPixelSize(max(14, int(unit * 0.45)))
        title_font.setBold(True)
        painter.setFont(title_font)
        title_rect = QRectF(rect.x(), rect.y() + 5, rect.width(), title_h)
        painter.drawText(title_rect, Qt.AlignCenter, title)

    # キーキャップのパディング
    pad = max(1, unit * 0.05)

    # フォント設定（pixelSize でサイズ統一、ポイントはDPI依存で不安定）
    label_font = QFont(font_family)
    label_size = max(10, int(unit * 0.30))
    label_font.setPixelSize(label_size)
    label_font.setBold(True)

    func_font = QFont(font_family)
    func_size = max(8, int(unit * 0.22))
    func_font.setPixelSize(func_size)

    modifier_font = QFont(font_family)
    mod_size = max(7, int(unit * 0.16))
    modifier_font.setPixelSize(mod_size)
    modifier_font.setBold(True)

    # 各キーを描画
    for (qt_key, key_label, kx, ky, kw, kh, is_numpad) in KEYBOARD_LAYOUT:
        # キーの矩形（パディング考慮）
        x = offset_x + kx * unit + pad
        y = offset_y + ky * unit + pad
        w = kw * unit - pad * 2
        h = kh * unit - pad * 2
        key_rect = QRectF(x, y, w, h)

        # バインディングを検索
        bound_entries = []
        if qt_key is not None:
            for mod in [
                "",
                "ctrl", "shift", "alt", "win",
                "ctrl+shift", "ctrl+alt", "ctrl+win",
                "shift+alt", "shift+win", "alt+win",
                "ctrl+shift+alt", "ctrl+shift+win", "ctrl+alt+win",
                "shift+alt+win", "ctrl+shift+alt+win",
            ]:
                bk = (mod, qt_key, is_numpad)
                if bk in bindings:
                    bound_entries.append(bindings[bk])

        # ヒットテスト用に矩形情報を記録
        if key_rects is not None:
            key_rects.append((QRectF(key_rect), key_label, bound_entries))

        # 色決定
        if bound_entries:
            bg = QColor(bound_entries[0]["color"])
            text_color = QColor(BOUND_TEXT_COLOR)
        else:
            bg = QColor(UNBOUND_COLOR)
            text_color = QColor(UNBOUND_TEXT_COLOR)

        # キーキャップ描画（角丸矩形）
        radius = max(2, unit * 0.08)
        painter.setPen(QPen(QColor(KEY_BORDER_COLOR), 1))
        painter.setBrush(bg)
        painter.drawRoundedRect(key_rect, radius, radius)

        # テキスト描画
        painter.setPen(text_color)

        if bound_entries:
            # バインドあり: 上段にキーラベル、下段に機能名
            # 修飾キーバッジがある場合は先頭に表示
            top_rect = QRectF(x + 2, y + 1, w - 4, h * 0.45)
            bottom_rect = QRectF(x + 2, y + h * 0.40, w - 4, h * 0.60)

            # キーラベル（左上寄せ）
            painter.setFont(label_font)
            painter.drawText(top_rect, Qt.AlignLeft | Qt.AlignTop, key_label)

            # 修飾キーバッジ（右上）
            for entry in bound_entries:
                mod = entry.get("modifier", "")
                if mod:
                    painter.setFont(modifier_font)
                    badge_text = f"{mod.upper()}+"
                    painter.setPen(QColor("#ffff00"))
                    badge_rect = QRectF(x + 2, y + 1, w - 4, h * 0.35)
                    painter.drawText(badge_rect, Qt.AlignRight | Qt.AlignTop, badge_text)
                    painter.setPen(text_color)

            # 機能名（下部、フィットするようにクリップ）
            painter.setFont(func_font)
            # 複数バインドがある場合はスラッシュ区切り
            func_labels = []
            for entry in bound_entries:
                mod = entry.get("modifier", "")
                prefix = f"{mod[0].upper()}:" if mod else ""
                func_labels.append(f"{prefix}{entry['label']}")
            func_text = " ".join(func_labels)

            # テキストが長い場合は省略
            fm = QFontMetrics(func_font)
            elided = fm.elidedText(func_text, Qt.ElideRight, int(w - 4))
            painter.drawText(bottom_rect, Qt.AlignLeft | Qt.AlignBottom, elided)
        else:
            # バインドなし: 中央にキーラベルのみ
            painter.setFont(label_font)
            painter.drawText(key_rect, Qt.AlignCenter, key_label)

    # === 凡例 ===
    legend_y = offset_y + total_h + 10
    legend_font = QFont(font_family)
    legend_size = max(10, int(unit * 0.22))
    legend_font.setPixelSize(legend_size)
    painter.setFont(legend_font)

    lx = offset_x
    for cat_key, cat_label in CATEGORY_LABELS.items():
        display_label = t(f"keyboard_map.category.{cat_key}", cat_label)
        color = QColor(CATEGORY_COLORS[cat_key])
        # 色見本
        swatch_size = max(12, unit * 0.35)
        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
        painter.drawRoundedRect(QRectF(lx, legend_y, swatch_size, swatch_size), 2, 2)
        # ラベル
        painter.setPen(QColor("#cccccc"))
        text_rect = QRectF(lx + swatch_size + 4, legend_y - 2, unit * 3, swatch_size + 4)
        painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, display_label)
        lx += swatch_size + 4 + unit * 2.2


# ===== KeyboardWidget =====

class KeyboardWidget(QWidget):
    """キーボードMAP描画ウィジェット（ホバーツールチップ対応）"""

    def __init__(self, bindings, title="", parent=None, font_family=None):
        super().__init__(parent)
        self.bindings = bindings
        self.title = title
        self.font_family = font_family or _KB_FONT_FAMILY
        self.setMinimumSize(800, 350)
        self.setMouseTracking(True)
        self._key_rects = []  # [(QRectF, key_label, bound_entries), ...]
        self._last_hover_key = None  # 前回ホバーしたキー（再描画抑止用）

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        self._key_rects = []
        _render_keyboard(
            painter, QRectF(self.rect()), self.bindings, self.title,
            key_rects=self._key_rects, font_family=self.font_family
        )
        painter.end()

    def mouseMoveEvent(self, event):
        pos = event.pos()
        for rect, key_label, entries in self._key_rects:
            if rect.contains(QPointF(pos)):
                # 同じキーの上なら再表示しない
                if self._last_hover_key == key_label:
                    return
                self._last_hover_key = key_label

                if entries:
                    lines = []
                    for entry in entries:
                        mod = entry.get("modifier", "")
                        mod_prefix = f"{mod.capitalize()}+" if mod else ""
                        desc = entry.get("description", entry.get("label", ""))
                        np_str = t("keyboard_map.numpad.suffix", " [テンキー]") if entry.get("is_numpad") else ""
                        lines.append(f"{mod_prefix}{key_label}{np_str}: {desc}")
                    QToolTip.showText(event.globalPos(), "\n".join(lines))
                else:
                    QToolTip.showText(event.globalPos(), key_label)
                return

        # どのキーの上でもない
        self._last_hover_key = None
        QToolTip.hideText()

    def leaveEvent(self, event):
        self._last_hover_key = None
        QToolTip.hideText()

    def sizeHint(self):
        return QSize(1200, 500)


# ===== 非モーダルダイアログ管理 =====
# show() で開くため、参照を保持しないとGCで消える
# app_name ごとに管理し、同じアプリの重複は防止、異なるアプリは共存可能
_active_dialogs = {}  # {app_name: dialog}

def _on_dialog_destroyed(app_name):
    if app_name in _active_dialogs:
        del _active_dialogs[app_name]


# ===== KeyboardMapDialog =====

class KeyboardMapDialog(QDialog):
    """ショートカットキーMAPダイアログ"""

    def __init__(self, parent, bindings, title="ショートカットMAP", current_app=None,
                 notes_html="", geometry_state=None, geometry_changed=None):
        super().__init__(parent)
        # フォント設定を読み込み
        font_settings = _load_font_settings()
        self._font_family = font_settings["family"]
        self._font_pixel_size = font_settings["pixel_size"]

        # キーボードマップ独自のフォント（親アプリに依存しない）
        dialog_font = QFont(self._font_family)
        dialog_font.setPixelSize(self._font_pixel_size)
        dialog_font.setBold(True)
        self.setFont(dialog_font)

        # 統一ダークテーマ（親アプリのパレットに依存しない）
        dark = QPalette()
        dark.setColor(QPalette.Window, QColor("#2d2d2d"))
        dark.setColor(QPalette.WindowText, QColor("#ffffff"))
        dark.setColor(QPalette.Base, QColor("#3a3a3a"))
        dark.setColor(QPalette.AlternateBase, QColor("#4a4a4a"))
        dark.setColor(QPalette.Text, QColor("#ffffff"))
        dark.setColor(QPalette.Button, QColor("#4a4a4a"))
        dark.setColor(QPalette.ButtonText, QColor("#ffffff"))
        dark.setColor(QPalette.Highlight, QColor("#4a90d9"))
        dark.setColor(QPalette.HighlightedText, QColor("#ffffff"))
        self.setPalette(dark)
        self.setAutoFillBackground(True)

        self.setWindowTitle(title)
        self.setMinimumSize(1280 if notes_html else 1000, 500)
        self.resize(1500 if notes_html else 1300, 620 if notes_html else 600)
        self._bindings = bindings
        self._title = title
        self._current_app = current_app
        self._notes_html = notes_html
        self._geometry_changed = geometry_changed
        self._app_buttons = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # アプリ切替ボタン行（2つ以上登録がある場合のみ表示）
        self._app_btn_layout = QHBoxLayout()
        self._build_app_buttons()
        layout.addLayout(self._app_btn_layout)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(8)

        self._kb_widget = KeyboardWidget(bindings, title, self, font_family=self._font_family)
        self._kb_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        content_layout.addWidget(self._kb_widget, 1)

        self._notes_widget = None
        if self._notes_html:
            self._notes_widget = self._build_notes_widget()
            content_layout.addWidget(self._notes_widget, 0)

        layout.addLayout(content_layout, 1)

        # ボタン行（フォント設定 + PNG保存 + 閉じる）
        btn_layout = QHBoxLayout()

        # フォント設定
        btn_layout.addWidget(QLabel(t("keyboard_map.font.label", "フォント:")))
        self._font_combo = QComboBox()
        self._font_combo.setEditable(True)
        font_families = QFontDatabase().families()
        self._font_combo.addItems(font_families)
        idx = self._font_combo.findText(self._font_family)
        if idx >= 0:
            self._font_combo.setCurrentIndex(idx)
        else:
            self._font_combo.setCurrentText(self._font_family)
        btn_layout.addWidget(self._font_combo)

        btn_layout.addWidget(QLabel(t("keyboard_map.size.label", "サイズ:")))
        self._font_size_spin = QSpinBox()
        self._font_size_spin.setRange(1, 999)
        self._font_size_spin.setValue(self._font_pixel_size)
        self._font_size_spin.setSuffix(" px")
        btn_layout.addWidget(self._font_size_spin)

        apply_font_btn = QPushButton(t("common.apply", "適用"))
        apply_font_btn.clicked.connect(self._apply_font_settings)
        btn_layout.addWidget(apply_font_btn)

        btn_layout.addStretch()

        save_btn = QPushButton(t("keyboard_map.save_png.button", "PNG保存"))
        save_btn.clicked.connect(self._save_png)
        btn_layout.addWidget(save_btn)

        close_btn = QPushButton(t("common.close", "閉じる"))
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

        # 全子ウィジェットにフォントを強制適用（親アプリのフォント漏れ防止）
        for child in self.findChildren(QWidget):
            child.setFont(dialog_font)
        self._restore_geometry_state(geometry_state)

    def _restore_geometry_state(self, geometry_state):
        if not isinstance(geometry_state, dict):
            return
        try:
            w = int(geometry_state.get("w", -1))
            h = int(geometry_state.get("h", -1))
            x = int(geometry_state.get("x", -1))
            y = int(geometry_state.get("y", -1))
        except Exception:
            return
        if w > 0 and h > 0:
            self.resize(max(self.minimumWidth(), w), max(self.minimumHeight(), h))
        if x >= 0 and y >= 0:
            self.move(x, y)

    def closeEvent(self, event):
        self._emit_geometry_changed()
        super().closeEvent(event)

    def accept(self):
        self._emit_geometry_changed()
        super().accept()

    def reject(self):
        self._emit_geometry_changed()
        super().reject()

    def _emit_geometry_changed(self):
        if self._geometry_changed is None:
            return
        geo = self.geometry()
        try:
            self._geometry_changed({
                "x": geo.x(),
                "y": geo.y(),
                "w": geo.width(),
                "h": geo.height(),
            })
        except Exception:
            pass

    def _build_notes_widget(self) -> QWidget:
        panel = QWidget(self)
        panel.setFixedWidth(310)
        panel.setStyleSheet(
            "QWidget { background: #242424; color: #e8e8e8; }"
            "QLabel { color: #e8e8e8; }"
            "QScrollArea { border: 1px solid #444; background: #242424; }"
        )
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QLabel(t("keyboard_map.notes.title", "操作メモ"))
        title_font = QFont(self._font_family)
        title_font.setPixelSize(max(14, self._font_pixel_size + 1))
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        body = QLabel(self._notes_html)
        body.setTextFormat(Qt.RichText)
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        body.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        body.setContentsMargins(8, 8, 8, 8)
        body.setStyleSheet("QLabel { background: #1e1e1e; line-height: 130%; }")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(body)
        layout.addWidget(scroll, 1)
        return panel

    def _apply_font_settings(self):
        """フォント設定を適用・保存"""
        family = self._font_combo.currentText().strip()
        pixel_size = self._font_size_spin.value()
        if not family:
            return
        self._font_family = family
        self._font_pixel_size = pixel_size
        # ダイアログフォント更新
        dialog_font = QFont(family)
        dialog_font.setPixelSize(pixel_size)
        dialog_font.setBold(True)
        self.setFont(dialog_font)
        for child in self.findChildren(QWidget):
            child.setFont(dialog_font)
        # キーボード描画フォント更新
        self._kb_widget.font_family = family
        self._kb_widget.update()
        if self._notes_widget is not None:
            self._notes_widget.setFont(dialog_font)
        # 保存
        _save_font_settings(family, pixel_size)

    def _build_app_buttons(self):
        """共有データからアプリ切替ボタンを構築"""
        app_data = _load_app_data()
        # _font_settings等の内部キーを除外
        app_names = [k for k in app_data if not k.startswith("_")]
        if len(app_names) < 2:
            return
        for app_name in app_names:
            btn = QPushButton(app_name)
            btn.setCheckable(True)
            btn.setChecked(app_name == self._current_app)
            btn.clicked.connect(lambda checked, name=app_name: self._switch_app(name))
            self._app_btn_layout.addWidget(btn)
            self._app_buttons[app_name] = btn
        self._app_btn_layout.addStretch()

    def _switch_app(self, app_name):
        """表示するアプリのキーボードマップを切り替える"""
        app_data = _load_app_data()
        if app_name not in app_data:
            return
        entry = app_data[app_name]
        bindings = _convert_simple_dict(entry.get("bindings", {}))
        title = entry.get("title", app_name)

        self._current_app = app_name
        self._bindings = bindings
        self._title = title

        # ボタンの状態更新
        for name, btn in self._app_buttons.items():
            btn.setChecked(name == app_name)

        # キーボードウィジェット更新
        self._kb_widget.bindings = bindings
        self._kb_widget.title = title
        self._kb_widget.update()

        self.setWindowTitle(title)

    def _save_png(self):
        """PNG画像として保存"""
        from .file_dialog_compat import get_folder
        folder = get_folder(
            self,
            title=t("keyboard_map.save_png.folder_title", "保存先フォルダを選択"),
        )
        if not folder:
            return
        output_path = os.path.join(folder, "keyboard_map.png")
        _save_image(self._bindings, output_path, title=self._title)
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.information(
            self,
            t("keyboard_map.save_png.complete.title", "保存完了"),
            t("keyboard_map.save_png.complete.body", "保存しました:\n{path}").format(
                path=output_path
            ),
        )

    @classmethod
    def show_from_config(cls, parent, config_module, title="ショートカットMAP",
                         label_overrides=None, app_name=None, notes_html="",
                         geometry_state=None, geometry_changed=None):
        """configモジュールからKEY_*を自動収集して表示（非モーダル）"""
        if title == "ショートカットMAP":
            title = t("keyboard_map.default_title", "ショートカットMAP")
        bindings = collect_keybindings(config_module, label_overrides)
        if app_name is None:
            app_name = _extract_app_name(title)
        # 共有データに保存（カテゴリ情報付き）
        save_dict = _bindings_to_save_dict(bindings)
        _save_app_data(app_name, title, save_dict)
        # 同じアプリの既存ダイアログがあれば前面化して終了
        existing = _active_dialogs.get(app_name)
        if existing is not None:
            try:
                existing.raise_()
                existing.activateWindow()
                return
            except RuntimeError:
                del _active_dialogs[app_name]
        dialog = cls(
            parent,
            bindings,
            title,
            current_app=app_name,
            notes_html=notes_html,
            geometry_state=geometry_state,
            geometry_changed=geometry_changed,
        )
        dialog.setAttribute(Qt.WA_DeleteOnClose)
        dialog.destroyed.connect(lambda: _on_dialog_destroyed(app_name))
        dialog.show()
        _active_dialogs[app_name] = dialog

    @classmethod
    def show_from_dict(cls, parent, binding_dict, title="ショートカットMAP",
                       app_name=None, notes_html="", geometry_state=None,
                       geometry_changed=None):
        """辞書形式でバインディングを渡して表示（非モーダル）"""
        if title == "ショートカットMAP":
            title = t("keyboard_map.default_title", "ショートカットMAP")
        bindings = _convert_simple_dict(binding_dict)
        if app_name is None:
            app_name = _extract_app_name(title)
        # 共有データに保存
        save_dict = {}
        for key_str, value in binding_dict.items():
            if isinstance(value, str):
                save_dict[key_str] = {"description": value, "category": "other"}
            else:
                save_dict[key_str] = value
        _save_app_data(app_name, title, save_dict)
        # 同じアプリの既存ダイアログがあれば前面化して終了
        existing = _active_dialogs.get(app_name)
        if existing is not None:
            try:
                existing.raise_()
                existing.activateWindow()
                return
            except RuntimeError:
                del _active_dialogs[app_name]
        dialog = cls(
            parent,
            bindings,
            title,
            current_app=app_name,
            notes_html=notes_html,
            geometry_state=geometry_state,
            geometry_changed=geometry_changed,
        )
        dialog.setAttribute(Qt.WA_DeleteOnClose)
        dialog.destroyed.connect(lambda: _on_dialog_destroyed(app_name))
        dialog.show()
        _active_dialogs[app_name] = dialog


# ===== PNG保存 =====

def _save_image(bindings, output_path, width=1600, title=""):
    """QImage + QPainter でキーボードMAPをPNG保存"""
    # キーが正方形に近くなるよう高さを計算（タイトル・凡例・マージン分を加算）
    aspect = LAYOUT_HEIGHT / LAYOUT_WIDTH
    extra = 120  # title(40) + legend(30) + margins(20) + padding(30)
    height = int(width * aspect) + extra
    height = max(height, 500)

    image = QImage(width, height, QImage.Format_ARGB32)
    image.fill(QColor(BG_COLOR))

    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    _render_keyboard(painter, QRectF(0, 0, width, height), bindings, title)
    painter.end()

    image.save(output_path)


def save_keyboard_map_image(config_module, output_path, width=1600,
                            title="ショートカットMAP", label_overrides=None):
    """
    config モジュールから KEY_* を収集してキーボードMAP画像を保存する。
    QApplication が起動している必要がある。
    """
    if title == "ショートカットMAP":
        title = t("keyboard_map.default_title", "ショートカットMAP")
    bindings = collect_keybindings(config_module, label_overrides)
    _save_image(bindings, output_path, width, title)


# ===== 簡易辞書形式の変換 =====

_SIMPLE_KEY_MAP = {
    "ESC": Qt.Key_Escape, "TAB": Qt.Key_Tab, "BS": Qt.Key_Backspace,
    "BACKSPACE": Qt.Key_Backspace, "ENTER": Qt.Key_Return, "RETURN": Qt.Key_Return,
    "SPACE": Qt.Key_Space, "INS": Qt.Key_Insert, "INSERT": Qt.Key_Insert,
    "DEL": Qt.Key_Delete, "DELETE": Qt.Key_Delete,
    "HOME": Qt.Key_Home, "END": Qt.Key_End,
    "PGUP": Qt.Key_PageUp, "PAGEUP": Qt.Key_PageUp,
    "PGDN": Qt.Key_PageDown, "PGDOWN": Qt.Key_PageDown, "PAGEDOWN": Qt.Key_PageDown,
    "LEFT": Qt.Key_Left, "RIGHT": Qt.Key_Right, "UP": Qt.Key_Up, "DOWN": Qt.Key_Down,
    "←": Qt.Key_Left, "→": Qt.Key_Right, "↑": Qt.Key_Up, "↓": Qt.Key_Down,
    "F1": Qt.Key_F1, "F2": Qt.Key_F2, "F3": Qt.Key_F3, "F4": Qt.Key_F4,
    "F5": Qt.Key_F5, "F6": Qt.Key_F6, "F7": Qt.Key_F7, "F8": Qt.Key_F8,
    "F9": Qt.Key_F9, "F10": Qt.Key_F10, "F11": Qt.Key_F11, "F12": Qt.Key_F12,
    "-": Qt.Key_Minus, "+": Qt.Key_Plus, "*": Qt.Key_Asterisk,
    "/": Qt.Key_Slash, ".": Qt.Key_Period, ",": Qt.Key_Comma,
    "@": Qt.Key_At, "[": Qt.Key_BracketLeft, "]": Qt.Key_BracketRight,
    ";": Qt.Key_Semicolon, ":": Qt.Key_Colon, "\\": Qt.Key_Backslash,
    "=": Qt.Key_Equal,
    "PRINTSCREEN": Qt.Key_Print, "PRTSC": Qt.Key_Print,
    "SCROLLLOCK": Qt.Key_ScrollLock, "SCRLK": Qt.Key_ScrollLock,
    "PAUSE": Qt.Key_Pause,
    "WIN": Qt.Key_Meta, "META": Qt.Key_Meta,
}

def _convert_simple_dict(d):
    """
    {"Ctrl+N": "複製", "B": "ブラウザ"} → 内部バインディング形式に変換。
    値がdictの場合は {"description": "...", "category": "..."} として扱う（レジストリ形式対応）。
    """
    bindings = {}
    for key_str, value in d.items():
        # 値の解析（文字列 or dict）
        if isinstance(value, dict):
            label = value.get("description", key_str)
            description = value.get("description", key_str)
            category = value.get("category", "other")
        else:
            label = str(value)
            description = str(value)
            category = "other"

        parts = key_str.upper().replace(" ", "").split("+")
        modifier_parts = []
        qt_key = None
        is_numpad = False

        for part in parts:
            if part in ("CTRL", "CONTROL"):
                modifier_parts.append("ctrl")
            elif part == "SHIFT":
                modifier_parts.append("shift")
            elif part == "ALT":
                modifier_parts.append("alt")
            elif part in ("WIN", "WINDOWS", "META"):
                modifier_parts.append("win")
            elif part.startswith("NUMPAD"):
                is_numpad = True
                rest = part[6:]
                if rest in _SIMPLE_KEY_MAP:
                    qt_key = _SIMPLE_KEY_MAP[rest]
                elif len(rest) == 1 and rest.isdigit():
                    qt_key = getattr(Qt, f"Key_{rest}", None)
                elif len(rest) == 1 and rest.isalpha():
                    qt_key = getattr(Qt, f"Key_{rest}", None)
            elif part in _SIMPLE_KEY_MAP:
                qt_key = _SIMPLE_KEY_MAP[part]
            elif len(part) == 1 and part.isalpha():
                qt_key = getattr(Qt, f"Key_{part}", None)
            elif len(part) == 1 and part.isdigit():
                qt_key = getattr(Qt, f"Key_{part}", None)

        if qt_key is not None:
            seen_modifiers = []
            for mod in modifier_parts:
                if mod not in seen_modifiers:
                    seen_modifiers.append(mod)
            modifier = "+".join(seen_modifiers)
            binding_key = (modifier, qt_key, is_numpad)
            bindings[binding_key] = {
                "label": label,
                "key_name": key_str,
                "category": category,
                "color": CATEGORY_COLORS.get(category, CATEGORY_COLORS["other"]),
                "modifier": modifier,
                "description": description,
            }

    return bindings
