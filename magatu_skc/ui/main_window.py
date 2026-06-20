"""メインウィンドウ - PyQt5 GUI"""
import base64
import copy
import ctypes
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from html import escape
from pathlib import Path

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QSpinBox, QFileDialog, QMessageBox, QSplitter,
    QGroupBox, QComboBox, QCheckBox, QListWidget, QApplication,
    QToolBar, QAction, QRadioButton, QButtonGroup, QShortcut, QToolButton,
    QSizePolicy
)
from PyQt5.QtCore import Qt, QSize, QEvent, QTimer, QUrl, QPoint
from PyQt5.QtGui import QPixmap, QKeySequence, QCursor, QColor, QPainter, QPen, QImage
from PyQt5.QtMultimedia import QSoundEffect

from .. import __version__
from ..core.rom import Rom, KNOWN_CRC32, is_known_jp_original_data
from ..core.level import Level, load_all_levels
from ..core.xml_io import level_to_xml_element, xml_element_to_level
from ..core.element import Wall, ElementType, LevelElement
from ..core.enemy_direction import DIRECTION_LABELS, enemy_direction_variant
from ..core import constants as c
from ..core.config import (
    DEFAULT_AUTOSAVE_KEEP_COUNT,
    DEFAULT_HOVER_INFO_POPUP_FONT_SIZE,
    DEFAULT_UNDO_LIMIT,
    MAX_HOVER_INFO_POPUP_FONT_SIZE,
    MAX_AUTOSAVE_KEEP_COUNT,
    MAX_UNDO_LIMIT,
    MIN_HOVER_INFO_POPUP_FONT_SIZE,
    MIN_AUTOSAVE_KEEP_COUNT,
    MIN_UNDO_LIMIT,
    DEFAULT_GAMEPAD_SHORTCUTS,
    GAMEPAD_BUTTON_OPTIONS,
    DEFAULT_SHORTCUTS,
    normalize_int_setting,
    normalize_gamepad_shortcuts,
    normalize_panel_variant_settings,
    normalize_shortcuts,
    resolve_project_path,
    get_config_path,
    save_config,
)
from ..core import saver, ips, wall_color_hack, stage_ext, save_validation
from ..gfx.tile_renderer import TileRenderer
from ..gfx.level_renderer import LevelRenderer
from ..nes.config_loader import SkcConfig
from ..nes.tile import load_chr_tiles
from .level_view import LevelView
from .element_picker import (
    ElementPicker, MODE_BLOCK, MODE_ITEM, MODE_ENEMY, MODE_META,
    BLOCK_NONE, BLOCK_BROWN, BLOCK_WHITE, BLOCK_BROWN_WHITE,
    BLOCK_CRACKED, BLOCK_BREAKABLE_WHITE, BLOCK_INVISIBLE_BREAKABLE,
    BLOCK_PASSABLE_WHITE, BLOCK_INVISIBLE_SOLID,
    BLOCK_PASSABLE_BROWN, BLOCK_SOLID_BROWN,
    BLOCK_PICKER_LABELS, DEFAULT_BLOCK_PICKER_ORDER,
    ENEMY_SPEED_TABLE, apply_enemy_speed, base_code_from_actual,
    ENEMIES_LIST, ITEMS_LIST, item_name,
)
from .rom_validation_dialog import RomValidationDialog

APP_DISPLAY_NAME = "SOLOMON_CUSTOMIZER"
WINDOW_STATE_DEBUG_ENV = "SOLOMON_WINDOW_STATE_DEBUG"


class _StageNumberLabel(QLabel):
    """Canvas stage label that also works as a stage selector."""

    def __init__(self, owner, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._owner = owner
        self.setCursor(Qt.PointingHandCursor)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta:
            # Match the existing right-side selector: wheel up moves to the previous stage.
            self._owner._change_stage_relative(-1 if delta > 0 else 1, play_sound=True)
            event.accept()
            return
        super().wheelEvent(event)


class _XInputGamepad(ctypes.Structure):
    _fields_ = [
        ("wButtons", ctypes.c_ushort),
        ("bLeftTrigger", ctypes.c_ubyte),
        ("bRightTrigger", ctypes.c_ubyte),
        ("sThumbLX", ctypes.c_short),
        ("sThumbLY", ctypes.c_short),
        ("sThumbRX", ctypes.c_short),
        ("sThumbRY", ctypes.c_short),
    ]


class _XInputState(ctypes.Structure):
    _fields_ = [
        ("dwPacketNumber", ctypes.c_uint32),
        ("Gamepad", _XInputGamepad),
    ]


_XINPUT_MAX_CONTROLLERS = 4
_XINPUT_BUTTON_DPAD_UP = 0x0001
_XINPUT_BUTTON_DPAD_DOWN = 0x0002
_XINPUT_BUTTON_DPAD_LEFT = 0x0004
_XINPUT_BUTTON_DPAD_RIGHT = 0x0008
_XINPUT_BUTTON_START = 0x0010
_XINPUT_BUTTON_BACK = 0x0020
_XINPUT_BUTTON_LEFT_THUMB = 0x0040
_XINPUT_BUTTON_RIGHT_THUMB = 0x0080
_XINPUT_BUTTON_LEFT_SHOULDER = 0x0100
_XINPUT_BUTTON_RIGHT_SHOULDER = 0x0200
_XINPUT_BUTTON_A = 0x1000
_XINPUT_BUTTON_B = 0x2000
_XINPUT_BUTTON_X = 0x4000
_XINPUT_BUTTON_Y = 0x8000
_XINPUT_BUTTON_BY_NAME = {
    "A": _XINPUT_BUTTON_A,
    "B": _XINPUT_BUTTON_B,
    "X": _XINPUT_BUTTON_X,
    "Y": _XINPUT_BUTTON_Y,
    "Back": _XINPUT_BUTTON_BACK,
    "Start": _XINPUT_BUTTON_START,
    "LB": _XINPUT_BUTTON_LEFT_SHOULDER,
    "RB": _XINPUT_BUTTON_RIGHT_SHOULDER,
    "LStick": _XINPUT_BUTTON_LEFT_THUMB,
    "RStick": _XINPUT_BUTTON_RIGHT_THUMB,
    "DPadUp": _XINPUT_BUTTON_DPAD_UP,
    "DPadDown": _XINPUT_BUTTON_DPAD_DOWN,
    "DPadLeft": _XINPUT_BUTTON_DPAD_LEFT,
    "DPadRight": _XINPUT_BUTTON_DPAD_RIGHT,
}


def _load_xinput_get_state():
    for dll_name in ("xinput1_4", "xinput1_3", "xinput9_1_0"):
        try:
            dll = ctypes.WinDLL(dll_name)
            fn = dll.XInputGetState
            fn.argtypes = [ctypes.c_uint32, ctypes.POINTER(_XInputState)]
            fn.restype = ctypes.c_uint32
            return fn
        except (OSError, AttributeError):
            continue
    return None


_ENEMY_HORIZONTAL_MIRROR_PAIRS = [
    (0x0C, 0x0D), (0x10, 0x11),
    (0x18, 0x19), (0x1A, 0x1B),
    (0x20, 0x21), (0x24, 0x25),
    (0x28, 0x29), (0x2C, 0x2D),
    (0x31, 0x33),
    (0x34, 0x36), (0x35, 0x37), (0x3C, 0x3E), (0x3D, 0x3F),
    (0x41, 0x43), (0x44, 0x46), (0x45, 0x47), (0x49, 0x4B), (0x4C, 0x4E), (0x4D, 0x4F),
    (0x50, 0x51), (0x52, 0x53), (0x54, 0x55), (0x56, 0x57), (0x58, 0x59), (0x5A, 0x5B),
    (0x5C, 0x5D), (0x5E, 0x5F), (0x60, 0x61), (0x62, 0x63), (0x64, 0x65), (0x66, 0x67),
    (0x68, 0x69), (0x6A, 0x6B), (0x6C, 0x6D), (0x6E, 0x6F),
    (0x70, 0x71), (0x72, 0x73), (0x74, 0x75), (0x76, 0x77),
    (0x78, 0x79), (0x7A, 0x7B), (0x7C, 0x7D), (0x7E, 0x7F),
]
_ENEMY_HORIZONTAL_MIRROR = {
    code: other
    for pair in _ENEMY_HORIZONTAL_MIRROR_PAIRS
    for code, other in (pair, (pair[1], pair[0]))
}


def _mirror_enemy_code_horizontal(code: int) -> int:
    return _ENEMY_HORIZONTAL_MIRROR.get(code, code)


class _EnemyCountIndicator(QWidget):
    """Compact initial-enemy count gauge over the level canvas."""

    _SAFE_COLOR = QColor("#22c55e")
    _WARN_COLOR = QColor("#facc15")
    _DANGER_COLOR = QColor("#ef4444")
    _EMPTY_BG = QColor(0, 0, 0, 145)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._count = 0
        self._maximum = c.ENEMY_COUNT_MAX
        self._key_enemy_number = 0
        self._fairy_enemy_number = 0
        self._slot_size = 18
        self._key_enemy_marker = QImage()
        self._fairy_enemy_marker = QImage()
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._apply_size_hints()
        self.setToolTip("敵配置数 0/15")

    def sizeHint(self):
        return QSize(self.minimumWidth(), self.height())

    def set_slot_size(self, size: int):
        try:
            value = int(size)
        except Exception:
            value = 18
        self._slot_size = max(10, min(32, value))
        self._apply_size_hints()
        self.update()

    def _apply_size_hints(self):
        gap = self._slot_gap()
        label_w = 52
        total_w = 8 + self._maximum * self._slot_size + gap * (self._maximum - 1) + label_w
        total_h = self._slot_size * 3 + 10
        self.setFixedHeight(total_h)
        self.setMinimumWidth(max(120, total_w))

    def set_count(self, count: int, maximum: int = c.ENEMY_COUNT_MAX):
        self._count = max(0, int(count))
        self._maximum = max(1, int(maximum))
        self._apply_size_hints()
        self._update_tooltip()
        self.update()

    def set_special_slots(self, key_enemy_number: int = 0, fairy_enemy_number: int = 0):
        self._key_enemy_number = self._normalize_slot_number(key_enemy_number)
        self._fairy_enemy_number = self._normalize_slot_number(fairy_enemy_number)
        self._update_tooltip()
        self.update()

    def set_marker_images(self, key_image=None, fairy_image=None):
        self._key_enemy_marker = key_image if isinstance(key_image, QImage) else QImage()
        self._fairy_enemy_marker = fairy_image if isinstance(fairy_image, QImage) else QImage()
        self.update()

    def _slot_gap(self):
        return 4 if self._slot_size >= 14 else 2

    def _slot_color(self, index: int) -> QColor:
        if index >= 13:
            return QColor(self._DANGER_COLOR)
        if index >= 9:
            return QColor(self._WARN_COLOR)
        return QColor(self._SAFE_COLOR)

    def _normalize_slot_number(self, value: int) -> int:
        try:
            number = int(value)
        except Exception:
            return 0
        if 1 <= number <= self._maximum:
            return number
        return 0

    def _update_tooltip(self):
        parts = [f"敵配置数 {self._count}/{self._maximum}"]
        if self._key_enemy_number:
            parts.append(f"鍵持ち敵: #{self._key_enemy_number}")
        if self._fairy_enemy_number:
            parts.append(f"落下死で妖精化: #{self._fairy_enemy_number}")
        self.setToolTip(" / ".join(parts))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        x = 4
        icon_size = self._slot_size
        y = icon_size + 5
        slot_h = self._slot_size
        label_w = 52 if self.width() >= self.minimumWidth() else 0
        gap = self._slot_gap()
        slot_area_w = max(self._maximum * 3, self.width() - 8 - label_w)
        slot_w = min(
            self._slot_size,
            max(3, (slot_area_w - gap * (self._maximum - 1)) // self._maximum),
        )
        key_icon_y = max(0, y - icon_size - 2)
        fairy_icon_y = y + slot_h + 2
        for index in range(1, self._maximum + 1):
            color = self._slot_color(index)
            is_filled = index <= self._count
            border = QColor(color)
            border.setAlpha(230 if is_filled else 135)
            fill = QColor(color if is_filled else self._EMPTY_BG)
            if not is_filled:
                fill.setAlpha(105)
            painter.setPen(QPen(border, 1))
            painter.setBrush(fill)
            painter.drawRect(x, y, slot_w, slot_h)
            if index == self._key_enemy_number:
                self._draw_marker_image(painter, self._key_enemy_marker, x, key_icon_y, slot_w, icon_size)
            if index == self._fairy_enemy_number:
                self._draw_marker_image(painter, self._fairy_enemy_marker, x, fairy_icon_y, slot_w, icon_size)
            x += slot_w + gap

        if label_w:
            text_color = self._slot_color(min(max(self._count, 1), self._maximum))
            painter.setPen(text_color)
            painter.drawText(x + 4, y, label_w, slot_h, Qt.AlignVCenter | Qt.AlignLeft, f"{self._count}/{self._maximum}")

    def _draw_marker_image(self, painter: QPainter, image: QImage, slot_x: int,
                           icon_y: int, slot_w: int, icon_size: int):
        if image.isNull():
            return
        scaled = image.scaled(
            icon_size,
            icon_size,
            Qt.KeepAspectRatio,
            Qt.FastTransformation,
        )
        icon_x = slot_x + (slot_w - scaled.width()) // 2
        painter.drawImage(icon_x, icon_y + (icon_size - scaled.height()) // 2, scaled)


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_DISPLAY_NAME} v{__version__}")
        # _build_ui で _app_config を読み込むのでここでは仮サイズ
        self.resize(1400, 800)

        self.rom: Rom = None
        self.original_rom_data: bytes = None  # IPS生成用
        self._bonus_items = []  # ボーナスステージ(51面)アイテムテーブル
        self.levels = []
        self.config: SkcConfig = None
        self.tile_renderer: TileRenderer = None
        self.level_renderer: LevelRenderer = None
        self.current_level_no = 0
        self._read_only_mode = False
        self._read_only_reason = ""
        self._restart_after_close = False
        self._stage_clipboard = None
        self._stage_swap_source_no = None
        self._stage_compare_png_image = None
        self._stage_compare_diff_image = None
        self._stage_compare_png_level = None
        self._stage_compare_level_no = None
        self._stage_compare_path = ""
        self._stage_compare_show_diff = False
        self._stage_compare_edit_mode = False
        self._stage_compare_edit_orientation = "horizontal"
        self._stage_compare_edit_current_size = None
        self._stage_compare_diff_count = None
        self._stage_compare_diff_cells = []
        self._rom_validation_warnings = []
        self._rom_validation_rom = None
        self._rom_validation_dialog = None
        self._stats_dialog = None
        self._rom_diff_dialog = None
        self.show_grid = False
        self.show_object_labels = False
        # Ctrl+クリックでの要素移動: 1回目で掴む、2回目で移動先
        # None または {"kind": "item|enemy|meta", "src": (x,y), "data": ...}
        self._move_pending = None
        # ROM読み込み履歴
        self.last_loaded_path: str = ""
        self._loaded_source_path: str = ""
        self._loaded_workstate_path: str = ""
        self._loaded_workstate_saved_at: str = ""
        self._history: list = self._load_history()
        # Undo/Redo: 編集前スナップショットのスタック、上限は設定で変更可能
        self._undo_stack: list = []
        self._redo_stack: list = []
        self._undo_limit = DEFAULT_UNDO_LIMIT

        # 操作ログ（メモリ上に蓄積、closeEventで保存）
        from datetime import datetime
        self._session_log = []
        self._session_start = datetime.now()
        self._window_state_first_show_logged = False

        from PyQt5.QtWidgets import QApplication
        self._default_font_size = QApplication.font().pointSize()
        self._default_font_family = QApplication.font().family()

        self._build_ui()
        self._setup_button_sound()
        self._setup_shortcuts()
        self._setup_gamepad_shortcut()

        # 起動時にフォントサイズを反映
        self._apply_font_size()

        # ドラッグ&ドロップ受け入れ
        self.setAcceptDrops(True)

        # ウィンドウ位置・サイズを復元
        self._restore_window_state()
        QTimer.singleShot(0, lambda: self._write_window_state_debug("startup_timer_0ms"))
        QTimer.singleShot(500, lambda: self._write_window_state_debug("startup_timer_500ms"))
        self._log("セッション開始")

    def _setup_shortcuts(self):
        self._app_config["shortcuts"] = normalize_shortcuts(
            self._app_config.get("shortcuts")
        )
        self._app_config["gamepad_shortcuts"] = normalize_gamepad_shortcuts(
            self._app_config.get("gamepad_shortcuts")
        )
        self.shortcut_test_play = QShortcut(self._shortcut_sequence("test_play"), self)
        self.shortcut_test_play.setContext(Qt.WindowShortcut)
        self.shortcut_test_play.setAutoRepeat(False)
        self.shortcut_test_play.activated.connect(self._on_test_play)
        self.shortcut_stage_prev = QShortcut(self._shortcut_sequence("stage_prev"), self)
        self.shortcut_stage_prev.setContext(Qt.WindowShortcut)
        self.shortcut_stage_prev.activated.connect(lambda: self._change_stage_relative(-1))
        self.shortcut_stage_next = QShortcut(self._shortcut_sequence("stage_next"), self)
        self.shortcut_stage_next.setContext(Qt.WindowShortcut)
        self.shortcut_stage_next.activated.connect(lambda: self._change_stage_relative(1))
        self.shortcut_stage_compare_toggle = QShortcut(self._shortcut_sequence("stage_compare"), self)
        self.shortcut_stage_compare_toggle.setContext(Qt.WindowShortcut)
        self.shortcut_stage_compare_toggle.activated.connect(self._toggle_stage_compare_view)
        self.shortcut_stage_compare_toggle.setEnabled(False)
        self.shortcut_stage_compare_orientation = QShortcut(QKeySequence("Q"), self)
        self.shortcut_stage_compare_orientation.setContext(Qt.WindowShortcut)
        self.shortcut_stage_compare_orientation.activated.connect(
            self._toggle_stage_compare_edit_orientation
        )
        self.shortcut_stage_compare_orientation.setEnabled(False)
        self.shortcut_item_replace = QShortcut(self._shortcut_sequence("item_replace"), self)
        self.shortcut_item_replace.setContext(Qt.WindowShortcut)
        self.shortcut_item_replace.setAutoRepeat(False)
        self.shortcut_item_replace.activated.connect(self._on_show_item_replace)
        self.shortcut_item_flag_toggle = QShortcut(
            self._shortcut_sequence("item_flag_toggle"), self
        )
        self.shortcut_item_flag_toggle.setContext(Qt.WindowShortcut)
        self.shortcut_item_flag_toggle.setAutoRepeat(False)
        self.shortcut_item_flag_toggle.activated.connect(self._cycle_hover_item_flag)
        self.shortcut_item_flag_toggle_reverse = QShortcut(
            self._shortcut_sequence("item_flag_toggle_reverse"), self
        )
        self.shortcut_item_flag_toggle_reverse.setContext(Qt.WindowShortcut)
        self.shortcut_item_flag_toggle_reverse.setAutoRepeat(False)
        self.shortcut_item_flag_toggle_reverse.activated.connect(
            lambda: self._cycle_hover_item_flag(reverse=True)
        )
        self.shortcut_hover_actions = []
        for action in (
            "hover_enemy_left",
            "hover_enemy_right",
            "hover_enemy_up",
            "hover_enemy_down",
            "hover_enemy_speed",
            "hover_info",
            "hover_item_normal",
            "hover_item_hidden",
            "hover_item_in_block",
            "hover_item_white_in_block",
            "hover_item_visible_in_block",
            "hover_item_cracked_in_block",
        ):
            sc = QShortcut(self._shortcut_sequence(action), self)
            sc.setContext(Qt.WindowShortcut)
            sc.setAutoRepeat(False)
            sc.activated.connect(lambda a=action: self._trigger_shortcut_action(a))
            self.shortcut_hover_actions.append((action, sc))

    def _shortcut_text(self, action: str) -> str:
        shortcuts = normalize_shortcuts(self._app_config.get("shortcuts"))
        return shortcuts.get(action, DEFAULT_SHORTCUTS.get(action, ""))

    def _shortcut_sequence(self, action: str) -> QKeySequence:
        return QKeySequence(self._shortcut_text(action))

    def _event_shortcut_sequence(self, event) -> QKeySequence:
        mods = int(event.modifiers() & (
            Qt.ControlModifier | Qt.ShiftModifier | Qt.AltModifier | Qt.MetaModifier
        ))
        return QKeySequence(mods | int(event.key()))

    def _event_matches_shortcut(self, event, action: str) -> bool:
        target = self._shortcut_sequence(action)
        if target.isEmpty():
            return False
        return self._event_shortcut_sequence(event).matches(target) == QKeySequence.ExactMatch

    def _apply_shortcut_settings(self):
        self._app_config["shortcuts"] = normalize_shortcuts(
            self._app_config.get("shortcuts")
        )
        self._app_config["gamepad_shortcuts"] = normalize_gamepad_shortcuts(
            self._app_config.get("gamepad_shortcuts")
        )
        mapping = {
            "test_play": "shortcut_test_play",
            "stage_prev": "shortcut_stage_prev",
            "stage_next": "shortcut_stage_next",
            "stage_compare": "shortcut_stage_compare_toggle",
            "item_replace": "shortcut_item_replace",
            "item_flag_toggle": "shortcut_item_flag_toggle",
            "item_flag_toggle_reverse": "shortcut_item_flag_toggle_reverse",
        }
        for action, attr in mapping.items():
            shortcut = getattr(self, attr, None)
            if shortcut is not None:
                shortcut.setKey(self._shortcut_sequence(action))
        for action, shortcut in getattr(self, "shortcut_hover_actions", []):
            shortcut.setKey(self._shortcut_sequence(action))

    def _trigger_shortcut_action(self, action: str) -> bool:
        if action == "help":
            self._show_keymap()
            return True
        if action == "test_play":
            self._on_test_play()
            return True
        if action == "stage_prev":
            self._change_stage_relative(-1, play_sound=True)
            return True
        if action == "stage_next":
            self._change_stage_relative(1, play_sound=True)
            return True
        if action == "stage_compare" and self._stage_compare_png_image is not None:
            self._toggle_stage_compare_view()
            return True
        if action == "settings":
            self._show_settings()
            return True
        if action == "grid":
            self.chk_grid.toggle()
            return True
        if action == "undo":
            self._on_undo()
            return True
        if action in ("redo", "redo_alt"):
            self._on_redo()
            return True
        if action == "select_all":
            self._select_all_editable_area()
            return True
        if action == "item_replace":
            self._on_show_item_replace()
            return True
        if action == "item_flag_toggle":
            self._cycle_hover_item_flag()
            return True
        if action == "item_flag_toggle_reverse":
            self._cycle_hover_item_flag(reverse=True)
            return True
        if action == "clear_selection":
            if self._selection_rect is not None:
                self._on_selection_cleared()
            return True
        if action == "copy_selection":
            self._copy_selection()
            return True
        if action == "paste_selection":
            self._paste_clipboard()
            return True
        if action == "cut_selection":
            self._cut_selection()
            return True
        if action in ("delete_hover_or_selection", "delete_hover_or_selection_alt"):
            self._delete_hover_or_selection()
            return True
        if action == "clear_selection_escape":
            if self._selection_rect is not None:
                self._on_selection_cleared()
            return True
        if action == "flip_horizontal":
            self._flip_selection_horizontal()
            return True
        if action == "flip_vertical":
            self._flip_selection_vertical()
            return True
        if action.startswith("favorite_"):
            try:
                slot = int(action.rsplit("_", 1)[1])
            except ValueError:
                return False
            return self._trigger_favorite_slot(slot)
        direction_by_action = {
            "hover_enemy_left": "left",
            "hover_enemy_right": "right",
            "hover_enemy_up": "up",
            "hover_enemy_down": "down",
        }
        direction = direction_by_action.get(action)
        if direction is not None:
            return self._set_hover_enemy_direction(direction)
        if action == "hover_enemy_speed":
            return self._cycle_hover_enemy_speed()
        if action == "hover_info":
            self._toggle_hover_info_popup()
            return True
        item_flag_by_action = {
            "hover_item_normal": (c.ITEM_FLAG_NORMAL, "通常"),
            "hover_item_hidden": (0x40, "隠し"),
            "hover_item_in_block": (c.ITEM_FLAG_IN_BLOCK, "ブロック内"),
            "hover_item_white_in_block": (
                c.ITEM_FLAG_WHITE_IN_BLOCK,
                "白ブロック内",
            ),
            "hover_item_visible_in_block": (
                c.ITEM_FLAG_VISIBLE_IN_BLOCK,
                "透明ブロック内",
            ),
            "hover_item_cracked_in_block": (
                c.ITEM_FLAG_CRACKED_IN_BLOCK,
                "ひび割れブロック内",
            ),
        }
        item_flag = item_flag_by_action.get(action)
        if item_flag is not None:
            flag, label = item_flag
            self._set_hover_item_flag(flag, label)
            return True
        return False

    def _item_flag_cycle_order(self, allow_visible: bool = True, allow_cracked: bool = True):
        flags = [
            c.ITEM_FLAG_NORMAL,
            c.ITEM_FLAG_HIDDEN,
            c.ITEM_FLAG_IN_BLOCK,
            c.ITEM_FLAG_WHITE_IN_BLOCK,
        ]
        if allow_visible:
            flags.append(c.ITEM_FLAG_VISIBLE_IN_BLOCK)
        if allow_cracked:
            flags.append(c.ITEM_FLAG_CRACKED_IN_BLOCK)
        return flags

    def _item_flag_label(self, flag: int) -> str:
        return {
            c.ITEM_FLAG_NORMAL: "通常",
            c.ITEM_FLAG_HIDDEN: "隠し",
            c.ITEM_FLAG_IN_BLOCK: "ブロック内",
            c.ITEM_FLAG_WHITE_IN_BLOCK: "白ブロック内",
            c.ITEM_FLAG_VISIBLE_IN_BLOCK: "透明ブロック内",
            c.ITEM_FLAG_CRACKED_IN_BLOCK: "ひび割れブロック内",
        }.get(flag, f"0x{int(flag):X}")

    def _next_item_flag(self, current: int, allowed, reverse: bool = False):
        order = [flag for flag in self._item_flag_cycle_order() if flag in set(allowed)]
        if not order:
            return c.ITEM_FLAG_NORMAL
        try:
            idx = order.index(current)
        except ValueError:
            return order[-1] if reverse else order[0]
        step = -1 if reverse else 1
        return order[(idx + step) % len(order)]

    def _cycle_hover_item_flag(self, reverse: bool = False):
        if self._hover_tile is None or not self.levels:
            self.statusBar().showMessage("状態を切り替える対象がありません", 1200)
            return
        lv = self.levels[self.current_level_no]
        tile = self._hover_tile
        allowed = self._item_flag_cycle_order()
        current = None

        if not lv.is_key_removed() and lv.fixed_key_pos == tile:
            from ..core import constants as cc
            allowed = self._item_flag_cycle_order()
            if tile in getattr(lv, "visible_in_block_item_cells", set()):
                current = c.ITEM_FLAG_VISIBLE_IN_BLOCK
            elif (
                tile in getattr(lv, "cracked_block_cells", set())
                and lv.key_status == cc.KEY_STATUS_HIDDEN
            ):
                current = c.ITEM_FLAG_CRACKED_IN_BLOCK
            else:
                current = {
                    cc.KEY_STATUS_NORMAL: c.ITEM_FLAG_NORMAL,
                    cc.KEY_STATUS_HIDDEN: c.ITEM_FLAG_HIDDEN,
                    cc.KEY_STATUS_IN_BLOCK: c.ITEM_FLAG_IN_BLOCK,
                    cc.KEY_STATUS_WHITE_IN_BLOCK: c.ITEM_FLAG_WHITE_IN_BLOCK,
                }.get(lv.key_status, c.ITEM_FLAG_NORMAL)
        elif not lv.is_door_removed() and lv.fixed_door_pos == tile:
            from ..core import room_flags as _rf
            allowed = self._item_flag_cycle_order(allow_visible=False, allow_cracked=False)
            door_state = lv.room_flags & _rf.DOOR_STATE_MASK
            current = {
                _rf.DOOR_STATE_NORMAL: c.ITEM_FLAG_NORMAL,
                _rf.DOOR_STATE_HIDDEN: c.ITEM_FLAG_HIDDEN,
                _rf.DOOR_STATE_IN_BLOCK: c.ITEM_FLAG_IN_BLOCK,
                _rf.DOOR_STATE_WHITE_IN_BLOCK: c.ITEM_FLAG_WHITE_IN_BLOCK,
            }.get(door_state, c.ITEM_FLAG_NORMAL)
        else:
            idx = lv.get_item_index(tile)
            if idx < 0:
                self.statusBar().showMessage("状態を切り替えるアイテムがありません", 1200)
                return
            item = lv.items[idx]
            if item.element_no >= c.ITEM_COPY_INDICATOR_MIN and not item.is_white_in_block():
                self.statusBar().showMessage("このアイテム形式は状態変更できません", 1500)
                return
            base = int(item.element_no) & 0x3F
            if base > c.ITEM_WHITE_IN_BLOCK_MAX_BASE:
                allowed = [
                    c.ITEM_FLAG_NORMAL,
                    c.ITEM_FLAG_HIDDEN,
                    c.ITEM_FLAG_IN_BLOCK,
                ]
            current = self._item_replace_state(lv, item)

        next_flag = self._next_item_flag(current, allowed, reverse=reverse)
        self._set_hover_item_flag(next_flag, self._item_flag_label(next_flag))

    def _delete_hover_or_selection(self):
        if self._selection_rect is not None:
            self._delete_in_selection()
        elif self._hover_tile is not None and self.levels:
            self._on_tile_right_clicked(self._hover_tile)

    def _trigger_favorite_slot(self, slot: int) -> bool:
        if not 0 <= int(slot) <= 9:
            return False
        if not self.picker.trigger_favorite_key(int(slot)):
            self.statusBar().showMessage(
                f"お気に入りスロット {int(slot)} は空です", 1500
            )
        else:
            self.statusBar().showMessage(
                f"お気に入りスロット {int(slot)} を選択", 1500
            )
        return True

    def _setup_button_sound(self):
        self._button_sounds = []
        self._button_sound_index = 0
        sound_path = Path(__file__).resolve().parent.parent / "button.wav"
        if not sound_path.exists():
            return
        sound_url = QUrl.fromLocalFile(str(sound_path))
        for _ in range(3):
            effect = QSoundEffect(self)
            effect.setSource(sound_url)
            effect.setVolume(0.8)
            self._button_sounds.append(effect)

    def _play_button_sound(self):
        sounds = getattr(self, "_button_sounds", [])
        if not sounds:
            return
        effect = sounds[self._button_sound_index % len(sounds)]
        self._button_sound_index += 1
        effect.play()

    def _setup_gamepad_shortcut(self):
        self._xinput_get_state = _load_xinput_get_state()
        self._xinput_last_buttons = [0] * _XINPUT_MAX_CONTROLLERS
        self._xinput_timer = None
        if self._xinput_get_state is None:
            return
        self._xinput_timer = QTimer(self)
        self._xinput_timer.setInterval(80)
        self._xinput_timer.timeout.connect(self._poll_gamepad_shortcut)
        self._xinput_timer.start()

    def _poll_gamepad_shortcut(self):
        if self._xinput_get_state is None:
            return
        active = self.isActiveWindow()
        gamepad_shortcuts = normalize_gamepad_shortcuts(
            self._app_config.get("gamepad_shortcuts")
        )
        for index in range(_XINPUT_MAX_CONTROLLERS):
            state = _XInputState()
            try:
                connected = self._xinput_get_state(index, ctypes.byref(state)) == 0
            except OSError:
                return
            buttons = state.Gamepad.wButtons if connected else 0
            last = self._xinput_last_buttons[index]
            pressed = buttons & ~last
            if active and pressed:
                for action, button_name in gamepad_shortcuts.items():
                    mask = _XINPUT_BUTTON_BY_NAME.get(button_name)
                    if mask and (pressed & mask):
                        self._xinput_last_buttons[index] = buttons
                        if self._trigger_shortcut_action(action):
                            return
            self._xinput_last_buttons[index] = buttons

    def _log(self, msg: str):
        """操作ログをメモリに追記（closeEventでファイルに書き出す）"""
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        self._session_log.append(f"[{ts}] {msg}")

    def _window_state_debug_path(self) -> Path:
        return Path(__file__).parent.parent.parent / "logs" / "window_state_debug.log"

    def _window_state_config_snapshot(self) -> dict:
        keys = (
            "window_x",
            "window_y",
            "window_w",
            "window_h",
            "window_fullscreen",
            "window_maximized",
            "splitter_sizes",
            "stage_selector_visible",
            "stage_selector_last_width",
            "settings_dialog_x",
            "settings_dialog_y",
            "settings_dialog_w",
            "settings_dialog_h",
            "settings_dialog_tab",
            "hack_dlg_x",
            "hack_dlg_y",
            "hack_dlg_w",
            "hack_dlg_h",
            "stats_dlg_x",
            "stats_dlg_y",
            "stats_dlg_w",
            "stats_dlg_h",
            "sprite_viewer_x",
            "sprite_viewer_y",
            "sprite_viewer_w",
            "sprite_viewer_h",
            "pixel_editor_x",
            "pixel_editor_y",
            "pixel_editor_w",
            "pixel_editor_h",
        )
        return {key: self._app_config.get(key) for key in keys}

    def _window_state_runtime_snapshot(self) -> dict:
        geo = self.geometry()
        fgeo = self.frameGeometry()
        normal = self.normalGeometry()
        screen = self.screen()
        splitter_sizes = None
        if hasattr(self, "splitter"):
            splitter_sizes = list(self.splitter.sizes())
        return {
            "geometry": [geo.x(), geo.y(), geo.width(), geo.height()],
            "frameGeometry": [fgeo.x(), fgeo.y(), fgeo.width(), fgeo.height()],
            "normalGeometry": [normal.x(), normal.y(), normal.width(), normal.height()],
            "pos": [self.x(), self.y()],
            "size": [self.width(), self.height()],
            "isVisible": self.isVisible(),
            "isMaximized": self.isMaximized(),
            "isFullScreen": self.isFullScreen(),
            "windowState": int(self.windowState()),
            "screen": screen.name() if screen is not None else None,
            "splitter_sizes": splitter_sizes,
        }

    def _window_state_screen_snapshot(self) -> list:
        screens = []
        for screen in QApplication.screens():
            geo = screen.geometry()
            avail = screen.availableGeometry()
            screens.append({
                "name": screen.name(),
                "geometry": [geo.x(), geo.y(), geo.width(), geo.height()],
                "availableGeometry": [avail.x(), avail.y(), avail.width(), avail.height()],
                "devicePixelRatio": float(screen.devicePixelRatio()),
            })
        return screens

    def _write_window_state_debug(self, label: str, extra: dict | None = None):
        if os.environ.get(WINDOW_STATE_DEBUG_ENV) != "1":
            return
        try:
            from datetime import datetime
            payload = {
                "time": datetime.now().isoformat(timespec="milliseconds"),
                "version": __version__,
                "label": str(label),
                "config_path": str(get_config_path()),
                "config": self._window_state_config_snapshot(),
                "runtime": self._window_state_runtime_snapshot(),
                "screens": self._window_state_screen_snapshot(),
            }
            if extra:
                payload["extra"] = extra
            path = self._window_state_debug_path()
            path.parent.mkdir(exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
                f.write("\n")
        except Exception:
            pass

    def _set_picker_override_cursor(self, cursor: QCursor):
        self._picker_canvas_cursor = QCursor(cursor)
        try:
            viewport = self.level_view.viewport()
            if viewport.underMouse():
                if getattr(self, "_picker_override_cursor_active", False):
                    QApplication.changeOverrideCursor(self._picker_canvas_cursor)
                else:
                    QApplication.setOverrideCursor(self._picker_canvas_cursor)
                    self._picker_override_cursor_active = True
        except Exception:
            pass

    def _apply_picker_override_cursor(self):
        cursor = getattr(self, "_picker_canvas_cursor", None)
        if cursor is None:
            return
        try:
            if getattr(self, "_picker_override_cursor_active", False):
                QApplication.changeOverrideCursor(cursor)
            else:
                QApplication.setOverrideCursor(cursor)
                self._picker_override_cursor_active = True
        except Exception:
            pass

    def _clear_picker_override_cursor(self):
        if not getattr(self, "_picker_override_cursor_active", False):
            return
        try:
            QApplication.restoreOverrideCursor()
        except Exception:
            pass
        self._picker_override_cursor_active = False

    def showEvent(self, event):
        super().showEvent(event)
        if not getattr(self, "_window_state_first_show_logged", False):
            self._window_state_first_show_logged = True
            self._write_window_state_debug("first_show_event")

    def _is_read_only(self) -> bool:
        return bool(getattr(self, "_read_only_mode", False))

    def _reject_read_only_edit(self) -> bool:
        if not self._is_read_only():
            return False
        self.statusBar().showMessage(
            "編集不可: 閲覧/ステージ出力専用ROMです", 3000
        )
        return True

    def _update_stage_operation_buttons(self):
        can_edit = bool(self.levels) and not self._is_read_only()
        if hasattr(self, "btn_stage_copy"):
            self.btn_stage_copy.setEnabled(can_edit)
        if hasattr(self, "btn_stage_paste"):
            self.btn_stage_paste.setEnabled(can_edit and self._stage_clipboard is not None)
        if hasattr(self, "btn_stage_swap"):
            self.btn_stage_swap.setEnabled(can_edit)
        if hasattr(self, "spin_stage_swap_target"):
            self.spin_stage_swap_target.setEnabled(can_edit)
            if can_edit:
                self.spin_stage_swap_target.setRange(1, len(self.levels))
            else:
                self._stage_swap_source_no = None
                self.spin_stage_swap_target.setVisible(False)
                if hasattr(self, "btn_stage_swap"):
                    self.btn_stage_swap.setText("面入れ替え")
        if hasattr(self, "lbl_stage_clipboard"):
            if self._stage_swap_source_no is not None:
                self.lbl_stage_clipboard.setText(
                    f"入れ替え元: {self._stage_label(self._stage_swap_source_no)}"
                )
            elif self._stage_clipboard is None:
                self.lbl_stage_clipboard.setText("コピー元: なし")
            else:
                source_no = int(self._stage_clipboard["source_level_no"]) + 1
                self.lbl_stage_clipboard.setText(f"コピー元: L{source_no:02d}")

    def _restore_window_state(self):
        """設定からウィンドウ位置・サイズ・最大化/フルスクリーン状態を復元"""
        cfg = self._app_config
        w = cfg.get("window_w", 1400)
        h = cfg.get("window_h", 800)
        x = cfg.get("window_x", -1)
        y = cfg.get("window_y", -1)
        restore_info = {
            "requested": {
                "x": x,
                "y": y,
                "w": w,
                "h": h,
                "fullscreen": cfg.get("window_fullscreen", False),
                "maximized": cfg.get("window_maximized", False),
            },
            "resize_applied": False,
            "move_applied": False,
            "move_rejected_reason": "",
            "state_applied": "normal",
        }
        self._write_window_state_debug("restore_before", restore_info)
        if isinstance(w, int) and isinstance(h, int) and w > 100 and h > 100:
            self.resize(w, h)
            restore_info["resize_applied"] = True
        if isinstance(x, int) and isinstance(y, int) and x >= 0 and y >= 0:
            # 画面外に行かないように軽くチェック
            from PyQt5.QtWidgets import QApplication
            screens = QApplication.screens()
            if screens:
                # いずれかのスクリーンに乗っていればOK
                for sc in screens:
                    g = sc.geometry()
                    if g.contains(x + 50, y + 50):
                        self.move(x, y)
                        restore_info["move_applied"] = True
                        break
                if not restore_info["move_applied"]:
                    restore_info["move_rejected_reason"] = "saved position is outside all screens"
            else:
                restore_info["move_rejected_reason"] = "no screens"
        else:
            restore_info["move_rejected_reason"] = "saved position is not set"
        if cfg.get("window_fullscreen", False):
            self.showFullScreen()
            restore_info["state_applied"] = "fullscreen"
        elif cfg.get("window_maximized", False):
            self.showMaximized()
            restore_info["state_applied"] = "maximized"
        self._write_window_state_debug("restore_after", restore_info)

    def _save_window_state(self):
        """現在のウィンドウ状態を設定に保存"""
        cfg = self._app_config
        self._write_window_state_debug("save_before")
        is_fullscreen = self.isFullScreen()
        cfg["window_fullscreen"] = is_fullscreen
        cfg["window_maximized"] = (not is_fullscreen) and self.isMaximized()
        if not is_fullscreen and not self.isMaximized():
            # 通常時のみ位置・サイズを記録（最大化/フルスクリーン状態のサイズは記録しない）
            # frameGeometry: タイトルバー・枠を含む外側座標（move() と対応）
            fgeo = self.frameGeometry()
            cfg["window_x"] = fgeo.x()
            cfg["window_y"] = fgeo.y()
            # サイズはクライアント領域（resize() と対応）
            cfg["window_w"] = self.width()
            cfg["window_h"] = self.height()
        # スプリッター幅
        cfg["splitter_sizes"] = list(self.splitter.sizes())
        if hasattr(self, "chk_stage_selector"):
            cfg["stage_selector_visible"] = self.chk_stage_selector.isChecked()
        if hasattr(self, "_stage_selector_last_width"):
            cfg["stage_selector_last_width"] = int(self._stage_selector_last_width)
        from ..core.config import save_config
        save_config(cfg)
        self._write_window_state_debug("save_after", {
            "saved_config": self._window_state_config_snapshot(),
        })

    def _build_ui(self):
        # 中央ウィジェット
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        # アプリ設定
        from ..core.config import load_config
        self._app_config = load_config()
        self._apply_history_limit_settings()

        # 左サイド
        left_widget = self._build_left_panel()

        # 最右: レベル選択（サムネイル付き）
        self.levelselect_widget = self._build_levelselect_panel()

        # 中右: 要素ピッカー
        self.picker = ElementPicker()
        self.picker.set_icon_size_value(self._app_config.get("picker_icon_size", 36))
        self.picker.icon_size_changed.connect(self._on_picker_icon_size_changed)
        self.picker.set_marker_overlay_scale(
            self._app_config.get("marker_overlay_scale", 3)
        )
        self.picker.set_marker_colors(self._marker_color_config())
        self.picker.set_marker_shapes(self._marker_shape_config())
        self.picker.selection_changed.connect(self._on_picker_selection_changed)
        self.picker.block_order_changed.connect(self._on_block_order_changed)
        # お気に入りの永続化
        self.picker.favorites.favorites_changed.connect(self._on_favorites_changed)
        # ボーナスパネルからのアイテム変更
        self.picker.bonus_panel.items_changed.connect(self._on_bonus_panel_items_changed)
        # ミラー敵セット変更
        self.picker.mirror_panel.enemies_changed.connect(self._on_mirror_panel_changed)
        self.picker.mirror_panel.mirror_active_toggle_requested.connect(
            self._on_toggle_mirror_schedule
        )
        self.btn_mirror = QPushButton("ミラー詳細設定")
        self.btn_mirror.setToolTip(
            "現在ステージの2つのミラーについて、出現タイミング(64ビット)とTTLを編集"
        )
        self.btn_mirror.clicked.connect(self._on_show_mirror)
        mirror_button_row = QWidget()
        mirror_button_layout = QHBoxLayout(mirror_button_row)
        mirror_button_layout.setContentsMargins(0, 0, 0, 0)
        mirror_button_layout.setSpacing(4)
        mirror_button_layout.addWidget(self.btn_mirror, 1)
        self.picker.set_mirror_detail_button(mirror_button_row)
        self.picker.set_extra_panel_widget(self._build_panel_variant_panel())

        # 中央: レベルビュー
        self.level_view = LevelView(self)
        self.level_view.set_marker_overlay_scale(
            self._app_config.get("marker_overlay_scale", 3)
        )
        self.level_view.set_marker_colors(self._marker_color_config())
        self.level_view.set_marker_shapes(self._marker_shape_config())
        self.level_view.tile_clicked.connect(self._on_tile_clicked)
        self.level_view.tile_right_clicked.connect(self._on_tile_right_clicked)
        # Ctrl+左ドラッグでの要素移動
        self.level_view.drag_start.connect(self._on_drag_start)
        self.level_view.drag_move.connect(self._on_drag_move)
        self.level_view.drag_end.connect(self._on_drag_end)
        # ホバーハイライト
        self.level_view.tile_hovered.connect(self._on_tile_hovered)
        self.level_view.direction_key_pressed.connect(self._set_hover_enemy_direction)
        self.level_view.hover_action_key_pressed.connect(self._on_level_view_hover_action)
        self._hover_tile = None
        self._hover_info_popup_label = QLabel(self.level_view.viewport())
        self._hover_info_popup_label.setTextFormat(Qt.RichText)
        self._hover_info_popup_label.setWordWrap(False)
        self._hover_info_popup_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._apply_hover_info_popup_style()
        self._hover_info_popup_label.hide()
        # 左/右 ドラッグ塗り・消し
        self.level_view.tile_painted.connect(self._on_tile_painted)
        self.level_view.tile_erased.connect(self._on_tile_erased)
        # Alt+左クリックでスポイト
        self.level_view.tile_picked.connect(self._on_tile_picked)
        # Shift+左ドラッグで矩形範囲選択
        self.level_view.selection_updated.connect(self._on_selection_updated)
        self.level_view.selection_cleared.connect(self._on_selection_cleared)
        self._selection_rect = None  # (start_tile, end_tile)
        # 選択範囲操作のクリップボード
        # {"w": int, "h": int, "blocks": {(x,y): wall}, "items": [...], "enemies": [...]}
        self._clipboard = None
        # 選択範囲ドラッグ移動用のベース状態
        self._drag_base_level = None
        # 未保存変更フラグ
        self._dirty = False
        self.level_view.rom_dropped.connect(self._on_rom_dropped)
        self.level_view.stage_png_dropped.connect(self._on_stage_png_dropped)
        self.enemy_count_indicator = _EnemyCountIndicator(self.level_view.viewport())
        self.enemy_count_indicator.set_slot_size(
            self._app_config.get("enemy_count_meter_slot_size", 18)
        )
        self.enemy_count_indicator.hide()
        self.stage_number_label = _StageNumberLabel(self, "", self.level_view.viewport())
        self.stage_number_label.setStyleSheet(
            "QLabel { color: #54ff4d; background: transparent; "
            "font-size: 34px; font-weight: 900; }"
        )
        self.stage_number_label.setAlignment(Qt.AlignCenter)
        self.stage_number_label.setFixedHeight(54)
        self.stage_number_label.hide()
        self.stage_compare_diff_label = QLabel("", self.level_view.viewport())
        self.stage_compare_diff_label.setStyleSheet(
            "QLabel { color: #ff5af7; background: rgba(0, 25, 8, 170); "
            "border: 1px solid #ff5af7; border-radius: 2px; "
            "font-size: 22px; font-weight: 900; padding: 3px 8px; }"
        )
        self.stage_compare_diff_label.setAlignment(Qt.AlignCenter)
        self.stage_compare_diff_label.hide()
        self.btn_stage_prev_canvas = QToolButton(self.level_view.viewport())
        self.btn_stage_next_canvas = QToolButton(self.level_view.viewport())
        for btn, text, tip, delta in (
            (self.btn_stage_prev_canvas, "◀", "前のステージ", -1),
            (self.btn_stage_next_canvas, "▶", "次のステージ", 1),
        ):
            btn.setText(text)
            btn.setToolTip(tip)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setAutoRaise(True)
            btn.setFixedSize(26, 24)
            btn.setStyleSheet(
                "QToolButton { color: #54ff4d; background: rgba(0, 40, 10, 150); "
                "border: 1px solid #168c2d; border-radius: 2px; font-size: 15px; "
                "font-weight: 900; padding: 0px; }"
                "QToolButton:hover { background: rgba(0, 130, 30, 190); "
                "border-color: #30ff53; }"
                "QToolButton:pressed { background: rgba(30, 255, 70, 210); color: #001800; }"
            )
            btn.clicked.connect(lambda _checked=False, d=delta: self._change_stage_relative(d, play_sound=True))
            btn.hide()
        self.level_view.viewport().installEventFilter(self)

        # スプリッター
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(left_widget)
        self.splitter.addWidget(self.level_view)
        self.splitter.addWidget(self.picker)
        self.splitter.addWidget(self.levelselect_widget)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setStretchFactor(2, 0)
        self.splitter.setStretchFactor(3, 0)
        # 保存されたサイズを復元（無ければデフォルト）
        saved_sizes = self._app_config.get("splitter_sizes", [280, 700, 250, 220])
        if isinstance(saved_sizes, list) and len(saved_sizes) == 4 and all(isinstance(s, int) and s >= 0 for s in saved_sizes):
            self.splitter.setSizes(saved_sizes)
        else:
            self.splitter.setSizes([280, 700, 250, 220])
        self._stage_selector_last_width = max(
            int(self._app_config.get("stage_selector_last_width", 220) or 220),
            160,
        )
        self._apply_stage_selector_visibility(
            bool(self._app_config.get("stage_selector_visible", True)),
            resize_splitter=False,
        )

        main_layout.addWidget(self.splitter)

        # ステータスバー
        self.statusBar().showMessage("準備完了 (F1: ヘルプ / F9: 設定)")
        # マウス下部のタイル情報を常時表示（右寄せ・固定）
        self.lbl_hover_info = QLabel("")
        self.lbl_hover_info.setMinimumWidth(420)
        self.statusBar().addPermanentWidget(self.lbl_hover_info)

    def eventFilter(self, obj, event):
        if (hasattr(self, "level_view") and
                obj is self.level_view.viewport() and
                event.type() in (QEvent.Resize, QEvent.Show)):
            self.level_view.set_top_viewport_padding(self._level_view_top_overlay_padding())
            self._position_enemy_count_indicator()
            self._position_stage_number_label()
            self._position_stage_compare_diff_label()
        if (hasattr(self, "level_view") and
                obj is self.level_view.viewport() and
                event.type() in (
                    QEvent.Enter,
                    QEvent.Leave,
                    QEvent.MouseButtonPress,
                    QEvent.MouseButtonRelease,
                    QEvent.MouseMove,
                    QEvent.FocusIn,
                    QEvent.FocusOut,
                )):
            if event.type() in (QEvent.Enter, QEvent.MouseMove, QEvent.FocusIn):
                self._apply_picker_override_cursor()
            elif event.type() in (QEvent.Leave, QEvent.FocusOut):
                self._clear_picker_override_cursor()
        return super().eventFilter(obj, event)

    def _level_view_top_overlay_padding(self) -> int:
        if not getattr(self, "levels", None):
            return 0
        heights = []
        label = getattr(self, "stage_number_label", None)
        if label is not None:
            heights.append(label.height())
        indicator = getattr(self, "enemy_count_indicator", None)
        if indicator is not None:
            heights.append(indicator.height())
        if not heights:
            return 0
        return max(heights) + 8

    def _position_stage_number_label(self):
        if not hasattr(self, "stage_number_label"):
            return
        label = self.stage_number_label
        viewport = self.level_view.viewport()
        h = label.height()
        x = 12
        y = 8

        pixmap_item = getattr(self.level_view, "_pixmap_item", None)
        if pixmap_item is not None:
            scene_rect = pixmap_item.mapRectToScene(pixmap_item.boundingRect())
            top_left = self.level_view.mapFromScene(scene_rect.topLeft())
            bottom_right = self.level_view.mapFromScene(scene_rect.bottomRight())
            top_margin = max(0, top_left.y())
            x = max(8, top_left.x() + 16)
            if top_margin >= h + 8:
                y = max(4, (top_margin - h) // 2)
            else:
                y = max(4, top_left.y() + 8)

        right_limit = viewport.width() - 8
        if hasattr(self, "enemy_count_indicator") and self.enemy_count_indicator.isVisible():
            right_limit = min(right_limit, self.enemy_count_indicator.x() - 8)
        button_w = 26
        gap = 4
        text_w = label.fontMetrics().horizontalAdvance(label.text()) + 10
        label_w = min(max(120, text_w), max(60, right_limit - x - (button_w * 2) - (gap * 2)))
        label.resize(label_w, h)
        label.move(x + button_w + gap, y)
        label.raise_()
        if hasattr(self, "btn_stage_prev_canvas") and hasattr(self, "btn_stage_next_canvas"):
            btn_y = max(4, y + (h - self.btn_stage_prev_canvas.height()) // 2)
            self.btn_stage_prev_canvas.move(x, btn_y)
            self.btn_stage_next_canvas.move(
                min(right_limit - button_w, x + button_w + gap + label_w + gap),
                btn_y,
            )
            self.btn_stage_prev_canvas.raise_()
            self.btn_stage_next_canvas.raise_()

    def _position_stage_compare_diff_label(self):
        label = getattr(self, "stage_compare_diff_label", None)
        if label is None or not label.isVisible():
            return
        viewport = self.level_view.viewport()
        label.adjustSize()
        w = label.width()
        h = label.height()
        y = 10
        x = viewport.width() - w - 12
        indicator = getattr(self, "enemy_count_indicator", None)
        if indicator is not None and indicator.isVisible():
            candidate_x = indicator.x() + indicator.width() + 16
            if candidate_x + w <= viewport.width() - 12:
                x = candidate_x
            else:
                x = max(12, viewport.width() - w - 12)
            y = indicator.y() + max(0, (indicator.height() - h) // 2)
        label.move(max(12, x), max(4, y))
        label.raise_()

    def _position_enemy_count_indicator(self):
        if not hasattr(self, "enemy_count_indicator"):
            return
        indicator = self.enemy_count_indicator
        viewport = self.level_view.viewport()
        h = indicator.height()
        w = min(max(356, indicator.minimumWidth()), max(92, viewport.width() - 8))
        indicator.resize(w, h)
        x = max(4, (viewport.width() - w) // 2)
        y = 10

        pixmap_item = getattr(self.level_view, "_pixmap_item", None)
        if pixmap_item is not None:
            scene_rect = pixmap_item.mapRectToScene(pixmap_item.boundingRect())
            top = self.level_view.mapFromScene(scene_rect.topLeft()).y()
            bottom = self.level_view.mapFromScene(scene_rect.bottomRight()).y()
            top_margin = max(0, top)
            bottom_margin = max(0, viewport.height() - bottom)
            if top_margin >= h + 8:
                y = max(4, (top_margin - h) // 2)
            elif bottom_margin >= h + 8:
                y = bottom + max(4, (bottom_margin - h) // 2)
            else:
                y = 8

        indicator.move(x, y)
        indicator.raise_()

    def _update_stage_number_label(self):
        if not hasattr(self, "stage_number_label"):
            return
        if not self.levels or not (0 <= self.current_level_no < len(self.levels)):
            self.stage_number_label.hide()
            if hasattr(self, "btn_stage_prev_canvas"):
                self.btn_stage_prev_canvas.hide()
            if hasattr(self, "btn_stage_next_canvas"):
                self.btn_stage_next_canvas.hide()
            return
        stage_no = self.current_level_no + 1
        self.stage_number_label.setText(f"STAGE {stage_no:02d}")
        self.stage_number_label.setToolTip(f"現在のステージ: {stage_no}\nマウスホイールでステージ切替")
        self.stage_number_label.show()
        max_stage = min(c.LEVEL_COUNT, len(self.levels))
        if hasattr(self, "btn_stage_prev_canvas"):
            self.btn_stage_prev_canvas.setEnabled(stage_no > 1)
            self.btn_stage_prev_canvas.show()
        if hasattr(self, "btn_stage_next_canvas"):
            self.btn_stage_next_canvas.setEnabled(stage_no < max_stage)
            self.btn_stage_next_canvas.show()
        self._position_stage_number_label()

    def _update_stage_compare_diff_label(self):
        label = getattr(self, "stage_compare_diff_label", None)
        if label is None:
            return
        if not self._is_stage_compare_edit_view() or self._stage_compare_diff_count is None:
            label.hide()
            return
        label.setText(f"差分 {self._stage_compare_diff_count}")
        label.show()
        self._position_stage_compare_diff_label()

    def _update_enemy_count_indicator(self):
        if not hasattr(self, "enemy_count_indicator"):
            return
        if not self.levels or not (0 <= self.current_level_no < len(self.levels)):
            self.enemy_count_indicator.hide()
            return
        level = self.levels[self.current_level_no]
        count = len(getattr(level, "enemies", []) or [])
        self.enemy_count_indicator.set_count(count, c.ENEMY_COUNT_MAX)
        key_marker, fairy_marker = self._enemy_count_indicator_marker_images(level)
        self.enemy_count_indicator.set_marker_images(key_marker, fairy_marker)
        self.enemy_count_indicator.set_special_slots(
            stage_ext.get_key_enemy_number(level),
            stage_ext.get_fairy_enemy_number(level),
        )
        self.enemy_count_indicator.show()
        self._position_enemy_count_indicator()

    def _enemy_count_indicator_marker_images(self, level):
        if self.tile_renderer is None or self.level_renderer is None:
            return QImage(), QImage()
        try:
            ts_no = self.level_renderer.get_actual_tileset_no(
                self.current_level_no,
                level.tileset_no,
            )
            wall_color = self.level_renderer.get_wall_color(self.current_level_no)
            key_img = self.level_renderer.key_enemy_overlay_image(64)
            fairy_img = self.tile_renderer.get_tile_image(
                self.level_renderer.get_enemy_animation(0x1C),
                ts_no,
                transparent=True,
                bg_main_color=wall_color,
            )
            return key_img, fairy_img
        except Exception:
            return QImage(), QImage()

    def _build_left_panel(self) -> QWidget:
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        # ファイル操作
        file_group = QGroupBox("ファイル")
        fl = QVBoxLayout(file_group)
        self.btn_open = QPushButton("ROMを開く")
        self.btn_open.clicked.connect(self._on_open_rom)
        fl.addWidget(self.btn_open)

        # 再起動・再読込・履歴ボタン（3列）
        btn_row = QHBoxLayout()
        self.btn_restart = QPushButton("再起動")
        self.btn_restart.setToolTip("アプリを再起動")
        self.btn_restart.clicked.connect(self._on_restart_app)
        btn_row.addWidget(self.btn_restart, 1)

        self.btn_reload = QPushButton("再読込")
        self.btn_reload.setToolTip("現在のROMを再読み込み（編集を破棄）")
        self.btn_reload.clicked.connect(self._on_reload_rom)
        self.btn_reload.setEnabled(False)
        btn_row.addWidget(self.btn_reload, 1)

        self.btn_history = QPushButton("履歴")
        self.btn_history.setToolTip("最近開いたROMから選択")
        self.btn_history.clicked.connect(self._on_show_history)
        btn_row.addWidget(self.btn_history, 1)
        fl.addLayout(btn_row)

        self.lbl_rom = QLabel("(未読込)")
        self.lbl_rom.setWordWrap(True)
        rom_info_row = QHBoxLayout()
        rom_info_row.addWidget(self.lbl_rom, 1)
        self.btn_rom_validation = QPushButton("不整合")
        self.btn_rom_validation.setToolTip("読み込んだROMの不整合らしき配置を一覧表示")
        self.btn_rom_validation.setVisible(False)
        self.btn_rom_validation.clicked.connect(self._on_show_rom_validation)
        rom_info_row.addWidget(self.btn_rom_validation, 0, Qt.AlignTop)
        fl.addLayout(rom_info_row)

        # 保存系は横2列に (改造ROM保存 / IPSパッチ出力)
        self.btn_save_rom = QPushButton("別名でROM保存")
        self.btn_save_rom.clicked.connect(self._on_save_rom)
        self.btn_save_rom.setEnabled(False)
        self.btn_save_ips = QPushButton("IPSパッチ出力")
        self.btn_save_ips.clicked.connect(self._on_save_ips)
        self.btn_save_ips.setEnabled(False)
        _save_row = QHBoxLayout()
        _save_row.addWidget(self.btn_save_rom)
        _save_row.addWidget(self.btn_save_ips)
        fl.addLayout(_save_row)

        self.btn_test_play = self._create_test_play_button(
            "▶ テストプレイ (現在ステージ)"
        )
        fl.addWidget(self.btn_test_play)

        stage_scope_row = QHBoxLayout()
        self.rb_stage_current = QRadioButton("現在のステージ")
        self.rb_stage_all = QRadioButton("すべてのステージ")
        self.rb_stage_current.setChecked(True)
        self._stage_scope_group = QButtonGroup(self)
        self._stage_scope_group.addButton(self.rb_stage_current)
        self._stage_scope_group.addButton(self.rb_stage_all)
        stage_scope_row.addWidget(self.rb_stage_current)
        stage_scope_row.addWidget(self.rb_stage_all)
        self.chk_stage_png_secrets = QCheckBox("隠し表示")
        self.chk_stage_png_secrets.setChecked(True)
        self.chk_stage_png_secrets.setToolTip(
            "ON: 制作者確認用として隠しアイテムや特殊ブロックを画像にも表示します。\n"
            "OFF: 友人へ渡すプレイ用として隠し要素を画像から隠します。\n"
            "PNG内のステージデータXMLはON/OFFに関係なく保持されます。"
        )
        stage_scope_row.addWidget(self.chk_stage_png_secrets)
        fl.addLayout(stage_scope_row)

        stage_btn_row = QHBoxLayout()
        self.btn_stage_load = QPushButton("ステージデータ読込")
        self.btn_stage_load.clicked.connect(self._on_stage_data_load)
        self.btn_stage_load.setEnabled(False)
        stage_btn_row.addWidget(self.btn_stage_load)

        self.btn_stage_save = QPushButton("ステージデータ保存")
        self.btn_stage_save.clicked.connect(self._on_stage_data_save)
        self.btn_stage_save.setEnabled(False)
        stage_btn_row.addWidget(self.btn_stage_save)
        fl.addLayout(stage_btn_row)

        self.btn_stage_compare_current = QPushButton("現在")
        self.btn_stage_compare_current.setCheckable(True)
        self.btn_stage_compare_current.clicked.connect(
            lambda: self._set_stage_compare_view(False)
        )

        self.btn_stage_compare_diff = QPushButton("差分")
        self.btn_stage_compare_diff.setCheckable(True)
        self.btn_stage_compare_diff.clicked.connect(
            lambda: self._set_stage_compare_view(True)
        )

        self._stage_compare_view_group = QButtonGroup(self)
        self._stage_compare_view_group.setExclusive(True)
        self._stage_compare_view_group.addButton(self.btn_stage_compare_current)
        self._stage_compare_view_group.addButton(self.btn_stage_compare_diff)
        self.lbl_stage_compare_mode = QLabel("")
        self.lbl_stage_compare_mode.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.lbl_stage_compare_mode.setMinimumWidth(0)
        stage_compare_edit_row = QHBoxLayout()
        stage_compare_edit_row.addWidget(self.lbl_stage_compare_mode, 1)
        self.btn_stage_compare_orientation = QPushButton("縦横(Q)")
        self.btn_stage_compare_orientation.setToolTip(
            "比較しながら編集の表示方向を横並び/縦並びで切り替えます。"
        )
        self.btn_stage_compare_orientation.clicked.connect(
            self._toggle_stage_compare_edit_orientation
        )
        stage_compare_edit_row.addWidget(self.btn_stage_compare_orientation)
        self.btn_stage_compare_edit_end = QPushButton("終了")
        self.btn_stage_compare_edit_end.setToolTip("比較編集モードを終了して通常表示に戻します。")
        self.btn_stage_compare_edit_end.clicked.connect(lambda: self._clear_stage_compare())
        stage_compare_edit_row.addWidget(self.btn_stage_compare_edit_end)
        fl.addLayout(stage_compare_edit_row)

        compare_tool_row = QHBoxLayout()
        self.btn_rom_diff = QPushButton("ROM比較")
        self.btn_rom_diff.setToolTip(
            "ROM/ZIP同士のステージ差分を比較します。PNGとの比較は比較編集を使います。"
        )
        self.btn_rom_diff.clicked.connect(self._on_show_rom_diff)
        compare_tool_row.addWidget(self.btn_rom_diff)
        self.btn_stage_compare_edit_start = QPushButton("比較編集")
        self.btn_stage_compare_edit_start.setToolTip(
            "現在ステージのスナップショットを横に表示して比較編集モードを開始します。"
        )
        self.btn_stage_compare_edit_start.clicked.connect(
            self.start_stage_compare_edit_from_snapshot
        )
        compare_tool_row.addWidget(self.btn_stage_compare_edit_start)
        fl.addLayout(compare_tool_row)
        self._set_stage_compare_controls_visible(False)
        left_layout.addWidget(file_group)

        # 表示オプション
        opt_group = QGroupBox("表示オプション")
        ol = QVBoxLayout(opt_group)
        self.chk_grid = QCheckBox("グリッド表示")
        self.chk_grid.toggled.connect(self._on_grid_toggled)
        ol.addWidget(self.chk_grid)
        self.chk_hidden = QCheckBox("隠し要素強調 (黄色枠)")
        self.chk_hidden.setChecked(False)
        self.chk_hidden.toggled.connect(self._refresh_view)
        ol.addWidget(self.chk_hidden)
        # 特殊処理マーカー表示 (Per-Room Special Process で動的配置されるマス)
        self.chk_special_marks = QCheckBox("特殊処理マーカー表示")
        self.chk_special_marks.setChecked(True)
        self.chk_special_marks.setToolTip(
            "ROMのハードコード特殊処理が動的に配置するマスを枠で表示。\n"
            "緑=壊せるブロック / 水色=強制クリア\n"
            "例: Stage 50 SOLOMON の (7,1) (12,7) (3,3) は壊せる隠しブロックとして配置される"
        )
        self.chk_special_marks.toggled.connect(self._refresh_view)
        ol.addWidget(self.chk_special_marks)
        self.chk_object_labels = QCheckBox("キャンバス上のオブジェクト名表示")
        self.chk_object_labels.setToolTip(
            "ONにすると、キャンバス上の鍵・扉・アイテム・敵・ミラーなどに"
            "短い名前ラベルを重ねて表示します。")
        self.chk_object_labels.toggled.connect(self._on_object_labels_toggled)
        ol.addWidget(self.chk_object_labels)
        self.chk_stage_selector = QCheckBox("ステージ選択ペイン表示")
        self.chk_stage_selector.setToolTip(
            "右端のサムネイル付きステージ選択ペインを表示/非表示にします。"
        )
        self.chk_stage_selector.setChecked(
            bool(self._app_config.get("stage_selector_visible", True))
        )
        self.chk_stage_selector.toggled.connect(self._on_stage_selector_toggled)
        ol.addWidget(self.chk_stage_selector)
        # 16列目（右端）の表示・編集
        self.chk_edit_col15 = QCheckBox("16列目を編集")
        self.chk_edit_col15.setChecked(False)
        self.chk_edit_col15.setToolTip(
            "右端列(16列目)はデータ上常に壁。通常は編集不可。\n"
            "ONにすると編集できる。"
        )
        ol.addWidget(self.chk_edit_col15)
        left_layout.addWidget(opt_group)

        # 編集ツール (2列グリッド)
        from PyQt5.QtWidgets import (
            QToolButton, QMenu as _QMenu, QGridLayout as _QGrid)
        edit_group = QGroupBox("編集ツール")
        el = _QGrid(edit_group)
        el.setColumnStretch(0, 1)
        el.setColumnStretch(1, 1)
        self.btn_clear = QToolButton()
        self.btn_clear.setText("オブジェクト削除 ▼")
        self.btn_clear.setToolTip("現在のステージから要素を削除（Undo可能）")
        self.btn_clear.setPopupMode(QToolButton.InstantPopup)
        clear_menu = _QMenu(self.btn_clear)
        act_all = clear_menu.addAction("すべて削除（鍵/扉/スタート/ミラーは保持）")
        act_blocks = clear_menu.addAction("ブロックのみ削除")
        act_items = clear_menu.addAction("アイテムのみ削除")
        act_enemies = clear_menu.addAction("モンスターのみ削除")
        act_all.triggered.connect(lambda: self._on_clear_level("all"))
        act_blocks.triggered.connect(lambda: self._on_clear_level("blocks"))
        act_items.triggered.connect(lambda: self._on_clear_level("items"))
        act_enemies.triggered.connect(lambda: self._on_clear_level("enemies"))
        self.btn_clear.setMenu(clear_menu)
        self.btn_clear.setEnabled(False)
        el.addWidget(self.btn_clear, 0, 0)

        # 全レベル統計
        self.btn_stats = QPushButton("全ステージ統計")
        self.btn_stats.setToolTip("53ステージのアイテム/敵/隠し配置を一覧表示")
        self.btn_stats.clicked.connect(self._on_show_stats)
        self.btn_stats.setEnabled(False)
        el.addWidget(self.btn_stats, 0, 1)

        # ゲーム改造（ROMバイト直接書換え）
        self.btn_hack = QPushButton("ゲーム挙動改造")
        self.btn_hack.setToolTip("開始ライフ・開始ステージ等の既知ROMアドレスを書き換え")
        self.btn_hack.clicked.connect(self._on_show_hack)
        self.btn_hack.setEnabled(False)
        el.addWidget(self.btn_hack, 1, 0)

        self.btn_enemy_hack = QPushButton("敵")
        self.btn_enemy_hack.setToolTip("敵AI・敵速度など、敵に関係するROM挙動を編集")
        self.btn_enemy_hack.clicked.connect(self._on_show_enemy_hack)
        self.btn_enemy_hack.setEnabled(False)
        el.addWidget(self.btn_enemy_hack, 1, 1)

        self.btn_palette = QPushButton("パレット編集")
        self.btn_palette.setToolTip("背景・スプライトのパレット (8パレット x 3色) を編集")
        self.btn_palette.clicked.connect(self._on_show_palette)
        self.btn_palette.setEnabled(False)
        el.addWidget(self.btn_palette, 2, 0)

        # スプライトビューア (CHR-ROM 全タイル一覧、読込専用)
        self.btn_sprite_viewer = QPushButton("スプライトビューア")
        self.btn_sprite_viewer.setToolTip(
            "CHR-ROM の全キャラクタータイル (8x8) を一覧表示。\n"
            "バンク・パレット・拡大率を切替可能。読込専用。"
        )
        self.btn_sprite_viewer.clicked.connect(self._on_show_sprite_viewer)
        self.btn_sprite_viewer.setEnabled(False)
        el.addWidget(self.btn_sprite_viewer, 2, 1)

        self.btn_title_screen = QPushButton("タイトル画面移植 (US↔JP)")
        self.btn_title_screen.setToolTip(
            "別ROMのタイトルを移植: 配置(nametable)+色区分(attribute)"
            "+絵(CHR bank3)をピース単位コピー。コード非改変・JP/US"
            "自動判定・CRC不要・双方向。データはツールに埋め込まず"
            "所有ROMから移植(著作権配慮)")
        self.btn_title_screen.clicked.connect(self._on_show_title_screen)
        self.btn_title_screen.setEnabled(False)
        el.addWidget(self.btn_title_screen, 3, 0)

        self.btn_pixel_editor = QPushButton("16x16ピクセル編集")
        self.btn_pixel_editor.setToolTip(
            "ROMフレーム由来の16x16スプライトを1ピクセル単位で編集。"
            "16x16画像の取り込みにも対応。"
        )
        self.btn_pixel_editor.clicked.connect(self._on_show_pixel_editor)
        self.btn_pixel_editor.setEnabled(False)
        el.addWidget(self.btn_pixel_editor, 3, 1)

        self.btn_sound_viewer = QPushButton("音楽データ表示")
        self.btn_sound_viewer.setToolTip(
            "ROM内サウンドデータをC/D/E表記のテキストで表示（読取専用）"
        )
        self.btn_sound_viewer.clicked.connect(self._on_show_sound_viewer)
        self.btn_sound_viewer.setEnabled(False)
        el.addWidget(self.btn_sound_viewer, 4, 0)

        self.btn_special_process = QPushButton("特殊処理ビューア")
        self.btn_special_process.setToolTip(
            "各ステージにハードコードされた特殊処理を表示します（読取専用）。"
        )
        self.btn_special_process.clicked.connect(self._on_show_special_process)
        self.btn_special_process.setEnabled(False)
        el.addWidget(self.btn_special_process, 4, 1)

        self.btn_item_replace = QPushButton("オブジェクト一括置換")
        self.btn_item_replace.setToolTip(
            "指定したブロック、アイテム、モンスターを同じ種別内で一括置換。"
            "選択範囲、現在ステージ、全ステージを対象にできます。"
        )
        self.btn_item_replace.clicked.connect(self._on_show_item_replace)
        self.btn_item_replace.setEnabled(False)
        el.addWidget(self.btn_item_replace, 5, 0, 1, 2)

        left_layout.addWidget(edit_group)

        # レベル設定（編集UI - skchain移植）
        meta_group = QGroupBox("ステージ設定")
        ml = QVBoxLayout(meta_group)
        self.lbl_info = QLabel("-")
        self.lbl_info.setWordWrap(True)
        self.lbl_info.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        ml.addWidget(self.lbl_info)
        from PyQt5.QtWidgets import QFormLayout
        form = QFormLayout()

        # タイルセット 0-2
        tileset_row = QHBoxLayout()
        self.tileset_btns = QButtonGroup(self)
        self.rb_tileset0 = QRadioButton("0")
        self.rb_tileset1 = QRadioButton("1")
        self.rb_tileset2 = QRadioButton("2")
        for rb, val in (
            (self.rb_tileset0, 0),
            (self.rb_tileset1, 1),
            (self.rb_tileset2, 2),
        ):
            self.tileset_btns.addButton(rb, val)
            tileset_row.addWidget(rb)
            rb.toggled.connect(
                lambda checked, v=val: self._on_meta_tileset_changed(v) if checked else None
            )
        tileset_row.addStretch()
        form.addRow("タイルセット:", tileset_row)

        # 制限時間: 0/1/2 はROM内の時間減少テーブルを選ぶ
        self.spin_time_dr = QSpinBox()
        self.spin_time_dr.setRange(0, 2)
        self.spin_time_dr.valueChanged.connect(self._on_meta_time_dr_changed)
        form.addRow("制限時間:", self.spin_time_dr)
        self.lbl_time_dr_hint = QLabel()
        self._update_time_dr_hint()
        form.addRow("", self.lbl_time_dr_hint)

        # Room Flag Table 拡張: 画面ごとの挙動改造 (原作level data非破壊)
        self.chk_no_bfire = QCheckBox("Bボタン（ファイア）禁止")
        self.chk_no_bfire.setToolTip(
            "この部屋だけBボタンの火球(魔法)を無効化。Aボタンの石生成は使えます。\n"
            "ROM保存時に bank0 のコードケーブへ注入 (位置+署名 検証付き)"
        )
        self.chk_no_bfire.toggled.connect(self._on_meta_no_bfire_toggled)
        form.addRow("ステージ設定:", self.chk_no_bfire)

        self.chk_no_astone = QCheckBox("Aボタン(換石)禁止")
        self.chk_no_astone.setToolTip(
            "この部屋だけAボタンの石生成を無効化 (Bファイアとは独立)。\n"
            "※石で階段が作れず進行不能になり得ます。意図して使う設定です"
        )
        self.chk_no_astone.toggled.connect(self._on_meta_no_astone_toggled)
        form.addRow("", self.chk_no_astone)

        self.chk_dark = QCheckBox("暗闇モード")
        self.chk_dark.setToolTip(
            "この面のプレイ中だけ背景(地形/HUD)を明滅で消し、敵とDana\n"
            "だけ見えるようにします。明の瞬間に地形/鍵/扉が見えるので\n"
            "記憶して進む暗闇面。明/暗の長さは全体共通(ゲーム挙動改造\n"
            "の『暗闇テンポ』)。タイトル/紹介/クリアは通常表示・必ず明から")
        self.chk_dark.toggled.connect(self._on_meta_dark_toggled)
        form.addRow("", self.chk_dark)

        # 星座: combo + position
        self.chk_fire_reset = QCheckBox("開始時にファイヤー所持をリセット")
        self.chk_fire_reset.setToolTip(
            "この面を開始した時に、前の面から持ち越したファイヤー/スーパーの所持を0にします。"
        )
        self.chk_fire_reset.toggled.connect(self._on_meta_fire_reset_toggled)
        form.addRow("", self.chk_fire_reset)

        self.spin_key_enemy = QSpinBox()
        self.spin_key_enemy.setRange(0, c.ENEMY_COUNT_MAX)
        self.spin_key_enemy.setSpecialValueText("(なし)")
        self.spin_key_enemy.setToolTip("0=なし。1から15は、このステージの初期配置敵リスト順です。")
        self.spin_key_enemy.valueChanged.connect(self._on_meta_key_enemy_changed)
        form.addRow("鍵持ち敵 (#):", self.spin_key_enemy)

        self.spin_fairy_enemy = QSpinBox()
        self.spin_fairy_enemy.setRange(0, c.ENEMY_COUNT_MAX)
        self.spin_fairy_enemy.setSpecialValueText("(なし)")
        self.spin_fairy_enemy.setToolTip("0=なし。1から15は、このステージの初期配置敵リスト順です。鍵持ち敵と同じ番号は指定できません。")
        self.spin_fairy_enemy.valueChanged.connect(self._on_meta_fairy_enemy_changed)
        form.addRow("落下死で妖精化する敵 (#):", self.spin_fairy_enemy)

        self.combo_const = QComboBox()
        self.combo_const.addItem("(なし)", -1)
        for code, (name, _) in c.CONSTELLATION_NAMES.items():
            self.combo_const.addItem(name, code)
        self.combo_const.currentIndexChanged.connect(self._on_meta_constellation_changed)
        form.addRow("星座:", self.combo_const)

        const_pos_row = QHBoxLayout()
        self.spin_const_x = QSpinBox()
        self.spin_const_x.setRange(0, c.LEVEL_W - 1)
        self.spin_const_x.valueChanged.connect(self._on_meta_const_pos_changed)
        self.spin_const_y = QSpinBox()
        self.spin_const_y.setRange(0, c.LEVEL_H - 1)
        self.spin_const_y.valueChanged.connect(self._on_meta_const_pos_changed)
        const_pos_row.addWidget(QLabel("位置 X:"))
        const_pos_row.addWidget(self.spin_const_x)
        const_pos_row.addWidget(QLabel("Y:"))
        const_pos_row.addWidget(self.spin_const_y)
        form.addRow(const_pos_row)

        ml.addLayout(form)
        # フラグ: スピンボックス変更を編集モードに紐づけるためのガード
        self._meta_loading = False
        self.meta_group = meta_group
        self.meta_group.setEnabled(False)
        left_layout.addWidget(meta_group)

        left_layout.addStretch()
        return left_widget

    def _build_panel_variant_panel(self) -> QWidget:
        wrap = QWidget()
        wrap_layout = QVBoxLayout(wrap)
        wrap_layout.setContentsMargins(0, 0, 0, 0)
        wrap_layout.setSpacing(4)

        group = QGroupBox("強化パネルモンスター")
        group.setToolTip(
            "A/B/Cパネルモンスターは全ステージ共通設定です。敵設定画面で変更します。"
        )
        layout = QVBoxLayout(group)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)

        notice = QLabel(
            "ステージごとのA/B/C速度・間隔設定は廃止しました。"
            "PRG0の保守余力確保のため、A/B/Cは敵設定画面の共通固定値を使います。"
        )
        notice.setWordWrap(True)
        notice.setStyleSheet("color: #a06000;")
        layout.addWidget(notice)

        self._panel_variant_controls = {}
        self.panel_variant_group = group
        wrap_layout.addWidget(group)

        self.btn_test_play_right = self._create_test_play_button("▶ テストプレイ")
        wrap_layout.addWidget(self.btn_test_play_right)
        return wrap

    def _create_test_play_button(self, text: str) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("testPlayButton")
        button.setMinimumHeight(30)
        button.setToolTip("現在の編集状態で、現在ステージから始まる一時ROMを作りエミュレータを起動")
        button.clicked.connect(self._on_test_play)
        button.setEnabled(False)
        return button

    def _build_levelselect_panel(self) -> QWidget:
        """最右ペイン: サムネイル付きレベル選択"""
        from PyQt5.QtWidgets import QListWidgetItem
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(4, 4, 4, 4)

        from PyQt5.QtGui import QWheelEvent

        class _InvertedSpinBox(QSpinBox):
            """上下操作を反転（下=数字増=サムネイルと同方向）"""
            def wheelEvent(self, event):
                inv = QWheelEvent(
                    event.posF(), event.globalPosF(),
                    -event.pixelDelta(), -event.angleDelta(),
                    event.buttons(), event.modifiers(),
                    event.phase(), event.inverted(), event.source()
                )
                super().wheelEvent(inv)
                event.accept()
            def keyPressEvent(self, event):
                if event.key() == Qt.Key_Up:
                    self.setValue(self.value() - 1)
                    event.accept()
                elif event.key() == Qt.Key_Down:
                    self.setValue(self.value() + 1)
                    event.accept()
                else:
                    super().keyPressEvent(event)

        self.spin_level = _InvertedSpinBox()
        self.spin_level.setObjectName("stageSelectSpin")
        self.spin_level.setRange(1, c.LEVEL_COUNT)
        self.spin_level.setValue(1)
        self.spin_level.setFocusPolicy(Qt.StrongFocus)
        self.spin_level.setMinimumHeight(30)
        self.spin_level.valueChanged.connect(self._on_level_changed)
        self.spin_level.hide()

        stage_ops = QHBoxLayout()
        self.btn_stage_copy = QPushButton("面コピー")
        self.btn_stage_copy.setToolTip("現在のステージデータ一式を内部クリップボードへコピー")
        self.btn_stage_copy.clicked.connect(self._on_stage_copy)
        self.btn_stage_copy.setEnabled(False)
        stage_ops.addWidget(self.btn_stage_copy)

        self.btn_stage_paste = QPushButton("貼り付け")
        self.btn_stage_paste.setToolTip("コピーしたステージデータ一式で現在のステージを上書き")
        self.btn_stage_paste.clicked.connect(self._on_stage_paste)
        self.btn_stage_paste.setEnabled(False)
        stage_ops.addWidget(self.btn_stage_paste)
        v.addLayout(stage_ops)

        swap_row = QHBoxLayout()
        self.btn_stage_swap = QPushButton("面入れ替え")
        self.btn_stage_swap.setToolTip("現在のステージと指定ステージのデータ一式を入れ替え")
        self.btn_stage_swap.clicked.connect(self._on_stage_swap)
        self.btn_stage_swap.setEnabled(False)
        swap_row.addWidget(self.btn_stage_swap, 1)

        self.spin_stage_swap_target = _InvertedSpinBox()
        self.spin_stage_swap_target.setObjectName("stageSwapTargetSpin")
        self.spin_stage_swap_target.setRange(1, c.LEVEL_COUNT)
        self.spin_stage_swap_target.setMinimumHeight(30)
        self.spin_stage_swap_target.setMinimumWidth(58)
        self.spin_stage_swap_target.setVisible(False)
        swap_row.addWidget(self.spin_stage_swap_target)
        v.addLayout(swap_row)

        self.lbl_stage_clipboard = QLabel("コピー元: なし")
        self.lbl_stage_clipboard.setObjectName("stageClipboardLabel")
        self.lbl_stage_clipboard.setWordWrap(True)
        v.addWidget(self.lbl_stage_clipboard)

        from PyQt5.QtWidgets import QListView

        class _StageListWidget(QListWidget):
            def __init__(self, owner):
                super().__init__()
                self._owner = owner

            def keyPressEvent(self, event):
                if event.modifiers() == Qt.ControlModifier:
                    if event.key() == Qt.Key_C:
                        self._owner._on_stage_copy()
                        event.accept()
                        return
                    if event.key() == Qt.Key_V:
                        self._owner._on_stage_paste()
                        event.accept()
                        return
                    if event.key() == Qt.Key_X:
                        self._owner._on_stage_swap()
                        event.accept()
                        return
                super().keyPressEvent(event)

            def wheelEvent(self, event):
                if event.modifiers() & Qt.ControlModifier:
                    delta = event.angleDelta().y()
                    if delta == 0:
                        delta = event.pixelDelta().y()
                    if delta:
                        self._owner._change_thumbnail_display_size(1 if delta > 0 else -1)
                        event.accept()
                        return
                super().wheelEvent(event)

        self.list_levels = _StageListWidget(self)
        # サムネイル表示用のサイズ設定（画像のみ・テキストなし）
        self._thumb_size = self._thumbnail_size_from_width(
            self._app_config.get("stage_thumbnail_width", 160)
        )
        self.list_levels.setIconSize(self._thumb_size)
        self.list_levels.setUniformItemSizes(True)
        self.list_levels.setViewMode(QListView.IconMode)
        self.list_levels.setMovement(QListView.Static)
        self.list_levels.setResizeMode(QListView.Adjust)
        self.list_levels.setWrapping(True)
        self.list_levels.setSpacing(2)
        self.list_levels.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_levels.customContextMenuRequested.connect(self._on_level_context_menu)
        # アイテム自体のサイズも明示しないとIconModeで潰れる
        item_size = self._thumbnail_item_size()
        for i in range(c.LEVEL_COUNT):
            item = QListWidgetItem()
            item.setToolTip(f"Stage {i+1}")
            item.setSizeHint(item_size)
            self.list_levels.addItem(item)
        self.list_levels.currentRowChanged.connect(self._on_list_changed)
        v.addWidget(self.list_levels, 1)

        return w

    def _thumbnail_size_from_width(self, width):
        try:
            value = int(width)
        except Exception:
            value = 160
        value = max(96, min(256, value))
        value = (value // 16) * 16
        return QSize(value, value * 3 // 4)

    def _thumbnail_item_size(self):
        return QSize(self._thumb_size.width() + 8, self._thumb_size.height() + 8)

    def _apply_thumbnail_display_size(self):
        self.list_levels.setIconSize(self._thumb_size)
        item_size = self._thumbnail_item_size()
        for i in range(self.list_levels.count()):
            item = self.list_levels.item(i)
            if item is not None:
                item.setSizeHint(item_size)

    def _change_thumbnail_display_size(self, direction: int):
        current_w = self._thumb_size.width()
        step = 16
        min_w = 96
        max_w = 256
        target_w = max(min_w, min(max_w, current_w + step * int(direction)))
        if target_w == current_w:
            return
        self._thumb_size = QSize(target_w, target_w * 3 // 4)
        self._app_config["stage_thumbnail_width"] = target_w
        save_config(self._app_config)
        self._apply_thumbnail_display_size()
        self._generate_all_thumbnails()

    def _generate_all_thumbnails(self):
        """全レベルのサムネイルを生成（ROM読込時 / 手動再生成）"""
        if not self.levels or self.level_renderer is None:
            return
        from PyQt5.QtGui import QIcon
        for i, level in enumerate(self.levels):
            bonus = self._bonus_items if i == 50 and getattr(self, "_bonus_items", None) else None
            img = self.level_renderer.render(
                level,
                level_no=i,
                show_grid=False,
                show_hidden_overlay=False,
                hover_tile=None,
                show_col15=True,
                selection_rect=None,
                special_marks=self._get_special_marks(i),
                show_border=True,
                bonus_items=bonus,
            )
            pix = QPixmap.fromImage(img).scaled(
                self._thumb_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            item = self.list_levels.item(i)
            if item is not None:
                item.setIcon(QIcon(pix))

    def _apply_item_bitmasks(self, rom, config, levels, rom_data=None):
        """skc_config.xml の item_bitmasks を ROM データから読み出して
        該当レベルの items に追加する。

        24バイト(16×12ビット)の bitmap を解読し、立っているビット位置に
        指定アイテムコードのアイテムを配置する。
        既に同じ(position, code)があれば重複追加しない。

        標準ROMで容量節約のため使われる仕組み (Level 20: Bat Symbol、Level 30: Opal)
        """
        from ..core.element import LevelElement, ElementType
        from ..core import constants as c

        ibs = getattr(config, "item_bitmasks", None) or []
        if not ibs:
            return
        if rom_data is None:
            rom_data = bytes(rom.data)
        for entry in ibs:
            level_no = entry["level_no"]
            item_no = entry["item_no"]
            offset = entry["offset"]
            if not (0 <= level_no < len(levels)):
                continue
            if offset + 24 > len(rom_data):
                continue
            lv = levels[level_no]
            # 24バイト = 16x12 bitmap (各バイト = 1行 16ビット = LSB-first or MSB-first?)
            # bytes_to_bitmask (C++) は MSB-first で読む実装
            existing = {(it.position, it.element_no) for it in lv.items}
            for j in range(c.LEVEL_H):
                # 1行 = 16ビット = 2バイト (16/8=2)
                b0 = rom_data[offset + j * 2]
                b1 = rom_data[offset + j * 2 + 1]
                for i in range(c.LEVEL_W):
                    # MSB-first: ビット (7-i) of b0 が i=0..7、ビット (15-i) of b1 が i=8..15
                    if i < 8:
                        bit = (b0 >> (7 - i)) & 1
                    else:
                        bit = (b1 >> (15 - i)) & 1
                    if bit:
                        pos = (i, j)
                        if (pos, item_no) in existing:
                            continue
                        lv.items.append(LevelElement(ElementType.ITEM, pos, item_no))
                        existing.add((pos, item_no))

    def _clear_item_bitmasks(self, rom, config):
        from ..core import constants as c

        ibs = getattr(config, "item_bitmasks", None) or []
        for entry in ibs:
            try:
                offset = int(entry["offset"])
            except (KeyError, TypeError, ValueError):
                continue
            end = offset + c.TILE_BITMASK_BYTE_SIZE
            if 0 <= offset and end <= len(rom.data):
                rom.data[offset:end] = bytes(c.TILE_BITMASK_BYTE_SIZE)

    def _load_bonus_stage_table(self, rom, allow_mutation: bool = True):
        """ボーナスステージ(51面)のアイテム位置・アイテムリストをROMから読み込み"""
        from ..core.element import position_from_byte
        from ..core.constants import ROM_OFFSETS
        region = rom.base_region()
        offsets = ROM_OFFSETS.get(region, ROM_OFFSETS["JP"])
        pos_addr = offsets.get("bonus_pos", 0x1955)
        item_addr = offsets.get("bonus_items", 0x1975)
        try:
            pos_bytes = bytearray(rom.data[pos_addr:pos_addr + 32])
            item_bytes = rom.data[item_addr:item_addr + 16]
            # JP版バグ修正: 位置[2]=0xD2(2,12)が画面外 → 0xB2(2,10)に補正
            if region == "JP" and len(pos_bytes) > 2 and pos_bytes[2] == 0xD2:
                pos_bytes[2] = 0xB2
                if allow_mutation:
                    rom.data[pos_addr + 2] = 0xB2
            positions = [position_from_byte(b) for b in pos_bytes]
            # 全32スポットの位置を保持（ドラッグ移動用）
            self._bonus_positions = list(positions)
            # レンダラー用: (pos, item_code) ペアのリスト（画面内のみ）
            self._bonus_items = [
                (positions[i], item_bytes[i % 16])
                for i in range(32)
                if 0 <= positions[i][0] < c.LEVEL_W and 0 <= positions[i][1] < c.LEVEL_H
            ]
        except Exception:
            self._bonus_positions = []
            self._bonus_items = []

    def _normalize_original_jp_enemy_data(self, rom, levels, allow_mutation: bool = True):
        """原本JP ROMの既知敵データを編集用に正規化する。"""
        if not allow_mutation or rom is None or not getattr(rom, "is_known_jp_original", lambda: False)():
            return 0
        if not levels or len(levels) <= 28:
            return 0
        fixed = 0
        for slot_idx, pos in ((1, (14, 4)), (2, (14, 6))):
            enemies = getattr(levels[28], "enemies", [])
            if slot_idx >= len(enemies):
                continue
            enemy = enemies[slot_idx]
            if enemy.position == pos and enemy.element_no == 0x4D:
                enemy.element_no = 0x4C
                fixed += 1
        return fixed

    def _import_original_jp_stage50_breakable_white(self, source_data: bytes, levels,
                                                    allow_mutation: bool = True):
        """Stage 50 の無条件特殊処理ブロックを編集用ステージデータへ取り込む。"""
        if not allow_mutation or not is_known_jp_original_data(source_data):
            return 0
        if not levels or len(levels) <= 49:
            return 0
        level = levels[49]
        imported = 0
        for pos in ((7, 1), (3, 3), (12, 7)):
            x, y = pos
            if not (0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H):
                continue
            if level.tiles[y][x] != Wall.WHITE:
                continue
            if pos not in level.breakable_white_cells:
                level.breakable_white_cells.add(pos)
                imported += 1
        return imported

    def _import_original_jp_stage49_breakable_white(self, source_data: bytes, levels,
                                                    allow_mutation: bool = True):
        """Stage 49 の無条件特殊処理ブロックを編集用ステージデータへ取り込む。"""
        if not allow_mutation or not is_known_jp_original_data(source_data):
            return 0
        if not levels or len(levels) <= 48:
            return 0
        level = levels[48]
        imported = 0
        positions = (
            (1, 3), (1, 4), (1, 5), (1, 6), (1, 7),
            (6, 3), (8, 3),
            (13, 3), (13, 4), (13, 5), (13, 6), (13, 7),
        )
        for pos in positions:
            x, y = pos
            if not (0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H):
                continue
            if level.tiles[y][x] != Wall.WHITE:
                continue
            if pos not in level.breakable_white_cells:
                level.breakable_white_cells.add(pos)
                imported += 1
        return imported

    def _import_original_jp_stage52_53_breakable_white(self, source_data: bytes, levels,
                                                       allow_mutation: bool = True):
        """Stage 52/53 の無条件特殊処理ブロックを編集用ステージデータへ取り込む。"""
        if not allow_mutation or not is_known_jp_original_data(source_data):
            return 0
        if not levels or len(levels) <= 52:
            return 0
        imported = 0
        positions = ((6, 3), (7, 3), (8, 3), (7, 8))
        for level_no in (51, 52):
            level = levels[level_no]
            for pos in positions:
                x, y = pos
                if not (0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H):
                    continue
                if level.tiles[y][x] != Wall.WHITE:
                    continue
                if pos not in level.breakable_white_cells:
                    level.breakable_white_cells.add(pos)
                    imported += 1
        return imported

    def _patch_stage50_breakable_white_hardcode(self, source_data: bytes, rom) -> int:
        """Stage 50 の無条件 $90 書き込み3箇所を止める。"""
        if rom is None or not is_known_jp_original_data(source_data):
            return 0
        off = 0x3626
        expected = bytes.fromhex("8d2b038d47038d9003")
        disabled = bytes([0xEA] * len(expected))
        current = bytes(rom.data[off:off + len(expected)])
        if current == disabled:
            return 0
        if current != expected:
            return 0
        rom.data[off:off + len(expected)] = disabled
        return 3

    def _patch_stage49_breakable_white_hardcode(self, source_data: bytes, rom) -> int:
        """Stage 49 の無条件 $90 テーブル書き込み12箇所を止める。"""
        if rom is None or not is_known_jp_original_data(source_data):
            return 0
        off = 0x359F
        expected = bytes.fromhex("990403")
        disabled = bytes([0xEA] * len(expected))
        current = bytes(rom.data[off:off + len(expected)])
        if current == disabled:
            return 0
        if current != expected:
            return 0
        rom.data[off:off + len(expected)] = disabled
        return 12

    def _patch_stage52_53_breakable_white_hardcode(self, source_data: bytes, rom) -> int:
        """Stage 52/53 の共有ルーチンにある無条件 $90 書き込み4箇所を止める。"""
        if rom is None or not is_known_jp_original_data(source_data):
            return 0
        patches = (
            (0x35E8, bytes.fromhex("8d9b03"), 1),
            (0x360D, bytes.fromhex("9d4a03"), 3),
        )
        disabled_count = 0
        for off, expected, count in patches:
            disabled = bytes([0xEA] * len(expected))
            current = bytes(rom.data[off:off + len(expected)])
            if current == disabled:
                continue
            if current != expected:
                continue
            rom.data[off:off + len(expected)] = disabled
            disabled_count += count
        return disabled_count

    def _stage50_conditional_breakable_positions(self):
        """Stage 50 条件付き壊せる白ブロックのトリガー/出現先をROMから読む。"""
        if self.rom is None or len(self.rom.data) <= 0x363C:
            return None
        data = self.rom.data
        if bytes(data[0x3632:0x3635]) != bytes.fromhex("a57ec9"):
            return None
        if bytes(data[0x3636:0x3638]) != bytes.fromhex("d0f7"):
            return None
        if bytes(data[0x3638:0x363B]) != bytes.fromhex("a9908d"):
            return None
        if data[0x363C] != 0x03:
            return None
        from ..core.element import position_from_byte
        trigger = position_from_byte(data[0x3635])
        target_byte = (data[0x363B] - 0x04) & 0xFF
        target = position_from_byte(target_byte)
        for pos in (trigger, target):
            x, y = pos
            if not (0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H):
                return None
        return {"trigger": trigger, "target": target}

    def _stage50_conditional_breakable_marker_at(self, tile):
        if self.current_level_no != 49:
            return None
        if not getattr(self, "chk_special_marks", None) or not self.chk_special_marks.isChecked():
            return None
        positions = self._stage50_conditional_breakable_positions()
        if not positions:
            return None
        if tile == positions["trigger"]:
            return "trigger"
        if tile == positions["target"]:
            return "target"
        return None

    def _move_stage50_conditional_breakable_marker(self, marker_kind: str, tile):
        if self.rom is None:
            return False
        positions = self._stage50_conditional_breakable_positions()
        if not positions or marker_kind not in ("trigger", "target"):
            return False
        from ..core.element import byte_from_position
        pos_byte = byte_from_position(tile)
        if marker_kind == "trigger":
            self.rom.data[0x3635] = pos_byte
        else:
            self.rom.data[0x363B] = (pos_byte + 0x04) & 0xFF
        self._set_dirty(True)
        return True

    def _stage52_53_conditional_breakable_positions(self):
        """Stage 52/53 共有の条件付き壊せる白ブロック座標をROMから読む。"""
        if self.rom is None or len(self.rom.data) <= 0x3609:
            return None
        data = self.rom.data
        if bytes(data[0x3601:0x3604]) != bytes.fromhex("a67ee0"):
            return None
        if bytes(data[0x3605:0x3607]) != bytes.fromhex("d0e4"):
            return None
        if data[0x3607] != 0x8D or data[0x3609] != 0x03:
            return None
        from ..core.element import position_from_byte
        trigger = position_from_byte(data[0x3604])
        target_byte = (data[0x3608] - 0x04) & 0xFF
        target = position_from_byte(target_byte)
        for pos in (trigger, target):
            x, y = pos
            if not (0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H):
                return None
        return {"trigger": trigger, "target": target}

    def _stage52_53_conditional_breakable_marker_at(self, tile):
        if self.current_level_no not in (51, 52):
            return None
        if not getattr(self, "chk_special_marks", None) or not self.chk_special_marks.isChecked():
            return None
        positions = self._stage52_53_conditional_breakable_positions()
        if not positions:
            return None
        if tile == positions["trigger"]:
            return "trigger"
        if tile == positions["target"]:
            return "target"
        return None

    def _move_stage52_53_conditional_breakable_marker(self, marker_kind: str, tile):
        if self.rom is None:
            return False
        positions = self._stage52_53_conditional_breakable_positions()
        if not positions or marker_kind not in ("trigger", "target"):
            return False
        from ..core.element import byte_from_position
        pos_byte = byte_from_position(tile)
        if marker_kind == "trigger":
            self.rom.data[0x3604] = pos_byte
        else:
            self.rom.data[0x3608] = (pos_byte + 0x04) & 0xFF
        self._set_dirty(True)
        return True

    def _stage49_conditional_breakable_positions(self):
        """Stage 49 の条件付き壊せる白ブロック2組の座標をROMから読む。"""
        if self.rom is None or len(self.rom.data) <= 0x35D8:
            return None
        data = self.rom.data
        if bytes(data[0x35A8:0x35AB]) != bytes.fromhex("a57ec9"):
            return None
        if bytes(data[0x35AC:0x35AE]) != bytes.fromhex("d0f7"):
            return None
        if bytes(data[0x35C4:0x35C7]) != bytes.fromhex("a9908d"):
            return None
        if data[0x35C8] != 0x03:
            return None
        if bytes(data[0x35CC:0x35CF]) != bytes.fromhex("a57ec9"):
            return None
        if bytes(data[0x35D0:0x35D2]) != bytes.fromhex("d0f7"):
            return None
        if bytes(data[0x35D2:0x35D5]) != bytes.fromhex("a9908d"):
            return None
        if data[0x35D6] != 0x03:
            return None
        from ..core.element import position_from_byte
        positions = {
            "trigger1": position_from_byte(data[0x35AB]),
            "target1": position_from_byte((data[0x35C7] - 0x04) & 0xFF),
            "trigger2": position_from_byte(data[0x35CF]),
            "target2": position_from_byte((data[0x35D5] - 0x04) & 0xFF),
        }
        for pos in positions.values():
            x, y = pos
            if not (0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H):
                return None
        return positions

    def _stage49_conditional_breakable_marker_at(self, tile):
        if self.current_level_no != 48:
            return None
        if not getattr(self, "chk_special_marks", None) or not self.chk_special_marks.isChecked():
            return None
        positions = self._stage49_conditional_breakable_positions()
        if not positions:
            return None
        for key, pos in positions.items():
            if tile == pos:
                return key
        return None

    def _move_stage49_conditional_breakable_marker(self, marker_kind: str, tile):
        if self.rom is None:
            return False
        positions = self._stage49_conditional_breakable_positions()
        if not positions or marker_kind not in ("trigger1", "target1", "trigger2", "target2"):
            return False
        from ..core.element import byte_from_position
        pos_byte = byte_from_position(tile)
        if marker_kind == "trigger1":
            self.rom.data[0x35AB] = pos_byte
        elif marker_kind == "target1":
            self.rom.data[0x35C7] = (pos_byte + 0x04) & 0xFF
        elif marker_kind == "trigger2":
            self.rom.data[0x35CF] = pos_byte
        else:
            self.rom.data[0x35D5] = (pos_byte + 0x04) & 0xFF
        self._set_dirty(True)
        return True

    def _conditional_breakable_marker_at(self, tile):
        stage49_marker = self._stage49_conditional_breakable_marker_at(tile)
        if stage49_marker is not None:
            return {"group": "stage49", "sub": stage49_marker}
        stage50_marker = self._stage50_conditional_breakable_marker_at(tile)
        if stage50_marker is not None:
            return {"group": "stage50", "sub": stage50_marker}
        stage52_53_marker = self._stage52_53_conditional_breakable_marker_at(tile)
        if stage52_53_marker is not None:
            return {"group": "stage52_53", "sub": stage52_53_marker}
        return None

    def _move_conditional_breakable_marker(self, group: str, marker_kind: str, tile):
        if group == "stage49":
            return self._move_stage49_conditional_breakable_marker(marker_kind, tile)
        if group == "stage50":
            return self._move_stage50_conditional_breakable_marker(marker_kind, tile)
        if group == "stage52_53":
            return self._move_stage52_53_conditional_breakable_marker(marker_kind, tile)
        return False

    def _bomb_jack_meta_for_level(self, level_no: int):
        if self.config is None:
            return None
        for mi in getattr(self.config, "level_meta_items", []) or []:
            if int(getattr(mi, "level_no", -1)) != int(level_no):
                continue
            desc = (str(getattr(mi, "description", "")) or "").lower()
            if "bomb jack" in desc and int(getattr(mi, "rom_offset", -1)) >= 0:
                return mi
        return None

    def _bomb_jack_spawn_offset(self, mi) -> int:
        return int(getattr(mi, "rom_offset", -1)) + 0x10

    def _bomb_jack_positions(self, level_no: int = None):
        """Mighty Bomb Jack の頭突き判定/出現先をROMから読む。"""
        if self.rom is None:
            return None
        target_level = self.current_level_no if level_no is None else int(level_no)
        mi = self._bomb_jack_meta_for_level(target_level)
        if mi is None:
            return None
        trigger_off = int(getattr(mi, "rom_offset", -1))
        spawn_off = self._bomb_jack_spawn_offset(mi)
        data = self.rom.data
        if trigger_off < 3 or spawn_off < 1 or spawn_off + 2 >= len(data):
            return None
        if bytes(data[trigger_off - 3:trigger_off]) != bytes.fromhex("a57fc9"):
            return None
        if bytes(data[trigger_off + 1:trigger_off + 3]) != bytes.fromhex("d0f7"):
            return None
        if data[spawn_off - 1] != 0xA9 or bytes(data[spawn_off + 1:spawn_off + 3]) != bytes.fromhex("8588"):
            return None
        from ..core.element import position_from_byte
        trigger = position_from_byte(data[trigger_off])
        spawn = position_from_byte(data[spawn_off])
        for pos in (trigger, spawn):
            x, y = pos
            if not (0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H):
                return None
        return {"trigger": trigger, "spawn": spawn, "meta": mi}

    def _bomb_jack_marker_at(self, tile):
        if not getattr(self, "chk_special_marks", None) or not self.chk_special_marks.isChecked():
            return None
        positions = self._bomb_jack_positions()
        if not positions:
            return None
        if tile == positions["trigger"]:
            return "trigger"
        if tile == positions["spawn"]:
            return "spawn"
        return None

    def _move_bomb_jack_marker(self, marker_kind: str, tile, level_no: int = None):
        positions = self._bomb_jack_positions(level_no)
        if not positions or marker_kind not in ("trigger", "spawn"):
            return False
        from ..core.element import byte_from_position
        pos_byte = byte_from_position(tile)
        mi = positions["meta"]
        if marker_kind == "trigger":
            self.rom.data[int(mi.rom_offset)] = pos_byte
            mi.position = tile
        else:
            self.rom.data[self._bomb_jack_spawn_offset(mi)] = pos_byte
        self._set_dirty(True)
        return True

    def _conditional_breakable_positions(self, group: str):
        if group == "stage49":
            return self._stage49_conditional_breakable_positions()
        if group == "stage50":
            return self._stage50_conditional_breakable_positions()
        if group == "stage52_53":
            return self._stage52_53_conditional_breakable_positions()
        return None

    def _conditional_breakable_group_label(self, group: str):
        if group == "stage49":
            return "Stage 49"
        if group == "stage52_53":
            return "Stage 52/53"
        return "Stage 50"

    def _conditional_breakable_marker_label(self, marker_kind: str):
        labels = {
            "trigger": "トリガー",
            "target": "出現先",
            "trigger1": "1:トリガー",
            "target1": "1:出現先",
            "trigger2": "2:トリガー",
            "target2": "2:出現先",
        }
        return labels.get(marker_kind, marker_kind)

    def _get_bonus_items(self):
        """現在のレベルがボーナスステージ(index 50)ならボーナスアイテムを返す"""
        if self.current_level_no == 50 and getattr(self, "_bonus_items", None):
            return self._bonus_items
        return None

    def _rebuild_bonus_items_from_positions(self):
        """_bonus_positions からレンダラー用 _bonus_items を再構築"""
        if not self.rom or not getattr(self, "_bonus_positions", None):
            return
        from ..core.constants import ROM_OFFSETS
        region = self.rom.base_region()
        offsets = ROM_OFFSETS.get(region, ROM_OFFSETS["JP"])
        item_addr = offsets.get("bonus_items", 0x1975)
        item_bytes = self.rom.data[item_addr:item_addr + 16]
        self._bonus_items = [
            (self._bonus_positions[i], item_bytes[i % 16])
            for i in range(32)
            if (0 <= self._bonus_positions[i][0] < c.LEVEL_W
                and 0 <= self._bonus_positions[i][1] < c.LEVEL_H)
        ]

    def _write_bonus_positions_to_rom(self):
        """_bonus_positions をROMに書き戻す"""
        if not self.rom or not getattr(self, "_bonus_positions", None):
            return
        if self._reject_read_only_edit():
            return
        from ..core.element import byte_from_position
        from ..core.constants import ROM_OFFSETS
        region = self.rom.base_region()
        offsets = ROM_OFFSETS.get(region, ROM_OFFSETS["JP"])
        pos_addr = offsets.get("bonus_pos", 0x1955)
        for i in range(min(32, len(self._bonus_positions))):
            self.rom.data[pos_addr + i] = byte_from_position(self._bonus_positions[i])
        self._set_dirty(True)

    def _refresh_thumbnail(self, level_no: int):
        """指定レベルのサムネだけ更新"""
        if not self.levels or self.level_renderer is None:
            return
        if not (0 <= level_no < len(self.levels)):
            return
        from PyQt5.QtGui import QIcon
        level = self.levels[level_no]
        bonus = self._bonus_items if level_no == 50 and getattr(self, "_bonus_items", None) else None
        img = self.level_renderer.render(
            level,
            level_no=level_no,
            show_grid=False,
            show_hidden_overlay=False,
            hover_tile=None,
            show_col15=True,
            selection_rect=None,
            special_marks=self._get_special_marks(level_no),
            show_border=True,
            bonus_items=bonus,
        )
        pix = QPixmap.fromImage(img).scaled(
            self._thumb_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        item = self.list_levels.item(level_no)
        if item is not None:
            item.setIcon(QIcon(pix))

    def _refresh_thumbnails_after_edit(self, level_no: int = None):
        if level_no is None:
            level_no = self.current_level_no
        self._refresh_thumbnail(level_no)

    def _refresh_thumbnails_after_conditional_marker_edit(self, group: str):
        if group == "stage52_53":
            self._refresh_thumbnail(51)
            self._refresh_thumbnail(52)
        else:
            self._refresh_thumbnail(self.current_level_no)

    def _read_wall_color_values(self):
        if self.rom is None:
            return None
        try:
            return tuple(wall_color_hack.current_values(self.rom.data))
        except wall_color_hack.WallColorHackError:
            return None

    def _sync_wall_color_preview(self):
        if self.level_renderer is None:
            return
        self.level_renderer.set_wall_color_values(self._read_wall_color_values())
        if self.tile_renderer is not None:
            self.tile_renderer.clear_cache()

    def _on_hack_dialog_applied(self):
        if self._reject_read_only_edit():
            return
        self._set_dirty(True)
        self._sync_wall_color_preview()
        self._refresh_view()
        self._generate_all_thumbnails()

    # ====== File ops ======

    def _on_open_rom(self):
        filter_str = "NES ROMs / ZIP (*.nes *.zip);;NES ROMs (*.nes);;ZIP archives (*.zip);;All files (*)"
        from .file_dialog_compat import get_file
        path = get_file(self, title="NES ROM を選択", filter=filter_str)

        if not path:
            return
        if not self._confirm_replace_current_work("別のROMを開きます"):
            return
        self.load_rom(path)

    def _on_rom_dropped(self, path: str):
        if not self._confirm_replace_current_work("ドロップされたROMを開きます"):
            return
        self.load_rom(path)

    def _confirm_replace_current_work(self, action_label: str = "別のROMを読み込みます") -> bool:
        if not self.rom or not self._dirty or self._is_read_only():
            return True
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle("未保存の変更")
        box.setText("現在の編集内容はまだ保存されていません。")
        box.setInformativeText(
            f"{action_label}。\n"
            "保存せずに続行すると、現在の編集内容は破棄されます。"
        )
        save_btn = box.addButton("保存して続行", QMessageBox.AcceptRole)
        discard_btn = box.addButton("破棄して続行", QMessageBox.DestructiveRole)
        cancel_btn = box.addButton("キャンセル", QMessageBox.RejectRole)
        box.setDefaultButton(cancel_btn)
        box.exec_()
        clicked = box.clickedButton()
        if clicked == save_btn:
            return bool(self._on_save_rom())
        if clicked == discard_btn:
            return True
        return False

    def load_rom(
        self,
        path: str,
        add_history: bool = True,
        status_message: str = "",
        source_path_override: str = "",
        display_name_override: str = "",
        workstate_path_override: str = "",
        workstate_saved_at_override: str = "",
        initial_level_no: int | None = None,
    ):
        try:
            self._rom_validation_warnings = []
            self._rom_validation_rom = None
            if getattr(self, "_rom_validation_dialog", None) is not None:
                self._rom_validation_dialog.close()
                self._rom_validation_dialog = None
            if getattr(self, "_stats_dialog", None) is not None:
                self._stats_dialog.close()
                self._stats_dialog = None
            if hasattr(self, "btn_rom_validation"):
                self.btn_rom_validation.setVisible(False)
            rom = Rom.load(path)
            if display_name_override:
                rom.display_name = str(display_name_override)
            loaded_rom_data = bytes(rom.data)
            editor_input = rom.is_supported_editor_input()
            read_only_reason = "" if editor_input else rom.readonly_input_reason()
            read_only_mode = bool(read_only_reason)
            if not editor_input and not read_only_mode:
                crc_hex = rom.get_crc32_hex()
                if rom.base_region() != "JP":
                    msg = (
                        "このROMは通常編集入口にも、閲覧/ステージ出力専用入口にも該当しません。\n"
                        "読み取り専用で受け入れるのは skchain US66 mapper66 ROM、"
                        "または US/JP mapper3 ROM だけです。\n"
                        f"Region: {rom.region}\nCRC32: {crc_hex}"
                    )
                    QMessageBox.warning(self, "非対応ROM", msg)
                    self.statusBar().showMessage("ROM読込を中止: 非対応ROM")
                    self._log(f"ROM読込拒否: {path} ({rom.region}, CRC32={crc_hex})")
                    return
                if rom.is_expanded() and not rom.has_customizer_metadata():
                    msg = (
                        "日本版 mapper66 拡張ROMは、本アプリで保存したROMだけ読み込めます。\n"
                        "SOLOMON_CUSTOMIZERのメタデータが見つかりません。\n"
                        f"CRC32: {crc_hex}"
                    )
                    QMessageBox.warning(self, "非対応ROM", msg)
                    self.statusBar().showMessage("ROM読込を中止: 未確認JP66拡張ROMは非対応")
                    self._log(f"ROM読込拒否: {path} ({rom.region}, CRC32={crc_hex}, no metadata)")
                    return
                msg = (
                    "このアプリの通常編集対象は日本版 Solomon no Kagi のROM、"
                    "または本アプリで保存した日本版 mapper66 拡張ROMだけです。\n"
                    f"CRC32: {crc_hex}"
                )
                QMessageBox.warning(self, "非対応ROM", msg)
                self.statusBar().showMessage("ROM読込を中止: 非対応ROM")
                self._log(f"ROM読込拒否: {path} ({rom.region}, CRC32={crc_hex})")
                return
            levels = load_all_levels(rom)
            validation_rom = Rom(loaded_rom_data, path)
            validation_rom.display_name = rom.display_name
            validation_levels = load_all_levels(validation_rom)
            validation_meta_items = None
            try:
                validation_meta_items = SkcConfig.load(
                    str(Path(__file__).parent.parent / "skc_config.xml"),
                    rom_data=bytes(validation_rom.data),
                    region=validation_rom.region,
                ).level_meta_items
            except Exception:
                validation_meta_items = None
            validation_warnings = save_validation.collect_save_warnings(
                validation_rom,
                validation_levels,
                level_meta_items=validation_meta_items,
            )

            # ボーナスステージテーブル読み込み（拡張前のアドレスで読む必要がある）
            self._load_bonus_stage_table(rom, allow_mutation=False)
            imported_stage49_breakable = 0
            imported_stage50_breakable = 0
            imported_stage52_53_breakable = 0
            if not read_only_mode:
                imported_stage49_breakable = self._import_original_jp_stage49_breakable_white(
                    loaded_rom_data, levels, allow_mutation=True
                )
                if imported_stage49_breakable:
                    self._log(
                        "JP版特殊処理補正: Stage 49 の無条件壊せる白ブロック12箇所をステージデータへ取り込み"
                    )
                imported_stage50_breakable = self._import_original_jp_stage50_breakable_white(
                    loaded_rom_data, levels, allow_mutation=True
                )
                if imported_stage50_breakable:
                    self._log(
                        "JP版特殊処理補正: Stage 50 の無条件壊せる白ブロック3箇所をステージデータへ取り込み"
                    )
                imported_stage52_53_breakable = self._import_original_jp_stage52_53_breakable_white(
                    loaded_rom_data, levels, allow_mutation=True
                )
                if imported_stage52_53_breakable:
                    self._log(
                        "JP版特殊処理補正: Stage 52/53 の無条件壊せる白ブロック各4箇所をステージデータへ取り込み"
                    )
                fixed_enemy_count = self._normalize_original_jp_enemy_data(
                    rom, levels, allow_mutation=True
                )
                if fixed_enemy_count:
                    self._log(
                        "JP版敵データ補正: Stage 29 の #2 Ghost 2体を通常Ghostへ正規化"
                    )

            # 通常ROM (mapper 3) なら自動的に拡張ROM (mapper 66) に変換
            # 容量制約 (敵726B/アイテム1402B) を回避するため
            auto_expanded = False
            self.original_rom_data = loaded_rom_data
            if not read_only_mode and not rom.is_expanded():
                from ..core import m66_expander
                m66_expander.expand_rom(rom, levels)
                auto_expanded = True
                if imported_stage49_breakable:
                    disabled_count = self._patch_stage49_breakable_white_hardcode(
                        loaded_rom_data, rom
                    )
                    if disabled_count:
                        self._log(
                            "JP版特殊処理補正: Stage 49 の無条件壊せる白ブロック生成コードを無効化"
                        )
                if imported_stage50_breakable:
                    disabled_count = self._patch_stage50_breakable_white_hardcode(
                        loaded_rom_data, rom
                    )
                    if disabled_count:
                        self._log(
                            "JP版特殊処理補正: Stage 50 の無条件壊せる白ブロック生成コードを無効化"
                        )
                if imported_stage52_53_breakable:
                    disabled_count = self._patch_stage52_53_breakable_white_hardcode(
                        loaded_rom_data, rom
                    )
                    if disabled_count:
                        self._log(
                            "JP版特殊処理補正: Stage 52/53 の無条件壊せる白ブロック生成コードを無効化"
                        )

            # JP ROM is normalized to the internal wide-title format after
            # mapper66 expansion. This must run after expand_rom(), because
            # bare change_mapper() does not populate the m66 level-data area.
            if not read_only_mode and rom.base_region() == "JP":
                try:
                    from ..core import title_screen
                    if not title_screen.is_wide_normalized(rom.data):
                        msgs = title_screen.normalize_title_to_wide(rom.data)
                        for msg in msgs:
                            self._log(msg)
                    else:
                        self._log("タイトル自動wide正規化: 既にwide形式のためスキップ")
                except Exception as e:
                    # Fail-safe: title normalization must never prevent ROM load.
                    self._log(f"タイトル自動wide正規化: スキップ ({type(e).__name__}: {e})")

            if not read_only_mode:
                self._load_bonus_stage_table(rom, allow_mutation=True)

            cfg_path = Path(__file__).parent.parent / "skc_config.xml"
            config = SkcConfig.load(str(cfg_path), rom_data=bytes(rom.data), region=rom.region)

            from ..core.constants import ROM_OFFSETS
            gfx_offset = ROM_OFFSETS[rom.base_region()]["gfx"]
            if rom.is_expanded():
                gfx_offset = 0x10010
            nes_tiles = load_chr_tiles(bytes(rom.data), gfx_offset, c.NES_TILE_COUNT)

            self.rom = rom
            self._read_only_mode = read_only_mode
            self._read_only_reason = read_only_reason
            self._auto_expanded = auto_expanded
            self.levels = levels
            self.config = config
            self._sync_main_palette_to_config()
            self.tile_renderer = TileRenderer(config, nes_tiles)
            self.level_renderer = LevelRenderer(self.tile_renderer, config)
            self._apply_renderer_marker_settings()
            self._sync_wall_color_preview()

            # item_bitmasks are a raw-ROM storage shortcut. Convert them into
            # editable stage data only during raw-ROM auto expansion, then
            # clear the copied source bytes so mapper66 reloads do not recreate
            # deleted items.
            if auto_expanded:
                self._apply_item_bitmasks(rom, config, levels, rom_data=loaded_rom_data)
            if not read_only_mode:
                self._clear_item_bitmasks(rom, config)

            # ピッカーにレンダラを渡してアイコン付きリストにする
            self.picker.set_tile_renderer(self.tile_renderer, config)
            self.picker.set_block_order(self._app_config.get("picker_block_order", []))

            # ROM情報表示（読み込んだ元ファイルのCRC32 + 既知ROMの名前判定 + 自動拡張表示）
            # 通常JP ROMはこの直前でmapper66/wide-title形式へ自動変換されるため、
            # 表示用CRCは変換後のメモリ上ROMではなく、最初に読み込んだROMバイトを見る。
            import zlib
            crc_hex = f"{zlib.crc32(bytes(self.original_rom_data)) & 0xFFFFFFFF:08X}"
            known = KNOWN_CRC32.get(crc_hex, "")
            verify_mark = "✓ 正規" if known else "? 不明/改造版"
            from ..core import rom_metadata
            meta = rom_metadata.read_metadata(bytes(rom.data))
            customizer_version = meta.get("app_version") if meta else ""
            expand_note = ""
            if auto_expanded:
                expand_note = "<br><span style='color:#fbbf24'>⚙ 拡張ROMに自動変換 (mapper 66)</span>"
            elif rom.is_expanded():
                expand_note = "<br><span style='color:#fbbf24'>拡張ROM (mapper 66)</span>"
            version_note = ""
            if customizer_version:
                version_note = (
                    f"<br>Customizer: <code>v{customizer_version}</code>"
                )
            readonly_note = ""
            if read_only_mode:
                readonly_note = (
                    "<br><span style='color:#ff4d4d; font-weight:700'>"
                    f"編集不可: 閲覧/ステージ出力専用 ({read_only_reason})"
                    "</span>"
                )
            workstate_note = ""
            if workstate_saved_at_override:
                workstate_note = (
                    "<br><span style='color:#fbbf24'>"
                    f"作業状態復元: {escape(self._format_autosave_saved_at(workstate_saved_at_override))}"
                    "</span>"
                )
            info_html = (
                f"<b>{rom.display_name}</b><br>"
                f"[{rom.region}, {len(rom)/1024:.0f}KB]<br>"
                f"CRC32: <code>{crc_hex}</code> {verify_mark}"
                f"{version_note}"
                f"{expand_note}"
                f"{readonly_note}"
                f"{workstate_note}"
            )
            if known:
                info_html += f"<br><span style='color:#aaa'>{known}</span>"
            self.lbl_rom.setText(info_html)
            self.lbl_rom.setTextFormat(Qt.RichText)
            self._rom_validation_rom = validation_rom
            self._rom_validation_warnings = validation_warnings
            self._update_rom_validation_button()
            self.statusBar().showMessage(f"読み込み完了: {len(levels)}ステージ")
            # ROM読込でアイコンが揃ったので、お気に入りを復元
            saved_favs = self._app_config.get("picker_favorites", [])
            self.picker.restore_favorites(saved_favs)
            edit_enabled = not read_only_mode
            # 拡張ROM保存対応 (Phase 2-1)
            self.btn_save_rom.setEnabled(edit_enabled)
            # IPS出力は通常ROM時の original_rom_data を基準にするため拡張ROMでも有効
            self.btn_save_ips.setEnabled(edit_enabled)
            self.btn_stage_load.setEnabled(edit_enabled)
            self.btn_stage_save.setEnabled(True)
            self._stage_clipboard = None
            self._stage_swap_source_no = None
            self._clear_stage_compare(refresh=False)
            if hasattr(self, "spin_stage_swap_target"):
                self.spin_stage_swap_target.setVisible(False)
            if hasattr(self, "btn_stage_swap"):
                self.btn_stage_swap.setText("面入れ替え")
            self._update_stage_operation_buttons()
            self.btn_clear.setEnabled(edit_enabled)
            self.btn_stats.setEnabled(True)
            self.btn_hack.setEnabled(edit_enabled)
            self.btn_enemy_hack.setEnabled(edit_enabled)
            self.btn_palette.setEnabled(edit_enabled)
            self.btn_title_screen.setEnabled(edit_enabled)
            self.btn_sprite_viewer.setEnabled(edit_enabled)
            self.btn_pixel_editor.setEnabled(edit_enabled)
            self.btn_sound_viewer.setEnabled(True)
            self.btn_special_process.setEnabled(True)
            self.btn_item_replace.setEnabled(edit_enabled)
            test_play_enabled = edit_enabled or self._can_readonly_test_play()
            self.btn_test_play.setEnabled(test_play_enabled)
            self.btn_test_play_right.setEnabled(test_play_enabled)
            self.meta_group.setEnabled(edit_enabled)
            self.picker.setEnabled(edit_enabled)
            self.chk_edit_col15.setEnabled(edit_enabled)
            if initial_level_no is None:
                target_level_no = 0
            else:
                try:
                    target_level_no = int(initial_level_no)
                except Exception:
                    target_level_no = 0
            if levels:
                target_level_no = max(0, min(target_level_no, len(levels) - 1))
            else:
                target_level_no = 0
            self.current_level_no = target_level_no
            self.list_levels.blockSignals(True)
            self.spin_level.blockSignals(True)
            self.list_levels.setCurrentRow(self.current_level_no)
            self.spin_level.setValue(self.current_level_no + 1)
            self.spin_level.blockSignals(False)
            self.list_levels.blockSignals(False)
            self._refresh_view()
            # 全レベルのサムネイル生成（53枚、約1〜3秒）
            self.statusBar().showMessage("サムネイル生成中...")
            QApplication.processEvents()
            self._generate_all_thumbnails()
            status_suffix = " (編集不可)" if read_only_mode else ""
            final_status = status_message or f"読み込み完了: {len(levels)}ステージ{status_suffix}"
            self.statusBar().showMessage(final_status)
            # 読込成功 → 再読込ボタンを有効化、履歴に追加、Undo履歴クリア、未保存マーククリア
            self.last_loaded_path = path
            self._loaded_source_path = source_path_override or path
            self._loaded_workstate_path = workstate_path_override
            self._loaded_workstate_saved_at = workstate_saved_at_override
            self.btn_reload.setEnabled(True)
            if add_history:
                self._add_to_history(path)
            self._clear_undo_history()
            self._set_dirty(False)
            log_suffix = ""
            if auto_expanded:
                log_suffix = " (拡張に自動変換)"
            elif read_only_mode:
                log_suffix = f" (読み取り専用: {read_only_reason})"
            self._log(f"ROM読込: {path}{log_suffix}")
        except Exception as e:
            QMessageBox.critical(self, "ロード失敗", f"{type(e).__name__}: {e}")

    def _update_rom_validation_button(self):
        count = len(getattr(self, "_rom_validation_warnings", []) or [])
        if count <= 0:
            self.btn_rom_validation.setVisible(False)
            return
        self.btn_rom_validation.setText(f"不整合 {count}")
        self.btn_rom_validation.setVisible(True)

    def _on_show_rom_validation(self):
        warnings = list(getattr(self, "_rom_validation_warnings", []) or [])
        rom = getattr(self, "_rom_validation_rom", None) or self.rom
        if not rom:
            return
        if (
            getattr(self, "_rom_validation_dialog", None) is not None
            and self._rom_validation_dialog.isVisible()
        ):
            self._rom_validation_dialog.raise_()
            self._rom_validation_dialog.activateWindow()
            return
        dlg = RomValidationDialog(
            rom,
            warnings,
            parent=self,
            jump_callback=self._jump_to_rom_validation_issue,
        )
        self._rom_validation_dialog = dlg
        dlg.finished.connect(lambda _result: setattr(self, "_rom_validation_dialog", None))
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def _jump_to_rom_validation_issue(self, stage_no: int, pos=None):
        if not self.levels:
            return
        max_stage = min(len(self.levels), c.LEVEL_COUNT)
        stage_no = max(1, min(max_stage, int(stage_no)))
        if self.spin_level.value() != stage_no:
            self.spin_level.setValue(stage_no)
        if pos is None:
            self.statusBar().showMessage(f"不整合: Stage {stage_no}へ移動", 3000)
            return
        try:
            x, y = int(pos[0]), int(pos[1])
        except Exception:
            self.statusBar().showMessage(f"不整合: Stage {stage_no}へ移動", 3000)
            return
        if not (0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H):
            self.statusBar().showMessage(
                f"不整合: Stage {stage_no}へ移動（座標は範囲外: {pos}）",
                3000,
            )
            return
        if hasattr(self, "level_view"):
            self.level_view._select_start = (x, y)
            self.level_view._select_end = (x, y)
        self._on_selection_updated((x, y), (x, y))
        self.statusBar().showMessage(
            f"不整合: Stage {stage_no} ({x}, {y})を選択",
            3000,
        )

    # ====== 再読込・履歴 ======

    def _history_file(self) -> Path:
        """履歴を保存するJSONファイルパス"""
        return Path(__file__).parent.parent.parent / "config" / "rom_history.json"

    def _autosave_dir(self) -> Path:
        return Path(__file__).parent.parent.parent / "autosave" / "workstate"

    def _autosave_manifest_file(self) -> Path:
        return self._autosave_dir() / "latest.json"

    def _autosave_undo_file_for_rom(self, rom_path: Path) -> Path:
        return rom_path.with_suffix(".undo.json")

    def _autosave_meta_file_for_rom(self, rom_path: Path) -> Path:
        return rom_path.with_suffix(".meta.json")

    def _load_autosave_manifest(self) -> dict:
        try:
            with open(self._autosave_manifest_file(), "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _load_autosave_metadata(self, autosave_path: str) -> dict:
        if not autosave_path:
            return {}
        try:
            rom_path = Path(autosave_path)
            meta_path = self._autosave_meta_file_for_rom(rom_path)
            if meta_path.exists():
                with open(meta_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass

        manifest = self._load_autosave_manifest()
        try:
            latest = str(Path(str(manifest.get("latest", ""))))
            current = str(Path(autosave_path))
        except Exception:
            latest = str(manifest.get("latest", ""))
            current = str(autosave_path)
        if latest and latest == current:
            return manifest if isinstance(manifest, dict) else {}
        return {}

    def _format_autosave_saved_at(self, saved_at: str) -> str:
        text = str(saved_at or "")
        if not text:
            return "保存日時不明"
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(text)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return text

    def _autosave_display_name_from_metadata(self, metadata: dict, autosave_path: str) -> str:
        display_name = str(metadata.get("display_name", "") or "")
        if display_name:
            return display_name
        source_path = str(metadata.get("source_path", "") or "")
        if source_path:
            return Path(source_path).name
        return "元ROM不明"

    def _write_autosave_metadata(self, autosave_path: Path, metadata: dict):
        meta_path = self._autosave_meta_file_for_rom(autosave_path)
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

    def _latest_autosave_path(self) -> str:
        path = self._load_autosave_manifest().get("latest", "")
        if not path:
            return ""
        try:
            p = Path(path)
            return str(p) if p.exists() else ""
        except Exception:
            return ""

    def _is_autosave_path(self, path: str) -> bool:
        if not path:
            return False
        try:
            p = Path(path).resolve()
            return self._autosave_dir().resolve() in (p.parent, *p.parents)
        except Exception:
            return False

    def _history_label_for_path(self, path: str) -> str:
        if self._is_autosave_path(path):
            metadata = self._load_autosave_metadata(path)
            display_name = self._autosave_display_name_from_metadata(metadata, path)
            saved_at = self._format_autosave_saved_at(metadata.get("saved_at", ""))
            latest = self._latest_autosave_path()
            prefix = "前回の作業状態" if latest and str(Path(path)) == str(Path(latest)) else "作業状態"
            return f"{prefix}: {display_name} / {saved_at}"
        p = Path(path)
        return f"{p.name}  ({p.parent.name})"

    def _load_history(self) -> list:
        try:
            with open(self._history_file(), "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("history", [])[:15]
        except Exception:
            return []

    def _save_history(self):
        try:
            p = self._history_file()
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"history": self._history[:15]}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _add_to_history(self, path: str):
        """履歴の先頭に追加（重複は除去）"""
        if not path:
            return
        # 重複除去
        self._history = [p for p in self._history if p != path]
        self._history.insert(0, path)
        self._history = self._history[:15]
        self._save_history()

    def _remember_previous_workstate_history(self, path: str):
        if path:
            self._add_to_history(path)

    def _prune_missing_autosave_history(self):
        kept = []
        changed = False
        for path in self._history:
            if self._is_autosave_path(path) and not Path(path).exists():
                changed = True
                continue
            kept.append(path)
        if changed:
            self._history = kept
            self._save_history()

    def _on_reload_rom(self):
        if not self.last_loaded_path:
            return
        if not self._confirm_replace_current_work("現在のROMを再読み込みします"):
            return
        if self._is_autosave_path(self.last_loaded_path):
            self._load_autosave_workstate(self.last_loaded_path, add_history=False)
        else:
            self.load_rom(self.last_loaded_path)

    def _on_restart_app(self):
        if not self._confirm_replace_current_work("アプリを再起動します"):
            return
        self._restart_after_close = True
        self.statusBar().showMessage("アプリを再起動します", 2000)
        self._log("アプリ再起動")
        self.close()

    def _load_autosave_workstate(self, path: str, add_history: bool = True) -> bool:
        metadata = self._load_autosave_metadata(path)
        source_path = str(metadata.get("source_path", "") or "")
        display_name = self._autosave_display_name_from_metadata(metadata, path)
        saved_at = str(metadata.get("saved_at", "") or "")
        try:
            level_no = int(metadata.get("last_level_no", 0))
        except Exception:
            level_no = 0
        self.load_rom(
            path,
            add_history=False,
            status_message=(
                f"{display_name} の作業状態を復元しました: "
                f"{self._format_autosave_saved_at(saved_at)}"
            ),
            source_path_override=source_path,
            display_name_override=display_name,
            workstate_path_override=path,
            workstate_saved_at_override=saved_at,
            initial_level_no=level_no,
        )
        if str(Path(self.last_loaded_path)) != str(Path(path)):
            return False
        self._restore_autosave_undo_history(self._autosave_undo_file_for_rom(Path(path)))
        if add_history:
            self._remember_previous_workstate_history(path)
        return True

    def _on_show_history(self):
        from PyQt5.QtWidgets import QMenu
        self._prune_missing_autosave_history()
        menu = QMenu(self)
        if not self._history:
            menu.addAction("(履歴なし)").setEnabled(False)
        else:
            for path in self._history:
                label = self._history_label_for_path(path)
                action = menu.addAction(label)
                action.setToolTip(path)
                action.triggered.connect(lambda checked, pp=path: self._open_history_path(pp))
            menu.addSeparator()
            clr = menu.addAction("履歴をクリア")
            clr.triggered.connect(self._on_clear_history)
        # ボタンの真下に表示
        btn = self.btn_history
        menu.exec_(btn.mapToGlobal(btn.rect().bottomLeft()))

    def _open_history_path(self, path: str):
        if not self._confirm_replace_current_work("履歴からROM/作業状態を開きます"):
            return
        if self._is_autosave_path(path):
            self._load_autosave_workstate(path)
        else:
            self.load_rom(path)

    def _on_clear_history(self):
        latest = self._latest_autosave_path()
        self._history = [latest] if latest else []
        self._save_history()
        self.statusBar().showMessage(
            "履歴をクリアしました（前回の作業状態は保持）", 2500
        )

    def _show_save_failure(self, title: str, error: Exception, log_prefix: str,
                           extra_message: str = ""):
        if isinstance(error, saver.SavePreflightError):
            msg = error.dialog_message()
            log_msg = error.log_message()
        else:
            msg = f"{type(error).__name__}: {error}"
            log_msg = msg
        if extra_message:
            msg = f"{msg}\n\n{extra_message}"
        QMessageBox.critical(self, title, msg)
        self._log(f"{log_prefix}: {log_msg}")

    def _preferred_save_dir(self) -> Path:
        for value in (
            self._app_config.get("last_save_dir", ""),
            self.last_loaded_path,
            self._history[0] if self._history else "",
        ):
            if not value:
                continue
            try:
                if self._is_autosave_path(value):
                    continue
                p = Path(value)
                folder = p if p.is_dir() else p.parent
                if folder.exists():
                    return folder
            except Exception:
                continue
        return Path.cwd()

    def _default_save_path(self, default_name: str) -> str:
        return str(self._preferred_save_dir() / default_name)

    def _remember_save_path(self, path: str) -> None:
        self._remember_save_dir(Path(path).parent)

    def _remember_save_dir(self, folder) -> None:
        try:
            folder = str(Path(folder))
            if folder and Path(folder).exists():
                self._app_config["last_save_dir"] = folder
                save_config(self._app_config)
        except Exception:
            pass

    def _panel_variant_settings_for_save(self) -> dict:
        settings = normalize_panel_variant_settings(
            self._app_config.get("panel_variant_settings")
        )
        self._app_config["panel_variant_settings"] = settings
        return settings

    def _on_save_rom(self):
        if not self.rom:
            return False
        if self._reject_read_only_edit():
            return False
        if not self._confirm_save_validation_warnings():
            return False
        # デフォルト名: 元ROM名のステム + _YYYYMMDD_HHMMSS.nes
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 元ROMのステムを取得（ZIP内ファイル名 "xxx.nes (in yyy.zip)" の場合は xxx を抜く）
        src_name = self.rom.display_name or "modified.nes"
        # "(in ...zip)" のサフィックスを除去
        if " (in " in src_name:
            src_name = src_name.split(" (in ")[0]
        stem = Path(src_name).stem
        default_name = f"{stem}_{ts}.nes"
        path, _ = QFileDialog.getSaveFileName(
            self, "改造ROMの保存先", self._default_save_path(default_name),
            "NES ROMs (*.nes);;All files (*)"
        )
        if not path:
            return False
        try:
            saved_data = saver.build_saved_rom_data(
                self.rom,
                self.levels,
                self._panel_variant_settings_for_save(),
            )
            saver.write_rom_data(saved_data, path)
            self._remember_save_path(path)
            self.rom.data = bytearray(saved_data)
            self.rom._crc32 = None
            bundle_msg = ""
            try:
                bundle_dir = self._save_rom_project_bundle(path, saved_data)
                bundle_msg = f" / project data: {bundle_dir}"
            except Exception as bundle_error:
                QMessageBox.warning(
                    self, "制作データ保存失敗",
                    "ROMは保存されましたが、共通設定JSONまたはステージPNGの保存に失敗しました。\n\n"
                    f"{type(bundle_error).__name__}: {bundle_error}"
                )
                self._log(
                    f"制作データ保存失敗: {type(bundle_error).__name__}: {bundle_error}"
                )
            self.statusBar().showMessage(f"ROM保存完了: {path}", 5000)
            self._set_dirty(False)
            self._log(f"ROM保存: {path}{bundle_msg}")
            return True
        except Exception as e:
            self._show_save_failure("保存失敗", e, "ROM保存失敗")
            return False

    def _on_test_play(self):
        """現在の編集状態 + ステージ選択(現在レベル) で一時ROMを生成しエミュ起動"""
        if not self.rom or not self.levels:
            return
        if self._is_read_only() and not self._can_readonly_test_play():
            self._reject_read_only_edit()
            return
        emu_path = self._app_config.get("emulator_path", "")
        if not emu_path or not os.path.exists(emu_path):
            QMessageBox.warning(
                self, "エミュレータ未設定",
                "F9 設定画面で『エミュレータ』のパスを指定してください"
            )
            return
        self._play_button_sound()

        import tempfile
        import subprocess

        # rom.dataを破壊しないよう、作業前のコピーを取っておく
        original_data = bytearray(self.rom.data)
        tmp_rom = None
        stage_no = self.current_level_no + 1

        try:
            try:
                if not self._is_read_only():
                    # レベルを反映
                    saver.save_levels_to_rom(
                        self.rom,
                        self.levels,
                        self._panel_variant_settings_for_save(),
                    )
                # ステージ選択: 現在レベルから開始
                self._patch_testplay_start_stage(stage_no)
                if not self._is_read_only():
                    self._patch_testplay_fast_start()

                # 一時ファイルへ書き出し
                tmpdir = Path(tempfile.gettempdir()) / "magatu_skc_testplay"
                tmpdir.mkdir(parents=True, exist_ok=True)
                tmp_rom = tmpdir / f"testplay_stage{stage_no:02d}.nes"
                saver.write_rom_data(bytes(self.rom.data), str(tmp_rom))
            finally:
                # rom.data を編集前に戻す（テストプレイ用の改変を残さない）
                self.rom.data = original_data
        except Exception as e:
            self._show_save_failure(
                "テストプレイ準備失敗",
                e,
                "テストプレイ準備失敗",
                "通常の「改造ROMとして保存」でも同じエラーが出る場合、"
                "保存前チェックまたはROM容量の制約です。",
            )
            return

        try:
            subprocess.Popen([emu_path, str(tmp_rom)])
            self.statusBar().showMessage(
                f"テストプレイ起動: Stage {stage_no} / {tmp_rom}", 5000
            )
            visible_cells = sorted(
                getattr(self.levels[self.current_level_no], "visible_in_block_item_cells", set()) or []
            )
            self._log(
                f"テストプレイ起動: Stage {stage_no} → {tmp_rom} "
                f"(透明ブロック内={len(visible_cells)} {visible_cells})"
            )
        except Exception as e:
            QMessageBox.critical(self, "エミュ起動失敗", f"{type(e).__name__}: {e}")
            self._log(f"テストプレイ失敗: {type(e).__name__}: {e}")

    def _can_readonly_test_play(self) -> bool:
        if not self.rom or not self._is_read_only():
            return False
        if self.rom.is_skchain_us66():
            return True
        return (
            not self.rom.is_expanded()
            and self.rom.is_mapper3()
            and self.rom.base_region() in ("JP", "US")
        )

    def _patch_testplay_start_stage(self, stage_no: int):
        if stage_no == 1:
            self.rom.data[0x1145] = 0x00
            self.rom.data[0x1149] = 0x8D
            self.rom.data[0x114B] = 0x04
        else:
            stage_byte = (stage_no - 1) & 0xff
            self.rom.data[0x1145] = stage_byte
            self.rom.data[0x1149] = 0xAD
            self.rom.data[0x114B] = 0x93

    def _patch_testplay_fast_start(self):
        # F9 testplay-only fast start. These bytes match the accepted raw-JP
        # test ROM: TEST_OrigJP_MinTitleSkip_CBB3_SkipStartWaits_9066_9082_9315.
        def patch_testplay_bytes(cpu_addr, original, patched, label):
            off = 0x10 + (cpu_addr - 0x8000)
            cur = bytes(self.rom.data[off:off + len(original)])
            if cur not in (original, patched):
                raise RuntimeError(
                    f"{label} signature mismatch at ${cpu_addr:04X}: "
                    f"got {cur.hex(' ')}"
                )
            self.rom.data[off:off + len(patched)] = patched

        patch_testplay_bytes(
            0xCB6E,
            bytes.fromhex("A2 01 20"),
            bytes.fromhex("4C B3 CB"),
            "title skip",
        )
        for wait_cpu in (0x9066, 0x9082, 0x9315):
            patch_testplay_bytes(
                wait_cpu,
                bytes.fromhex("20 D5 9B"),
                bytes.fromhex("EA EA EA"),
                "start-screen wait skip",
            )

    def _on_save_ips(self):
        if not self.rom:
            return
        if self._reject_read_only_edit():
            return
        if not self._confirm_save_validation_warnings():
            return

        # 1. 原本ROM（市販吸出し）を選択
        from .file_dialog_compat import get_file
        base_path = get_file(self, title="原本ROM（市販吸出し）を選択", filter="*.nes")
        if not base_path:
            return

        try:
            with open(base_path, "rb") as f:
                base_data = f.read()
        except Exception as e:
            QMessageBox.critical(self, "原本ROM読込失敗", f"{type(e).__name__}: {e}")
            return

        # 2. 現在の編集状態を保存用ROMデータに反映
        try:
            modified_data = saver.build_saved_rom_data(
                self.rom,
                self.levels,
                self._panel_variant_settings_for_save(),
            )
        except Exception as e:
            self._show_save_failure("IPS生成失敗", e, "IPS保存失敗")
            return

        # 3. IPS保存先を選択
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        src_name = self.rom.display_name or "patch.ips"
        if " (in " in src_name:
            src_name = src_name.split(" (in ")[0]
        stem = Path(src_name).stem
        default_name = f"{stem}_{ts}.ips"
        path, _ = QFileDialog.getSaveFileName(
            self, "IPSパッチ保存", self._default_save_path(default_name),
            "IPS Patch (*.ips);;All files (*)"
        )
        if not path:
            return

        try:
            ips.save_ips_patch(base_data, modified_data, path)
            self._remember_save_path(path)
            self.statusBar().showMessage(f"IPS保存完了: {path}", 5000)
            self._log(f"IPS保存: {path} (原本: {base_path})")
        except Exception as e:
            QMessageBox.critical(self, "IPS生成失敗", f"{type(e).__name__}: {e}")
            self._log(f"IPS保存失敗: {type(e).__name__}: {e}")

    def _confirm_save_validation_warnings(self) -> bool:
        level_meta_items = getattr(self.config, "level_meta_items", []) if self.config else []
        warnings = save_validation.collect_save_warnings(
            self.rom,
            self.levels,
            level_meta_items=level_meta_items,
        )
        if not warnings:
            return True
        shown_limit = 24
        shown = warnings[:shown_limit]
        more = len(warnings) - len(shown)
        body = "\n".join(f"- {msg}" for msg in shown)
        if more > 0:
            body += f"\n- ...ほか {more} 件"
        self._log("保存前不整合: " + " / ".join(warnings))
        reply = QMessageBox.warning(
            self,
            "保存前チェック",
            "保存前チェックで不整合らしき項目が見つかりました。\n"
            "エラーではありませんが、見落としの可能性があります。\n\n"
            f"{body}\n\n"
            "このまま保存を続行しますか？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return reply == QMessageBox.Yes

    def _save_rom_project_bundle(self, rom_path: str, saved_data: bytes) -> Path:
        """Save the reproducible project data beside a saved ROM."""
        import json
        from ..core.rom import Rom as _Rom
        from .hack_dialog import HackDialog

        rom_file = Path(rom_path)
        stem = rom_file.stem
        out_dir = rom_file.parent
        stage_dir = out_dir / f"{stem}_stage_data"
        stage_dir.mkdir(parents=True, exist_ok=True)

        work_rom = _Rom(bytes(saved_data), self.rom.path)
        work_rom.display_name = rom_file.name
        dlg = HackDialog(work_rom, parent=self, app_config=self._app_config)
        try:
            payload = dlg._collect_global_settings()
        finally:
            dlg.deleteLater()

        try:
            from ..core import title_screen
            payload["settings"]["title_extra_text"] = title_screen.read_title_text_line(
                bytearray(saved_data)
            )
        except Exception:
            pass
        payload["saved_rom"] = rom_file.name
        payload["stage_data_dir"] = stage_dir.name
        original_data = getattr(self, "original_rom_data", None)
        if original_data:
            import zlib
            payload["original_rom_crc32"] = f"{zlib.crc32(bytes(original_data)) & 0xFFFFFFFF:08X}"
            payload["original_rom_size"] = len(original_data)

        global_path = out_dir / f"{stem}_global_settings.json"
        with open(global_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        if not self.level_renderer:
            raise RuntimeError("level renderer is not ready.")
        for i, level in enumerate(self.levels):
            bonus = self._bonus_items if i == 50 and getattr(self, "_bonus_items", None) else None
            img = self.level_renderer.render(
                level,
                level_no=i,
                show_grid=self.show_grid,
                show_hidden_overlay=self.chk_hidden.isChecked(),
                show_border=True,
                bonus_items=bonus,
            )
            self._sync_enemy_codes_from_rom(i)
            self._save_png_with_xml(img, level, stage_dir / f"level_{i + 1:02d}.png", level_no=i)
            QApplication.processEvents()
        return stage_dir

    def _make_export_dir(self):
        """ROM名+時刻のエクスポートフォルダを作成して返す"""
        from datetime import datetime
        rom_stem = Path(self.rom.display_name).stem if self.rom and self.rom.display_name else "unknown"
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_dir = self._preferred_save_dir() / f"{rom_stem}_stage_data_{ts}"
        export_dir.mkdir(parents=True, exist_ok=True)
        self._remember_save_dir(export_dir.parent)
        return export_dir

    @staticmethod
    def _is_stage_level_meta_position_target(mi) -> bool:
        no = int(getattr(mi, "no", -1))
        if 0 <= no <= 7:
            return True
        return no in (10, 11, 12, 13)

    @staticmethod
    def _stage_level_meta_kind(no: int) -> str:
        if 0 <= no <= 7:
            return "solomon_seal"
        if no in (10, 11):
            return "tecmo_bunny"
        if no == 12:
            return "page_space"
        if no == 13:
            return "page_time"
        return "unknown"

    def _solomon_seal_meta_at(self, level_no: int, tile: tuple):
        if self.config is None:
            return None
        for mi in getattr(self.config, "level_meta_items", []) or []:
            if int(getattr(mi, "level_no", -1)) != int(level_no):
                continue
            no = int(getattr(mi, "no", -1))
            if self._stage_level_meta_kind(no) != "solomon_seal":
                continue
            if tuple(getattr(mi, "position", (-1, -1))) == tuple(tile):
                return mi
        return None

    def _solomon_seal_block_combo_at(self, level, level_no: int, tile: tuple):
        mi = self._solomon_seal_meta_at(level_no, tile)
        if mi is None:
            return None
        x, y = tile
        if not (0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H):
            return None
        wall = level.tiles[y][x]
        if wall == Wall.BROWN and tile not in getattr(level, "cracked_block_cells", set()):
            return {"meta": mi, "wall_type": wall, "runtime_markers": set()}
        if wall == Wall.WHITE and tile in getattr(level, "breakable_white_cells", set()):
            return {
                "meta": mi,
                "wall_type": wall,
                "runtime_markers": {"breakable_white_cells"},
            }
        if wall == Wall.NONE and tile in getattr(level, "invisible_breakable_cells", set()):
            return {
                "meta": mi,
                "wall_type": wall,
                "runtime_markers": {"invisible_breakable_cells"},
            }
        return None

    def _solomon_seal_tile_block_label(self, level, tile: tuple) -> str:
        x, y = tile
        wall = level.tiles[y][x]
        if wall == Wall.NONE and tile in getattr(level, "invisible_breakable_cells", set()):
            return "壊せる透明ブロック"
        if wall == Wall.NONE and tile in getattr(level, "invisible_solid_cells", set()):
            return "壊せない透明ブロック"
        if wall == Wall.NONE:
            return "空気"
        if wall == Wall.BROWN and tile in getattr(level, "passable_brown_cells", set()):
            return "すり抜ける茶色ブロック"
        if wall == Wall.BROWN and tile in getattr(level, "solid_brown_cells", set()):
            return "壊せない茶色ブロック"
        if wall == Wall.BROWN and tile in getattr(level, "cracked_block_cells", set()):
            return "ひび割れブロック"
        if wall == Wall.BROWN:
            return "茶ブロック"
        if wall == Wall.WHITE and tile in getattr(level, "breakable_white_cells", set()):
            return "壊せる白ブロック"
        if wall == Wall.WHITE and tile in getattr(level, "passable_white_cells", set()):
            return "すり抜ける白ブロック"
        if wall == Wall.WHITE:
            return "壊せない白ブロック"
        if wall == Wall.BROWN_WHITE:
            return "壊せる白ブロック"
        return "ブロック"

    def _solomon_seal_can_overlap_tile(self, level, tile: tuple) -> bool:
        x, y = tile
        if not (0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H):
            return False
        wall = level.tiles[y][x]
        if wall == Wall.NONE:
            return tile not in getattr(level, "invisible_solid_cells", set())
        if wall == Wall.BROWN:
            return (
                tile not in getattr(level, "passable_brown_cells", set())
                and tile not in getattr(level, "solid_brown_cells", set())
                and tile not in getattr(level, "cracked_block_cells", set())
            )
        if wall == Wall.WHITE:
            return tile in getattr(level, "breakable_white_cells", set())
        if wall == Wall.BROWN_WHITE:
            return True
        return False

    def _show_solomon_seal_block_overlap_message(self, level, tile: tuple):
        label = self._solomon_seal_tile_block_label(level, tile)
        self.statusBar().showMessage(
            f"ソロモンの封印は {label} には重ねられません {tile}", 3000
        )

    def _solomon_seal_can_move_to_tile(self, level, tile: tuple) -> bool:
        if not self._solomon_seal_can_overlap_tile(level, tile):
            return False
        return bool(level.is_door_removed() or level.fixed_door_pos != tile)

    def _show_solomon_seal_move_rejected_message(self, level, tile: tuple):
        if not self._solomon_seal_can_overlap_tile(level, tile):
            self._show_solomon_seal_block_overlap_message(level, tile)
            return
        self.statusBar().showMessage(
            f"ソロモンの封印は扉には重ねられません {tile}", 3000
        )

    def _collect_stage_level_meta_positions(self, level_no: int) -> list:
        if self.config is None:
            return []
        from ..core.element import position_from_byte

        result = []
        for mi in getattr(self.config, "level_meta_items", []) or []:
            if int(getattr(mi, "level_no", -1)) != int(level_no):
                continue
            if not self._is_stage_level_meta_position_target(mi):
                continue
            rom_offset = int(getattr(mi, "rom_offset", -1))
            if self.rom is not None and 0 <= rom_offset < len(self.rom.data):
                pos = position_from_byte(self.rom.data[rom_offset])
            else:
                pos = tuple(getattr(mi, "position", (0, 0)))
            result.append({
                "kind": self._stage_level_meta_kind(int(getattr(mi, "no", -1))),
                "no": int(getattr(mi, "no", -1)),
                "level_no": int(level_no),
                "description": str(getattr(mi, "description", "")),
                "position": [int(pos[0]), int(pos[1])],
            })
        return result

    @staticmethod
    def _parse_stage_level_meta_entry(entry):
        pos = entry.attrib.get("position", "")
        parts = pos.strip().split(",")
        if len(parts) != 2:
            raise ValueError("level_meta_positions position must be x,y.")
        x = int(parts[0])
        y = int(parts[1])
        if not (0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H):
            raise ValueError(f"level_meta_positions position out of range: {x},{y}")
        return (
            int(entry.attrib["no"]),
            int(entry.attrib["level_no"]),
            (x, y),
        )

    def _apply_stage_level_meta_positions_from_xml(self, root, target_level_no: int) -> list:
        positions_elem = root.find("level_meta_positions")
        if positions_elem is None or self.config is None:
            return []
        from ..core.element import byte_from_position, position_from_byte

        meta_by_key = {
            (int(getattr(mi, "no", -1)), int(getattr(mi, "level_no", -1))): mi
            for mi in getattr(self.config, "level_meta_items", []) or []
        }
        changed = []
        for entry in positions_elem.findall("meta"):
            no, level_no, pos = self._parse_stage_level_meta_entry(entry)
            if int(level_no) != int(target_level_no):
                continue
            if not (0 <= no <= 7 or no in (10, 11, 12, 13)):
                continue
            mi = meta_by_key.get((no, level_no))
            if mi is None:
                continue
            rom_offset = int(getattr(mi, "rom_offset", -1))
            old_pos = tuple(getattr(mi, "position", (0, 0)))
            if self.rom is not None and 0 <= rom_offset < len(self.rom.data):
                old_pos = position_from_byte(self.rom.data[rom_offset])
                self.rom.data[rom_offset] = byte_from_position(pos)
            mi.position = pos
            if old_pos != pos:
                changed.append(str(getattr(mi, "description", "") or f"meta {no}"))
        return changed

    def _conditional_breakable_groups_for_level(self, level_no: int) -> list:
        if int(level_no) == 48:
            return ["stage49"]
        if int(level_no) == 49:
            return ["stage50"]
        if int(level_no) in (51, 52):
            return ["stage52_53"]
        return []

    def _collect_stage_conditional_breakable_positions(self, level_no: int) -> list:
        result = []
        for group in self._conditional_breakable_groups_for_level(level_no):
            positions = self._conditional_breakable_positions(group)
            if not positions:
                continue
            for sub, pos in positions.items():
                result.append({
                    "level_no": int(level_no),
                    "group": group,
                    "sub": sub,
                    "position": [int(pos[0]), int(pos[1])],
                })
        return result

    @staticmethod
    def _parse_stage_conditional_breakable_entry(entry):
        pos = entry.attrib.get("position", "")
        parts = pos.strip().split(",")
        if len(parts) != 2:
            raise ValueError("conditional_breakable_positions position must be x,y.")
        x = int(parts[0])
        y = int(parts[1])
        if not (0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H):
            raise ValueError(f"conditional_breakable_positions position out of range: {x},{y}")
        return (
            int(entry.attrib["level_no"]),
            str(entry.attrib["group"]),
            str(entry.attrib["sub"]),
            (x, y),
        )

    def _apply_stage_conditional_breakable_positions_from_xml(self, root, target_level_no: int) -> list:
        positions_elem = root.find("conditional_breakable_positions")
        if positions_elem is None:
            return []
        changed = []
        allowed_groups = set(self._conditional_breakable_groups_for_level(target_level_no))
        for entry in positions_elem.findall("marker"):
            level_no, group, sub, pos = self._parse_stage_conditional_breakable_entry(entry)
            if int(level_no) != int(target_level_no):
                continue
            if group not in allowed_groups:
                continue
            before = self._conditional_breakable_positions(group) or {}
            old_pos = before.get(sub)
            if self._move_conditional_breakable_marker(group, sub, pos):
                if old_pos != pos:
                    changed.append(f"{group}:{sub}")
        return changed

    def _collect_stage_bomb_jack_positions(self, level_no: int) -> list:
        positions = self._bomb_jack_positions(level_no)
        if not positions:
            return []
        return [
            {
                "level_no": int(level_no),
                "sub": "trigger",
                "position": [int(positions["trigger"][0]), int(positions["trigger"][1])],
            },
            {
                "level_no": int(level_no),
                "sub": "spawn",
                "position": [int(positions["spawn"][0]), int(positions["spawn"][1])],
            },
        ]

    @staticmethod
    def _parse_stage_bomb_jack_entry(entry):
        pos = entry.attrib.get("position", "")
        parts = pos.strip().split(",")
        if len(parts) != 2:
            raise ValueError("bomb_jack_positions position must be x,y.")
        x = int(parts[0])
        y = int(parts[1])
        if not (0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H):
            raise ValueError(f"bomb_jack_positions position out of range: {x},{y}")
        return (
            int(entry.attrib["level_no"]),
            str(entry.attrib["sub"]),
            (x, y),
        )

    def _apply_stage_bomb_jack_positions_from_xml(self, root, target_level_no: int) -> list:
        positions_elem = root.find("bomb_jack_positions")
        if positions_elem is None:
            return []
        changed = []
        for entry in positions_elem.findall("marker"):
            level_no, sub, pos = self._parse_stage_bomb_jack_entry(entry)
            if int(level_no) != int(target_level_no):
                continue
            before = self._bomb_jack_positions(target_level_no) or {}
            old_pos = before.get(sub)
            if self._move_bomb_jack_marker(sub, pos, level_no=target_level_no):
                if old_pos != pos:
                    changed.append(f"bomb_jack:{sub}")
        return changed

    def _save_png_with_xml(self, img, level, path, level_no=None):
        """QImageをPNGで保存し、iTXtチャンクにレベルXMLを埋め込む"""
        import struct, zlib
        from ..core.xml_io import level_to_magatu_xml
        from PyQt5.QtCore import QBuffer, QIODevice

        # QImage → PNGバイト列
        buf = QBuffer()
        buf.open(QIODevice.WriteOnly)
        img.save(buf, "PNG")
        png_data = bytearray(buf.data())
        buf.close()

        # XMLデータ
        meta_positions = []
        conditional_positions = []
        bomb_jack_positions = []
        if level_no is not None:
            meta_positions = self._collect_stage_level_meta_positions(level_no)
            conditional_positions = self._collect_stage_conditional_breakable_positions(level_no)
            bomb_jack_positions = self._collect_stage_bomb_jack_positions(level_no)
        xml_str = level_to_magatu_xml(
            level,
            level_meta_positions=meta_positions,
            conditional_breakable_positions=conditional_positions,
            bomb_jack_positions=bomb_jack_positions,
        )
        xml_bytes = xml_str.encode("utf-8")

        # iTXt チャンク構築
        # keyword(null) + compression_flag(0) + compression_method(0)
        # + language_tag(null) + translated_keyword(null) + text
        keyword = b"msc_level"
        chunk_payload = keyword + b"\x00" + b"\x00\x00" + b"\x00" + b"\x00" + xml_bytes
        chunk_type = b"iTXt"
        chunk_len = struct.pack(">I", len(chunk_payload))
        chunk_crc = struct.pack(">I", zlib.crc32(chunk_type + chunk_payload) & 0xFFFFFFFF)
        itxt_chunk = chunk_len + chunk_type + chunk_payload + chunk_crc

        # IEND の直前に挿入（末尾12バイト = IEND チャンク）
        insert_pos = len(png_data) - 12
        png_data[insert_pos:insert_pos] = itxt_chunk

        with open(str(path), "wb") as f:
            f.write(png_data)

    def _on_export_current(self):
        if not self.levels or self.level_renderer is None:
            return
        from datetime import datetime
        stage_no = self.current_level_no + 1
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"level_{stage_no:02d}_{ts}.png"
        path, _ = QFileDialog.getSaveFileName(
            self, "ステージデータPNGの保存先", self._default_save_path(default_name),
            "PNG Images (*.png);;All files (*)"
        )
        if not path:
            return
        level = self.levels[self.current_level_no]
        img = self.level_renderer.render(
            level,
            level_no=self.current_level_no,
            show_grid=self.show_grid,
            show_hidden_overlay=(
                self.chk_hidden.isChecked()
                and self.chk_stage_png_secrets.isChecked()
            ),
            show_secret_elements=self.chk_stage_png_secrets.isChecked(),
            special_marks=self._get_special_marks(self.current_level_no),
            show_border=True,
            bonus_items=self._get_bonus_items(),
        )
        self._sync_enemy_codes_from_rom(self.current_level_no)
        self._save_png_with_xml(img, level, path, level_no=self.current_level_no)
        self._remember_save_path(path)
        self.statusBar().showMessage(f"保存: {path} (XML埋込)", 5000)

    def _on_export_all(self):
        if not self.levels or self.level_renderer is None:
            return
        export_dir = self._make_export_dir()
        for i, level in enumerate(self.levels):
            path = export_dir / f"level_{i + 1:02d}.png"
            bonus = self._bonus_items if i == 50 and getattr(self, "_bonus_items", None) else None
            img = self.level_renderer.render(
                level,
                level_no=i,
                show_grid=self.show_grid,
                show_hidden_overlay=(
                    self.chk_hidden.isChecked()
                    and self.chk_stage_png_secrets.isChecked()
                ),
                show_secret_elements=self.chk_stage_png_secrets.isChecked(),
                special_marks=self._get_special_marks(i),
                show_border=True,
                bonus_items=bonus,
            )
            self._sync_enemy_codes_from_rom(i)
            self._save_png_with_xml(img, level, path, level_no=i)
            self.statusBar().showMessage(f"保存中: {i+1}/{len(self.levels)} (XML埋込)")
            QApplication.processEvents()
        self.statusBar().showMessage(
            f"全 {len(self.levels)} ステージ保存完了 (XML埋込) → {export_dir.absolute()}", 8000
        )
        QMessageBox.information(
            self, "完了",
            f"全 {len(self.levels)} ステージを保存しました (XML埋込)\n\n保存先:\n{export_dir.absolute()}"
        )

    # ====== ステージデータ読込 (PNG埋め込みXML) ======

    def _on_stage_data_load(self):
        if self._reject_read_only_edit():
            return
        if self.rb_stage_current.isChecked():
            self._on_png_import_current()
        else:
            self._on_png_import_all()

    def _on_stage_data_save(self):
        if self.rb_stage_current.isChecked():
            self._on_export_current()
        else:
            self._on_export_all()

    def _set_stage_compare_controls_visible(self, visible: bool):
        for attr in ("btn_stage_compare_current", "btn_stage_compare_diff"):
            widget = getattr(self, attr, None)
            if widget is not None:
                widget.setVisible(False)
        label = getattr(self, "lbl_stage_compare_mode", None)
        if label is not None:
            label.setVisible(bool(visible))
            if not visible:
                label.setText("")
        orientation_btn = getattr(self, "btn_stage_compare_orientation", None)
        if orientation_btn is not None:
            orientation_btn.setVisible(bool(visible and self._stage_compare_edit_mode))
        end_btn = getattr(self, "btn_stage_compare_edit_end", None)
        if end_btn is not None:
            end_btn.setVisible(bool(visible and self._stage_compare_edit_mode))
        orientation_shortcut = getattr(self, "shortcut_stage_compare_orientation", None)
        if orientation_shortcut is not None:
            orientation_shortcut.setEnabled(bool(visible and self._stage_compare_edit_mode))
        shortcut = getattr(self, "shortcut_stage_compare_toggle", None)
        if shortcut is not None:
            shortcut.setEnabled(bool(visible))

    def _is_stage_compare_diff_view(self) -> bool:
        return bool(
            self._stage_compare_show_diff
            and self._stage_compare_diff_image is not None
            and self._stage_compare_level_no == self.current_level_no
        )

    def _is_stage_compare_edit_view(self) -> bool:
        return bool(
            self._stage_compare_edit_mode
            and self._stage_compare_png_image is not None
            and self._stage_compare_level_no == self.current_level_no
        )

    def _clear_stage_compare(self, refresh: bool = True):
        self._stage_compare_png_image = None
        self._stage_compare_diff_image = None
        self._stage_compare_png_level = None
        self._stage_compare_level_no = None
        self._stage_compare_path = ""
        self._stage_compare_show_diff = False
        self._stage_compare_edit_mode = False
        self._stage_compare_edit_orientation = "horizontal"
        self._stage_compare_edit_current_size = None
        self._stage_compare_diff_count = None
        self._stage_compare_diff_cells = []
        self._set_stage_compare_controls_visible(False)
        if hasattr(self, "stage_compare_diff_label"):
            self.stage_compare_diff_label.hide()
        if hasattr(self, "btn_stage_compare_current"):
            self.btn_stage_compare_current.setChecked(True)
        if hasattr(self, "level_view"):
            self.level_view.set_tile_offset_override(None)
        if refresh:
            self._refresh_view()

    def _set_stage_compare_view(self, show_diff: bool):
        if self._stage_compare_diff_image is None:
            return
        self._stage_compare_show_diff = bool(show_diff)
        if show_diff:
            self.btn_stage_compare_diff.setChecked(True)
            self.lbl_stage_compare_mode.setText("差分")
        else:
            self.btn_stage_compare_current.setChecked(True)
            self.lbl_stage_compare_mode.setText("現在")
        self._refresh_view()

    def _toggle_stage_compare_view(self):
        if self._stage_compare_png_image is None:
            return
        self._set_stage_compare_view(not self._stage_compare_show_diff)

    def _read_stage_png_level(self, path: str):
        xml_str = self._extract_xml_from_png(path)
        if xml_str is None:
            raise ValueError("このPNGにはステージデータが埋め込まれていません")
        root = ET.fromstring(xml_str)
        if root.tag != "solomon_customizer":
            raise ValueError("このPNGはSOLOMON_CUSTOMIZERのステージPNGではありません")
        lv = self._xml_element_to_level_compat(root)
        if lv is None:
            raise ValueError("ステージデータの解析に失敗しました")
        return lv, root

    @staticmethod
    def _image_cells_equal(a: QImage, ax: int, ay: int, b: QImage, bx: int, by: int) -> bool:
        tw = c.TILE_WIDTH
        for yy in range(tw):
            for xx in range(tw):
                if a.pixelColor(ax + xx, ay + yy) != b.pixelColor(bx + xx, by + yy):
                    return False
        return True

    @staticmethod
    def _stage_png_cell_offset(img: QImage) -> int:
        tw = c.TILE_WIDTH
        if img.width() >= (c.LEVEL_W + 1) * tw and img.height() >= (c.LEVEL_H + 1) * tw:
            return 1
        return 0

    def _stage_image_cell_difference_positions(
            self, current_image: QImage, reference_image: QImage) -> list:
        tw = c.TILE_WIDTH
        current_offset = self._stage_png_cell_offset(current_image)
        reference_offset = self._stage_png_cell_offset(reference_image)
        differences = []
        for y in range(c.LEVEL_H):
            for x in range(c.LEVEL_W):
                sx_cur = (x + current_offset) * tw
                sy_cur = y * tw
                sx_ref = (x + reference_offset) * tw
                sy_ref = y * tw
                if (
                    sx_cur + tw > current_image.width()
                    or sy_cur + tw > current_image.height()
                    or sx_ref + tw > reference_image.width()
                    or sy_ref + tw > reference_image.height()
                ):
                    differences.append((x, y))
                    continue
                if not self._image_cells_equal(
                    current_image,
                    sx_cur,
                    sy_cur,
                    reference_image,
                    sx_ref,
                    sy_ref,
                ):
                    differences.append((x, y))
        return differences

    def _count_stage_image_cell_differences(self, current_image: QImage, reference_image: QImage) -> int:
        return len(self._stage_image_cell_difference_positions(current_image, reference_image))

    def _render_current_stage_for_png_compare(self) -> QImage:
        level = self.levels[self.current_level_no]
        return self.level_renderer.render(
            level,
            level_no=self.current_level_no,
            show_grid=self.show_grid,
            show_hidden_overlay=(
                self.chk_hidden.isChecked()
                and self.chk_stage_png_secrets.isChecked()
            ),
            show_secret_elements=self.chk_stage_png_secrets.isChecked(),
            special_marks=self._get_special_marks(self.current_level_no),
            show_border=True,
            bonus_items=self._get_bonus_items(),
        )

    def _render_current_stage_for_compare_edit_base(self) -> QImage:
        level = self.levels[self.current_level_no]
        return self.level_renderer.render(
            level,
            level_no=self.current_level_no,
            show_grid=self.show_grid,
            show_hidden_overlay=False,
            hover_tile=None,
            show_col15=True,
            selection_rect=None,
            special_marks=None,
            show_border=True,
            bonus_items=self._get_bonus_items(),
            draw_editor_markers=False,
        )

    def _make_stage_png_diff_image(self, current_image: QImage, png_image: QImage) -> QImage:
        tw = c.TILE_WIDTH
        out_w = (c.LEVEL_W + 1) * tw
        out_h = (c.LEVEL_H + 1) * tw
        result = QImage(out_w, out_h, QImage.Format_ARGB32)
        result.fill(QColor(0, 0, 0))
        png_offset = self._stage_png_cell_offset(png_image)
        current_offset = self._stage_png_cell_offset(current_image)
        painter = QPainter(result)
        try:
            for y in range(c.LEVEL_H):
                for x in range(c.LEVEL_W):
                    sx_png = (x + png_offset) * tw
                    sy_png = y * tw
                    sx_cur = (x + current_offset) * tw
                    sy_cur = y * tw
                    if (
                        sx_png + tw > png_image.width()
                        or sy_png + tw > png_image.height()
                        or sx_cur + tw > current_image.width()
                        or sy_cur + tw > current_image.height()
                    ):
                        continue
                    if self._image_cells_equal(current_image, sx_cur, sy_cur, png_image, sx_png, sy_png):
                        continue
                    painter.drawImage((x + 1) * tw, y * tw, png_image, sx_png, sy_png, tw, tw)
        finally:
            painter.end()
        return result

    def _stage_compare_edit_gap(self) -> int:
        return 12

    def _make_stage_png_edit_reference_image(self, current_image: QImage, png_image: QImage) -> QImage:
        gap = self._stage_compare_edit_gap()
        if self._stage_compare_edit_orientation == "vertical":
            out_w = max(current_image.width(), png_image.width())
            out_h = current_image.height() + gap + png_image.height()
        else:
            out_w = current_image.width() + gap + png_image.width()
            out_h = max(current_image.height(), png_image.height())
        result = QImage(out_w, out_h, QImage.Format_ARGB32)
        result.fill(QColor(0, 0, 0))
        painter = QPainter(result)
        try:
            painter.drawImage(0, 0, current_image)
            if self._stage_compare_edit_orientation == "vertical":
                painter.drawImage(0, current_image.height() + gap, png_image)
            else:
                painter.drawImage(current_image.width() + gap, 0, png_image)
        finally:
            painter.end()
        return result

    def _stage_compare_canvas_image(self, current_image: QImage) -> QImage:
        if self._is_stage_compare_edit_view():
            self._stage_compare_diff_cells = self._stage_image_cell_difference_positions(
                current_image,
                self._stage_compare_png_image,
            )
            self._stage_compare_diff_count = len(self._stage_compare_diff_cells)
            self._stage_compare_edit_current_size = (
                current_image.width(),
                current_image.height(),
            )
            return self._make_stage_png_edit_reference_image(
                current_image,
                self._stage_compare_png_image,
            )
        self._stage_compare_edit_current_size = None
        self._stage_compare_diff_count = None
        self._stage_compare_diff_cells = []
        return current_image

    def _stage_compare_reference_tile_rect(self, tile):
        if not self._is_stage_compare_edit_view() or tile is None:
            return None
        if self._stage_compare_png_image is None or self._stage_compare_edit_current_size is None:
            return None
        x, y = tile
        if not (0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H):
            return None
        tw = c.TILE_WIDTH
        current_w, current_h = self._stage_compare_edit_current_size
        png_offset = self._stage_png_cell_offset(self._stage_compare_png_image)
        if self._stage_compare_edit_orientation == "vertical":
            sx = (x + png_offset) * tw
            sy = current_h + self._stage_compare_edit_gap() + y * tw
        else:
            sx = current_w + self._stage_compare_edit_gap() + (x + png_offset) * tw
            sy = y * tw
        if (
            sx < 0
            or sy < 0
            or sx + tw > self.level_view.scene().sceneRect().right() + 1
            or sy + tw > self.level_view.scene().sceneRect().bottom() + 1
        ):
            return None
        return (sx, sy, tw, tw)

    def _stage_compare_reference_hover_rect(self):
        return self._stage_compare_reference_tile_rect(self._hover_tile)

    def _stage_compare_reference_diff_rects(self):
        if not self._is_stage_compare_edit_view() or not self._stage_compare_diff_cells:
            return []
        rects = []
        for tile in self._stage_compare_diff_cells:
            rect = self._stage_compare_reference_tile_rect(tile)
            if rect is not None:
                rects.append(rect)
        return rects

    def start_stage_compare_edit_from_png(self, png_path: str):
        if not self.levels:
            return
        keep_orientation = (
            self._stage_compare_edit_orientation
            if self._is_stage_compare_edit_view()
            else "horizontal"
        )
        png_image = QImage(png_path)
        if png_image.isNull():
            QMessageBox.warning(self, "比較編集", "PNG画像の読み込みに失敗しました")
            return
        self._start_stage_compare_edit(png_image, png_path, keep_orientation)

    def start_stage_compare_edit_from_snapshot(self):
        if not self.levels:
            return
        try:
            snapshot_path = self._write_compare_edit_snapshot_png()
        except Exception as exc:
            QMessageBox.warning(
                self,
                "比較編集",
                f"比較編集用スナップショットを保存できませんでした。\n{type(exc).__name__}: {exc}",
            )
            return
        self.start_stage_compare_edit_from_png(str(snapshot_path))

    def _compare_edit_snapshot_dir(self) -> Path:
        return Path(__file__).parent.parent.parent / "autosave" / "compare_snapshots"

    def _write_compare_edit_snapshot_png(self) -> Path:
        from datetime import datetime
        out_dir = self._compare_edit_snapshot_dir()
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stage_no = self.current_level_no + 1
        path = out_dir / f"compare_snapshot_stage{stage_no:02d}_{stamp}.png"
        level = self.levels[self.current_level_no]
        image = self._render_current_stage_for_compare_edit_base()
        self._sync_enemy_codes_from_rom(self.current_level_no)
        self._save_png_with_xml(image, level, path, level_no=self.current_level_no)
        return path

    def _start_stage_compare_edit(self, reference_image: QImage, reference_label: str,
                                  orientation: str = "horizontal"):
        if reference_image.isNull():
            return
        self._stage_compare_png_image = reference_image
        self._stage_compare_png_level = None
        self._stage_compare_diff_image = None
        self._stage_compare_level_no = self.current_level_no
        self._stage_compare_path = reference_label
        self._stage_compare_show_diff = False
        self._stage_compare_edit_mode = True
        self._stage_compare_diff_cells = []
        self._stage_compare_edit_orientation = (
            "vertical" if orientation == "vertical" else "horizontal"
        )
        self._set_stage_compare_controls_visible(True)
        self._update_stage_compare_edit_label()
        self._refresh_view()
        self.statusBar().showMessage(
            f"比較しながら編集: L{self.current_level_no + 1} と {self._stage_compare_label_text()}",
            5000,
        )

    def _stage_compare_label_text(self) -> str:
        path = str(self._stage_compare_path or "")
        if not path:
            return ""
        try:
            p = Path(path)
            if p.name and p.name != ".":
                return p.name
        except Exception:
            pass
        return path

    def _update_stage_compare_edit_label(self):
        if not hasattr(self, "lbl_stage_compare_mode"):
            return
        direction = "縦" if self._stage_compare_edit_orientation == "vertical" else "横"
        full_text = f"比較編集({direction}): {self._stage_compare_label_text()}"
        max_width = max(40, self.lbl_stage_compare_mode.width() - 6)
        display_text = self.lbl_stage_compare_mode.fontMetrics().elidedText(
            full_text,
            Qt.ElideMiddle,
            max_width,
        )
        self.lbl_stage_compare_mode.setText(display_text)
        self.lbl_stage_compare_mode.setToolTip(full_text)

    def _toggle_stage_compare_edit_orientation(self):
        if not self._is_stage_compare_edit_view():
            return
        self._stage_compare_edit_orientation = (
            "vertical"
            if self._stage_compare_edit_orientation == "horizontal"
            else "horizontal"
        )
        self._update_stage_compare_edit_label()
        self._refresh_view()

    def _on_stage_compare_png(self):
        if not self.levels:
            return
        from .file_dialog_compat import get_file
        path = get_file(self, title="比較するステージPNGを選択", filter="*.png")
        if not path:
            return
        try:
            png_level, _root = self._read_stage_png_level(path)
            png_image = QImage(path)
            if png_image.isNull():
                raise ValueError("PNG画像の読み込みに失敗しました")
            current_image = self._render_current_stage_for_png_compare()
            diff_image = self._make_stage_png_diff_image(current_image, png_image)
            self._stage_compare_png_image = png_image
            self._stage_compare_png_level = png_level
            self._stage_compare_diff_image = diff_image
            self._stage_compare_level_no = self.current_level_no
            self._stage_compare_path = path
            self._set_stage_compare_controls_visible(True)
            self._set_stage_compare_view(True)
            self.statusBar().showMessage(
                f"PNG比較: L{self.current_level_no + 1} と {Path(path).name}", 5000
            )
        except Exception as e:
            QMessageBox.warning(self, "比較失敗", str(e))

    @staticmethod
    def _extract_xml_from_png(png_path: str) -> str:
        """PNGファイルからmsc_level iTXtチャンクのXMLを抽出"""
        import struct
        with open(png_path, "rb") as f:
            data = f.read()
        if len(data) < 8 or data[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        pos = 8  # PNGシグネチャの後
        while pos + 12 <= len(data):
            length = struct.unpack(">I", data[pos:pos + 4])[0]
            chunk_type = data[pos + 4:pos + 8]
            if pos + 12 + length > len(data):
                return None
            if chunk_type == b"iTXt":
                payload = data[pos + 8:pos + 8 + length]
                try:
                    null_idx = payload.index(0)
                except ValueError:
                    pos += 12 + length
                    continue
                keyword = payload[:null_idx]
                if keyword == b"msc_level":
                    # keyword\0 + compression_flag + compression_method + lang\0 + translated\0 + text
                    text_pos = null_idx + 1 + 2  # skip flag + method
                    try:
                        text_pos = payload.index(0, text_pos) + 1  # skip lang
                        text_pos = payload.index(0, text_pos) + 1  # skip translated
                    except ValueError:
                        return None
                    try:
                        return payload[text_pos:].decode("utf-8")
                    except UnicodeDecodeError:
                        return None
            pos += 12 + length
            if chunk_type == b"IEND":
                break
        return None

    def _load_stage_png_to_current(self, path: str) -> bool:
        if not self.levels:
            return False
        if self._reject_read_only_edit():
            return False
        xml_str = self._extract_xml_from_png(path)
        if xml_str is None:
            QMessageBox.warning(self, "読込失敗", "このPNGにはステージデータが埋め込まれていません")
            return False
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml_str)
        if root.tag != "solomon_customizer":
            QMessageBox.warning(self, "読込失敗", "このPNGはSOLOMON_CUSTOMIZERのステージPNGではありません")
            return False
        lv = self._xml_element_to_level_compat(root)
        if lv is None:
            QMessageBox.warning(self, "読込失敗", "ステージデータの解析に失敗しました")
            return False
        self._push_undo()
        self.levels[self.current_level_no] = lv
        self._apply_stage_level_meta_positions_from_xml(root, self.current_level_no)
        self._apply_stage_conditional_breakable_positions_from_xml(root, self.current_level_no)
        self._apply_stage_bomb_jack_positions_from_xml(root, self.current_level_no)
        self._write_mirror_data_to_rom(self.current_level_no)
        self._sync_mirror_panel()
        self._refresh_view()
        self._refresh_thumbnail(self.current_level_no)
        self._set_dirty(True)
        self.statusBar().showMessage(
            f"ステージデータ読込: L{self.current_level_no + 1} に上書き ({Path(path).name})", 5000
        )
        self._log(f"PNG読込(現在L{self.current_level_no + 1}): {path}")
        return True

    def _on_stage_png_dropped(self, path: str):
        if self._is_stage_compare_edit_view():
            self.start_stage_compare_edit_from_png(path)
            return
        try:
            self._load_stage_png_to_current(path)
        except Exception as e:
            QMessageBox.critical(self, "読込失敗", f"{type(e).__name__}: {e}")

    def _on_png_import_current(self):
        if not self.levels:
            return
        if self._reject_read_only_edit():
            return
        from .file_dialog_compat import get_file
        path = get_file(self, title="ステージデータPNGを選択", filter="*.png")
        if not path:
            return
        try:
            self._load_stage_png_to_current(path)
        except Exception as e:
            QMessageBox.critical(self, "読込失敗", f"{type(e).__name__}: {e}")

    def _on_png_import_all(self):
        if not self.levels:
            return
        if self._reject_read_only_edit():
            return
        from .file_dialog_compat import get_folder
        folder = get_folder(self, title="ステージデータPNGフォルダを選択")
        if not folder:
            return
        in_dir = Path(folder)
        loaded_count = 0
        try:
            for i in range(len(self.levels)):
                path = in_dir / f"level_{i + 1:02d}.png"
                if not path.exists():
                    continue
                xml_str = self._extract_xml_from_png(str(path))
                if xml_str is None:
                    continue
                import xml.etree.ElementTree as ET
                root = ET.fromstring(xml_str)
                lv = self._xml_element_to_level_compat(root)
                if lv is not None:
                    self.levels[i] = lv
                    self._apply_stage_level_meta_positions_from_xml(root, i)
                    self._apply_stage_conditional_breakable_positions_from_xml(root, i)
                    self._apply_stage_bomb_jack_positions_from_xml(root, i)
                    self._write_mirror_data_to_rom(i)
                    loaded_count += 1
            self._sync_mirror_panel()
            self._refresh_view()
            if loaded_count > 0:
                self._generate_all_thumbnails()
                self._set_dirty(True)
            self._clear_undo_history()
            QMessageBox.information(
                self, "完了",
                f"{loaded_count}/{len(self.levels)} ステージをPNGから読み込みました"
            )
            self._log(f"PNG読込(全): {loaded_count}/{len(self.levels)} from {in_dir}")
        except Exception as e:
            QMessageBox.critical(self, "読込失敗", f"{type(e).__name__}: {e}")

    @staticmethod
    def _xml_element_to_level_compat(root):
        """solomon_customizer / skchain 両方のルート要素に対応"""
        from ..core.xml_io import xml_element_to_level
        level_elem = root.find("level")
        if level_elem is not None:
            return xml_element_to_level(level_elem)
        return None

    # ====== Stage copy / paste / swap ======

    @staticmethod
    def _stage_label(level_no: int) -> str:
        return f"L{level_no + 1:02d}"

    def _sync_stage_sidecar_to_level(self, level_no: int):
        if 0 <= level_no < len(self.levels):
            self._sync_enemy_codes_from_rom(level_no)

    def _refresh_changed_stages(self, level_nos):
        changed = sorted({ln for ln in level_nos if 0 <= ln < len(self.levels)})
        for level_no in changed:
            self._write_mirror_data_to_rom(level_no)
            self._refresh_thumbnail(level_no)
        self._sync_mirror_panel()
        self._refresh_view()
        self._update_stage_operation_buttons()

    def _highlight_stage_items_for_confirmation(self, level_nos):
        rows = sorted({ln for ln in level_nos if 0 <= ln < self.list_levels.count()})
        previous = {}
        for row in rows:
            item = self.list_levels.item(row)
            if item is None:
                continue
            previous[row] = item.data(Qt.BackgroundRole)
            item.setData(Qt.BackgroundRole, QColor("#facc15"))
        self.list_levels.viewport().update()
        QApplication.processEvents()

        def restore():
            for row, background in previous.items():
                item = self.list_levels.item(row)
                if item is not None:
                    item.setData(Qt.BackgroundRole, background)
            self.list_levels.viewport().update()

        return restore

    def _on_stage_copy(self):
        if not self.levels:
            return
        if self._reject_read_only_edit():
            return
        source_no = self.current_level_no
        self._sync_stage_sidecar_to_level(source_no)
        self._stage_clipboard = {
            "source_level_no": source_no,
            "level": copy.deepcopy(self.levels[source_no]),
        }
        self._update_stage_operation_buttons()
        self.statusBar().showMessage(
            f"{self._stage_label(source_no)} をコピーしました", 3000
        )
        self._log(f"ステージコピー: {self._stage_label(source_no)}")

    def _on_stage_paste(self):
        if not self.levels or self._stage_clipboard is None:
            return
        if self._reject_read_only_edit():
            return
        target_no = self.current_level_no
        source_no = int(self._stage_clipboard["source_level_no"])
        restore_highlight = self._highlight_stage_items_for_confirmation([source_no, target_no])
        try:
            reply = QMessageBox.question(
                self,
                "ステージ貼り付け",
                f"{self._stage_label(source_no)} のデータを "
                f"{self._stage_label(target_no)} へ貼り付けます。\n\n"
                f"{self._stage_label(target_no)} の現在の内容は上書きされます。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
        finally:
            restore_highlight()
        if reply != QMessageBox.Yes:
            return
        self._sync_stage_sidecar_to_level(target_no)
        self._push_undo_levels([target_no], focus_level_no=target_no)
        self.levels[target_no] = copy.deepcopy(self._stage_clipboard["level"])
        self._refresh_changed_stages([target_no])
        self.statusBar().showMessage(
            f"{self._stage_label(source_no)} を {self._stage_label(target_no)} へ貼り付けました",
            4000,
        )
        self._log(
            f"ステージ貼り付け: {self._stage_label(source_no)} -> {self._stage_label(target_no)}"
        )

    def _on_stage_swap(self):
        if not self.levels:
            return
        if self._reject_read_only_edit():
            return
        if self._stage_swap_source_no is None:
            self._begin_stage_swap(self.current_level_no)
            return

        source_no = self._stage_swap_source_no
        target_no = self.spin_stage_swap_target.value() - 1
        if target_no == source_no:
            self.statusBar().showMessage("同じステージは入れ替え不要です", 2500)
            self.spin_stage_swap_target.setFocus()
            self.spin_stage_swap_target.selectAll()
            return
        restore_highlight = self._highlight_stage_items_for_confirmation([source_no, target_no])
        try:
            reply = QMessageBox.question(
                self,
                "ステージ入れ替え",
                f"{self._stage_label(source_no)} と {self._stage_label(target_no)} の"
                "データ一式を入れ替えます。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
        finally:
            restore_highlight()
        if reply != QMessageBox.Yes:
            return
        self._swap_stages(source_no, target_no)
        self._finish_stage_swap()

    def _begin_stage_swap(self, source_no: int):
        self._stage_swap_source_no = source_no
        default_no = source_no + 2 if source_no + 1 < len(self.levels) else source_no
        self.spin_stage_swap_target.blockSignals(True)
        self.spin_stage_swap_target.setRange(1, len(self.levels))
        self.spin_stage_swap_target.setValue(default_no)
        self.spin_stage_swap_target.blockSignals(False)
        self.spin_stage_swap_target.setVisible(True)
        self.spin_stage_swap_target.setFocus()
        self.spin_stage_swap_target.selectAll()
        self.btn_stage_swap.setText("入替実行")
        self._update_stage_operation_buttons()

    def _finish_stage_swap(self):
        self._stage_swap_source_no = None
        self.spin_stage_swap_target.setVisible(False)
        self.btn_stage_swap.setText("面入れ替え")
        self._update_stage_operation_buttons()

    def _set_stage_swap_target_from_thumbnail(self, level_no: int):
        if self._stage_swap_source_no is None:
            return
        self.spin_stage_swap_target.setValue(level_no + 1)

    def _on_level_context_menu(self, pos):
        if not self.levels:
            return
        item = self.list_levels.itemAt(pos)
        if item is None:
            return
        row = self.list_levels.row(item)
        if not (0 <= row < len(self.levels)):
            return

        if row >= 0:
            self._set_stage_swap_target_from_thumbnail(row)
        if row != self.current_level_no:
            self.list_levels.setCurrentRow(row)

        from PyQt5.QtWidgets import QMenu
        menu = QMenu(self)
        copy_action = menu.addAction("面コピー")
        paste_action = menu.addAction("貼り付け")
        swap_action = menu.addAction(self.btn_stage_swap.text())

        can_edit = not self._is_read_only()
        copy_action.setEnabled(can_edit)
        paste_action.setEnabled(can_edit and self._stage_clipboard is not None)
        swap_action.setEnabled(can_edit)

        action = menu.exec_(self.list_levels.viewport().mapToGlobal(pos))
        if action == copy_action:
            self._on_stage_copy()
        elif action == paste_action:
            self._on_stage_paste()
        elif action == swap_action:
            self._on_stage_swap()

    def _swap_stages(self, current_no: int, target_no: int):
        self._sync_stage_sidecar_to_level(current_no)
        self._sync_stage_sidecar_to_level(target_no)
        self._push_undo_levels([current_no, target_no], focus_level_no=current_no)
        self.levels[current_no], self.levels[target_no] = (
            self.levels[target_no],
            self.levels[current_no],
        )
        self._refresh_changed_stages([current_no, target_no])
        self.statusBar().showMessage(
            f"{self._stage_label(current_no)} と {self._stage_label(target_no)} を入れ替えました",
            4000,
        )
        self._log(
            f"ステージ入れ替え: {self._stage_label(current_no)} <-> {self._stage_label(target_no)}"
        )

    # ====== Level navigation ======

    def _change_stage_relative(self, delta: int, play_sound: bool = False):
        if not self.levels:
            return
        max_stage = min(c.LEVEL_COUNT, len(self.levels))
        current = self.spin_level.value()
        target = max(1, min(max_stage, current + int(delta)))
        if target != current:
            if play_sound:
                self._play_button_sound()
            self.spin_level.setValue(target)

    def _on_level_changed(self, value: int):
        new_no = value - 1
        if new_no == self.current_level_no:
            return
        self._clear_stage_compare(refresh=False)
        # 離れる側のサムネを最新化
        self._refresh_thumbnail(self.current_level_no)
        self.current_level_no = new_no
        self.list_levels.blockSignals(True)
        self.list_levels.setCurrentRow(self.current_level_no)
        self.list_levels.blockSignals(False)
        self._refresh_view()

    def _on_list_changed(self, row: int):
        if row >= 0:
            self._set_stage_swap_target_from_thumbnail(row)
        if row < 0 or row == self.current_level_no:
            return
        self._clear_stage_compare(refresh=False)
        # 離れる側のサムネを最新化
        self._refresh_thumbnail(self.current_level_no)
        self.spin_level.blockSignals(True)
        self.spin_level.setValue(row + 1)
        self.spin_level.blockSignals(False)
        self.current_level_no = row
        self._refresh_view()

    def _on_grid_toggled(self, checked: bool):
        self.show_grid = checked
        self._refresh_view()

    def _on_object_labels_toggled(self, checked: bool):
        self.show_object_labels = checked
        self._refresh_view()

    def _on_stage_selector_toggled(self, checked: bool):
        self._apply_stage_selector_visibility(checked, resize_splitter=True)
        self._app_config["stage_selector_visible"] = bool(checked)
        self._app_config["stage_selector_last_width"] = int(self._stage_selector_last_width)
        from ..core.config import save_config
        save_config(self._app_config)

    def _apply_stage_selector_visibility(self, visible: bool, resize_splitter: bool = True):
        if not hasattr(self, "levelselect_widget"):
            return
        sizes = self.splitter.sizes() if hasattr(self, "splitter") else []
        if len(sizes) == 4 and sizes[3] > 30:
            self._stage_selector_last_width = sizes[3]
        self.levelselect_widget.setVisible(bool(visible))
        if not resize_splitter or len(sizes) != 4:
            return
        new_sizes = list(sizes)
        if visible:
            restored = max(int(getattr(self, "_stage_selector_last_width", 220)), 160)
            take = min(restored, max(0, new_sizes[1] - 320))
            if take > 0:
                new_sizes[1] -= take
            new_sizes[3] = restored
        else:
            freed = new_sizes[3] if new_sizes[3] > 0 else int(getattr(self, "_stage_selector_last_width", 220))
            if freed > 30:
                self._stage_selector_last_width = freed
            new_sizes[1] += freed
            new_sizes[3] = 0
        self.splitter.setSizes(new_sizes)

    def _sync_object_labels(self):
        if self._is_stage_compare_diff_view():
            self.level_view.set_object_labels([])
            return
        if not getattr(self, "show_object_labels", False):
            self.level_view.set_object_labels([])
            return
        if not self.levels or self.level_renderer is None:
            self.level_view.set_object_labels([])
            return
        level = self.levels[self.current_level_no]
        labels = self.level_renderer.object_labels(
            level,
            level_no=self.current_level_no,
            bonus_items=self._get_bonus_items(),
        )
        self.level_view.set_object_labels(labels, with_border=True)

    def _refresh_view(self):
        if not self.levels or self.level_renderer is None:
            self.level_view.set_top_viewport_padding(0)
            self._stage_compare_diff_count = None
            self._update_stage_compare_diff_label()
            self._update_enemy_count_indicator()
            self._update_stage_number_label()
            return
        if not (0 <= self.current_level_no < len(self.levels)):
            self.level_view.set_top_viewport_padding(0)
            self._stage_compare_diff_count = None
            self._update_stage_compare_diff_label()
            self._update_enemy_count_indicator()
            self._update_stage_number_label()
            return
        level = self.levels[self.current_level_no]
        if (
            self._stage_compare_png_image is not None
            and self._stage_compare_level_no == self.current_level_no
            and not self._stage_compare_edit_mode
        ):
            self._stage_compare_diff_image = self._make_stage_png_diff_image(
                self._render_current_stage_for_png_compare(),
                self._stage_compare_png_image,
            )
        # ピッカーのアイコンを現在レベルのタイルセットで再描画（skchain互換）
        ts_no = self.level_renderer.get_actual_tileset_no(self.current_level_no, level.tileset_no)
        self.picker.set_current_level_context(
            self.current_level_no,
            ts_no,
            self.level_renderer.get_wall_color(self.current_level_no),
        )
        # 特殊処理マーカーを抽出（表示ONかつ ROM対応リージョンの場合のみ）
        sp_marks = self._get_special_marks()
        if self._is_stage_compare_diff_view():
            img = self._stage_compare_diff_image
        else:
            current_img = self._render_current_stage_for_compare_edit_base()
            img = self._stage_compare_canvas_image(current_img)
        if self._is_stage_compare_edit_view():
            self.level_view.set_tile_offset_override((1, 0))
        else:
            self.level_view.set_tile_offset_override(None)
        self.level_view.set_top_viewport_padding(self._level_view_top_overlay_padding())
        self.level_view.set_image(img)
        self.picker.set_marker_source_tile_size(self.level_view.display_tile_size())
        if self._is_stage_compare_diff_view():
            self.level_view.set_editor_overlays({}, with_border=True)
        else:
            self.level_view.set_editor_overlays(
                self._build_editor_overlays(level, sp_marks),
                with_border=True,
            )
        self._update_enemy_count_indicator()
        self._update_stage_number_label()
        self._update_stage_compare_diff_label()
        self._sync_object_labels()
        self._update_info()
        self._load_meta_to_ui()
        # タイルセット変更でアイコン色が変わるのでカーソルも更新
        self._update_cursor_from_picker()
        # ボーナス編集ボタン: Level 51 (index 50) のときだけ有効
        is_bonus = self.current_level_no == 50 and self.rom is not None
        # ピッカー下部: Level 51ならボーナスパネル、それ以外はお気に入り
        if is_bonus:
            self._sync_bonus_panel()
        else:
            self.picker.set_bonus_mode(False)
        # ミラー敵セットパネル更新
        self._sync_mirror_panel()

    def _get_special_marks(self, level_no=None):
        """特殊処理マーカーを抽出して返す（チェックOFFや未対応リージョンなら None）"""
        if not getattr(self, "chk_special_marks", None) or not self.chk_special_marks.isChecked():
            return None
        if not self.rom:
            return None
        target_level_no = self.current_level_no if level_no is None else level_no
        marks = {}
        try:
            from ..core import special_process as sp
            region = self.rom.base_region()
            marks = sp.find_marks_for_level(
                bytes(self.rom.data), region, target_level_no
            )
        except Exception:
            marks = {}
        return marks or None

    def _build_editor_overlays(self, level, special_marks=None):
        invisible_breakable_cells = set(getattr(level, "invisible_breakable_cells", set()))
        visible_in_block_cells = set(getattr(level, "visible_in_block_item_cells", set()))
        seal_visible_in_block_cells = set()
        if self.config is not None:
            for mi in getattr(self.config, "level_meta_items", []) or []:
                if int(getattr(mi, "level_no", -1)) != self.current_level_no:
                    continue
                if self._stage_level_meta_kind(int(getattr(mi, "no", -1))) != "solomon_seal":
                    continue
                pos = tuple(getattr(mi, "position", (-1, -1)))
                if pos in invisible_breakable_cells:
                    seal_visible_in_block_cells.add(pos)
        invisible_breakable_cells.difference_update(seal_visible_in_block_cells)
        visible_in_block_cells.update(seal_visible_in_block_cells)
        overlays = {
            "breakable_white": list(getattr(level, "breakable_white_cells", set())),
            "invisible_breakable": list(invisible_breakable_cells),
            "passable_white": list(getattr(level, "passable_white_cells", set())),
            "passable_brown": list(getattr(level, "passable_brown_cells", set())),
            "solid_brown": list(getattr(level, "solid_brown_cells", set())),
            "invisible_solid": list(getattr(level, "invisible_solid_cells", set())),
            "visible_in_block_item": list(visible_in_block_cells),
            "hidden_item": [],
            "hidden_meta": [],
            "mirrors": [],
            "bonus": [],
            "special_marks": special_marks,
            "selection_rect": self._selection_rect,
            "hover_tile": self._hover_tile,
            "compare_reference_diff_rects": self._stage_compare_reference_diff_rects(),
            "compare_reference_hover_rect": self._stage_compare_reference_hover_rect(),
        }

        if self.chk_hidden.isChecked():
            overlays["hidden_item"] = [
                item.position for item in level.items
                if item.is_hidden() or item.is_in_block()
            ]
            for mi in getattr(self.config, "level_meta_items", []):
                if mi.level_no != self.current_level_no:
                    continue
                pos = tuple(mi.position)
                mx, my = pos
                if not (0 <= mx < c.LEVEL_W and 0 <= my < c.LEVEL_H):
                    continue
                in_block = (
                    level.tiles[my][mx] == Wall.BROWN
                    or (
                        level.tiles[my][mx] == Wall.WHITE
                        and pos in getattr(level, "breakable_white_cells", set())
                    )
                    or pos in seal_visible_in_block_cells
                    or pos in invisible_breakable_cells
                )
                if (in_block or mi.transparent) and pos not in seal_visible_in_block_cells:
                    overlays["hidden_meta"].append(pos)

        item_positions = {item.position for item in level.items}
        for mi, mirror in enumerate(level.demon_mirrors):
            mx, my = mirror.position
            if not (0 <= mx < c.LEVEL_W and 0 <= my < c.LEVEL_H):
                continue
            if level.tiles[my][mx] != Wall.NONE or (mx, my) in item_positions:
                continue
            overlays["mirrors"].append((mi, mirror.position))

        if self.current_level_no == 50:
            overlays["bonus"] = [
                bpos for bpos, _bitem_no in self._get_bonus_items()
            ]

        return overlays

    def _on_picker_selection_changed(self, mode, value):
        """ピッカー選択変更時 → カーソル形状を選択中アイコンに"""
        self._update_cursor_from_picker()

    def _update_cursor_from_picker(self):
        """ピッカーで選択中のアイコンを LevelView のカーソル形状に設定"""
        icon_provider = getattr(self.picker, "current_icon", None)
        icon = icon_provider() if callable(icon_provider) else None
        if icon.isNull():
            self.level_view.unsetCursor()
            self.level_view.viewport().unsetCursor()
            self._picker_canvas_cursor = None
            self._clear_picker_override_cursor()
            return
        # 32x32 のカーソル（小さすぎず大きすぎず）
        pixmap = icon.pixmap(32, 32)
        if pixmap.isNull():
            self.level_view.unsetCursor()
            self.level_view.viewport().unsetCursor()
            self._picker_canvas_cursor = None
            self._clear_picker_override_cursor()
            return
        # ホットスポットは中央
        cursor = QCursor(pixmap, 16, 16)
        self.level_view.setCursor(cursor)
        self.level_view.viewport().setCursor(cursor)
        self._set_picker_override_cursor(cursor)

    def _on_tile_hovered(self, tile):
        """ホバー位置変化時の処理 - 軽量再描画 + ステータスバー更新"""
        if self._hover_tile == tile:
            return
        self._hover_tile = tile
        # 描画だけ更新（_update_info は呼ばない）
        if self.levels and self.level_renderer is not None:
            level = self.levels[self.current_level_no]
            img = self._render_current_stage_for_compare_edit_base()
            self.level_view.set_top_viewport_padding(self._level_view_top_overlay_padding())
            self.level_view.set_image(self._stage_compare_canvas_image(img))
            sp_marks = self._get_special_marks()
            self.level_view.set_editor_overlays(
                self._build_editor_overlays(level, sp_marks),
                with_border=True,
            )
            self._sync_object_labels()
            self._update_stage_compare_diff_label()
        # ステータスバーのホバー情報を更新
        self._update_hover_info(tile)
        self._update_hover_info_popup(tile)

    def _update_hover_info(self, tile):
        """マウス下部のタイル中身をステータスバーに表示"""
        if tile is None or not self.levels:
            self.lbl_hover_info.setText("")
            return
        x, y = tile
        lv = self.levels[self.current_level_no]
        parts = [f"({x:2d},{y:2d})"]

        # ブロック
        block_id, block_label = self._block_info_for_tile(lv, tile)
        if block_id:
            parts.append(f"Block ID {block_id}: {block_label}")
        # BROWN_WHITE は v0.1.99 で廃止 (読込時に WHITE へ正規化)

        # アイテム
        item_idx = lv.get_item_index(tile)
        if item_idx >= 0:
            it = lv.items[item_idx]
            base = it.element_no & 0x3F
            flag = it.element_no & 0xC0
            desc = self.config.item_desc.get(base, f"item 0x{base:02x}") if self.config else f"0x{base:02x}"
            tag = ""
            if tile in getattr(lv, "visible_in_block_item_cells", set()):
                tag = "[透明ブロック内]"
            elif flag == 0x40: tag = "[隠し]"
            elif flag in (0x80, 0xC0): tag = "[in_block]"
            # ★アイテム番号も表示 (base コード。flag付きは raw も併記)
            code = f"0x{base:02X}"
            if flag:
                code += f"(raw 0x{it.element_no:02X})"
            parts.append(f"アイテム:{code} {desc}{tag}")

        # 敵（複数あり得る）
        enemy_hits = [(i, e) for i, e in enumerate(lv.enemies, start=1) if e.position == tile]
        if enemy_hits:
            for enemy_no, en in enemy_hits:
                edesc = self.config.enemy_desc.get(en.element_no, f"0x{en.element_no:02x}") if self.config else f"0x{en.element_no:02x}"
                parts.append(f"敵#{enemy_no}:{edesc}")

        # メタ要素
        if lv.fixed_start_pos == tile:
            parts.append("[スタート]")
        if not lv.is_key_removed() and lv.fixed_key_pos == tile:
            key_tag = "[鍵]"
            if tile in getattr(lv, "visible_in_block_item_cells", set()):
                key_tag = "[鍵:透明ブロック内]"
            elif lv.is_key_white_in_block():
                key_tag = "[鍵:白ブロック内]"
            elif lv.is_key_in_block():
                key_tag = "[鍵:ブロック内]"
            elif lv.is_key_hidden():
                key_tag = "[鍵:隠し]"
            parts.append(key_tag)
        if not lv.is_door_removed() and lv.fixed_door_pos == tile:
            from ..core import room_flags as _rf
            door_state = lv.room_flags & _rf.DOOR_STATE_MASK
            if door_state == _rf.DOOR_STATE_WHITE_IN_BLOCK:
                parts.append("[扉:白ブロック内]")
            elif door_state == _rf.DOOR_STATE_IN_BLOCK:
                parts.append("[扉:ブロック内]")
            elif door_state == _rf.DOOR_STATE_HIDDEN:
                parts.append("[扉:隠し]")
            else:
                parts.append("[扉]")
        for i, m in enumerate(lv.demon_mirrors):
            if m.position == tile:
                parts.append(f"[ミラー{i+1}]")

        # 星座
        if lv.has_constellation() and lv.get_constellation_pos() == tile:
            from ..core.constants import CONSTELLATION_NAMES
            cn = lv.get_constellation_no()
            name, _ = CONSTELLATION_NAMES.get(cn, (f"0x{cn:02x}", 0))
            parts.append(f"[星座:{name}]")
        seal_meta = self._solomon_seal_meta_at(self.current_level_no, tile)
        if seal_meta is not None:
            parts.append("[ソロモンの紋章]")

        self.lbl_hover_info.setText(" / ".join(parts))

    def _hover_enemy_hits(self, tile):
        if tile is None or not self.levels:
            return []
        lv = self.levels[self.current_level_no]
        return [(i, e) for i, e in enumerate(lv.enemies, start=1) if e.position == tile]

    def _block_info_for_tile(self, lv, tile):
        x, y = tile
        wall = lv.tiles[y][x]
        if wall == Wall.BROWN and tile in getattr(lv, "passable_brown_cells", set()):
            return "0x01", "すり抜ける茶色ブロック"
        if wall == Wall.BROWN and tile in getattr(lv, "solid_brown_cells", set()):
            return "0x01", "壊せない茶色ブロック"
        if wall == Wall.BROWN and tile in getattr(lv, "cracked_block_cells", set()):
            return "0x01", "ひび割れブロック"
        if wall == Wall.BROWN:
            return "0x01", "茶色ブロック"
        if wall == Wall.WHITE and tile in getattr(lv, "breakable_white_cells", set()):
            return "0x02", "壊せる白ブロック"
        if wall == Wall.WHITE and tile in getattr(lv, "passable_white_cells", set()):
            return "0x02", "すり抜ける白ブロック"
        if wall == Wall.WHITE:
            return "0x02", "白ブロック"
        if wall == Wall.NONE and tile in getattr(lv, "invisible_breakable_cells", set()):
            return "0x00", "壊せる透明ブロック"
        if wall == Wall.NONE and tile in getattr(lv, "invisible_solid_cells", set()):
            return "0x00", "壊せない透明ブロック"
        if wall == Wall.BROWN_WHITE:
            return "0x03", "壊せる白ブロック"
        return None, None

    def _item_state_label(self, lv, item, tile):
        if tile in getattr(lv, "visible_in_block_item_cells", set()):
            return "透明ブロック内"
        if item.is_white_in_block():
            return "白ブロック内"
        if item.is_hidden():
            return "隠し"
        if item.is_in_block():
            return "ブロック内"
        return ""

    def _key_state_label(self, lv):
        if lv.fixed_key_pos in getattr(lv, "visible_in_block_item_cells", set()):
            return "透明ブロック内"
        if (
            lv.fixed_key_pos in getattr(lv, "cracked_block_cells", set())
            and lv.is_key_hidden()
        ):
            return "ひび割れブロック内"
        if lv.is_key_white_in_block():
            return "白ブロック内"
        if lv.is_key_in_block():
            return "ブロック内"
        if lv.is_key_hidden():
            return "隠し"
        return ""

    def _door_state_label(self, lv):
        from ..core import room_flags as _rf
        door_state = lv.room_flags & _rf.DOOR_STATE_MASK
        if door_state == _rf.DOOR_STATE_WHITE_IN_BLOCK:
            return "白ブロック内"
        if door_state == _rf.DOOR_STATE_IN_BLOCK:
            return "ブロック内"
        if door_state == _rf.DOOR_STATE_HIDDEN:
            return "隠し"
        return ""

    def _enemy_speed_info(self, code: int):
        base_code, speed = base_code_from_actual(code)
        table = ENEMY_SPEED_TABLE.get(base_code)
        if not table:
            return base_code, speed, []
        available = [
            (i + 1, int(enemy_code) & 0xFF)
            for i, enemy_code in enumerate(table)
            if enemy_code is not None
        ]
        return base_code, speed, available

    def _build_hover_info_popup_text(self, tile):
        if tile is None or not self.levels:
            return ""
        x, y = tile
        lv = self.levels[self.current_level_no]
        lines = [
            f'<div style="color:#9AE6FF; font-weight:700;">({x}, {y})</div>'
        ]

        enemy_hits = self._hover_enemy_hits(tile)
        if enemy_hits:
            for enemy_no, en in enemy_hits:
                code = int(en.element_no) & 0xFF
                desc = (
                    self.config.enemy_desc.get(code, f"0x{code:02X}")
                    if self.config else f"0x{code:02X}"
                )
                _base_code, speed, available = self._enemy_speed_info(code)
                speed_text = f"SP{speed}" if available else ""
                suffix = (
                    f' <span style="color:#FFE6A3;">{speed_text}</span>'
                    if speed_text else ""
                )
                lines.append(
                    '<div style="color:#FFD166; font-weight:700;">'
                    f'敵#{enemy_no} ID 0x{code:02X}: {escape(desc)}{suffix}'
                    "</div>"
                )

        item_idx = lv.get_item_index(tile)
        if item_idx >= 0:
            item = lv.items[item_idx]
            base = int(item.element_no) & 0x3F
            desc = (
                self.config.item_desc.get(base, f"0x{base:02X}")
                if self.config else f"0x{base:02X}"
            )
            state = self._item_state_label(lv, item, tile)
            state_suffix = (
                f' <span style="color:#BFE8FF;">[{escape(state)}]</span>'
                if state else ""
            )
            lines.append(
                '<div style="color:#7DD3FC; font-weight:700;">'
                f"Item ID 0x{base:02X}: {escape(desc)}{state_suffix}"
                "</div>"
            )

        block_id, block_label = self._block_info_for_tile(lv, tile)
        if block_id:
            lines.append(
                '<div style="color:#A7F3D0;">'
                f"Block ID {escape(block_id)}: {escape(block_label)}"
                "</div>"
            )

        meta = []
        if lv.fixed_start_pos == tile:
            meta.append("スタート")
        if not lv.is_key_removed() and lv.fixed_key_pos == tile:
            key_state = self._key_state_label(lv)
            meta.append(f"鍵 [{key_state}]" if key_state else "鍵")
        if not lv.is_door_removed() and lv.fixed_door_pos == tile:
            door_state = self._door_state_label(lv)
            meta.append(f"扉 [{door_state}]" if door_state else "扉")
        for i, mirror in enumerate(lv.demon_mirrors, start=1):
            if mirror.position == tile:
                meta.append(f"ミラー{i}")
        if meta:
            lines.append(
                '<div style="color:#C4B5FD;">'
                f"Meta {escape(', '.join(meta))}"
                "</div>"
            )
        seal_meta = self._solomon_seal_meta_at(self.current_level_no, tile)
        if seal_meta is not None:
            lines.append(
                '<div style="color:#FACC15; font-weight:700;">'
                "Solomon's Seal"
                "</div>"
            )
        return "<qt>" + "".join(lines) + "</qt>"

    def _hide_hover_info_popup(self):
        label = getattr(self, "_hover_info_popup_label", None)
        if label is not None:
            label.hide()

    def _hover_info_popup_font_size(self) -> int:
        return normalize_int_setting(
            self._app_config.get("hover_info_popup_font_size"),
            DEFAULT_HOVER_INFO_POPUP_FONT_SIZE,
            MIN_HOVER_INFO_POPUP_FONT_SIZE,
            MAX_HOVER_INFO_POPUP_FONT_SIZE,
        )

    def _apply_hover_info_popup_style(self):
        label = getattr(self, "_hover_info_popup_label", None)
        if label is None:
            return
        font_size = self._hover_info_popup_font_size()
        self._app_config["hover_info_popup_font_size"] = font_size
        label.setStyleSheet(
            "QLabel {"
            "background: #061006;"
            "border: 1px solid #4FB85A;"
            "padding: 6px 9px;"
            "font-family: Consolas, 'MS Gothic', monospace;"
            f"font-size: {font_size}px;"
            "}"
        )

    def _hover_info_popup_pos_for_tile(self, tile, label):
        rect = self.level_view.tile_view_rect(tile)
        viewport = self.level_view.viewport()
        gap = 8
        margin = 4
        max_x = max(margin, viewport.width() - label.width() - margin)
        max_y = max(margin, viewport.height() - label.height() - margin)
        if rect is None:
            return QPoint(margin, margin)

        center_y = rect.center().y() - label.height() // 2
        right_x = rect.right() + gap
        left_x = rect.left() - label.width() - gap
        if right_x <= max_x:
            x = right_x
            y = center_y
        elif left_x >= margin:
            x = left_x
            y = center_y
        else:
            center_x = rect.center().x() - label.width() // 2
            below_y = rect.bottom() + gap
            above_y = rect.top() - label.height() - gap
            x = center_x
            y = below_y if below_y <= max_y else above_y
        x = max(margin, min(x, max_x))
        y = max(margin, min(y, max_y))
        return QPoint(x, y)

    def _update_hover_info_popup(self, tile=None):
        if tile is None:
            tile = self._hover_tile
        if not self._app_config.get("hover_info_popup_enabled", False):
            self._hide_hover_info_popup()
            return
        text = self._build_hover_info_popup_text(tile)
        if not text:
            return
        label = self._hover_info_popup_label
        label.setText(text)
        label.adjustSize()
        label.move(self._hover_info_popup_pos_for_tile(tile, label))
        label.raise_()
        label.show()

    def _update_info(self):
        if not self.levels:
            return
        lv = self.levels[self.current_level_no]
        info = f"""<b>Stage {self.current_level_no + 1}</b><br>
アイテム: {len(lv.items)}個<br>
敵: {len(lv.enemies)}体<br>
ミラー1: {lv.demon_mirrors[0].position}<br>
ミラー2: {lv.demon_mirrors[1].position}<br>
"""
        self.lbl_info.setText(info)

    # ====== Edit operations ======

    def _on_tile_clicked(self, button: int, tile: tuple, modifiers: int):
        """左クリック: 選択中の要素を配置（Ctrl+左ドラッグは drag_* シグナル側で処理）"""
        if not self.levels:
            return
        if self._is_stage_compare_diff_view():
            self.statusBar().showMessage("差分表示中は編集できません。「現在」に戻すと編集できます", 2500)
            return
        if self._reject_read_only_edit():
            return
        # 16列目の編集ロック
        if not self.chk_edit_col15.isChecked() and tile[0] == 15:
            self.statusBar().showMessage("16列目は編集不可です（「16列目を編集」をONにしてください）", 2000)
            return
        lv = self.levels[self.current_level_no]

        undo_stack_before = list(self._undo_stack)
        redo_stack_before = list(self._redo_stack)
        dirty_before_undo = self._dirty

        def restore_rejected_click_edit():
            self._undo_stack = undo_stack_before
            self._redo_stack = redo_stack_before
            self._set_dirty(dirty_before_undo)

        self._push_undo()

        mode, value = self.picker.get_current()

        if mode == MODE_BLOCK:
            passable_block_values = (BLOCK_NONE, BLOCK_PASSABLE_WHITE, BLOCK_PASSABLE_BROWN)
            in_block_absorb_values = (BLOCK_BROWN, BLOCK_BROWN_WHITE, BLOCK_BREAKABLE_WHITE)
            seal_meta = self._solomon_seal_meta_at(self.current_level_no, tile)
            if seal_meta is not None and value not in (
                BLOCK_NONE,
                BLOCK_BROWN,
                BLOCK_BREAKABLE_WHITE,
                BLOCK_INVISIBLE_BREAKABLE,
            ):
                self.statusBar().showMessage(
                    f"ソロモンの紋章位置に置けるブロックは茶色/壊せる白/透明壊せるのみです {tile}",
                    3000,
                )
                restore_rejected_click_edit()
                return
            # 敵と同位置にブロックは置けない
            if value not in passable_block_values and lv.get_enemy_index(tile) >= 0:
                self.statusBar().showMessage(
                    f"敵がいる位置にはブロックを置けません {tile}", 2500
                )
                restore_rejected_click_edit()
                return

            # スタート位置にブロックは置けない（主人公が埋まる）
            if value not in passable_block_values and lv.fixed_start_pos == tile:
                self.statusBar().showMessage(
                    f"スタート位置にブロックは置けません {tile}", 2500
                )
                restore_rejected_click_edit()
                return

            # 扉位置に通常ブロックは置けない。茶/壊せる白は特殊扉状態へ吸収する。
            if (value != BLOCK_NONE and
                    value not in in_block_absorb_values and
                    not lv.is_door_removed() and lv.fixed_door_pos == tile):
                self.statusBar().showMessage(
                    f"扉位置にブロックは置けません {tile}", 2500
                )
                restore_rejected_click_edit()
                return

            # 白ブロック（壊せない）にアイテムが既にあると、そのアイテムは取れなくなるので拒否
            if value in (
                BLOCK_WHITE, BLOCK_PASSABLE_WHITE,
                BLOCK_PASSABLE_BROWN, BLOCK_SOLID_BROWN,
            ) and lv.get_item_index(tile) >= 0:
                self.statusBar().showMessage(
                    f"アイテムがある位置に特殊壁は置けません（取れなくなる） {tile}", 3000
                )
                restore_rejected_click_edit()
                return

            protected_open_door_idx = lv.get_item_index(tile)
            if (
                protected_open_door_idx >= 0
                and self._is_protected_open_door_item(lv, lv.items[protected_open_door_idx])
                and value != BLOCK_NONE
            ):
                self.statusBar().showMessage(
                    self._protected_open_door_message(lv, action="block"),
                    3500,
                )
                restore_rejected_click_edit()
                return

            # ブロック（茶 / ひび割れ / 壊せる白 / 透明壊せる）+ メタ/アイテム → 状態へ吸収
            skip_block_placement = False
            if value in (BLOCK_BROWN, BLOCK_BROWN_WHITE):
                if not lv.is_key_removed() and lv.fixed_key_pos == tile:
                    from ..core import constants as cc
                    lv.key_status = cc.KEY_STATUS_IN_BLOCK
                    lv.visible_in_block_item_cells.discard(tile)
                    lv.set_block(Wall.NONE, tile)
                    skip_block_placement = True
                    self.statusBar().showMessage(
                        f"鍵をブロック内状態に自動変換 {tile}", 2500
                    )
                elif not lv.is_door_removed() and lv.fixed_door_pos == tile:
                    from ..core import room_flags as _rf
                    lv.room_flags = (
                        lv.room_flags & ~_rf.DOOR_STATE_MASK
                    ) | _rf.DOOR_STATE_IN_BLOCK
                    lv.set_block(Wall.NONE, tile)
                    skip_block_placement = True
                    self.statusBar().showMessage(
                        f"扉をブロック内状態に自動変換 {tile}", 2500
                    )
                else:
                    idx = lv.get_item_index(tile)
                    if idx >= 0:
                        item = lv.items[idx]
                        base = item.element_no & 0x3F
                        item.element_no = base | c.ITEM_FLAG_IN_BLOCK
                        lv.visible_in_block_item_cells.discard(tile)
                        lv.set_block(Wall.NONE, tile)
                        skip_block_placement = True
                        self.statusBar().showMessage(
                            f"アイテムを in_block フラグ付きに自動変換 {tile}", 2500
                        )
            elif value == BLOCK_CRACKED:
                idx = lv.get_item_index(tile)
                if idx >= 0:
                    item = lv.items[idx]
                    item.element_no = int(item.element_no) & 0x3F
                    lv.visible_in_block_item_cells.discard(tile)
                    self.statusBar().showMessage(
                        f"アイテムをひび割れブロック内に自動変換 {tile}", 2500
                    )
            elif value == BLOCK_BREAKABLE_WHITE:
                if not lv.is_key_removed() and lv.fixed_key_pos == tile:
                    from ..core import constants as cc
                    lv.key_status = cc.KEY_STATUS_WHITE_IN_BLOCK
                    lv.visible_in_block_item_cells.discard(tile)
                    lv.set_block(Wall.NONE, tile)
                    skip_block_placement = True
                    self.statusBar().showMessage(
                        f"鍵を白ブロック内状態に自動変換 {tile}", 2500
                    )
                elif not lv.is_door_removed() and lv.fixed_door_pos == tile:
                    from ..core import room_flags as _rf
                    lv.room_flags = (
                        lv.room_flags & ~_rf.DOOR_STATE_MASK
                    ) | _rf.DOOR_STATE_WHITE_IN_BLOCK
                    lv.set_block(Wall.NONE, tile)
                    skip_block_placement = True
                    self.statusBar().showMessage(
                        f"扉を白ブロック内状態に自動変換 {tile}", 2500
                    )
                else:
                    idx = lv.get_item_index(tile)
                    if idx >= 0:
                        item = lv.items[idx]
                        base = item.element_no & 0x3F
                        if base > c.ITEM_WHITE_IN_BLOCK_MAX_BASE:
                            self.statusBar().showMessage(
                                f"このアイテムは白い壊せるブロック内に入れられません: 0x{base:02X}", 3000
                            )
                            restore_rejected_click_edit()
                            return
                        item.element_no = base | c.ITEM_FLAG_WHITE_IN_BLOCK
                        lv.visible_in_block_item_cells.discard(tile)
                        lv.set_block(Wall.NONE, tile)
                        skip_block_placement = True
                        self.statusBar().showMessage(
                            f"アイテムを白い壊せるブロック内に自動変換 {tile}", 2500
                        )
            elif value == BLOCK_INVISIBLE_BREAKABLE:
                if not lv.is_key_removed() and lv.fixed_key_pos == tile:
                    from ..core import constants as cc
                    lv.key_status = cc.KEY_STATUS_NORMAL
                    lv.set_block(Wall.NONE, tile)
                    lv.visible_in_block_item_cells.add(tile)
                    skip_block_placement = True
                    self.statusBar().showMessage(
                        f"鍵を透明ブロック内状態に自動変換 {tile}", 2500
                    )
                else:
                    idx = lv.get_item_index(tile)
                    if idx >= 0:
                        item = lv.items[idx]
                        base = item.element_no & 0x3F
                        if base > c.ITEM_WHITE_IN_BLOCK_MAX_BASE:
                            self.statusBar().showMessage(
                                f"このアイテムは透明ブロック内に入れられません: 0x{base:02X}", 3000
                            )
                            restore_rejected_click_edit()
                            return
                        item.element_no = base
                        lv.set_block(Wall.NONE, tile)
                        lv.visible_in_block_item_cells.add(tile)
                        skip_block_placement = True
                        self.statusBar().showMessage(
                            f"アイテムを透明ブロック内に自動変換 {tile}", 2500
                        )

            if skip_block_placement:
                pass
            elif value == BLOCK_NONE:
                lv.set_block(Wall.NONE, tile)
                lv.cracked_block_cells.discard(tile)
                lv.breakable_white_cells.discard(tile)
                lv.invisible_breakable_cells.discard(tile)
                lv.invisible_solid_cells.discard(tile)
                lv.passable_brown_cells.discard(tile)
                lv.solid_brown_cells.discard(tile)
            elif value == BLOCK_BROWN:
                lv.set_block(Wall.BROWN, tile)
                lv.cracked_block_cells.discard(tile)
                lv.passable_brown_cells.discard(tile)
                lv.solid_brown_cells.discard(tile)
            elif value == BLOCK_CRACKED:
                lv.set_block(Wall.BROWN, tile)
                lv.breakable_white_cells.discard(tile)
                lv.passable_white_cells.discard(tile)
                lv.invisible_breakable_cells.discard(tile)
                lv.invisible_solid_cells.discard(tile)
                lv.passable_brown_cells.discard(tile)
                lv.solid_brown_cells.discard(tile)
                lv.cracked_block_cells.add(tile)
            elif value == BLOCK_WHITE:
                lv.set_block(Wall.WHITE, tile)
                lv.cracked_block_cells.discard(tile)
                lv.breakable_white_cells.discard(tile)
                lv.passable_white_cells.discard(tile)
                lv.passable_brown_cells.discard(tile)
                lv.solid_brown_cells.discard(tile)
            elif value == BLOCK_BREAKABLE_WHITE:
                lv.set_block(Wall.WHITE, tile)
                lv.cracked_block_cells.discard(tile)
                lv.invisible_breakable_cells.discard(tile)
                lv.passable_white_cells.discard(tile)
                lv.passable_brown_cells.discard(tile)
                lv.solid_brown_cells.discard(tile)
                lv.breakable_white_cells.add(tile)
            elif value == BLOCK_INVISIBLE_BREAKABLE:
                lv.set_block(Wall.NONE, tile)
                lv.cracked_block_cells.discard(tile)
                lv.breakable_white_cells.discard(tile)
                lv.invisible_solid_cells.discard(tile)
                lv.passable_white_cells.discard(tile)
                lv.passable_brown_cells.discard(tile)
                lv.solid_brown_cells.discard(tile)
                lv.invisible_breakable_cells.add(tile)
            elif value == BLOCK_PASSABLE_WHITE:
                lv.set_block(Wall.WHITE, tile)
                lv.cracked_block_cells.discard(tile)
                lv.breakable_white_cells.discard(tile)
                lv.invisible_breakable_cells.discard(tile)
                lv.invisible_solid_cells.discard(tile)
                lv.passable_brown_cells.discard(tile)
                lv.solid_brown_cells.discard(tile)
                lv.passable_white_cells.add(tile)
            elif value == BLOCK_INVISIBLE_SOLID:
                lv.set_block(Wall.NONE, tile)
                lv.cracked_block_cells.discard(tile)
                lv.breakable_white_cells.discard(tile)
                lv.invisible_breakable_cells.discard(tile)
                lv.passable_white_cells.discard(tile)
                lv.passable_brown_cells.discard(tile)
                lv.solid_brown_cells.discard(tile)
                lv.invisible_solid_cells.add(tile)
            elif value == BLOCK_PASSABLE_BROWN:
                lv.set_block(Wall.BROWN, tile)
                lv.cracked_block_cells.discard(tile)
                lv.breakable_white_cells.discard(tile)
                lv.passable_white_cells.discard(tile)
                lv.invisible_breakable_cells.discard(tile)
                lv.invisible_solid_cells.discard(tile)
                lv.solid_brown_cells.discard(tile)
                lv.passable_brown_cells.add(tile)
            elif value == BLOCK_SOLID_BROWN:
                lv.set_block(Wall.BROWN, tile)
                lv.cracked_block_cells.discard(tile)
                lv.breakable_white_cells.discard(tile)
                lv.passable_white_cells.discard(tile)
                lv.invisible_breakable_cells.discard(tile)
                lv.invisible_solid_cells.discard(tile)
                lv.passable_brown_cells.discard(tile)
                lv.solid_brown_cells.add(tile)
            elif value == BLOCK_BROWN_WHITE:
                lv.set_block(Wall.BROWN_WHITE, tile)
                lv.cracked_block_cells.discard(tile)
                lv.breakable_white_cells.discard(tile)
                lv.passable_white_cells.discard(tile)
                lv.invisible_breakable_cells.discard(tile)
                lv.invisible_solid_cells.discard(tile)
                lv.passable_brown_cells.discard(tile)
                lv.solid_brown_cells.discard(tile)
            self._warn_demon_mirror_real_block_enemy_fall(lv, tile, value)
        elif mode == MODE_ITEM:
            tx, ty = tile

            if tile in getattr(lv, "invisible_solid_cells", set()):
                self.statusBar().showMessage(
                    f"透明な白壁にはアイテムを配置できません {tile}", 3000
                )
                restore_rejected_click_edit()
                return

            if (tile in getattr(lv, "passable_brown_cells", set()) or
                    tile in getattr(lv, "solid_brown_cells", set())):
                self.statusBar().showMessage(
                    f"特殊壁にはアイテムを配置できません {tile}", 3000
                )
                restore_rejected_click_edit()
                return

            picker_flag = self.picker.get_item_flag()

            if self._tile_has_visible_key_or_door(lv, tile):
                self.statusBar().showMessage(
                    f"鍵・扉の位置にはアイテムを置けません {tile}", 3000
                )
                restore_rejected_click_edit()
                return
            if self._solomon_seal_meta_at(self.current_level_no, tile) is not None:
                self.statusBar().showMessage(
                    f"ソロモンの紋章位置には通常アイテムを置けません {tile}", 3000
                )
                restore_rejected_click_edit()
                return

            # 壊せない白ブロック内アイテムは禁止（取れなくなる）
            if (lv.tiles[ty][tx] == Wall.WHITE and
                    tile not in getattr(lv, "breakable_white_cells", set()) and
                    picker_flag not in (
                        c.ITEM_FLAG_WHITE_IN_BLOCK,
                        c.ITEM_FLAG_VISIBLE_IN_BLOCK,
                        c.ITEM_FLAG_CRACKED_IN_BLOCK,
                    )):
                self.statusBar().showMessage(
                    f"白ブロック内にはアイテムを配置できません {tile}", 3000
                )
                restore_rejected_click_edit()
                return

            # アイテム × アイテム 重複禁止 → 置換
            existing = lv.get_item_index(tile)
            if existing >= 0:
                if self._is_protected_open_door_item(lv, lv.items[existing]):
                    self.statusBar().showMessage(
                        self._protected_open_door_message(lv, action="replace"),
                        3500,
                    )
                    restore_rejected_click_edit()
                    return
                lv.delete_item(existing)
                self.statusBar().showMessage(
                    f"既存アイテムを置換 {tile}", 2500
                )

            # フラグ決定:
            # - タイルが茶 → 強制 in_block (0x80)
            # - ひび割れ → 通常アイテム + ひび割れセルの組み合わせ
            # - 壊せる白 → 強制 white-in-block (0xC0) に吸収
            # - 透明な壊せるブロック → 強制 透明ブロック内 に吸収
            # - ピッカーが白ブロック内 → item flag だけで表現
            # - ピッカーが透明ブロック内 → 通常アイテム + runtime変換マーカー
            # - タイルが空 → ピッカーで選択中のフラグを使用
            target_is_transparent_in_block = tile in getattr(lv, "invisible_breakable_cells", set())
            target_is_cracked_in_block = tile in getattr(lv, "cracked_block_cells", set())
            visible_in_block_item = (
                picker_flag == c.ITEM_FLAG_VISIBLE_IN_BLOCK or
                target_is_transparent_in_block
            )
            if picker_flag == c.ITEM_FLAG_CRACKED_IN_BLOCK:
                base = value & 0x3F
                if base > c.ITEM_WHITE_IN_BLOCK_MAX_BASE:
                    self.statusBar().showMessage(
                        f"このアイテムはひび割れブロック内に入れられません: 0x{base:02X}", 3000
                    )
                    restore_rejected_click_edit()
                    return
                lv.set_block(Wall.BROWN, tile)
                lv.cracked_block_cells.add(tile)
                flag = c.ITEM_FLAG_NORMAL
            elif visible_in_block_item:
                base = value & 0x3F
                if base > c.ITEM_WHITE_IN_BLOCK_MAX_BASE:
                    self.statusBar().showMessage(
                        f"このアイテムは透明ブロック内に入れられません: 0x{base:02X}", 3000
                    )
                    restore_rejected_click_edit()
                    return
                lv.set_block(Wall.NONE, tile)
                flag = c.ITEM_FLAG_NORMAL
                if target_is_transparent_in_block and picker_flag != c.ITEM_FLAG_VISIBLE_IN_BLOCK:
                    self.statusBar().showMessage(
                        f"透明な壊せるブロック内のため自動で透BL ON {tile}", 2500
                    )
            elif tile in getattr(lv, "breakable_white_cells", set()):
                base = value & 0x3F
                if base > c.ITEM_WHITE_IN_BLOCK_MAX_BASE:
                    self.statusBar().showMessage(
                        f"このアイテムは白い壊せるブロック内に入れられません: 0x{base:02X}", 3000
                    )
                    restore_rejected_click_edit()
                    return
                lv.set_block(Wall.NONE, tile)
                flag = c.ITEM_FLAG_WHITE_IN_BLOCK
                if picker_flag != c.ITEM_FLAG_WHITE_IN_BLOCK:
                    self.statusBar().showMessage(
                        f"白い壊せるブロック内のため自動で白ブロック内フラグON {tile}", 2500
                    )
            elif target_is_cracked_in_block:
                flag = c.ITEM_FLAG_NORMAL
                if picker_flag != c.ITEM_FLAG_NORMAL:
                    self.statusBar().showMessage(
                        f"ひび割れブロック内のため通常item_idで保存 {tile}", 2500
                    )
            elif lv.tiles[ty][tx] in (Wall.BROWN, Wall.BROWN_WHITE):
                flag = c.ITEM_FLAG_IN_BLOCK
                lv.set_block(Wall.NONE, tile)
                if picker_flag != c.ITEM_FLAG_IN_BLOCK:
                    self.statusBar().showMessage(
                        f"ブロック内のため自動で in_block フラグON {tile}", 2500
                    )
            elif picker_flag == c.ITEM_FLAG_WHITE_IN_BLOCK:
                base = value & 0x3F
                if base > c.ITEM_WHITE_IN_BLOCK_MAX_BASE:
                    self.statusBar().showMessage(
                        f"このアイテムは白い壊せるブロック内に入れられません: 0x{base:02X}", 3000
                    )
                    restore_rejected_click_edit()
                    return
                lv.set_block(Wall.NONE, tile)
                flag = c.ITEM_FLAG_WHITE_IN_BLOCK
            else:
                flag = picker_flag

            lv.add_item(value | flag, tile)
            if visible_in_block_item:
                lv.visible_in_block_item_cells.add(tile)
                self._log(
                    f"透明ブロック内アイテム配置: L{self.current_level_no + 1} "
                    f"{tile} item=0x{base:02X}"
                )
            else:
                lv.visible_in_block_item_cells.discard(tile)
        elif mode == MODE_ENEMY:
            # 敵 + ブロック同位置は禁止（原作はほぼ皆無）
            tx, ty = tile
            passable_runtime_cells = (
                set(getattr(lv, "passable_white_cells", set()) or []) |
                set(getattr(lv, "passable_brown_cells", set()) or [])
            )
            if ((lv.tiles[ty][tx] != Wall.NONE and
                 tile not in passable_runtime_cells) or
                    tile in getattr(lv, "invisible_breakable_cells", set()) or
                    tile in getattr(lv, "invisible_solid_cells", set()) or
                    tile in getattr(lv, "solid_brown_cells", set())):
                self.statusBar().showMessage(
                    f"ブロックがある位置には敵を置けません {tile}", 2500
                )
                restore_rejected_click_edit()
                return
            # 敵 × 敵 の同位置重複は許可（原作USA ROM全53レベルで8件あり、
            # 同マスから複数体生成する意図的な配置）。上書きせず追加のみ。
            if lv.fixed_start_pos == tile:
                self.statusBar().showMessage(
                    f"スタート位置には敵を置けません（開始直後に死亡します） {tile}", 3000
                )
                restore_rejected_click_edit()
                return
            # スピードフラグ (1/2/3) を適用して実コードに変換
            from .element_picker import apply_enemy_speed
            actual_code = apply_enemy_speed(value, self.picker.get_enemy_speed())
            ok = lv.add_enemy(actual_code, tile)
            if not ok:
                self.statusBar().showMessage(
                    f"敵は1ステージ {c.ENEMY_COUNT_MAX} 体まで（拡張ROM形式の制限）", 3000
                )
                restore_rejected_click_edit()
                return
            count = sum(1 for e in lv.enemies if e.position == tile)
            if count > 1:
                self.statusBar().showMessage(
                    f"敵を追加 {tile} (このマスに{count}体)", 2500
                )
            self._refresh_key_enemy_spin_range()
            self._refresh_fairy_enemy_spin_range()
        elif mode == MODE_META:
            tx, ty = tile
            target_is_white_in_block = tile in getattr(lv, "breakable_white_cells", set())
            target_is_cracked_in_block = tile in getattr(lv, "cracked_block_cells", set())
            target_is_brown_in_block = lv.tiles[ty][tx] in (Wall.BROWN, Wall.BROWN_WHITE)
            if value == "start":
                if lv.get_enemy_index(tile) >= 0:
                    self.statusBar().showMessage(
                        f"敵がいる位置にはスタートを置けません（開始直後に死亡します） {tile}", 3000
                    )
                    restore_rejected_click_edit()
                    return
                lv.fixed_start_pos = tile
            elif value == "key":
                if lv.is_door_removed():
                    self.statusBar().showMessage(
                        "扉が削除されているステージには鍵を置けません", 3000
                    )
                    restore_rejected_click_edit()
                    return
                if lv.get_item_index(tile) >= 0:
                    self.statusBar().showMessage(
                        f"アイテムがある位置には鍵を置けません {tile}", 3000
                    )
                    restore_rejected_click_edit()
                    return
                from ..core import constants as cc
                old_key_pos = tuple(lv.fixed_key_pos)
                old_key_was_cracked = (
                    old_key_pos in getattr(lv, "cracked_block_cells", set())
                    and lv.key_status == cc.KEY_STATUS_HIDDEN
                )
                lv.fixed_key_pos = tile
                if old_key_pos != tile:
                    lv.visible_in_block_item_cells.discard(old_key_pos)
                    if old_key_was_cracked:
                        lv.set_block(Wall.NONE, old_key_pos)
                    else:
                        lv.cracked_block_cells.discard(old_key_pos)
                # 配置フラグを key_status に反映
                picker_flag = self.picker.get_item_flag()
                if target_is_white_in_block:
                    lv.key_status = cc.KEY_STATUS_WHITE_IN_BLOCK
                    lv.set_block(Wall.NONE, tile)
                    lv.visible_in_block_item_cells.discard(tile)
                    lv.cracked_block_cells.discard(tile)
                elif target_is_cracked_in_block or picker_flag == c.ITEM_FLAG_CRACKED_IN_BLOCK:
                    lv.key_status = cc.KEY_STATUS_HIDDEN
                    lv.set_block(Wall.BROWN, tile)
                    lv.cracked_block_cells.add(tile)
                    lv.visible_in_block_item_cells.discard(tile)
                elif target_is_brown_in_block:
                    lv.key_status = cc.KEY_STATUS_IN_BLOCK
                    lv.set_block(Wall.NONE, tile)
                    lv.visible_in_block_item_cells.discard(tile)
                    lv.cracked_block_cells.discard(tile)
                else:
                    flag_map = {
                        0x00: cc.KEY_STATUS_NORMAL,
                        0x40: cc.KEY_STATUS_HIDDEN,
                        0x80: cc.KEY_STATUS_IN_BLOCK,
                        0xC0: cc.KEY_STATUS_WHITE_IN_BLOCK,
                    }
                    if picker_flag == c.ITEM_FLAG_VISIBLE_IN_BLOCK:
                        lv.key_status = cc.KEY_STATUS_NORMAL
                        lv.visible_in_block_item_cells.add(tile)
                        lv.cracked_block_cells.discard(tile)
                    else:
                        lv.key_status = flag_map.get(picker_flag, cc.KEY_STATUS_NORMAL)
                        lv.visible_in_block_item_cells.discard(tile)
                        lv.cracked_block_cells.discard(tile)
                    if lv.key_status == cc.KEY_STATUS_WHITE_IN_BLOCK:
                        lv.set_block(Wall.NONE, tile)
            elif value == "door":
                if lv.get_item_index(tile) >= 0:
                    self.statusBar().showMessage(
                        f"アイテムがある位置には扉を置けません {tile}", 3000
                    )
                    restore_rejected_click_edit()
                    return
                lv.fixed_door_pos = tile
                from ..core import room_flags as _rf
                picker_flag = self.picker.get_item_flag()
                if target_is_white_in_block:
                    door_state = _rf.DOOR_STATE_WHITE_IN_BLOCK
                    lv.set_block(Wall.NONE, tile)
                elif target_is_brown_in_block:
                    door_state = _rf.DOOR_STATE_IN_BLOCK
                    lv.set_block(Wall.NONE, tile)
                else:
                    door_state_map = {
                        0x00: _rf.DOOR_STATE_NORMAL,
                        0x40: _rf.DOOR_STATE_HIDDEN,
                        0x80: _rf.DOOR_STATE_IN_BLOCK,
                        0xC0: _rf.DOOR_STATE_WHITE_IN_BLOCK,
                    }
                    door_state = door_state_map.get(picker_flag, _rf.DOOR_STATE_NORMAL)
                lv.room_flags = (lv.room_flags & ~_rf.DOOR_STATE_MASK) | door_state
            elif value == "mirror1":
                lv.demon_mirrors[0].position = tile
                block_kind = self._apply_mirror_block_flag_to_tile(lv, tile, self.picker.get_item_flag())
                self._warn_demon_mirror_real_block_enemy_fall(lv, tile, block_kind)
            elif value == "mirror2":
                lv.demon_mirrors[1].position = tile
                block_kind = self._apply_mirror_block_flag_to_tile(lv, tile, self.picker.get_item_flag())
                self._warn_demon_mirror_real_block_enemy_fall(lv, tile, block_kind)

        self._refresh_view()
        self._refresh_thumbnails_after_edit()

    # ====== Ctrl+左ドラッグでの要素移動 ======

    def _on_drag_start(self, tile: tuple):
        """Ctrl+左クリックで要素を掴む。掴んだ element の参照を保持"""
        if not self.levels:
            return
        if self._is_stage_compare_diff_view():
            self.statusBar().showMessage("差分表示中は編集できません。「現在」に戻すと編集できます", 2500)
            return
        if self._reject_read_only_edit():
            return
        if self._is_locked_col15_tile(tile):
            self._show_col15_locked_message()
            return
        lv = self.levels[self.current_level_no]
        self._move_pending = None  # リセット

        # 選択範囲内をクリック → 選択全体を移動
        bounds = self._get_selection_bounds()
        if bounds is not None:
            x1, y1, x2, y2 = bounds
            if x1 <= tile[0] <= x2 and y1 <= tile[1] <= y2:
                # 選択内容を取得 → 元位置を空にする
                drag_clip = self._build_clipboard_from_selection()
                if drag_clip is not None and (
                    drag_clip["blocks"] or drag_clip["items"] or
                    drag_clip["enemies"] or drag_clip.get("meta")
                ):
                    self._push_undo()
                    # 元位置を空にする（self._delete_in_selection は undo を積むので直接実行）
                    for y in range(y1, y2 + 1):
                        for x in range(x1, x2 + 1):
                            lv.tiles[y][x] = Wall.NONE
                            self._pop_runtime_markers_at(lv, (x, y))
                    lv.items = [it for it in lv.items
                                if not (x1 <= it.position[0] <= x2 and y1 <= it.position[1] <= y2)]
                    lv.enemies = [en for en in lv.enemies
                                  if not (x1 <= en.position[0] <= x2 and y1 <= en.position[1] <= y2)]
                    # ベース状態（削除後）を保存して、毎回ここから再構築
                    self._drag_base_level = copy.deepcopy(lv)
                    self._move_pending = {
                        "kind": "selection",
                        "click_offset": (tile[0] - x1, tile[1] - y1),
                        "clip": drag_clip,
                    }
                    # 仮で今の位置に貼り（削除済みなのですぐ戻る）
                    self._paste_clipboard_at(drag_clip, x1, y1)
                    self.statusBar().showMessage("選択範囲を移動中…", 0)
                    self._refresh_view()
                    return

        seal_block_combo = self._solomon_seal_block_combo_at(lv, self.current_level_no, tile)
        if seal_block_combo is not None:
            self._push_undo()
            self._move_pending = {
                "kind": "seal_block",
                "ref": seal_block_combo["meta"],
                "wall_type": seal_block_combo["wall_type"],
                "runtime_markers": set(seal_block_combo["runtime_markers"]),
                "item_refs": [it for it in lv.items if it.position == tile],
                "current_pos": tile,
                "prev_wall_at_current": Wall.NONE,
                "prev_markers_at_current": set(),
            }
            self.statusBar().showMessage(
                f"{seal_block_combo['meta'].description} + ブロックを掴み中 → ドラッグで移動", 0)
            self._refresh_view()
            return

        # 優先順位: item > enemy > meta（start/key/door/mirror1/mirror2）
        idx = lv.get_item_index(tile)
        if idx >= 0:
            self._push_undo()
            item = lv.items[idx]
            move_absorb_flag = self._detach_item_absorb_state_for_move(lv, item, tile)
            self._move_pending = {
                "kind": "item",
                "ref": item,
                "move_absorb_flag": move_absorb_flag,
                "current_pos": tile,
            }
            self.statusBar().showMessage(f"アイテムを掴み中 → ドラッグで移動", 0)
            self._refresh_view()
            return

        idx = lv.get_enemy_index(tile)
        if idx >= 0:
            self._push_undo()
            self._move_pending = {"kind": "enemy", "ref": lv.enemies[idx]}
            self.statusBar().showMessage(f"敵を掴み中 → ドラッグで移動", 0)
            return

        # ボーナスマーカー (Level 51専用)
        if self.current_level_no == 50 and getattr(self, "_bonus_positions", None):
            for bi, bpos in enumerate(self._bonus_positions):
                if bpos == tile:
                    self._push_undo()
                    self._move_pending = {"kind": "bonus", "index": bi}
                    self.statusBar().showMessage(
                        f"ボーナススポット[{bi}] を掴み中 → ドラッグで移動", 0)
                    return

        special_marker = self._conditional_breakable_marker_at(tile)
        if special_marker is not None:
            self._push_undo()
            self._move_pending = {
                "kind": "conditional_breakable",
                "group": special_marker["group"],
                "sub": special_marker["sub"],
            }
            group_label = self._conditional_breakable_group_label(special_marker["group"])
            label = self._conditional_breakable_marker_label(special_marker["sub"])
            self.statusBar().showMessage(
                f"{group_label} 条件付き壊せる白ブロック[{label}]を掴み中 → ドラッグで移動", 0
            )
            self._refresh_view()
            return

        bomb_jack_marker = self._bomb_jack_marker_at(tile)
        if bomb_jack_marker is not None:
            self._push_undo()
            self._move_pending = {
                "kind": "bomb_jack",
                "sub": bomb_jack_marker,
            }
            label = "頭突き判定" if bomb_jack_marker == "trigger" else "出現先"
            self.statusBar().showMessage(
                f"Mighty Bomb Jack [{label}] を掴み中 → ドラッグで移動", 0
            )
            self._refresh_view()
            return

        if lv.fixed_start_pos == tile:
            self._move_pending = {"kind": "meta", "sub": "start"}
        elif lv.fixed_key_pos == tile and not lv.is_key_removed():
            self._move_pending = {
                "kind": "meta",
                "sub": "key",
                "current_pos": tile,
            }
        elif lv.fixed_door_pos == tile and not lv.is_door_removed():
            self._move_pending = {
                "kind": "meta",
                "sub": "door",
                "current_pos": tile,
            }
        elif lv.demon_mirrors[0].position == tile:
            self._move_pending = {"kind": "meta", "sub": "mirror1"}
        elif lv.demon_mirrors[1].position == tile:
            self._move_pending = {"kind": "meta", "sub": "mirror2"}

        # ソロモンの紋章（level_meta_items）
        if self._move_pending is None and self.config:
            for mi in self.config.level_meta_items:
                if mi.level_no == self.current_level_no and mi.position == tile and mi.rom_offset >= 0:
                    self._push_undo()
                    self._move_pending = {"kind": "seal", "ref": mi}
                    self.statusBar().showMessage(
                        f"{mi.description} を掴み中 → ドラッグで移動", 0)
                    self._refresh_view()
                    return

        if self._move_pending:
            self._push_undo()
            sub = self._move_pending.get("sub")
            if sub == "key":
                self._move_pending["move_absorb_flag"] = (
                    self._detach_key_absorb_state_for_move(lv, tile)
                )
                if self._move_pending["move_absorb_flag"] is not None:
                    self._apply_moving_key_absorb_state(lv, self._move_pending, tile)
            elif sub == "door":
                self._move_pending["move_absorb_flag"] = (
                    self._detach_door_absorb_state_for_move(lv)
                )
                if self._move_pending["move_absorb_flag"] is not None:
                    self._apply_moving_door_absorb_state(lv, self._move_pending, tile)
            self.statusBar().showMessage(
                f"{self._move_pending['sub']} を掴み中 → ドラッグで移動", 0
            )
            self._refresh_view()
            return

        # ブロックを掴む（最後の優先順位、他の要素が無い場合のみ）
        tx, ty = tile
        wall = lv.tiles[ty][tx]
        has_runtime_marker = any(
            tile in getattr(lv, name, set())
            for name in self._runtime_marker_names()
        )
        if wall != Wall.NONE or has_runtime_marker:
            self._push_undo()
            runtime_markers = self._pop_runtime_markers_at(lv, tile)
            self._move_pending = {
                "kind": "block",
                "wall_type": wall,
                "runtime_markers": runtime_markers,
                "current_pos": tile,
                # 現在位置に「元々あった壁」（drag_moveで復元するため）
                # 元位置は今クリアしたので NONE
                "prev_wall_at_current": Wall.NONE,
                "prev_markers_at_current": set(),
            }
            # 元位置を空白に
            lv.tiles[ty][tx] = Wall.NONE
            if "cracked_block_cells" in runtime_markers:
                label = "ひび割れブロック"
            elif "invisible_breakable_cells" in runtime_markers:
                label = "透明な壊せる壁"
            elif "invisible_solid_cells" in runtime_markers:
                label = "透明な白壁"
            elif "breakable_white_cells" in runtime_markers:
                label = "壊せる白壁"
            elif "passable_white_cells" in runtime_markers:
                label = "すり抜ける白壁"
            elif "passable_brown_cells" in runtime_markers:
                label = "すり抜ける茶色壁"
            elif "solid_brown_cells" in runtime_markers:
                label = "壊せない茶色壁"
            else:
                label = {Wall.BROWN: "茶ブロック", Wall.WHITE: "白ブロック",
                         Wall.BROWN_WHITE: "壊せる白"}.get(wall, "ブロック")
            self.statusBar().showMessage(f"{label} を掴み中 → ドラッグで移動", 0)
            self._refresh_view()

    def _on_drag_move(self, tile: tuple):
        """ドラッグ中、掴んでいる要素を tile に追従させる"""
        if not self.levels or self._move_pending is None:
            return
        if self._is_stage_compare_diff_view():
            self._move_pending = None
            self.statusBar().showMessage("差分表示中は編集できません。「現在」に戻すと編集できます", 2500)
            return
        if self._reject_read_only_edit():
            self._move_pending = None
            return
        lv = self.levels[self.current_level_no]
        mp = self._move_pending
        kind = mp["kind"]
        selection_target = None
        if kind == "selection":
            clip = mp["clip"]
            ox = tile[0] - mp["click_offset"][0]
            oy = tile[1] - mp["click_offset"][1]
            if self._clip_targets_locked_col15(clip, ox, oy):
                self._show_col15_locked_message("16列目へは移動できません（「16列目を編集」をONにしてください）")
                return
            base_lv = self._drag_base_level or lv
            if self._clip_has_start_enemy_overlap(base_lv, clip, ox, oy):
                self._show_start_enemy_overlap_message((ox, oy))
                return
            if self._clip_has_key_door_item_overlap(base_lv, clip, ox, oy):
                self._show_key_door_item_overlap_message((ox, oy))
                return
            if self._clip_has_item_block_overlap(base_lv, clip, ox, oy):
                self._show_block_absorb_rejected_message((ox, oy))
                return
            if self._clip_has_actor_block_overlap(base_lv, clip, ox, oy):
                self._show_actor_block_overlap_message((ox, oy))
                return
            selection_target = (clip, ox, oy)
        elif self._is_locked_col15_tile(tile):
            self._show_col15_locked_message("16列目へは移動できません（「16列目を編集」をONにしてください）")
            return

        if kind in ("item", "enemy"):
            if kind == "item" and self._tile_has_visible_key_or_door(lv, tile):
                self._show_key_door_item_overlap_message(tile)
                return
            if kind == "item" and self._solomon_seal_meta_at(self.current_level_no, tile) is not None:
                self._show_key_door_item_overlap_message(tile)
                return
            item_absorb_flag = None
            if kind == "item":
                item_absorb_flag = self._block_absorb_flag_at_tile(lv, tile)
                if self._is_blocking_edit_block_cell(lv, tile):
                    if not self._can_apply_absorb_flag_to_moving_item(mp.get("ref"), item_absorb_flag):
                        self._show_block_absorb_rejected_message(tile)
                        return
            if kind == "enemy" and lv.fixed_start_pos == tile:
                self._show_start_enemy_overlap_message(tile)
                return
            if kind == "enemy" and self._is_blocking_edit_block_cell(lv, tile):
                self._show_actor_block_overlap_message(tile)
                return
            if kind == "item":
                self._restore_drag_item_absorbed_block(lv, mp)
            if kind == "item" and item_absorb_flag is not None:
                if not self._apply_absorb_flag_to_moving_item(lv, mp, tile, item_absorb_flag):
                    self._show_block_absorb_rejected_message(tile)
                    return
            elif kind == "item" and mp.get("move_absorb_flag") is not None:
                self._clear_moving_item_absorb_state(lv, mp)
                self._apply_moving_item_absorb_state(lv, mp, tile)
            elif kind == "item":
                mp["current_pos"] = tile
            mp["ref"].position = tile
        elif kind == "meta":
            sub = mp["sub"]
            if sub == "key":
                if lv.get_item_index(tile) >= 0:
                    self._show_key_door_item_overlap_message(tile)
                    return
                target_absorb_flag = self._block_absorb_flag_at_tile(lv, tile)
                if self._is_blocking_edit_block_cell(lv, tile) and not self._can_apply_absorb_flag_to_moving_key(target_absorb_flag):
                    self._show_block_absorb_rejected_message(tile)
                    return
                self._restore_drag_meta_absorbed_block(lv, mp)
                self._clear_moving_key_absorb_state(lv, mp)
                lv.fixed_key_pos = tile
                if target_absorb_flag is not None:
                    self._apply_absorb_flag_to_moving_key(lv, mp, tile, target_absorb_flag)
                elif mp.get("move_absorb_flag") is not None:
                    self._apply_moving_key_absorb_state(lv, mp, tile)
                mp["current_pos"] = tile
            elif sub == "door":
                if lv.get_item_index(tile) >= 0:
                    self._show_key_door_item_overlap_message(tile)
                    return
                target_absorb_flag = self._block_absorb_flag_at_tile(lv, tile)
                if self._is_blocking_edit_block_cell(lv, tile) and not self._can_apply_absorb_flag_to_moving_door(target_absorb_flag):
                    self._show_block_absorb_rejected_message(tile)
                    return
                self._restore_drag_meta_absorbed_block(lv, mp)
                self._clear_moving_door_absorb_state(lv, mp)
                lv.fixed_door_pos = tile
                if target_absorb_flag is not None:
                    self._apply_absorb_flag_to_moving_door(lv, mp, tile, target_absorb_flag)
                elif mp.get("move_absorb_flag") is not None:
                    self._apply_moving_door_absorb_state(lv, mp, tile)
                mp["current_pos"] = tile
            elif sub == "start":
                if lv.get_enemy_index(tile) >= 0:
                    self._show_start_enemy_overlap_message(tile)
                    return
                if self._is_blocking_edit_block_cell(lv, tile):
                    self._show_actor_block_overlap_message(tile)
                    return
                lv.fixed_start_pos = tile
            elif sub == "mirror1":
                lv.demon_mirrors[0].position = tile
            elif sub == "mirror2":
                lv.demon_mirrors[1].position = tile
        elif kind == "seal":
            if not self._solomon_seal_can_move_to_tile(lv, tile):
                self._show_solomon_seal_move_rejected_message(lv, tile)
                return
            mp["ref"].position = tile
        elif kind == "seal_block":
            item_refs = list(mp.get("item_refs") or [])
            if not self._solomon_seal_can_move_to_tile(lv, tile):
                self._show_solomon_seal_move_rejected_message(lv, tile)
                return
            if self._tile_has_actor_for_block_move(lv, tile):
                self._show_actor_block_overlap_message(tile)
                return
            if any(it.position == tile and it not in item_refs for it in getattr(lv, "items", []) or []):
                self._show_key_door_item_overlap_message(tile)
                return
            cx, cy = mp["current_pos"]
            lv.tiles[cy][cx] = mp["prev_wall_at_current"]
            self._pop_runtime_markers_at(lv, (cx, cy))
            self._restore_runtime_markers_at(
                lv, (cx, cy), mp.get("prev_markers_at_current", set())
            )
            tx, ty = tile
            mp["prev_wall_at_current"] = lv.tiles[ty][tx]
            mp["prev_markers_at_current"] = self._pop_runtime_markers_at(lv, tile)
            lv.tiles[ty][tx] = mp["wall_type"]
            self._restore_runtime_markers_at(lv, tile, mp.get("runtime_markers", set()))
            mp["ref"].position = tile
            for item in item_refs:
                item.position = tile
            mp["current_pos"] = tile
        elif kind == "bonus":
            bi = mp["index"]
            self._bonus_positions[bi] = tile
            # _bonus_items も再構築（レンダラー用）
            self._rebuild_bonus_items_from_positions()
        elif kind == "conditional_breakable":
            self._move_conditional_breakable_marker(mp["group"], mp["sub"], tile)
        elif kind == "bomb_jack":
            self._move_bomb_jack_marker(mp["sub"], tile)
        elif kind == "block":
            if self._tile_has_actor_for_block_move(lv, tile):
                self._show_actor_block_overlap_message(tile)
                return
            absorb_flag = self._block_absorb_flag_from_parts(
                mp.get("wall_type"), mp.get("runtime_markers", set())
            )
            target_has_absorb = self._tile_has_absorb_target(lv, tile)
            if target_has_absorb and not self._can_apply_absorb_flag_to_tile(lv, tile, absorb_flag):
                self._show_block_absorb_rejected_message(tile)
                return
            # 通り過ぎたタイルの「元の壁」を復元してから新位置にブロック配置
            cx, cy = mp["current_pos"]
            # 現在位置を元に戻す
            lv.tiles[cy][cx] = mp["prev_wall_at_current"]
            self._pop_runtime_markers_at(lv, (cx, cy))
            self._restore_runtime_markers_at(
                lv, (cx, cy), mp.get("prev_markers_at_current", set())
            )
            self._restore_absorb_target_state(lv, mp.get("prev_absorb_state_at_current"))
            # 新位置の元の壁を保存
            tx, ty = tile
            mp["prev_wall_at_current"] = lv.tiles[ty][tx]
            mp["prev_markers_at_current"] = self._pop_runtime_markers_at(lv, tile)
            mp["prev_absorb_state_at_current"] = None
            if target_has_absorb:
                mp["prev_absorb_state_at_current"] = self._snapshot_absorb_target_state(lv, tile)
                lv.tiles[ty][tx] = Wall.NONE
                if not self._apply_absorb_flag_to_tile(lv, tile, absorb_flag):
                    self._restore_absorb_target_state(lv, mp.get("prev_absorb_state_at_current"))
                    mp["prev_absorb_state_at_current"] = None
                    self._show_block_absorb_rejected_message(tile)
                    return
            else:
                # 新位置にブロック配置
                lv.tiles[ty][tx] = mp["wall_type"]
                self._restore_runtime_markers_at(lv, tile, mp.get("runtime_markers", set()))
            mp["current_pos"] = tile
        elif kind == "selection":
            # ベース状態（削除後の状態）に復元してから新位置に貼り直す
            clip, ox, oy = selection_target
            self.levels[self.current_level_no] = copy.deepcopy(self._drag_base_level)
            self._paste_clipboard_at(clip, ox, oy)
            # 選択範囲も新位置に追従
            self._selection_rect = (
                (ox, oy), (ox + clip["w"] - 1, oy + clip["h"] - 1)
            )

        self._refresh_view()

    def _on_drag_end(self):
        """Ctrl解放 / マウス解放でドラッグ確定"""
        if self._is_read_only():
            self._move_pending = None
            return
        if self._move_pending is not None:
            kind = self._move_pending.get("kind")
            if kind == "selection":
                self.statusBar().showMessage("選択範囲の移動完了", 2000)
                self._drag_base_level = None
                self._refresh_thumbnails_after_edit()
            elif kind == "bonus":
                self._write_bonus_positions_to_rom()
                self.statusBar().showMessage("ボーナススポット移動完了", 2000)
                self._refresh_thumbnails_after_edit()
            elif kind == "seal":
                mi = self._move_pending["ref"]
                if self.rom and mi.rom_offset >= 0 and mi.rom_offset < len(self.rom.data):
                    from ..core.element import byte_from_position
                    self.rom.data[mi.rom_offset] = byte_from_position(mi.position)
                self.statusBar().showMessage(
                    f"{mi.description} 移動完了 → {mi.position}", 2000)
                self._refresh_thumbnails_after_edit()
            elif kind == "seal_block":
                mi = self._move_pending["ref"]
                if self.rom and mi.rom_offset >= 0 and mi.rom_offset < len(self.rom.data):
                    from ..core.element import byte_from_position
                    self.rom.data[mi.rom_offset] = byte_from_position(mi.position)
                self.statusBar().showMessage(
                    f"{mi.description} + ブロック移動完了 → {mi.position}", 2000)
                self._refresh_thumbnails_after_edit()
            elif kind == "conditional_breakable":
                group = self._move_pending.get("group")
                sub = self._move_pending.get("sub")
                positions = self._conditional_breakable_positions(group) or {}
                pos = positions.get(sub)
                group_label = self._conditional_breakable_group_label(group)
                label = self._conditional_breakable_marker_label(sub)
                self.statusBar().showMessage(
                    f"{group_label} 条件付き壊せる白ブロック[{label}]移動完了 → {pos}", 2000
                )
                self._refresh_thumbnails_after_conditional_marker_edit(group)
            elif kind == "bomb_jack":
                sub = self._move_pending.get("sub")
                positions = self._bomb_jack_positions() or {}
                pos = positions.get(sub)
                label = "頭突き判定" if sub == "trigger" else "出現先"
                self.statusBar().showMessage(
                    f"Mighty Bomb Jack [{label}] 移動完了 → {pos}", 2000
                )
                self._refresh_thumbnails_after_edit()
            elif kind == "item":
                lv = self.levels[self.current_level_no]
                item = self._move_pending.get("ref")
                if item is not None and item.is_in_block():
                    lv.set_block(Wall.NONE, item.position)
                self.statusBar().showMessage("アイテム移動完了", 2000)
                self._refresh_thumbnails_after_edit()
            elif kind == "meta" and self._move_pending.get("sub") in ("key", "door"):
                self._finish_key_door_drag_absorb_state()
                self.statusBar().showMessage("移動完了", 2000)
                self._refresh_thumbnails_after_edit()
            else:
                self.statusBar().showMessage("移動完了", 2000)
                self._refresh_thumbnails_after_edit()
        self._move_pending = None

    def _finish_key_door_drag_absorb_state(self):
        if not self.levels or self._move_pending is None:
            return
        mp = self._move_pending
        if mp.get("kind") != "meta":
            return
        sub = mp.get("sub")
        if sub not in ("key", "door"):
            return
        lv = self.levels[self.current_level_no]
        tile = mp.get("current_pos")
        if tile is None:
            return
        target_absorb_flag = self._block_absorb_flag_at_tile(lv, tile)
        if sub == "key":
            state = mp.get("absorbed_block_state")
            if state and state.get("tile") == tile:
                mp.pop("absorbed_block_state", None)
            if mp.get("active_absorb_flag") is None and target_absorb_flag is not None:
                self._apply_absorb_flag_to_moving_key(lv, mp, tile, target_absorb_flag)
            elif mp.get("active_absorb_flag") is None and mp.get("move_absorb_flag") is not None:
                self._apply_moving_key_absorb_state(lv, mp, tile)
        else:
            state = mp.get("absorbed_block_state")
            if state and state.get("tile") == tile:
                mp.pop("absorbed_block_state", None)
            if mp.get("active_absorb_flag") is None and target_absorb_flag is not None:
                self._apply_absorb_flag_to_moving_door(lv, mp, tile, target_absorb_flag)
            elif mp.get("active_absorb_flag") is None and mp.get("move_absorb_flag") is not None:
                self._apply_moving_door_absorb_state(lv, mp, tile)

    def _on_tile_right_clicked(self, tile: tuple):
        """右クリック: そのタイルの全要素を削除（編集モード非依存）

        優先順位は気にせず、その位置に存在するもの全て削除:
          - アイテム / 敵 / ブロック を順に消す
          - メタ要素（鍵/扉/スタート/ミラー）は移動が原則なので削除対象外
        """
        if not self.levels:
            return
        if self._is_stage_compare_diff_view():
            self.statusBar().showMessage("差分表示中は編集できません。「現在」に戻すと編集できます", 2500)
            return
        if self._reject_read_only_edit():
            return
        # 16列目の編集ロック
        if not self.chk_edit_col15.isChecked() and tile[0] == 15:
            return
        lv = self.levels[self.current_level_no]
        if not getattr(self, '_suppress_next_undo', False):
            self._right_drag_has_undo = False

        marker_names = (
            "breakable_white_cells",
            "cracked_block_cells",
            "invisible_breakable_cells",
            "passable_white_cells",
            "invisible_solid_cells",
            "passable_brown_cells",
            "solid_brown_cells",
            "visible_in_block_item_cells",
        )
        has_runtime_marker = any(tile in getattr(lv, name, set()) for name in marker_names)
        can_delete_key = (
            not lv.is_key_removed()
            and lv.fixed_key_pos == tile
            and self._can_delete_key_meta(lv)
        )
        can_delete_door = (
            not lv.is_door_removed()
            and lv.fixed_door_pos == tile
            and self._can_delete_door_meta(lv)
        )
        if (
            lv.get_item_index(tile) < 0
            and lv.get_enemy_index(tile) < 0
            and lv.tiles[tile[1]][tile[0]] == Wall.NONE
            and not has_runtime_marker
            and not can_delete_key
            and not can_delete_door
        ):
            return
        if can_delete_door and stage_ext.get_key_enemy_number(lv) > 0:
            self.statusBar().showMessage(
                "扉を削除する前に鍵持ち敵を解除してください", 3000
            )
            return
        if can_delete_door and not lv.is_key_removed() and not can_delete_key:
            self.statusBar().showMessage(
                "扉を削除する前に鍵メタを削除してください", 3000
            )
            return
        key_enemy_number = stage_ext.get_key_enemy_number(lv)
        if self._key_enemy_is_required_for_exit(lv) and key_enemy_number > 0:
            idx = lv.get_enemy_index(tile)
            while idx >= 0:
                if idx <= key_enemy_number - 1:
                    self.statusBar().showMessage(
                        "鍵メタが無いため、この鍵持ち敵に影響する敵は削除できません", 3000
                    )
                    return
                next_idx = -1
                for i in range(idx - 1, -1, -1):
                    if lv.enemies[i].position == tile:
                        next_idx = i
                        break
                idx = next_idx

        self._push_undo()
        if not getattr(self, '_suppress_next_undo', False):
            self._right_drag_has_undo = True

        deleted = []

        if can_delete_key:
            from ..core import constants as cc
            lv.visible_in_block_item_cells.discard(tile)
            lv.fixed_key_pos = (0, -1)
            lv.key_status = cc.KEY_STATUS_HIDDEN
            deleted.append("key")

        if can_delete_door:
            from ..core import room_flags as _rf
            lv.fixed_door_pos = (0, -1)
            lv.room_flags = lv.room_flags & ~_rf.DOOR_STATE_MASK
            deleted.append("door")

        # アイテム削除（同位置に複数ある場合に備えてループ）
        while True:
            idx = lv.get_item_index(tile)
            if idx < 0:
                break
            if self._is_protected_open_door_item(lv, lv.items[idx]):
                self.statusBar().showMessage(
                    self._protected_open_door_message(lv, action="delete"),
                    3500,
                )
                break
            lv.delete_item(idx)
            deleted.append("item")

        # 敵削除
        while True:
            idx = lv.get_enemy_index(tile)
            if idx < 0:
                break
            lv.delete_enemy(idx)
            deleted.append("enemy")
        if "enemy" in deleted:
            self._refresh_key_enemy_spin_range(warn=True)
            self._refresh_fairy_enemy_spin_range(warn=True)

        # ブロック削除
        had_runtime_marker = False
        for name in marker_names:
            cells = getattr(lv, name, set())
            if tile in cells:
                cells.discard(tile)
                had_runtime_marker = True

        if lv.tiles[tile[1]][tile[0]] != Wall.NONE or had_runtime_marker:
            lv.set_block(Wall.NONE, tile)
            deleted.append("block")

        if deleted:
            self.statusBar().showMessage(f"削除: {tile} ({', '.join(deleted)})", 2000)
        self._refresh_view()
        self._refresh_thumbnails_after_edit()

    def _on_tile_painted(self, button: int, tile: tuple, modifiers: int):
        """ドラッグ塗り（左ボタン押しっぱなし）— undoは press 時の1回だけ"""
        self._suppress_next_undo = True
        try:
            self._on_tile_clicked(button, tile, modifiers)
        finally:
            self._suppress_next_undo = False

    def _on_tile_erased(self, tile: tuple):
        """ドラッグ消し（右ボタン押しっぱなし）— undoは press 時の1回だけ"""
        needs_initial_undo = not getattr(self, "_right_drag_has_undo", False)
        self._suppress_next_undo = not needs_initial_undo
        try:
            self._on_tile_right_clicked(tile)
        finally:
            self._suppress_next_undo = False

    def _on_selection_updated(self, start, end):
        """Shift+左ドラッグの矩形範囲選択 — start/end は (x, y) タプル"""
        normalized = self._normalize_selection_endpoints(start, end)
        if normalized is None:
            self._selection_rect = None
            self.statusBar().showMessage(
                "16列目は範囲選択不可です（「16列目を編集」をONにしてください）", 2000
            )
            self._refresh_view()
            return
        start, end = normalized
        self._selection_rect = (start, end)
        # ステータスバーで通知
        if start and end:
            x1, y1 = min(start[0], end[0]), min(start[1], end[1])
            x2, y2 = max(start[0], end[0]), max(start[1], end[1])
            w, h = x2 - x1 + 1, y2 - y1 + 1
            self.statusBar().showMessage(
                f"選択範囲: ({x1},{y1})-({x2},{y2})  {w}×{h}", 0
            )
        self._refresh_view()

    def _on_selection_cleared(self):
        """選択解除（通常クリックなど）"""
        self._selection_rect = None
        self.statusBar().showMessage("", 0)
        self._refresh_view()

    # ====== 選択範囲操作（コピー / ペースト / 反転 / 削除） ======

    def _select_all_editable_area(self):
        """Select the normal editable playfield: columns 0-14, rows 0-11."""
        end_x = min(14, c.LEVEL_W - 1)
        end_y = c.LEVEL_H - 1
        self._on_selection_updated((0, 0), (end_x, end_y))

    def _is_col15_locked(self) -> bool:
        return hasattr(self, "chk_edit_col15") and not self.chk_edit_col15.isChecked()

    def _is_locked_col15_tile(self, tile) -> bool:
        return (
            tile is not None
            and len(tile) >= 1
            and tile[0] == 15
            and self._is_col15_locked()
        )

    def _show_col15_locked_message(self, message: str | None = None):
        self.statusBar().showMessage(
            message or "16列目は編集不可です（「16列目を編集」をONにしてください）",
            2000,
        )

    def _can_edit_tile_pos(self, x: int, y: int) -> bool:
        return 0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H and not (x == 15 and self._is_col15_locked())

    def _level_has_open_door_item(self, lv) -> bool:
        return any((int(item.element_no) & 0x3F) == 0x07 for item in getattr(lv, "items", []) or [])

    def _is_open_door_item(self, item) -> bool:
        return (int(getattr(item, "element_no", 0)) & 0x3F) == 0x07

    def _is_protected_open_door_item(self, lv, item) -> bool:
        return bool(
            self._is_open_door_item(item)
            and (
                lv.is_door_removed()
                or (
                    lv.is_key_removed()
                    and stage_ext.get_key_enemy_number(lv) <= 0
                )
            )
        )

    def _protected_open_door_message(self, lv, action: str = "edit") -> str:
        if lv.is_door_removed():
            reason = "扉削除中"
        elif lv.is_key_removed() and stage_ext.get_key_enemy_number(lv) <= 0:
            reason = "鍵が無いステージ"
        else:
            reason = "ステージ成立条件保護中"
        if action == "delete":
            return f"{reason}のOpen Doorは削除できません"
        if action == "replace":
            return f"{reason}のOpen Doorは他アイテムで上書きできません"
        if action == "block":
            return f"{reason}のOpen Doorにはブロックを置けません"
        return f"{reason}のOpen Doorは編集できません"

    def _can_delete_key_meta(self, lv) -> bool:
        return bool(self._level_has_open_door_item(lv) or stage_ext.get_key_enemy_number(lv) > 0)

    def _can_delete_door_meta(self, lv) -> bool:
        return bool(self._level_has_open_door_item(lv))

    def _key_enemy_is_required_for_exit(self, lv) -> bool:
        return bool(
            not lv.is_door_removed()
            and lv.is_key_removed()
            and not self._level_has_open_door_item(lv)
            and stage_ext.get_key_enemy_number(lv) > 0
        )

    def _tile_has_visible_key_or_door(self, lv, tile) -> bool:
        has_key = not lv.is_key_removed() and lv.fixed_key_pos == tile
        has_door = not lv.is_door_removed() and lv.fixed_door_pos == tile
        return has_key or has_door

    def _is_blocking_edit_block_cell(self, lv, tile) -> bool:
        x, y = tile
        if not (0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H):
            return False
        if lv.tiles[y][x] != Wall.NONE:
            return True
        block_marker_names = set(self._runtime_marker_names()) - {"visible_in_block_item_cells"}
        return any(tile in getattr(lv, name, set()) for name in block_marker_names)

    def _tile_has_actor_for_block_move(self, lv, tile) -> bool:
        return lv.fixed_start_pos == tile or lv.get_enemy_index(tile) >= 0

    def _clip_has_actor_block_overlap(self, lv, clip, ox: int, oy: int) -> bool:
        if clip is None:
            return False
        block_positions = {
            (x, y)
            for y in range(c.LEVEL_H)
            for x in range(c.LEVEL_W)
            if self._is_blocking_edit_block_cell(lv, (x, y))
        }
        actor_positions = {enemy.position for enemy in lv.enemies}
        start_pos = lv.fixed_start_pos

        for (rx, ry), _wall in clip.get("blocks", {}).items():
            tx, ty = ox + rx, oy + ry
            if self._can_edit_tile_pos(tx, ty):
                block_positions.add((tx, ty))
        for name, rel_cells in clip.get("runtime_markers", {}).items():
            if name == "visible_in_block_item_cells":
                continue
            for rx, ry in rel_cells:
                tx, ty = ox + rx, oy + ry
                if self._can_edit_tile_pos(tx, ty):
                    block_positions.add((tx, ty))
        for en_data in clip.get("enemies", []):
            rx, ry = en_data["rel_pos"]
            tx, ty = ox + rx, oy + ry
            if self._can_edit_tile_pos(tx, ty):
                actor_positions.add((tx, ty))
        for meta_data in clip.get("meta", []):
            if meta_data.get("kind") != "start":
                continue
            rx, ry = meta_data["rel_pos"]
            tx, ty = ox + rx, oy + ry
            if self._can_edit_tile_pos(tx, ty):
                start_pos = (tx, ty)
            break
        actor_positions.add(start_pos)
        return bool(block_positions.intersection(actor_positions))

    def _clip_has_item_block_overlap(self, lv, clip, ox: int, oy: int) -> bool:
        if clip is None:
            return False
        block_positions = {
            (x, y)
            for y in range(c.LEVEL_H)
            for x in range(c.LEVEL_W)
            if self._is_blocking_edit_block_cell(lv, (x, y))
        }
        item_positions = {item.position for item in lv.items}

        for (rx, ry), _wall in clip.get("blocks", {}).items():
            tx, ty = ox + rx, oy + ry
            if self._can_edit_tile_pos(tx, ty):
                block_positions.add((tx, ty))
        for name, rel_cells in clip.get("runtime_markers", {}).items():
            if name == "visible_in_block_item_cells":
                continue
            for rx, ry in rel_cells:
                tx, ty = ox + rx, oy + ry
                if self._can_edit_tile_pos(tx, ty):
                    block_positions.add((tx, ty))
        for it_data in clip.get("items", []):
            rx, ry = it_data["rel_pos"]
            tx, ty = ox + rx, oy + ry
            if self._can_edit_tile_pos(tx, ty):
                item_positions.add((tx, ty))
        return bool(block_positions.intersection(item_positions))

    def _show_actor_block_overlap_message(self, tile):
        self.statusBar().showMessage(
            f"主人公・敵とブロックは同じ位置にできません {tile}", 3000
        )

    def _block_absorb_flag_from_parts(self, wall_type, runtime_markers) -> int | None:
        markers = set(runtime_markers or ())
        if wall_type == Wall.NONE and "invisible_breakable_cells" in markers:
            return c.ITEM_FLAG_VISIBLE_IN_BLOCK
        if wall_type == Wall.WHITE and "breakable_white_cells" in markers:
            return c.ITEM_FLAG_WHITE_IN_BLOCK
        if wall_type == Wall.BROWN and "cracked_block_cells" in markers:
            return c.ITEM_FLAG_CRACKED_IN_BLOCK
        if wall_type in (Wall.BROWN, Wall.BROWN_WHITE) and not markers.intersection({
            "cracked_block_cells",
            "passable_brown_cells",
            "solid_brown_cells",
        }):
            return c.ITEM_FLAG_IN_BLOCK
        return None

    def _runtime_block_markers_at_tile(self, lv, tile) -> set:
        marker_names = set(self._runtime_marker_names()) - {"visible_in_block_item_cells"}
        return {name for name in marker_names if tile in getattr(lv, name, set())}

    def _block_absorb_flag_at_tile(self, lv, tile) -> int | None:
        x, y = tile
        if not (0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H):
            return None
        return self._block_absorb_flag_from_parts(
            lv.tiles[y][x],
            self._runtime_block_markers_at_tile(lv, tile),
        )

    def _show_block_absorb_rejected_message(self, tile):
        self.statusBar().showMessage(
            f"このブロックとはアイテム/鍵/扉を重ねられません {tile}", 3000
        )

    def _snapshot_absorb_target_state(self, lv, tile):
        state = {"tile": tile}
        if not lv.is_key_removed() and lv.fixed_key_pos == tile:
            state["key_status"] = lv.key_status
            state["key_visible"] = tile in getattr(lv, "visible_in_block_item_cells", set())
        if not lv.is_door_removed() and lv.fixed_door_pos == tile:
            from ..core import room_flags as _rf
            state["door_state"] = lv.room_flags & _rf.DOOR_STATE_MASK
        idx = lv.get_item_index(tile)
        if idx >= 0:
            item = lv.items[idx]
            state["item_ref"] = item
            state["item_element_no"] = item.element_no
            state["item_visible"] = tile in getattr(lv, "visible_in_block_item_cells", set())
        return state

    def _restore_absorb_target_state(self, lv, state):
        if not state:
            return
        tile = state.get("tile")
        visible_cells = getattr(lv, "visible_in_block_item_cells", set())
        if "key_status" in state:
            lv.key_status = state["key_status"]
            if state.get("key_visible"):
                visible_cells.add(tile)
            else:
                visible_cells.discard(tile)
        if "door_state" in state:
            from ..core import room_flags as _rf
            lv.room_flags = (lv.room_flags & ~_rf.DOOR_STATE_MASK) | state["door_state"]
        item = state.get("item_ref")
        if item is not None:
            item.element_no = state.get("item_element_no", item.element_no)
            if state.get("item_visible"):
                visible_cells.add(tile)
            else:
                visible_cells.discard(tile)

    def _apply_absorb_flag_to_tile(self, lv, tile, flag: int) -> bool:
        visible_cells = getattr(lv, "visible_in_block_item_cells", set())
        if not lv.is_key_removed() and lv.fixed_key_pos == tile:
            from ..core import constants as cc
            old_cracked = (
                tile in getattr(lv, "cracked_block_cells", set())
                and lv.key_status == cc.KEY_STATUS_HIDDEN
            )
            if flag == c.ITEM_FLAG_VISIBLE_IN_BLOCK:
                lv.key_status = cc.KEY_STATUS_NORMAL
                visible_cells.add(tile)
                if old_cracked:
                    lv.set_block(Wall.NONE, tile)
                else:
                    lv.cracked_block_cells.discard(tile)
            elif flag == c.ITEM_FLAG_CRACKED_IN_BLOCK:
                lv.key_status = cc.KEY_STATUS_HIDDEN
                visible_cells.discard(tile)
                lv.set_block(Wall.BROWN, tile)
                lv.cracked_block_cells.add(tile)
            else:
                lv.key_status = {
                    c.ITEM_FLAG_IN_BLOCK: cc.KEY_STATUS_IN_BLOCK,
                    c.ITEM_FLAG_WHITE_IN_BLOCK: cc.KEY_STATUS_WHITE_IN_BLOCK,
                }.get(flag, cc.KEY_STATUS_NORMAL)
                visible_cells.discard(tile)
                if old_cracked:
                    lv.set_block(Wall.NONE, tile)
                else:
                    lv.cracked_block_cells.discard(tile)
            return True
        if not lv.is_door_removed() and lv.fixed_door_pos == tile:
            if flag in (c.ITEM_FLAG_VISIBLE_IN_BLOCK, c.ITEM_FLAG_CRACKED_IN_BLOCK):
                return False
            from ..core import room_flags as _rf
            door_state = {
                c.ITEM_FLAG_IN_BLOCK: _rf.DOOR_STATE_IN_BLOCK,
                c.ITEM_FLAG_WHITE_IN_BLOCK: _rf.DOOR_STATE_WHITE_IN_BLOCK,
            }.get(flag, _rf.DOOR_STATE_NORMAL)
            lv.room_flags = (lv.room_flags & ~_rf.DOOR_STATE_MASK) | door_state
            return True
        idx = lv.get_item_index(tile)
        if idx < 0:
            return False
        item = lv.items[idx]
        if self._is_protected_open_door_item(lv, item):
            return False
        base = int(item.element_no) & 0x3F
        if flag in (c.ITEM_FLAG_WHITE_IN_BLOCK, c.ITEM_FLAG_VISIBLE_IN_BLOCK):
            if base > c.ITEM_WHITE_IN_BLOCK_MAX_BASE:
                return False
        if flag == c.ITEM_FLAG_CRACKED_IN_BLOCK:
            if base > c.ITEM_WHITE_IN_BLOCK_MAX_BASE:
                return False
            item.element_no = base
            visible_cells.discard(tile)
            lv.set_block(Wall.BROWN, tile)
            lv.cracked_block_cells.add(tile)
            return True
        if flag == c.ITEM_FLAG_VISIBLE_IN_BLOCK:
            item.element_no = base
            visible_cells.add(tile)
        else:
            item.element_no = base | flag
            visible_cells.discard(tile)
        return True

    def _apply_mirror_block_flag_to_tile(self, lv, tile, flag: int):
        flag = int(flag)
        if flag == c.ITEM_FLAG_IN_BLOCK:
            block_kind = BLOCK_BROWN
        elif flag == c.ITEM_FLAG_WHITE_IN_BLOCK:
            block_kind = BLOCK_BREAKABLE_WHITE
        elif flag == c.ITEM_FLAG_VISIBLE_IN_BLOCK:
            block_kind = BLOCK_INVISIBLE_BREAKABLE
        elif flag == c.ITEM_FLAG_CRACKED_IN_BLOCK:
            block_kind = BLOCK_CRACKED
        else:
            block_kind = BLOCK_NONE
        self._set_block_replace_kind(lv, tile, block_kind)
        return block_kind

    def _warn_demon_mirror_real_block_enemy_fall(self, lv, tile, block_kind):
        if block_kind not in (
            BLOCK_BROWN,
            BLOCK_BROWN_WHITE,
            BLOCK_BREAKABLE_WHITE,
            BLOCK_CRACKED,
            BLOCK_WHITE,
            BLOCK_INVISIBLE_BREAKABLE,
            BLOCK_INVISIBLE_SOLID,
            BLOCK_SOLID_BROWN,
        ):
            return
        if not any(tuple(m.position) == tile for m in lv.demon_mirrors):
            return
        self.statusBar().showMessage(
            "警告: ミラー上の実体ブロック配置はドラゴン/ガーゴイル/ゴーレムが落下して死にます",
            5000,
        )

    def _can_apply_absorb_flag_to_moving_item(self, item, flag: int) -> bool:
        if not self._absorb_allowed("item", flag):
            return False
        base = int(getattr(item, "element_no", 0)) & 0x3F
        if self._absorb_requires_low_item_id("item", flag):
            return base <= c.ITEM_WHITE_IN_BLOCK_MAX_BASE
        return True

    def _absorb_rule_matrix(self):
        # Placement/move overlap rules for block-contained targets.
        # Columns are brown, white, visible, cracked in-block flags.
        return {
            "item": {
                c.ITEM_FLAG_IN_BLOCK,
                c.ITEM_FLAG_WHITE_IN_BLOCK,
                c.ITEM_FLAG_VISIBLE_IN_BLOCK,
                c.ITEM_FLAG_CRACKED_IN_BLOCK,
            },
            "key": {
                c.ITEM_FLAG_IN_BLOCK,
                c.ITEM_FLAG_WHITE_IN_BLOCK,
                c.ITEM_FLAG_VISIBLE_IN_BLOCK,
                c.ITEM_FLAG_CRACKED_IN_BLOCK,
            },
            "door": {
                c.ITEM_FLAG_IN_BLOCK,
                c.ITEM_FLAG_WHITE_IN_BLOCK,
            },
        }

    def _absorb_allowed(self, target_kind: str, flag: int | None) -> bool:
        return flag in self._absorb_rule_matrix().get(target_kind, set())

    def _absorb_requires_low_item_id(self, target_kind: str, flag: int | None) -> bool:
        return target_kind == "item" and flag in (
            c.ITEM_FLAG_WHITE_IN_BLOCK,
            c.ITEM_FLAG_VISIBLE_IN_BLOCK,
            c.ITEM_FLAG_CRACKED_IN_BLOCK,
        )

    def _absorb_target_kind_at_tile(self, lv, tile) -> str | None:
        if not lv.is_key_removed() and lv.fixed_key_pos == tile:
            return "key"
        if not lv.is_door_removed() and lv.fixed_door_pos == tile:
            return "door"
        if lv.get_item_index(tile) >= 0:
            return "item"
        return None

    def _can_absorb_flag_to_target_at_tile(self, lv, tile, flag: int | None) -> bool:
        target_kind = self._absorb_target_kind_at_tile(lv, tile)
        if target_kind is None or not self._absorb_allowed(target_kind, flag):
            return False
        if target_kind != "item" or not self._absorb_requires_low_item_id(target_kind, flag):
            return True
        idx = lv.get_item_index(tile)
        if idx < 0:
            return False
        base = int(lv.items[idx].element_no) & 0x3F
        return base <= c.ITEM_WHITE_IN_BLOCK_MAX_BASE

    def _item_absorb_flag_for_move(self, lv, item, tile) -> int | None:
        if item is None:
            return None
        if item.is_white_in_block():
            return c.ITEM_FLAG_WHITE_IN_BLOCK
        if item.is_in_block():
            return c.ITEM_FLAG_IN_BLOCK
        if tile in getattr(lv, "visible_in_block_item_cells", set()):
            return c.ITEM_FLAG_VISIBLE_IN_BLOCK
        if (
            tile in getattr(lv, "cracked_block_cells", set())
            and self._can_apply_absorb_flag_to_moving_item(item, c.ITEM_FLAG_CRACKED_IN_BLOCK)
        ):
            return c.ITEM_FLAG_CRACKED_IN_BLOCK
        return None

    def _detach_item_absorb_state_for_move(self, lv, item, tile) -> int | None:
        flag = self._item_absorb_flag_for_move(lv, item, tile)
        if flag is None:
            return None
        base = int(item.element_no) & 0x3F
        item.element_no = base
        visible_cells = getattr(lv, "visible_in_block_item_cells", set())
        visible_cells.discard(tile)
        if flag in (c.ITEM_FLAG_IN_BLOCK, c.ITEM_FLAG_CRACKED_IN_BLOCK):
            lv.set_block(Wall.NONE, tile)
        return flag

    def _clear_moving_item_absorb_state(self, lv, mp):
        flag = mp.get("move_absorb_flag")
        if flag is None:
            return
        tile = mp.get("current_pos")
        item = mp.get("ref")
        if item is not None:
            item.element_no = int(item.element_no) & 0x3F
        if tile is None:
            return
        visible_cells = getattr(lv, "visible_in_block_item_cells", set())
        if flag == c.ITEM_FLAG_VISIBLE_IN_BLOCK:
            visible_cells.discard(tile)
        elif flag == c.ITEM_FLAG_CRACKED_IN_BLOCK:
            lv.set_block(Wall.NONE, tile)

    def _apply_moving_item_absorb_state(self, lv, mp, tile):
        item = mp.get("ref")
        if item is None:
            return
        flag = mp.get("move_absorb_flag")
        base = int(item.element_no) & 0x3F
        visible_cells = getattr(lv, "visible_in_block_item_cells", set())
        if flag == c.ITEM_FLAG_VISIBLE_IN_BLOCK:
            item.element_no = base
            visible_cells.add(tile)
        elif flag == c.ITEM_FLAG_CRACKED_IN_BLOCK:
            item.element_no = base
            visible_cells.discard(tile)
            lv.set_block(Wall.BROWN, tile)
            lv.cracked_block_cells.add(tile)
        elif flag in (c.ITEM_FLAG_IN_BLOCK, c.ITEM_FLAG_WHITE_IN_BLOCK):
            item.element_no = base | flag
            visible_cells.discard(tile)
        mp["current_pos"] = tile

    def _key_absorb_flag_for_move(self, lv, tile) -> int | None:
        from ..core import constants as cc
        if tile in getattr(lv, "visible_in_block_item_cells", set()):
            return c.ITEM_FLAG_VISIBLE_IN_BLOCK
        if (
            tile in getattr(lv, "cracked_block_cells", set())
            and lv.key_status == cc.KEY_STATUS_HIDDEN
        ):
            return c.ITEM_FLAG_CRACKED_IN_BLOCK
        if lv.key_status == cc.KEY_STATUS_WHITE_IN_BLOCK:
            return c.ITEM_FLAG_WHITE_IN_BLOCK
        if lv.key_status == cc.KEY_STATUS_IN_BLOCK:
            return c.ITEM_FLAG_IN_BLOCK
        return None

    def _detach_key_absorb_state_for_move(self, lv, tile) -> int | None:
        from ..core import constants as cc
        flag = self._key_absorb_flag_for_move(lv, tile)
        if flag is None:
            return None
        visible_cells = getattr(lv, "visible_in_block_item_cells", set())
        visible_cells.discard(tile)
        if flag == c.ITEM_FLAG_CRACKED_IN_BLOCK:
            lv.set_block(Wall.NONE, tile)
        lv.key_status = cc.KEY_STATUS_NORMAL
        return flag

    def _can_apply_absorb_flag_to_moving_key(self, flag: int | None) -> bool:
        return self._absorb_allowed("key", flag)

    def _clear_moving_key_absorb_state(self, lv, mp):
        from ..core import constants as cc
        tile = mp.get("current_pos")
        if tile is None:
            return
        flag = mp.pop("active_absorb_flag", mp.get("move_absorb_flag"))
        visible_cells = getattr(lv, "visible_in_block_item_cells", set())
        visible_cells.discard(tile)
        if flag == c.ITEM_FLAG_CRACKED_IN_BLOCK:
            lv.set_block(Wall.NONE, tile)
        lv.key_status = cc.KEY_STATUS_NORMAL

    def _apply_moving_key_absorb_state(self, lv, mp, tile, flag=None):
        from ..core import constants as cc
        if flag is None:
            flag = mp.get("move_absorb_flag")
        visible_cells = getattr(lv, "visible_in_block_item_cells", set())
        if flag == c.ITEM_FLAG_VISIBLE_IN_BLOCK:
            lv.key_status = cc.KEY_STATUS_NORMAL
            visible_cells.add(tile)
        elif flag == c.ITEM_FLAG_CRACKED_IN_BLOCK:
            lv.key_status = cc.KEY_STATUS_HIDDEN
            visible_cells.discard(tile)
            lv.set_block(Wall.BROWN, tile)
            lv.cracked_block_cells.add(tile)
        else:
            lv.key_status = {
                c.ITEM_FLAG_IN_BLOCK: cc.KEY_STATUS_IN_BLOCK,
                c.ITEM_FLAG_WHITE_IN_BLOCK: cc.KEY_STATUS_WHITE_IN_BLOCK,
            }.get(flag, cc.KEY_STATUS_NORMAL)
            visible_cells.discard(tile)
        if flag is not None:
            mp["active_absorb_flag"] = flag
        mp["current_pos"] = tile

    def _door_absorb_flag_for_move(self, lv) -> int | None:
        from ..core import room_flags as _rf
        door_state = lv.room_flags & _rf.DOOR_STATE_MASK
        if door_state == _rf.DOOR_STATE_WHITE_IN_BLOCK:
            return c.ITEM_FLAG_WHITE_IN_BLOCK
        if door_state == _rf.DOOR_STATE_IN_BLOCK:
            return c.ITEM_FLAG_IN_BLOCK
        return None

    def _detach_door_absorb_state_for_move(self, lv) -> int | None:
        from ..core import room_flags as _rf
        flag = self._door_absorb_flag_for_move(lv)
        lv.room_flags = (lv.room_flags & ~_rf.DOOR_STATE_MASK) | _rf.DOOR_STATE_NORMAL
        return flag

    def _can_apply_absorb_flag_to_moving_door(self, flag: int | None) -> bool:
        return self._absorb_allowed("door", flag)

    def _clear_moving_door_absorb_state(self, lv, mp):
        from ..core import room_flags as _rf
        lv.room_flags = (lv.room_flags & ~_rf.DOOR_STATE_MASK) | _rf.DOOR_STATE_NORMAL
        mp.pop("active_absorb_flag", None)

    def _apply_moving_door_absorb_state(self, lv, mp, tile, flag=None):
        from ..core import room_flags as _rf
        if flag is None:
            flag = mp.get("move_absorb_flag")
        door_state = {
            c.ITEM_FLAG_IN_BLOCK: _rf.DOOR_STATE_IN_BLOCK,
            c.ITEM_FLAG_WHITE_IN_BLOCK: _rf.DOOR_STATE_WHITE_IN_BLOCK,
        }.get(flag, _rf.DOOR_STATE_NORMAL)
        lv.room_flags = (lv.room_flags & ~_rf.DOOR_STATE_MASK) | door_state
        if flag is not None:
            mp["active_absorb_flag"] = flag
        mp["current_pos"] = tile

    def _restore_drag_meta_absorbed_block(self, lv, mp):
        state = mp.pop("absorbed_block_state", None)
        if not state:
            return
        tile = state.get("tile")
        if tile is None:
            return
        x, y = tile
        lv.tiles[y][x] = state.get("wall_type", Wall.NONE)
        self._pop_runtime_markers_at(lv, tile)
        self._restore_runtime_markers_at(lv, tile, state.get("runtime_markers", set()))
        visible_cells = getattr(lv, "visible_in_block_item_cells", set())
        if state.get("visible_cell"):
            visible_cells.add(tile)
        else:
            visible_cells.discard(tile)

    def _save_drag_meta_absorbed_block(self, lv, mp, tile):
        x, y = tile
        visible_cells = getattr(lv, "visible_in_block_item_cells", set())
        mp["absorbed_block_state"] = {
            "tile": tile,
            "wall_type": lv.tiles[y][x],
            "runtime_markers": self._runtime_markers_at(lv, tile),
            "visible_cell": tile in visible_cells,
        }

    def _apply_absorb_flag_to_moving_key(self, lv, mp, tile, flag: int) -> bool:
        if not self._can_apply_absorb_flag_to_moving_key(flag):
            return False
        self._save_drag_meta_absorbed_block(lv, mp, tile)
        self._apply_moving_key_absorb_state(lv, mp, tile, flag)
        return True

    def _apply_absorb_flag_to_moving_door(self, lv, mp, tile, flag: int) -> bool:
        if not self._can_apply_absorb_flag_to_moving_door(flag):
            return False
        self._save_drag_meta_absorbed_block(lv, mp, tile)
        self._apply_moving_door_absorb_state(lv, mp, tile, flag)
        return True

    def _restore_drag_item_absorbed_block(self, lv, mp):
        state = mp.pop("absorbed_block_state", None)
        if not state:
            return
        tile = state.get("tile")
        if tile is None:
            return
        x, y = tile
        lv.tiles[y][x] = state.get("wall_type", Wall.NONE)
        self._pop_runtime_markers_at(lv, tile)
        self._restore_runtime_markers_at(lv, tile, state.get("runtime_markers", set()))
        item = mp.get("ref")
        if item is not None:
            item.element_no = state.get("item_element_no", item.element_no)
            visible_cells = getattr(lv, "visible_in_block_item_cells", set())
            if state.get("item_visible"):
                visible_cells.add(tile)
            else:
                visible_cells.discard(tile)

    def _apply_absorb_flag_to_moving_item(self, lv, mp, tile, flag: int) -> bool:
        item = mp.get("ref")
        if item is None or not self._can_apply_absorb_flag_to_moving_item(item, flag):
            return False
        visible_cells = getattr(lv, "visible_in_block_item_cells", set())
        x, y = tile
        old_pos = item.position
        mp["absorbed_block_state"] = {
            "tile": tile,
            "wall_type": lv.tiles[y][x],
            "runtime_markers": self._pop_runtime_markers_at(lv, tile),
            "item_element_no": item.element_no,
            "item_visible": old_pos in visible_cells,
        }
        visible_cells.discard(old_pos)
        base = int(item.element_no) & 0x3F
        item.position = tile
        if flag == c.ITEM_FLAG_CRACKED_IN_BLOCK:
            lv.tiles[y][x] = Wall.BROWN
            lv.cracked_block_cells.add(tile)
            item.element_no = base
            visible_cells.discard(tile)
        elif flag == c.ITEM_FLAG_VISIBLE_IN_BLOCK:
            lv.tiles[y][x] = Wall.NONE
            item.element_no = base
            visible_cells.add(tile)
        else:
            lv.tiles[y][x] = Wall.NONE
            item.element_no = base | flag
            visible_cells.discard(tile)
        mp["current_pos"] = tile
        return True

    def _tile_has_absorb_target(self, lv, tile) -> bool:
        return bool(
            (not lv.is_key_removed() and lv.fixed_key_pos == tile) or
            (not lv.is_door_removed() and lv.fixed_door_pos == tile) or
            lv.get_item_index(tile) >= 0
        )

    def _can_apply_absorb_flag_to_tile(self, lv, tile, flag: int) -> bool:
        if not self._can_absorb_flag_to_target_at_tile(lv, tile, flag):
            return False
        if not lv.is_key_removed() and lv.fixed_key_pos == tile:
            return True
        if not lv.is_door_removed() and lv.fixed_door_pos == tile:
            return True
        idx = lv.get_item_index(tile)
        if idx < 0:
            return False
        item = lv.items[idx]
        if self._is_protected_open_door_item(lv, item):
            return False
        return True

    def _clip_has_start_enemy_overlap(self, lv, clip, ox: int, oy: int) -> bool:
        if clip is None:
            return False
        start_pos = lv.fixed_start_pos
        for meta_data in clip.get("meta", []):
            if meta_data.get("kind") != "start":
                continue
            rx, ry = meta_data["rel_pos"]
            tx, ty = ox + rx, oy + ry
            if self._can_edit_tile_pos(tx, ty):
                start_pos = (tx, ty)
            break
        enemy_positions = {enemy.position for enemy in lv.enemies}
        for en_data in clip.get("enemies", []):
            rx, ry = en_data["rel_pos"]
            tx, ty = ox + rx, oy + ry
            if self._can_edit_tile_pos(tx, ty):
                enemy_positions.add((tx, ty))
        return start_pos in enemy_positions

    def _clip_has_key_door_item_overlap(self, lv, clip, ox: int, oy: int) -> bool:
        if clip is None:
            return False
        key_pos = None if lv.is_key_removed() else lv.fixed_key_pos
        door_pos = None if lv.is_door_removed() else lv.fixed_door_pos
        seal_positions = {
            tuple(getattr(mi, "position", (-1, -1)))
            for mi in getattr(self.config, "level_meta_items", []) or []
            if int(getattr(mi, "level_no", -1)) == self.current_level_no
            and self._stage_level_meta_kind(int(getattr(mi, "no", -1))) == "solomon_seal"
        }
        for meta_data in clip.get("meta", []):
            kind = meta_data.get("kind")
            if kind not in ("key", "door", "level_meta"):
                continue
            rx, ry = meta_data["rel_pos"]
            tx, ty = ox + rx, oy + ry
            if not self._can_edit_tile_pos(tx, ty):
                continue
            if kind == "key":
                key_pos = (tx, ty)
            elif kind == "door":
                door_pos = (tx, ty)
            elif kind == "level_meta" and self.config is not None:
                idx = meta_data.get("index", -1)
                level_meta_items = getattr(self.config, "level_meta_items", [])
                if 0 <= idx < len(level_meta_items):
                    mi = level_meta_items[idx]
                    if self._stage_level_meta_kind(int(getattr(mi, "no", -1))) == "solomon_seal":
                        seal_positions.discard(tuple(getattr(mi, "position", (-1, -1))))
                        seal_positions.add((tx, ty))
        item_positions = {item.position for item in lv.items}
        for it_data in clip.get("items", []):
            rx, ry = it_data["rel_pos"]
            tx, ty = ox + rx, oy + ry
            if self._can_edit_tile_pos(tx, ty):
                item_positions.add((tx, ty))
        return (
            key_pos in item_positions
            or door_pos in item_positions
            or any(pos in item_positions for pos in seal_positions)
        )

    def _show_start_enemy_overlap_message(self, tile):
        self.statusBar().showMessage(
            f"主人公と敵は同じ位置にできません（開始直後に死亡します） {tile}", 3000
        )

    def _show_key_door_item_overlap_message(self, tile):
        self.statusBar().showMessage(
            f"鍵・扉・ソロモンの紋章とアイテムは同じ位置にできません {tile}", 3000
        )

    def _clip_targets_locked_col15(self, clip, ox: int, oy: int) -> bool:
        """Return True if moving clip content would edit locked column 15."""
        if clip is None or not self._is_col15_locked():
            return False

        def hits_locked_col15(rel_pos):
            rx, ry = rel_pos
            tx, ty = ox + rx, oy + ry
            return 0 <= ty < c.LEVEL_H and tx == 15

        for rel_pos in clip.get("blocks", {}):
            if hits_locked_col15(rel_pos):
                return True
        for rel_cells in clip.get("runtime_markers", {}).values():
            for rel_pos in rel_cells:
                if hits_locked_col15(rel_pos):
                    return True
        for it_data in clip.get("items", []):
            if hits_locked_col15(it_data["rel_pos"]):
                return True
        for en_data in clip.get("enemies", []):
            if hits_locked_col15(en_data["rel_pos"]):
                return True
        for meta_data in clip.get("meta", []):
            if hits_locked_col15(meta_data["rel_pos"]):
                return True
        return False

    def _runtime_marker_names(self):
        return (
            "breakable_white_cells",
            "cracked_block_cells",
            "invisible_breakable_cells",
            "passable_white_cells",
            "invisible_solid_cells",
            "passable_brown_cells",
            "solid_brown_cells",
            "visible_in_block_item_cells",
        )

    def _pop_runtime_markers_at(self, level, pos) -> set:
        names = set()
        for name in self._runtime_marker_names():
            cells = getattr(level, name, set())
            if pos in cells:
                cells.discard(pos)
                names.add(name)
        return names

    def _runtime_markers_at(self, level, pos) -> set:
        names = set()
        for name in self._runtime_marker_names():
            cells = getattr(level, name, set())
            if pos in cells:
                names.add(name)
        return names

    def _restore_runtime_markers_at(self, level, pos, names):
        for name in names or ():
            getattr(level, name, set()).add(pos)

    def _normalize_selection_endpoints(self, start, end):
        if start is None or end is None:
            return (start, end)
        if not self._is_col15_locked():
            return (start, end)
        sx, sy = start
        ex, ey = end
        if min(sx, ex) >= 15:
            return None
        return ((min(sx, 14), sy), (min(ex, 14), ey))

    def _get_selection_bounds(self):
        """選択範囲の (x1, y1, x2, y2) を返す。なければ None"""
        if self._selection_rect is None:
            return None
        (sx, sy), (ex, ey) = self._selection_rect
        if sx is None or ex is None:
            return None
        x1, y1 = min(sx, ex), min(sy, ey)
        x2, y2 = max(sx, ex), max(sy, ey)
        if self._is_col15_locked():
            if x1 >= 15:
                return None
            x2 = min(x2, 14)
        return (x1, y1, x2, y2)

    def _build_clipboard_from_selection(self):
        """選択範囲の内容を dict として返す（self._clipboard は変更しない）"""
        bounds = self._get_selection_bounds()
        if bounds is None or not self.levels:
            return None
        x1, y1, x2, y2 = bounds
        lv = self.levels[self.current_level_no]
        clip = {
            "w": x2 - x1 + 1,
            "h": y2 - y1 + 1,
            "blocks": {},
            "runtime_markers": {},
            "items": [],
            "enemies": [],
            "meta": [],
        }
        for y in range(y1, y2 + 1):
            for x in range(x1, x2 + 1):
                w = lv.tiles[y][x]
                if w != Wall.NONE:
                    clip["blocks"][(x - x1, y - y1)] = w
        for name in self._runtime_marker_names():
            rel = set()
            for mx, my in getattr(lv, name, set()):
                if x1 <= mx <= x2 and y1 <= my <= y2:
                    rel.add((mx - x1, my - y1))
            if rel:
                clip["runtime_markers"][name] = rel
        for it in lv.items:
            ix, iy = it.position
            if x1 <= ix <= x2 and y1 <= iy <= y2:
                clip["items"].append({
                    "rel_pos": (ix - x1, iy - y1),
                    "element_no": it.element_no,
                })
        for en in lv.enemies:
            ex_, ey_ = en.position
            if x1 <= ex_ <= x2 and y1 <= ey_ <= y2:
                clip["enemies"].append({
                    "rel_pos": (ex_ - x1, ey_ - y1),
                    "element_no": en.element_no,
                })
        def add_meta(kind, pos):
            mx, my = pos
            if x1 <= mx <= x2 and y1 <= my <= y2:
                clip["meta"].append({
                    "kind": kind,
                    "rel_pos": (mx - x1, my - y1),
                })

        if not lv.is_key_removed():
            add_meta("key", lv.fixed_key_pos)
        if not lv.is_door_removed():
            add_meta("door", lv.fixed_door_pos)
        add_meta("start", lv.fixed_start_pos)
        if lv.constellation is not None:
            add_meta("constellation", lv.constellation.position)
        for mi, mirror in enumerate(lv.demon_mirrors):
            add_meta(f"mirror{mi + 1}", mirror.position)
        if self.config is not None:
            for idx, mi in enumerate(getattr(self.config, "level_meta_items", [])):
                if mi.level_no != self.current_level_no:
                    continue
                if mi.rom_offset < 0:
                    continue
                mx, my = mi.position
                if x1 <= mx <= x2 and y1 <= my <= y2:
                    clip["meta"].append({
                        "kind": "level_meta",
                        "index": idx,
                        "rel_pos": (mx - x1, my - y1),
                    })
        return clip

    def _copy_selection(self):
        """選択範囲を内部クリップボードへコピー"""
        clip = self._build_clipboard_from_selection()
        if clip is None:
            self.statusBar().showMessage("選択範囲がありません", 1500)
            return
        self._clipboard = clip
        total = (
            len(clip["blocks"]) + len(clip["items"]) +
            len(clip["enemies"]) + len(clip.get("meta", []))
        )
        self.statusBar().showMessage(
            f"コピー: {clip['w']}×{clip['h']} 範囲 ({total}要素)", 3000
        )

    def _paste_clipboard_at(self, clip, ox, oy):
        """clip 辞書を (ox, oy) を起点にレベルに貼る（Undoはこのメソッドでは押さない）"""
        if clip is None or not self.levels:
            return
        from ..core.element import LevelElement, ElementType
        lv = self.levels[self.current_level_no]
        for (rx, ry), w in clip["blocks"].items():
            tx, ty = ox + rx, oy + ry
            if self._can_edit_tile_pos(tx, ty):
                lv.tiles[ty][tx] = w
        for name, rel_cells in clip.get("runtime_markers", {}).items():
            cells = getattr(lv, name, set())
            for rx, ry in rel_cells:
                tx, ty = ox + rx, oy + ry
                if self._can_edit_tile_pos(tx, ty):
                    cells.add((tx, ty))
        for it_data in clip["items"]:
            rx, ry = it_data["rel_pos"]
            tx, ty = ox + rx, oy + ry
            if self._can_edit_tile_pos(tx, ty):
                if self._solomon_seal_meta_at(self.current_level_no, (tx, ty)) is not None:
                    continue
                idx = lv.get_item_index((tx, ty))
                if idx >= 0:
                    lv.delete_item(idx)
                lv.items.append(LevelElement(ElementType.ITEM, (tx, ty), it_data["element_no"]))
        for en_data in clip["enemies"]:
            rx, ry = en_data["rel_pos"]
            tx, ty = ox + rx, oy + ry
            if self._can_edit_tile_pos(tx, ty):
                lv.enemies.append(LevelElement(ElementType.ENEMY, (tx, ty), en_data["element_no"]))
        for meta_data in clip.get("meta", []):
            rx, ry = meta_data["rel_pos"]
            tx, ty = ox + rx, oy + ry
            if not self._can_edit_tile_pos(tx, ty):
                continue
            kind = meta_data["kind"]
            if kind == "key":
                lv.fixed_key_pos = (tx, ty)
            elif kind == "door":
                lv.fixed_door_pos = (tx, ty)
            elif kind == "start":
                lv.fixed_start_pos = (tx, ty)
            elif kind == "constellation" and lv.constellation is not None:
                lv.constellation.position = (tx, ty)
            elif kind == "mirror1" and len(lv.demon_mirrors) >= 1:
                lv.demon_mirrors[0].position = (tx, ty)
            elif kind == "mirror2" and len(lv.demon_mirrors) >= 2:
                lv.demon_mirrors[1].position = (tx, ty)
            elif kind == "level_meta" and self.config is not None:
                idx = meta_data.get("index", -1)
                level_meta_items = getattr(self.config, "level_meta_items", [])
                if 0 <= idx < len(level_meta_items):
                    mi = level_meta_items[idx]
                    mi.position = (tx, ty)
                    if self.rom is not None and 0 <= mi.rom_offset < len(self.rom.data):
                        from ..core.element import byte_from_position
                        self.rom.data[mi.rom_offset] = byte_from_position(mi.position)

    def _paste_clipboard(self):
        """クリップボードを選択範囲の左上 or ホバー位置にペースト"""
        if self._reject_read_only_edit():
            return
        if self._clipboard is None or not self.levels:
            self.statusBar().showMessage("クリップボードが空です", 1500)
            return
        bounds = self._get_selection_bounds()
        if bounds is not None:
            ox, oy = bounds[0], bounds[1]
        elif self._hover_tile is not None:
            ox, oy = self._hover_tile
        else:
            self.statusBar().showMessage("ペースト先が不明（選択 or ホバーが必要）", 2000)
            return

        if self._clip_has_start_enemy_overlap(self.levels[self.current_level_no], self._clipboard, ox, oy):
            self._show_start_enemy_overlap_message((ox, oy))
            return
        if self._clip_has_key_door_item_overlap(self.levels[self.current_level_no], self._clipboard, ox, oy):
            self._show_key_door_item_overlap_message((ox, oy))
            return
        self._push_undo()
        self._paste_clipboard_at(self._clipboard, ox, oy)
        self._refresh_key_enemy_spin_range()
        self._refresh_fairy_enemy_spin_range()
        self.statusBar().showMessage(f"ペースト: ({ox},{oy}) 起点", 2000)
        self._refresh_view()

    def _cut_selection(self):
        """切り取り = コピー + 範囲削除"""
        if self._reject_read_only_edit():
            return
        self._copy_selection()
        self._delete_in_selection()

    def _delete_in_selection(self):
        """選択範囲内の要素を全削除"""
        if self._reject_read_only_edit():
            return
        bounds = self._get_selection_bounds()
        if bounds is None or not self.levels:
            self.statusBar().showMessage("選択範囲がありません", 1500)
            return
        x1, y1, x2, y2 = bounds
        lv = self.levels[self.current_level_no]
        key_enemy_number = stage_ext.get_key_enemy_number(lv)
        if self._key_enemy_is_required_for_exit(lv) and key_enemy_number > 0:
            for idx, enemy in enumerate(lv.enemies):
                ex, ey = enemy.position
                if idx <= key_enemy_number - 1 and x1 <= ex <= x2 and y1 <= ey <= y2:
                    self.statusBar().showMessage(
                        "鍵メタが無いため、鍵持ち敵に影響する敵は範囲削除できません", 3000
                    )
                    return
        self._push_undo()
        # ブロック
        for y in range(y1, y2 + 1):
            for x in range(x1, x2 + 1):
                lv.tiles[y][x] = Wall.NONE
        for name in self._runtime_marker_names():
            cells = getattr(lv, name, set())
            setattr(lv, name, {
                pos for pos in cells
                if not (x1 <= pos[0] <= x2 and y1 <= pos[1] <= y2)
            })
        # アイテム
        lv.items = [it for it in lv.items
                    if self._is_protected_open_door_item(lv, it)
                    or not (x1 <= it.position[0] <= x2 and y1 <= it.position[1] <= y2)]
        # 敵
        old_enemy_count = len(lv.enemies)
        lv.enemies = [en for en in lv.enemies
                      if not (x1 <= en.position[0] <= x2 and y1 <= en.position[1] <= y2)]
        if len(lv.enemies) != old_enemy_count:
            self._refresh_key_enemy_spin_range(warn=True)
            self._refresh_fairy_enemy_spin_range(warn=True)
        self.statusBar().showMessage(
            f"範囲削除: ({x1},{y1})-({x2},{y2})", 2000
        )
        self._refresh_view()

    def _flip_selection_horizontal(self):
        """選択範囲を左右反転"""
        self._flip_selection(horizontal=True)

    def _flip_selection_vertical(self):
        """選択範囲を上下反転"""
        self._flip_selection(horizontal=False)

    def _flip_selection(self, horizontal: bool):
        if self._reject_read_only_edit():
            return
        bounds = self._get_selection_bounds()
        if bounds is None or not self.levels:
            self.statusBar().showMessage("選択範囲がありません", 1500)
            return
        x1, y1, x2, y2 = bounds
        self._push_undo()
        lv = self.levels[self.current_level_no]

        def flip_marker_set(name, fn):
            cells = getattr(lv, name, set())
            moved = set()
            for cx, cy in cells:
                if x1 <= cx <= x2 and y1 <= cy <= y2:
                    moved.add(fn(cx, cy))
                else:
                    moved.add((cx, cy))
            setattr(lv, name, moved)

        def flip_meta_positions(fn, horizontal: bool):
            def in_selection(pos):
                px, py = pos
                return x1 <= px <= x2 and y1 <= py <= y2

            def flip_constellation_pos(pos):
                cx, cy = pos
                if horizontal:
                    # The constellation graphic is 3 cells wide. Mirror its
                    # center cell, then convert back to the left-cell position.
                    center_x, center_y = fn(cx + 1, cy)
                    nx, ny = center_x - 1, center_y
                else:
                    # The constellation graphic is 2 cells tall.
                    nx, ny = cx, y1 + y2 - cy - 1
                nx = max(0, min(c.LEVEL_W - 3, nx))
                ny = max(0, min(c.LEVEL_H - 2, ny))
                return nx, ny

            if in_selection(lv.fixed_start_pos):
                lv.fixed_start_pos = fn(*lv.fixed_start_pos)
            if not lv.is_key_removed() and in_selection(lv.fixed_key_pos):
                lv.fixed_key_pos = fn(*lv.fixed_key_pos)
            if not lv.is_door_removed() and in_selection(lv.fixed_door_pos):
                lv.fixed_door_pos = fn(*lv.fixed_door_pos)
            if lv.constellation is not None and in_selection(lv.constellation.position):
                lv.constellation.position = flip_constellation_pos(lv.constellation.position)
            for mirror in lv.demon_mirrors:
                if in_selection(mirror.position):
                    mirror.position = fn(*mirror.position)
            if self.config is not None:
                from ..core.element import byte_from_position
                for mi in getattr(self.config, "level_meta_items", []):
                    if mi.level_no != self.current_level_no:
                        continue
                    if mi.rom_offset < 0:
                        continue
                    if not in_selection(mi.position):
                        continue
                    mi.position = fn(*mi.position)
                    if self.rom is not None and 0 <= mi.rom_offset < len(self.rom.data):
                        self.rom.data[mi.rom_offset] = byte_from_position(mi.position)

        if horizontal:
            flip_x = lambda cx, cy: (x1 + x2 - cx, cy)
            # ブロック左右反転
            for y in range(y1, y2 + 1):
                row = lv.tiles[y]
                left, right = x1, x2
                while left < right:
                    row[left], row[right] = row[right], row[left]
                    left += 1
                    right -= 1
            # アイテム/敵 位置反転
            for it in lv.items:
                ix, iy = it.position
                if x1 <= ix <= x2 and y1 <= iy <= y2:
                    it.position = flip_x(ix, iy)
            for en in lv.enemies:
                ex_, ey_ = en.position
                if x1 <= ex_ <= x2 and y1 <= ey_ <= y2:
                    en.position = flip_x(ex_, ey_)
                    en.element_no = _mirror_enemy_code_horizontal(en.element_no)
            flip_meta_positions(flip_x, horizontal=True)
            for name in self._runtime_marker_names():
                flip_marker_set(name, flip_x)
            self.statusBar().showMessage("左右反転", 2000)
        else:
            flip_y = lambda cx, cy: (cx, y1 + y2 - cy)
            # 上下反転
            for x in range(x1, x2 + 1):
                top, bottom = y1, y2
                while top < bottom:
                    lv.tiles[top][x], lv.tiles[bottom][x] = lv.tiles[bottom][x], lv.tiles[top][x]
                    top += 1
                    bottom -= 1
            for it in lv.items:
                ix, iy = it.position
                if x1 <= ix <= x2 and y1 <= iy <= y2:
                    it.position = flip_y(ix, iy)
            for en in lv.enemies:
                ex_, ey_ = en.position
                if x1 <= ex_ <= x2 and y1 <= ey_ <= y2:
                    en.position = flip_y(ex_, ey_)
            flip_meta_positions(flip_y, horizontal=False)
            for name in self._runtime_marker_names():
                flip_marker_set(name, flip_y)
            self.statusBar().showMessage("上下反転", 2000)

        self._refresh_view()

    def _on_tile_picked(self, tile: tuple):
        """Alt+左クリック: スポイト — その位置の要素をピッカーに取り込む

        優先順: 敵 > アイテム > メタ要素 > ブロック
        """
        if not self.levels:
            return
        if self._is_stage_compare_diff_view():
            self.statusBar().showMessage("差分表示中はスポイトできません。「現在」に戻すと使えます", 2500)
            return
        from .element_picker import (
            MODE_BLOCK, MODE_ITEM, MODE_ENEMY, MODE_META,
            BLOCK_BROWN, BLOCK_WHITE, BLOCK_BROWN_WHITE, BLOCK_CRACKED, BLOCK_BREAKABLE_WHITE,
            BLOCK_INVISIBLE_BREAKABLE, BLOCK_PASSABLE_WHITE, BLOCK_INVISIBLE_SOLID,
            BLOCK_PASSABLE_BROWN, BLOCK_SOLID_BROWN,
            ITEM_FLAG_NORMAL, ITEM_FLAG_HIDDEN, ITEM_FLAG_IN_BLOCK,
            ITEM_FLAG_WHITE_IN_BLOCK, ITEM_FLAG_VISIBLE_IN_BLOCK,
            ITEM_FLAG_CRACKED_IN_BLOCK,
        )
        lv = self.levels[self.current_level_no]
        x, y = tile

        # 敵 (最優先)
        idx = lv.get_enemy_index(tile)
        if idx >= 0:
            code = lv.enemies[idx].element_no
            # 実コード → ベースコード+スピード を逆引き
            from .element_picker import base_code_from_actual
            base, speed = base_code_from_actual(code)
            self.picker.set_enemy_speed(speed)
            self._set_picker_value(base, mode=MODE_ENEMY)
            self.statusBar().showMessage(
                f"スポイト: 敵 0x{code:02X} (base 0x{base:02X}, SP{speed}) を選択", 2500
            )
            return

        # アイテム
        idx = lv.get_item_index(tile)
        if idx >= 0:
            it = lv.items[idx]
            base = it.element_no & 0x3F
            flag = it.element_no & 0xC0
            self._set_picker_value(base, mode=MODE_ITEM)
            # フラグも反映
            if tile in getattr(lv, "visible_in_block_item_cells", set()):
                self.picker.rb_flag_visible_in_block.setChecked(True)
            elif (
                tile in getattr(lv, "cracked_block_cells", set())
                and flag == ITEM_FLAG_NORMAL
            ):
                self.picker.rb_flag_cracked_in_block.setChecked(True)
            elif flag == 0x40:
                self.picker.rb_flag_hidden.setChecked(True)
            elif flag == ITEM_FLAG_WHITE_IN_BLOCK:
                self.picker.rb_flag_white_in_block.setChecked(True)
            elif flag in (0x80, 0xC0):
                self.picker.rb_flag_in_block.setChecked(True)
            else:
                self.picker.rb_flag_normal.setChecked(True)
            self.statusBar().showMessage(
                f"スポイト: アイテム 0x{base:02X} を選択", 2000
            )
            return

        # メタ要素
        meta = None
        if lv.fixed_start_pos == tile:
            meta = "start"
        elif not lv.is_key_removed() and lv.fixed_key_pos == tile:
            meta = "key"
        elif not lv.is_door_removed() and lv.fixed_door_pos == tile:
            meta = "door"
        elif lv.demon_mirrors[0].position == tile:
            meta = "mirror1"
        elif lv.demon_mirrors[1].position == tile:
            meta = "mirror2"
        if meta:
            self._set_picker_value(meta, mode=MODE_META)
            self.statusBar().showMessage(f"スポイト: {meta} を選択", 2000)
            return

        # ブロック
        wall = lv.tiles[y][x]
        block_value = None
        block_label = None
        if wall == Wall.BROWN and tile in getattr(lv, "passable_brown_cells", set()):
            block_value, block_label = BLOCK_PASSABLE_BROWN, "すり抜ける土色壁"
        elif wall == Wall.BROWN and tile in getattr(lv, "solid_brown_cells", set()):
            block_value, block_label = BLOCK_SOLID_BROWN, "壊せない土色壁"
        elif wall == Wall.BROWN and tile in getattr(lv, "cracked_block_cells", set()):
            block_value, block_label = BLOCK_CRACKED, "ひび割れブロック"
        elif wall == Wall.BROWN:
            block_value, block_label = BLOCK_BROWN, "茶ブロック"
        elif wall == Wall.WHITE and tile in getattr(lv, "breakable_white_cells", set()):
            block_value, block_label = BLOCK_BREAKABLE_WHITE, "壊せる白壁"
        elif wall == Wall.WHITE and tile in getattr(lv, "passable_white_cells", set()):
            block_value, block_label = BLOCK_PASSABLE_WHITE, "WHITE visual / EMPTY behavior"
        elif wall == Wall.NONE and tile in getattr(lv, "invisible_breakable_cells", set()):
            block_value, block_label = BLOCK_INVISIBLE_BREAKABLE, "透明な壊せる壁"
        elif wall == Wall.NONE and tile in getattr(lv, "invisible_solid_cells", set()):
            block_value, block_label = BLOCK_INVISIBLE_SOLID, "EMPTY visual / WHITE solid"
        elif wall == Wall.WHITE:
            block_value, block_label = BLOCK_WHITE, "白ブロック"
        elif wall == Wall.BROWN_WHITE:
            block_value, block_label = BLOCK_BROWN_WHITE, "壊せる白"
        if block_value is not None:
            self._set_picker_value(block_value, mode=MODE_BLOCK)
            self.statusBar().showMessage(f"スポイト: {block_label} を選択", 2000)
            return

        self.statusBar().showMessage(
            f"スポイト: {tile} に何もありません", 1500
        )

    # ====== Keyboard shortcuts ======

    # ====== 設定画面 (F9) ======

    def _on_favorites_changed(self, slots: list):
        """ピッカーのお気に入りが変更されたら設定に保存"""
        # tupleはJSON化できないのでlistに変換
        norm = []
        for s in slots:
            if s is None:
                norm.append(None)
            elif isinstance(s, (list, tuple)) and len(s) == 2:
                norm.append([s[0], s[1]])
            else:
                norm.append(None)
        self._app_config["picker_favorites"] = norm
        from ..core.config import save_config
        save_config(self._app_config)

    def _on_block_order_changed(self, order: list):
        self._app_config["picker_block_order"] = list(order)
        from ..core.config import save_config
        save_config(self._app_config)

    def _on_picker_icon_size_changed(self, size: int):
        self._app_config["picker_icon_size"] = int(size)
        save_config(self._app_config)

    def _show_settings(self):
        from .settings_dialog import SettingsDialog
        dlg = SettingsDialog(self._app_config, parent=self)
        dlg.exec_()

    def _save_settings_dialog_state(self, dialog_config: dict):
        keys = (
            "settings_dialog_x",
            "settings_dialog_y",
            "settings_dialog_w",
            "settings_dialog_h",
            "settings_dialog_tab",
        )
        changed = False
        for key in keys:
            if key in dialog_config and self._app_config.get(key) != dialog_config[key]:
                self._app_config[key] = dialog_config[key]
                changed = True
        if changed:
            save_config(self._app_config)

    def _marker_color_config(self):
        from .level_view import DEFAULT_MARKER_COLORS
        return {
            key: self._app_config.get(key, default)
            for key, default in DEFAULT_MARKER_COLORS.items()
        }

    def _marker_shape_config(self):
        from .level_view import DEFAULT_MARKER_SHAPES
        return {
            key: self._app_config.get(key, default)
            for key, default in DEFAULT_MARKER_SHAPES.items()
        }

    def _apply_renderer_marker_settings(self):
        if self.level_renderer is None:
            return
        self.level_renderer.set_marker_overlay_scale(
            self._app_config.get("marker_overlay_scale", 3)
        )
        self.level_renderer.set_marker_colors(self._marker_color_config())
        self.level_renderer.set_marker_shapes(self._marker_shape_config())

    def _apply_settings(self, new_config: dict):
        """設定ダイアログから呼び出される。即時反映 + JSON保存"""
        self._app_config = dict(new_config)
        self._apply_shortcut_settings()
        self._apply_history_limit_settings()
        from ..core.config import save_config
        save_config(self._app_config)
        self._update_title()
        self._apply_theme()
        self._apply_font_size()
        self._apply_hover_info_popup_style()
        self._update_hover_info_popup(self._hover_tile)
        self.level_view.set_marker_overlay_scale(
            self._app_config.get("marker_overlay_scale", 3)
        )
        self.picker.set_marker_overlay_scale(
            self._app_config.get("marker_overlay_scale", 3)
        )
        self.level_view.set_marker_colors(self._marker_color_config())
        self.picker.set_marker_colors(self._marker_color_config())
        self.level_view.set_marker_shapes(self._marker_shape_config())
        self.picker.set_marker_shapes(self._marker_shape_config())
        if hasattr(self, "enemy_count_indicator"):
            self.enemy_count_indicator.set_slot_size(
                self._app_config.get("enemy_count_meter_slot_size", 18)
            )
        self._apply_renderer_marker_settings()
        self._refresh_view()
        if self.levels and self.level_renderer is not None:
            self._generate_all_thumbnails()
        self._apply_icon()

    def _autosave_keep_count(self) -> int:
        return normalize_int_setting(
            self._app_config.get("autosave_keep_count"),
            DEFAULT_AUTOSAVE_KEEP_COUNT,
            MIN_AUTOSAVE_KEEP_COUNT,
            MAX_AUTOSAVE_KEEP_COUNT,
        )

    def _apply_history_limit_settings(self):
        self._app_config["autosave_keep_count"] = self._autosave_keep_count()
        self._undo_limit = normalize_int_setting(
            self._app_config.get("undo_limit"),
            DEFAULT_UNDO_LIMIT,
            MIN_UNDO_LIMIT,
            MAX_UNDO_LIMIT,
        )
        self._app_config["undo_limit"] = self._undo_limit
        if len(self._undo_stack) > self._undo_limit:
            del self._undo_stack[:-self._undo_limit]
        if len(self._redo_stack) > self._undo_limit:
            del self._redo_stack[:-self._undo_limit]

    def _apply_theme(self):
        """configの画面グレー設定をアプリ全体に反映"""
        from PyQt5.QtWidgets import QApplication
        from .theme import build_app_stylesheet, DEFAULT_THEME_GRAY
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(
                build_app_stylesheet(
                    self._app_config.get("theme_gray", DEFAULT_THEME_GRAY)
                )
            )

    def _apply_font_size(self):
        """configのフォント設定(ファミリー/サイズ/太字)をアプリ全体に反映

        font_family 空 = アプリ標準ファミリー / font_size 0 = 標準サイズ
        """
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtGui import QFont
        family = self._app_config.get("font_family", "")
        size = self._app_config.get("font_size", 0)
        bold = bool(self._app_config.get("font_bold", False))

        font = QApplication.font()
        if family:
            font.setFamily(family)
        else:
            font.setFamily(self._default_font_family)
        if size > 0:
            font.setPointSize(size)
        else:
            font.setPointSize(self._default_font_size)
        font.setBold(bold)
        app = QApplication.instance()
        app.setFont(font)
        self.setFont(font)
        for widget in app.topLevelWidgets():
            widget.setFont(font)
            for child in widget.findChildren(QWidget):
                child.setFont(font)
            widget.updateGeometry()
            widget.update()

    def _apply_icon(self):
        """configのicon_pathをウィンドウアイコンに反映"""
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtGui import QIcon
        icon_path = self._app_config.get("icon_path", "")
        resolved_icon_path = resolve_project_path(icon_path) if icon_path else None
        if resolved_icon_path and resolved_icon_path.exists():
            icon = QIcon(str(resolved_icon_path))
            QApplication.instance().setWindowIcon(icon)
            self.setWindowIcon(icon)

    def _serialize_undo_entry(self, entry) -> dict:
        levels = self._undo_entry_levels(entry)
        level_nos = sorted(levels.keys())
        focus_level_no = self._undo_entry_focus_level_no(entry, level_nos)
        data = {
            "focus_level_no": int(focus_level_no),
            "levels": [],
        }
        for level_no in level_nos:
            elem = level_to_xml_element(levels[level_no])
            data["levels"].append({
                "level_no": int(level_no),
                "xml": ET.tostring(elem, encoding="unicode"),
            })
        if isinstance(entry, dict) and "rom_data" in entry:
            data["rom_data_b64"] = base64.b64encode(bytes(entry["rom_data"])).decode("ascii")
        return data

    def _deserialize_undo_entry(self, data: dict) -> dict:
        if not isinstance(data, dict):
            raise ValueError("undo entry is not an object")
        levels = {}
        for item in data.get("levels", []):
            level_no = int(item["level_no"])
            if not (0 <= level_no < len(self.levels)):
                continue
            elem = ET.fromstring(str(item["xml"]))
            levels[level_no] = xml_element_to_level(elem)
        if not levels:
            raise ValueError("undo entry has no levels")
        focus_level_no = int(data.get("focus_level_no", sorted(levels.keys())[0]))
        if focus_level_no not in levels:
            focus_level_no = sorted(levels.keys())[0]
        entry = {
            "focus_level_no": focus_level_no,
            "levels": levels,
        }
        rom_b64 = data.get("rom_data_b64")
        if rom_b64:
            entry["rom_data"] = base64.b64decode(str(rom_b64).encode("ascii"), validate=True)
        return entry

    def _write_autosave_undo_history(self, path: Path):
        payload = {
            "format": "solomon_customizer_autosave_undo",
            "format_version": 1,
            "app_version": __version__,
            "undo_limit": int(self._undo_limit),
            "undo": [self._serialize_undo_entry(e) for e in self._undo_stack[-self._undo_limit:]],
            "redo": [self._serialize_undo_entry(e) for e in self._redo_stack[-self._undo_limit:]],
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def _restore_autosave_undo_history(self, path: Path) -> bool:
        try:
            if not path.exists():
                self._clear_undo_history()
                return False
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            if payload.get("format") != "solomon_customizer_autosave_undo":
                raise ValueError("unknown undo history format")
            undo = [
                self._deserialize_undo_entry(e)
                for e in payload.get("undo", [])[-self._undo_limit:]
            ]
            redo = [
                self._deserialize_undo_entry(e)
                for e in payload.get("redo", [])[-self._undo_limit:]
            ]
            self._undo_stack = undo
            self._redo_stack = redo
            self._log(
                f"Undo/Redo履歴を復元: undo={len(undo)}, redo={len(redo)}"
            )
            return True
        except Exception as e:
            self._clear_undo_history()
            self._log(
                f"Undo/Redo履歴を復元できないため破棄: {type(e).__name__}: {e}"
            )
            return False

    def _write_autosave_manifest(self, autosave_path: Path, saved_at: str):
        undo_path = self._autosave_undo_file_for_rom(autosave_path)
        last_level_no = self.current_level_no
        if self._undo_stack:
            levels = self._undo_entry_levels(self._undo_stack[-1])
            last_level_no = self._undo_entry_focus_level_no(
                self._undo_stack[-1], sorted(levels.keys())
            )
        manifest = {
            "format": "solomon_customizer_autosave_meta",
            "latest": str(autosave_path),
            "latest_undo": str(undo_path),
            "autosave_path": str(autosave_path),
            "saved_at": saved_at,
            "source_path": self._loaded_source_path or self.last_loaded_path,
            "display_name": self.rom.display_name if self.rom else "",
            "last_level_no": int(last_level_no),
            "app_version": __version__,
        }
        path = self._autosave_manifest_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        self._write_autosave_metadata(autosave_path, manifest)

    def _prune_autosaves(self):
        autosaves = sorted(
            self._autosave_dir().glob("workstate_*.nes"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for old in autosaves[self._autosave_keep_count():]:
            try:
                old.unlink()
            except Exception:
                pass
            try:
                self._autosave_undo_file_for_rom(old).unlink()
            except Exception:
                pass
            try:
                self._autosave_meta_file_for_rom(old).unlink()
            except Exception:
                pass
        self._prune_missing_autosave_history()

    def _autosave_workstate(self) -> str:
        if not self.rom or self._is_read_only():
            return ""
        from datetime import datetime
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        saved_at = datetime.now().isoformat(timespec="seconds")
        out_dir = self._autosave_dir()
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"workstate_{stamp}.nes"
        saved_data = saver.build_saved_rom_data(
            self.rom,
            self.levels,
            self._panel_variant_settings_for_save(),
        )
        saver.write_rom_data(saved_data, str(path))
        self._write_autosave_undo_history(self._autosave_undo_file_for_rom(path))
        self._write_autosave_manifest(path, saved_at)
        self._prune_autosaves()
        self._remember_previous_workstate_history(str(path))
        self._log(f"作業状態を自動保存: {path}")
        return str(path)

    def restore_previous_workstate_if_available(self) -> bool:
        if self._app_config.get("last_session_restore_kind") == "readonly":
            if self._restore_previous_readonly_rom_if_available():
                return True
        path = self._latest_autosave_path()
        if not path:
            return self._restore_previous_readonly_rom_if_available()
        try:
            if not self._load_autosave_workstate(path, add_history=False):
                return False
            self._remember_previous_workstate_history(path)
            metadata = self._load_autosave_metadata(path)
            display_name = self._autosave_display_name_from_metadata(metadata, path)
            saved_at = self._format_autosave_saved_at(metadata.get("saved_at", ""))
            self.statusBar().showMessage(
                f"{display_name} の作業状態を復元しました: {saved_at} / Stage {self.current_level_no + 1}",
                5000,
            )
            self._log(
                f"前回の作業状態を復元: {display_name} / {saved_at} / {path} / Stage {self.current_level_no + 1}"
            )
            return True
        except Exception as e:
            QMessageBox.warning(
                self,
                "前回の作業状態を復元できません",
                f"{type(e).__name__}: {e}",
            )
            self._log(f"前回の作業状態を復元失敗: {type(e).__name__}: {e}")
            return False

    def _restore_previous_readonly_rom_if_available(self) -> bool:
        path = str(self._app_config.get("last_readonly_rom_path", "") or "")
        if not path:
            return False
        try:
            if not Path(path).exists():
                return False
            self.load_rom(
                path,
                add_history=False,
                status_message="前回の閲覧専用ROMを復元しました",
            )
            if not self._is_read_only():
                return False
            try:
                level_no = int(self._app_config.get("last_readonly_rom_level_no", 0))
            except Exception:
                level_no = 0
            if self.levels and 0 <= level_no < len(self.levels):
                self.spin_level.setValue(level_no + 1)
            self._remember_previous_workstate_history(path)
            self.statusBar().showMessage(
                f"前回の閲覧専用ROMを復元しました: Stage {self.current_level_no + 1}",
                5000,
            )
            self._log(
                f"前回の閲覧専用ROMを復元: {path} / Stage {self.current_level_no + 1}"
            )
            return True
        except Exception as e:
            QMessageBox.warning(
                self,
                "前回の閲覧専用ROMを復元できません",
                f"{type(e).__name__}: {e}",
            )
            self._log(f"前回の閲覧専用ROMを復元失敗: {type(e).__name__}: {e}")
            return False

    def closeEvent(self, event):
        """ウィンドウを閉じる時、現在の作業状態を自動保存する"""
        if self.rom and not self._is_read_only():
            try:
                path = self._autosave_workstate()
                self._app_config["last_session_restore_kind"] = "autosave"
                save_config(self._app_config)
                QMessageBox.information(
                    self,
                    "作業状態の自動保存",
                    "作業状態を自動保存しました。\n安全に終了します。\n\n"
                    "次回、ROMを指定せずに起動した場合は、この作業状態を自動的に復元します。\n\n"
                    f"{path}",
                )
            except Exception as e:
                if isinstance(e, saver.SavePreflightError):
                    detail = e.dialog_message()
                    log_msg = e.log_message()
                else:
                    detail = f"{type(e).__name__}: {e}"
                    log_msg = detail
                self._log(f"作業状態の自動保存失敗: {log_msg}")
                ans = QMessageBox.warning(
                    self,
                    "作業状態の自動保存に失敗",
                    "作業状態を自動保存できませんでした。\n"
                    "このまま終了すると、今回の変更が失われる可能性があります。\n\n"
                    f"{detail}\n\n"
                    "自動保存せずに終了しますか？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if ans != QMessageBox.Yes:
                    event.ignore()
                    return
        elif self.rom and self._is_read_only():
            self._remember_readonly_rom_state()
        # ウィンドウ状態を保存してから閉じる
        self._save_window_state()
        self._log("セッション終了")
        self._save_session_log()
        if getattr(self, "_restart_after_close", False):
            try:
                args = [sys.executable] + sys.argv
                subprocess.Popen(args, cwd=str(Path(__file__).parent.parent.parent))
            except Exception as e:
                self._restart_after_close = False
                QMessageBox.critical(self, "再起動失敗", f"{type(e).__name__}: {e}")
                self._log(f"再起動失敗: {type(e).__name__}: {e}")
                event.ignore()
                return
        event.accept()

    def _remember_readonly_rom_state(self):
        if not self.last_loaded_path:
            return
        try:
            self._app_config["last_session_restore_kind"] = "readonly"
            self._app_config["last_readonly_rom_path"] = str(self.last_loaded_path)
            self._app_config["last_readonly_rom_level_no"] = int(self.current_level_no)
            save_config(self._app_config)
            self._log(
                f"閲覧専用ROM状態を記録: {self.last_loaded_path} / Stage {self.current_level_no + 1}"
            )
        except Exception:
            pass

    def _save_session_log(self):
        """メモリに溜めた操作ログをファイルへ書き出す。

        保存先: <project_root>/logs/session_YYYYMMDD_HHMMSS.log
        セッション中に何も操作がない（ROM読込もしてない）場合は書き出さない。
        """
        if not self._session_log:
            return
        # 「セッション開始」と「セッション終了」しかない場合は無意味なので捨てる
        meaningful = [e for e in self._session_log
                      if not e.endswith("セッション開始") and not e.endswith("セッション終了")]
        if not meaningful:
            return
        try:
            from datetime import datetime
            stamp = self._session_start.strftime("%Y%m%d_%H%M%S")
            log_dir = Path(__file__).parent.parent.parent / "logs"
            log_dir.mkdir(exist_ok=True)
            log_path = log_dir / f"session_{stamp}.log"
            header = (
                f"# {APP_DISPLAY_NAME} セッションログ\n"
                f"# 開始: {self._session_start.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"# 終了: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"# バージョン: {__version__}\n\n"
            )
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(header)
                f.write("\n".join(self._session_log))
                f.write("\n")
        except Exception:
            pass  # ログ保存失敗でアプリを止めない

    def keyPressEvent(self, event):
        key = event.key()
        if self._event_matches_shortcut(event, "stage_compare") and self._stage_compare_png_image is not None:
            self._toggle_stage_compare_view()
            event.accept()
            return
        # Undo / Redo / 選択範囲操作
        if self._event_matches_shortcut(event, "redo_alt"):
            self._on_redo()
            return
        if self._event_matches_shortcut(event, "undo"):
            self._on_undo()
            return
        if self._event_matches_shortcut(event, "redo"):
            self._on_redo()
            return
        if self._event_matches_shortcut(event, "select_all"):
            self._select_all_editable_area()
            return
        if self._event_matches_shortcut(event, "clear_selection"):
            if self._selection_rect is not None:
                self._on_selection_cleared()
            return
        if self._event_matches_shortcut(event, "copy_selection"):
            self._copy_selection()
            return
        if self._event_matches_shortcut(event, "paste_selection"):
            self._paste_clipboard()
            return
        if self._event_matches_shortcut(event, "cut_selection"):
            self._cut_selection()
            return
        if self._event_matches_shortcut(event, "item_replace"):
            self._on_show_item_replace()
            return
        if self._event_matches_shortcut(event, "item_flag_toggle"):
            self._cycle_hover_item_flag()
            return
        if self._event_matches_shortcut(event, "item_flag_toggle_reverse"):
            self._cycle_hover_item_flag(reverse=True)
            return
        if self._event_matches_shortcut(event, "delete_hover_or_selection"):
            self._delete_hover_or_selection()
            return
        if self._event_matches_shortcut(event, "delete_hover_or_selection_alt"):
            self._delete_hover_or_selection()
            return
        if self._event_matches_shortcut(event, "clear_selection_escape"):
            if self._selection_rect is not None:
                self._on_selection_cleared()
            return
        for slot_action in (
            "favorite_1",
            "favorite_2",
            "favorite_3",
            "favorite_4",
            "favorite_5",
            "favorite_6",
            "favorite_7",
            "favorite_8",
            "favorite_9",
            "favorite_0",
        ):
            if self._event_matches_shortcut(event, slot_action):
                self._trigger_shortcut_action(slot_action)
                return
        for action in (
            "hover_enemy_left",
            "hover_enemy_right",
            "hover_enemy_up",
            "hover_enemy_down",
            "hover_enemy_speed",
            "hover_info",
            "hover_item_normal",
            "hover_item_hidden",
            "hover_item_in_block",
            "hover_item_white_in_block",
            "hover_item_visible_in_block",
            "hover_item_cracked_in_block",
        ):
            if self._event_matches_shortcut(event, action):
                if self._trigger_shortcut_action(action):
                    return
                super().keyPressEvent(event)
                return
        if self._event_matches_shortcut(event, "help"):
            self._show_keymap()
        elif self._event_matches_shortcut(event, "settings"):
            self._show_settings()
        elif self._event_matches_shortcut(event, "grid"):
            self.chk_grid.toggle()
        elif self._event_matches_shortcut(event, "flip_vertical"):
            self._flip_selection_vertical()
        elif self._event_matches_shortcut(event, "flip_horizontal"):
            self._flip_selection_horizontal()
        else:
            super().keyPressEvent(event)

    def _set_hover_item_flag(self, flag: int, label: str):
        """N/H/B shortcut: change the hovered item/key placement state."""
        flag = int(flag)
        if flag not in (c.ITEM_FLAG_VISIBLE_IN_BLOCK, c.ITEM_FLAG_CRACKED_IN_BLOCK):
            flag &= 0xC0
        if self._hover_tile is not None and self.levels:
            lv = self.levels[self.current_level_no]
            if not lv.is_key_removed() and lv.fixed_key_pos == self._hover_tile:
                if self._reject_read_only_edit():
                    return
                from ..core import constants as cc
                old_visible = self._hover_tile in getattr(lv, "visible_in_block_item_cells", set())
                old_cracked = (
                    self._hover_tile in getattr(lv, "cracked_block_cells", set())
                    and lv.key_status == cc.KEY_STATUS_HIDDEN
                )
                key_flag_map = {
                    0x00: cc.KEY_STATUS_NORMAL,
                    0x40: cc.KEY_STATUS_HIDDEN,
                    0x80: cc.KEY_STATUS_IN_BLOCK,
                    0xC0: cc.KEY_STATUS_WHITE_IN_BLOCK,
                }
                new_visible = flag == c.ITEM_FLAG_VISIBLE_IN_BLOCK
                new_cracked = flag == c.ITEM_FLAG_CRACKED_IN_BLOCK
                new_status = (
                    cc.KEY_STATUS_NORMAL if new_visible
                    else cc.KEY_STATUS_HIDDEN if new_cracked
                    else key_flag_map[flag]
                )
                if (
                    new_status == lv.key_status
                    and new_visible == old_visible
                    and new_cracked == old_cracked
                ):
                    self.statusBar().showMessage(
                        f"ホバー位置の鍵状態: {label}", 1500
                    )
                    return
                old_was_white = lv.is_key_white_in_block()
                self._push_undo()
                lv.key_status = new_status
                visible_cells = getattr(lv, "visible_in_block_item_cells", set())
                if new_visible:
                    visible_cells.add(self._hover_tile)
                else:
                    visible_cells.discard(self._hover_tile)
                if new_cracked:
                    lv.set_block(Wall.BROWN, self._hover_tile)
                    lv.cracked_block_cells.add(self._hover_tile)
                elif old_cracked:
                    lv.set_block(Wall.NONE, self._hover_tile)
                else:
                    lv.cracked_block_cells.discard(self._hover_tile)
                if new_status == cc.KEY_STATUS_WHITE_IN_BLOCK:
                    lv.set_block(Wall.NONE, self._hover_tile)
                elif old_was_white:
                    lv.set_block(Wall.NONE, self._hover_tile)
                self._refresh_view()
                self._refresh_thumbnails_after_edit()
                self._set_dirty(True)
                self._update_hover_info(self._hover_tile)
                self.statusBar().showMessage(
                    f"ホバー位置の鍵状態を{label}に変更", 1500
                )
                return

            if (flag != c.ITEM_FLAG_VISIBLE_IN_BLOCK and
                    not lv.is_door_removed() and lv.fixed_door_pos == self._hover_tile):
                if self._reject_read_only_edit():
                    return
                if flag == c.ITEM_FLAG_CRACKED_IN_BLOCK:
                    self.statusBar().showMessage(
                        "扉はひび割れブロック内状態にできません", 1500
                    )
                    return
                from ..core import room_flags as _rf
                old_state = lv.room_flags & _rf.DOOR_STATE_MASK
                state_by_flag = {
                    0x00: _rf.DOOR_STATE_NORMAL,
                    0x40: _rf.DOOR_STATE_HIDDEN,
                    0x80: _rf.DOOR_STATE_IN_BLOCK,
                    c.ITEM_FLAG_WHITE_IN_BLOCK: _rf.DOOR_STATE_WHITE_IN_BLOCK,
                }
                new_state = state_by_flag.get(flag, _rf.DOOR_STATE_NORMAL)
                if old_state == new_state:
                    state = {
                        _rf.DOOR_STATE_HIDDEN: "隠し",
                        _rf.DOOR_STATE_IN_BLOCK: "ブロック内",
                        _rf.DOOR_STATE_WHITE_IN_BLOCK: "白ブロック内",
                    }.get(old_state, "通常")
                    self.statusBar().showMessage(
                        f"ホバー位置の扉状態: {state}", 1500
                    )
                    return
                self._push_undo()
                lv.room_flags = (lv.room_flags & ~_rf.DOOR_STATE_MASK) | new_state
                self._refresh_view()
                self._refresh_thumbnails_after_edit()
                self._set_dirty(True)
                self._update_hover_info(self._hover_tile)
                self._update_info()
                self.statusBar().showMessage(
                    f"ホバー位置の扉状態を{label}に変更", 1500
                )
                return

            if flag == 0x40 and any(
                mirror.position == self._hover_tile for mirror in lv.demon_mirrors
            ):
                if self._reject_read_only_edit():
                    return
                item_no = 0x48
                idx = lv.get_item_index(self._hover_tile)
                if idx >= 0:
                    if lv.items[idx].element_no == item_no:
                        self.statusBar().showMessage(
                            "デーモンミラー上の隠しアイテムは設定済みです", 1500
                        )
                        return
                    self._push_undo()
                    lv.items[idx].element_no = item_no
                    action = "変更"
                else:
                    self._push_undo()
                    lv.items.append(LevelElement(ElementType.ITEM, self._hover_tile, item_no))
                    action = "追加"
                self._refresh_view()
                self._refresh_thumbnails_after_edit()
                self._set_dirty(True)
                self._update_hover_info(self._hover_tile)
                self.statusBar().showMessage(
                    f"デーモンミラー上に隠しアイテム 0x48 を{action}", 1500
                )
                return

            idx = lv.get_item_index(self._hover_tile)
            if idx >= 0:
                if self._reject_read_only_edit():
                    return
                item = lv.items[idx]
                if item.element_no >= c.ITEM_COPY_INDICATOR_MIN:
                    if not item.is_white_in_block():
                        self.statusBar().showMessage(
                            "このアイテム形式は状態変更できません", 1500
                        )
                        return
                tx, ty = self._hover_tile
                base = int(item.element_no) & 0x3F
                if flag == c.ITEM_FLAG_VISIBLE_IN_BLOCK:
                    if base > c.ITEM_WHITE_IN_BLOCK_MAX_BASE:
                        self.statusBar().showMessage(
                            f"このアイテムは透明ブロック内に入れられません: 0x{base:02X}", 1500
                        )
                        return
                    new_no = base
                elif flag == c.ITEM_FLAG_CRACKED_IN_BLOCK:
                    if base > c.ITEM_WHITE_IN_BLOCK_MAX_BASE:
                        self.statusBar().showMessage(
                            f"このアイテムはひび割れブロック内に入れられません: 0x{base:02X}", 1500
                        )
                        return
                    new_no = base
                elif flag == c.ITEM_FLAG_WHITE_IN_BLOCK:
                    if base > c.ITEM_WHITE_IN_BLOCK_MAX_BASE:
                        self.statusBar().showMessage(
                            f"このアイテムは白い壊せるブロック内に入れられません: 0x{base:02X}", 1500
                        )
                        return
                    new_no = base | c.ITEM_FLAG_WHITE_IN_BLOCK
                elif flag == c.ITEM_FLAG_IN_BLOCK and self._hover_tile in getattr(lv, "breakable_white_cells", set()):
                    new_no = base | c.ITEM_FLAG_WHITE_IN_BLOCK
                else:
                    new_no = base | flag
                old_visible = self._hover_tile in getattr(lv, "visible_in_block_item_cells", set())
                new_visible = flag == c.ITEM_FLAG_VISIBLE_IN_BLOCK
                old_cracked = (
                    self._hover_tile in getattr(lv, "cracked_block_cells", set())
                    and not item.is_in_block()
                    and not item.is_white_in_block()
                )
                new_cracked = flag == c.ITEM_FLAG_CRACKED_IN_BLOCK
                if new_no == item.element_no and old_visible == new_visible and old_cracked == new_cracked:
                    self.statusBar().showMessage(
                        f"ホバー位置のアイテム状態: {label}", 1500
                    )
                    return
                old_was_in_block = bool(int(item.element_no) & 0x80)
                clear_backing_block = (
                    (old_was_in_block or old_cracked)
                    and flag not in (
                        c.ITEM_FLAG_IN_BLOCK,
                        c.ITEM_FLAG_WHITE_IN_BLOCK,
                        c.ITEM_FLAG_VISIBLE_IN_BLOCK,
                        c.ITEM_FLAG_CRACKED_IN_BLOCK,
                    )
                    and (
                        lv.tiles[ty][tx] in (Wall.BROWN, Wall.BROWN_WHITE)
                        or self._hover_tile in getattr(lv, "breakable_white_cells", set())
                    )
                )
                self._push_undo()
                old_no = int(item.element_no) & 0xFF
                item.element_no = new_no
                visible_cells = getattr(lv, "visible_in_block_item_cells", set())
                if new_visible:
                    visible_cells.add(self._hover_tile)
                    lv.set_block(Wall.NONE, self._hover_tile)
                else:
                    visible_cells.discard(self._hover_tile)
                if flag == c.ITEM_FLAG_CRACKED_IN_BLOCK:
                    lv.set_block(Wall.BROWN, self._hover_tile)
                    lv.cracked_block_cells.add(self._hover_tile)
                if (new_no & 0x80) != 0:
                    lv.set_block(Wall.NONE, self._hover_tile)
                if clear_backing_block:
                    lv.set_block(Wall.NONE, self._hover_tile)
                self._refresh_view()
                self._refresh_thumbnails_after_edit()
                self._set_dirty(True)
                self._update_hover_info(self._hover_tile)
                self._log(
                    f"アイテム状態変更: L{self.current_level_no + 1} "
                    f"{self._hover_tile} 0x{old_no:02X}->0x{new_no:02X} {label}"
                )
                msg = f"ホバー位置のアイテム状態を{label}に変更"
                if clear_backing_block:
                    msg += "（元ブロックも削除）"
                self.statusBar().showMessage(msg, 1500)
                return
        self.statusBar().showMessage(
            "ホバー位置に状態変更できるアイテム/鍵/扉がありません", 1500
        )

    def _on_level_view_hover_action(self, action: str):
        if action == "speed":
            self._cycle_hover_enemy_speed()
        elif action == "info":
            self._toggle_hover_info_popup()

    def _toggle_hover_info_popup(self):
        enabled = not bool(self._app_config.get("hover_info_popup_enabled", False))
        self._app_config["hover_info_popup_enabled"] = enabled
        save_config(self._app_config)
        if enabled:
            self._update_hover_info_popup(self._hover_tile)
            self.statusBar().showMessage("ホバー情報ポップアップ: ON", 1500)
        else:
            self._hide_hover_info_popup()
            self.statusBar().showMessage("ホバー情報ポップアップ: OFF", 1500)

    def _cycle_hover_enemy_speed(self) -> bool:
        if self._hover_tile is None or not self.levels:
            return False
        lv = self.levels[self.current_level_no]
        idx = lv.get_enemy_index(self._hover_tile)
        if idx < 0:
            return False
        if self._reject_read_only_edit():
            return True

        enemy = lv.enemies[idx]
        old_no = int(enemy.element_no) & 0xFF
        base_code, speed, available = self._enemy_speed_info(old_no)
        if len(available) <= 1:
            self.statusBar().showMessage("この敵はスピード変更に対応していません", 1500)
            return True
        speeds = [sp for sp, _code in available]
        try:
            current_idx = speeds.index(speed)
        except ValueError:
            current_idx = 0
        next_speed = speeds[(current_idx + 1) % len(speeds)]
        new_no = apply_enemy_speed(base_code, next_speed)
        if new_no == old_no:
            self.statusBar().showMessage(f"この敵はSP{speed}です", 1500)
            return True

        self._push_undo()
        enemy.element_no = new_no
        self._refresh_view()
        self._refresh_thumbnails_after_edit()
        self._set_dirty(True)
        self._update_hover_info(self._hover_tile)
        self._update_hover_info_popup(self._hover_tile)
        old_desc = (
            self.config.enemy_desc.get(old_no, f"0x{old_no:02X}")
            if self.config else f"0x{old_no:02X}"
        )
        new_desc = (
            self.config.enemy_desc.get(new_no, f"0x{new_no:02X}")
            if self.config else f"0x{new_no:02X}"
        )
        self._log(
            f"敵スピード変更: L{self.current_level_no + 1} {self._hover_tile} "
            f"0x{old_no:02X}->0x{new_no:02X} {old_desc}->{new_desc}"
        )
        self.statusBar().showMessage(
            f"ホバー位置の敵スピードをSP{next_speed}へ変更: {new_desc}", 1500
        )
        return True

    def _set_hover_enemy_direction(self, direction: str) -> bool:
        """Arrow shortcut: change the hovered enemy to the same enemy facing another direction."""
        if self._hover_tile is None or not self.levels:
            return False
        lv = self.levels[self.current_level_no]
        idx = lv.get_enemy_index(self._hover_tile)
        if idx < 0:
            return False
        if self._reject_read_only_edit():
            return True

        enemy = lv.enemies[idx]
        old_no = int(enemy.element_no) & 0xFF
        new_no = enemy_direction_variant(self.config, old_no, direction)
        direction_label = DIRECTION_LABELS.get(direction, direction)
        if new_no is None:
            self.statusBar().showMessage(
                f"この敵は{direction_label}向きに変更できません", 1500
            )
            return True
        if new_no == old_no:
            self.statusBar().showMessage(
                f"この敵はすでに{direction_label}向きです", 1500
            )
            return True

        self._push_undo()
        enemy.element_no = new_no
        self._refresh_view()
        self._refresh_thumbnails_after_edit()
        self._set_dirty(True)
        self._update_hover_info(self._hover_tile)
        self._update_hover_info_popup(self._hover_tile)
        old_desc = (
            self.config.enemy_desc.get(old_no, f"0x{old_no:02X}")
            if self.config else f"0x{old_no:02X}"
        )
        new_desc = (
            self.config.enemy_desc.get(new_no, f"0x{new_no:02X}")
            if self.config else f"0x{new_no:02X}"
        )
        self._log(
            f"敵向き変更: L{self.current_level_no + 1} {self._hover_tile} "
            f"0x{old_no:02X}->0x{new_no:02X} {old_desc}->{new_desc}"
        )
        self.statusBar().showMessage(
            f"ホバー位置の敵を{direction_label}向きに変更: {new_desc}", 1500
        )
        return True

    def _quick_place_at_hover(self, n: int):
        """数字キー 0-9 でホバー位置にクイック配置

        モード別:
          BLOCK: 0=消去, 1=茶, 2=白, 3=ひび割れ, 4=壊せる白
          ITEM : 1-9 = ピッカー先頭から9件目までのアイテム、0=既存削除
          ENEMY: 1-9 = ピッカー先頭から9件目までの敵、0=既存削除
          META : 1-5 = start/key/door/mirror1/mirror2
        """
        if self._hover_tile is None or not self.levels:
            return
        if self._reject_read_only_edit():
            return
        mode, _ = self.picker.get_current()
        from .element_picker import (
            BLOCK_NONE, BLOCK_BROWN, BLOCK_WHITE, BLOCK_BROWN_WHITE,
            BLOCK_CRACKED, BLOCK_BREAKABLE_WHITE, BLOCK_INVISIBLE_BREAKABLE,
            BLOCK_PASSABLE_WHITE, BLOCK_INVISIBLE_SOLID,
            BLOCK_PASSABLE_BROWN, BLOCK_SOLID_BROWN,
            MODE_BLOCK, MODE_ITEM, MODE_ENEMY, MODE_META,
            ITEMS_LIST, ENEMIES_LIST,
        )

        if mode == MODE_BLOCK:
            block_map = {0: BLOCK_NONE, 1: BLOCK_BROWN, 2: BLOCK_WHITE,
                         3: BLOCK_CRACKED, 4: BLOCK_BREAKABLE_WHITE,
                         5: BLOCK_INVISIBLE_BREAKABLE, 6: BLOCK_PASSABLE_WHITE,
                         7: BLOCK_INVISIBLE_SOLID, 8: BLOCK_PASSABLE_BROWN,
                         9: BLOCK_SOLID_BROWN}
            target = block_map.get(n)
            if target is None:
                return
            # ピッカー選択を更新してから配置
            self._set_picker_value(target)
            self._on_tile_clicked(int(Qt.LeftButton), self._hover_tile, 0)
        elif mode == MODE_ITEM:
            if n == 0:
                self._on_tile_right_clicked(self._hover_tile)
                return
            if n - 1 < len(ITEMS_LIST):
                code = ITEMS_LIST[n - 1]   # ITEMS_LIST はコード一覧 (名前は持たない)
                self._set_picker_value(code)
                self._on_tile_clicked(int(Qt.LeftButton), self._hover_tile, 0)
        elif mode == MODE_ENEMY:
            if n == 0:
                self._on_tile_right_clicked(self._hover_tile)
                return
            if n - 1 < len(ENEMIES_LIST):
                code = ENEMIES_LIST[n - 1][0]
                self._set_picker_value(code)
                self._on_tile_clicked(int(Qt.LeftButton), self._hover_tile, 0)
        elif mode == MODE_META:
            meta_map = {1: "start", 2: "key", 3: "door", 4: "mirror1", 5: "mirror2"}
            target = meta_map.get(n)
            if target:
                self._set_picker_value(target)
                self._on_tile_clicked(int(Qt.LeftButton), self._hover_tile, 0)

    def _set_picker_value(self, value, mode=None):
        """ピッカーの選択値をプログラム的に変更

        UserRoleは (mode, value) のタプル。mode 指定が無ければ value 一致のみで検索。
        """
        self.picker.find_and_select(value, mode)

    # ====== レベル設定（メタ編集） ======

    def _cancel_canvas_mouse_button_state(self):
        view = getattr(self, "level_view", None)
        if view is not None and hasattr(view, "cancel_mouse_button_state"):
            view.cancel_mouse_button_state()

    def _set_tileset_radio(self, val: int):
        buttons = (self.rb_tileset0, self.rb_tileset1, self.rb_tileset2)
        idx = max(0, min(2, int(val)))
        buttons[idx].setChecked(True)

    def _set_tileset_enabled(self, enabled: bool):
        for rb in (self.rb_tileset0, self.rb_tileset1, self.rb_tileset2):
            rb.setEnabled(enabled)

    def _refresh_key_enemy_spin_range(self, warn: bool = False):
        if not self.levels or not hasattr(self, "spin_key_enemy"):
            return
        lv = self.levels[self.current_level_no]
        max_enemy = min(len(lv.enemies), c.ENEMY_COUNT_MAX)
        from ..core import stage_ext as _se
        from ..core import enemy_slot_rules as _esr
        current = _se.get_key_enemy_number(lv)
        fairy_current = _se.get_fairy_enemy_number(lv)
        display_current = current
        invalid = current > max_enemy or not _esr.can_key_enemy_number(lv, current, fairy_current)
        if invalid:
            if self._is_read_only():
                display_current = 0
            else:
                _se.set_key_enemy_number(lv, 0)
                display_current = 0
                self._set_dirty(True)
            if warn and not self._is_read_only():
                self._cancel_canvas_mouse_button_state()
                QMessageBox.warning(
                    self,
                    "鍵持ち敵設定を解除",
                    "鍵持ち敵に指定していた番号が、このステージの敵数を超えたため解除しました。"
                )
                self._cancel_canvas_mouse_button_state()
        old_block = self.spin_key_enemy.blockSignals(True)
        self.spin_key_enemy.setRange(0, max_enemy)
        self.spin_key_enemy.setValue(display_current)
        self.spin_key_enemy.blockSignals(old_block)
        self.spin_key_enemy.setToolTip(
            f"0=なし。1から{max_enemy}は初期配置敵の順番です。Flame系と妖精化敵と同じ番号は指定できません。"
        )

    def _refresh_fairy_enemy_spin_range(self, warn: bool = False):
        if not self.levels or not hasattr(self, "spin_fairy_enemy"):
            return
        lv = self.levels[self.current_level_no]
        max_enemy = min(len(lv.enemies), c.ENEMY_COUNT_MAX)
        from ..core import stage_ext as _se
        from ..core import enemy_slot_rules as _esr
        current = _se.get_fairy_enemy_number(lv)
        key_current = _se.get_key_enemy_number(lv)
        display_current = current
        invalid = current > max_enemy or not _esr.can_fairy_enemy_number(lv, current, key_current)
        if invalid:
            if self._is_read_only():
                display_current = 0
            else:
                _se.set_fairy_enemy_number(lv, 0)
                display_current = 0
                self._set_dirty(True)
            if warn and not self._is_read_only():
                self._cancel_canvas_mouse_button_state()
                QMessageBox.warning(
                    self,
                    "妖精化敵設定を解除",
                    "妖精化敵に指定していた番号が、このステージで使えないため解除しました。"
                )
                self._cancel_canvas_mouse_button_state()
        old_block = self.spin_fairy_enemy.blockSignals(True)
        self.spin_fairy_enemy.setRange(0, max_enemy)
        self.spin_fairy_enemy.setValue(display_current)
        self.spin_fairy_enemy.blockSignals(old_block)
        self.spin_fairy_enemy.setToolTip(
            f"0=なし。Dragon/Golem/Gargoyle系のみ。Flame系と鍵持ち敵と同じ番号は指定できません。"
        )

    def _load_meta_to_ui(self):
        """現在レベルのメタ情報をUIに反映（シグナル抑制）"""
        if not self.levels:
            return
        lv = self.levels[self.current_level_no]
        self._meta_loading = True
        try:
            self._set_tileset_radio(lv.tileset_no)
            self.spin_time_dr.setValue(lv.time_decrease_rate)
            from ..core import room_flags as _rf
            self.chk_no_bfire.setChecked(bool(lv.room_flags & _rf.BIT_NO_BFIRE))
            self.chk_no_astone.setChecked(
                bool(lv.room_flags & _rf.BIT_NO_ASTONE))
            self.chk_dark.setChecked(bool(lv.room_flags & _rf.BIT_DARK))
            from ..core import stage_ext as _se
            self.chk_fire_reset.setChecked(_se.fire_reset_enabled(lv))
            self._refresh_key_enemy_spin_range()
            self._refresh_fairy_enemy_spin_range()
            # 星座
            if lv.has_constellation():
                cn = lv.get_constellation_no()
                idx = self.combo_const.findData(cn)
                self.combo_const.setCurrentIndex(idx if idx >= 0 else 0)
                cx, cy = lv.get_constellation_pos()
                self.spin_const_x.setValue(cx)
                self.spin_const_y.setValue(cy)
                # BESK互換: 星座がある場合タイルセットは星座が決定するため無効化
                self._set_tileset_enabled(False)
            else:
                self.combo_const.setCurrentIndex(0)  # (なし)
                self.spin_const_x.setValue(0)
                self.spin_const_y.setValue(0)
                self._set_tileset_enabled(True)
            self._load_panel_variant_to_ui(lv)
        finally:
            self._meta_loading = False

    def _load_panel_variant_to_ui(self, level):
        return

    def _on_panel_variant_setting_changed(self, key):
        return

    def _on_meta_tileset_changed(self, val):
        if self._meta_loading or not self.levels:
            return
        if self._reject_read_only_edit():
            return
        self._push_undo()
        level = self.levels[self.current_level_no]
        level.tileset_no = val
        # C++ skchain互換: タイルセット変更時に星座グループも連動
        if level.has_constellation():
            from ..core.level import LevelElement, ElementType
            from ..core import constants as cc
            base = (level.get_constellation_no() - cc.ITEM_CONSTELLATION_MIN) % 4
            new_no = cc.ITEM_CONSTELLATION_MIN + 4 * val + base
            if new_no <= cc.ITEM_CONSTELLATION_MAX:
                level.constellation = LevelElement(
                    ElementType.ITEM, level.get_constellation_pos(), new_no)
        self._refresh_view()

    def _on_meta_time_dr_changed(self, val):
        self._update_time_dr_hint()
        if self._meta_loading or not self.levels:
            return
        if self._reject_read_only_edit():
            return
        self._push_undo()
        self.levels[self.current_level_no].time_decrease_rate = val
        self._update_info()

    def _update_time_dr_hint(self):
        try:
            from ..core import time_decrease_hack
            values = (
                time_decrease_hack.current_values(self.rom.data)
                if self.rom else time_decrease_hack.ORIGINAL_VALUES
            )
            parts = []
            for idx, raw in enumerate(values):
                seconds = time_decrease_hack.estimate_total_seconds(raw)
                if seconds is None:
                    seconds_text = "停止"
                else:
                    seconds_text = f"約{int(seconds + 0.5)}秒"
                parts.append(f"{idx}={seconds_text}")
            self.lbl_time_dr_hint.setText(" / ".join(parts))
        except Exception:
            self.lbl_time_dr_hint.setText("0=約24秒 / 1=約32秒 / 2=約44秒")

    def _on_meta_no_bfire_toggled(self, checked):
        if self._meta_loading or not self.levels:
            return
        if self._reject_read_only_edit():
            return
        self._push_undo()
        from ..core import room_flags as _rf
        lv = self.levels[self.current_level_no]
        if checked:
            lv.room_flags |= _rf.BIT_NO_BFIRE
        else:
            lv.room_flags &= ~_rf.BIT_NO_BFIRE
        self._set_dirty(True)
        self._update_info()

    def _on_meta_no_astone_toggled(self, checked):
        if self._meta_loading or not self.levels:
            return
        if self._reject_read_only_edit():
            return
        self._push_undo()
        from ..core import room_flags as _rf
        lv = self.levels[self.current_level_no]
        if checked:
            lv.room_flags |= _rf.BIT_NO_ASTONE
        else:
            lv.room_flags &= ~_rf.BIT_NO_ASTONE
        self._set_dirty(True)
        self._update_info()

    def _on_meta_dark_toggled(self, checked):
        if self._meta_loading or not self.levels:
            return
        if self._reject_read_only_edit():
            return
        self._push_undo()
        from ..core import room_flags as _rf
        lv = self.levels[self.current_level_no]
        if checked:
            lv.room_flags |= _rf.BIT_DARK
        else:
            lv.room_flags &= ~_rf.BIT_DARK
        self._set_dirty(True)
        self._update_info()

    def _on_meta_fire_reset_toggled(self, checked):
        if self._meta_loading or not self.levels:
            return
        if self._reject_read_only_edit():
            return
        self._push_undo()
        from ..core import stage_ext as _se
        lv = self.levels[self.current_level_no]
        _se.set_fire_reset_enabled(lv, checked)
        self._set_dirty(True)
        self._update_info()

    def _on_meta_key_enemy_changed(self, enemy_number):
        if self._meta_loading or not self.levels:
            return
        if self._reject_read_only_edit():
            return
        max_enemy = min(len(self.levels[self.current_level_no].enemies), c.ENEMY_COUNT_MAX)
        if enemy_number > max_enemy:
            self._refresh_key_enemy_spin_range()
            self._refresh_fairy_enemy_spin_range()
            return
        from ..core import stage_ext as _se
        from ..core import enemy_slot_rules as _esr
        lv = self.levels[self.current_level_no]
        if int(enemy_number) <= 0 and self._key_enemy_is_required_for_exit(lv):
            self.statusBar().showMessage(
                "鍵メタが無いため、この鍵持ち敵は解除できません", 3000
            )
            self._refresh_key_enemy_spin_range()
            return
        if int(enemy_number) > 0 and lv.is_door_removed():
            self.statusBar().showMessage(
                "扉が削除されているステージには鍵持ち敵を設定できません", 3000
            )
            self._refresh_key_enemy_spin_range()
            return
        self._push_undo()
        current = _se.get_key_enemy_number(lv)
        fairy_enemy_number = _se.get_fairy_enemy_number(lv)
        enemy_number = _esr.coerce_enemy_number(
            lv,
            enemy_number,
            current,
            lambda n: _esr.can_key_enemy_number(lv, n, fairy_enemy_number),
        )
        if enemy_number is None:
            self._refresh_key_enemy_spin_range()
            return
        _se.set_key_enemy_number(lv, enemy_number)
        self._set_dirty(True)
        self._refresh_fairy_enemy_spin_range()
        self._refresh_view()

    def _on_meta_fairy_enemy_changed(self, enemy_number):
        if self._meta_loading or not self.levels:
            return
        if self._reject_read_only_edit():
            return
        max_enemy = min(len(self.levels[self.current_level_no].enemies), c.ENEMY_COUNT_MAX)
        if enemy_number > max_enemy:
            self._refresh_fairy_enemy_spin_range()
            return
        self._push_undo()
        from ..core import stage_ext as _se
        from ..core import enemy_slot_rules as _esr
        lv = self.levels[self.current_level_no]
        current = _se.get_fairy_enemy_number(lv)
        key_enemy_number = _se.get_key_enemy_number(lv)
        enemy_number = _esr.coerce_enemy_number(
            lv,
            enemy_number,
            current,
            lambda n: _esr.can_fairy_enemy_number(lv, n, key_enemy_number),
        )
        if enemy_number is None:
            self._refresh_fairy_enemy_spin_range()
            return
        _se.set_fairy_enemy_number(lv, enemy_number)
        self._set_dirty(True)
        self._refresh_fairy_enemy_spin_range()
        self._refresh_view()

    def _on_meta_constellation_changed(self, idx):
        if self._meta_loading or not self.levels:
            return
        if self._reject_read_only_edit():
            return
        self._push_undo()
        lv = self.levels[self.current_level_no]
        code = self.combo_const.itemData(idx)
        if code == -1 or code is None:
            lv.constellation = None
            # 星座なし → タイルセット自由選択可
            self._set_tileset_enabled(True)
        else:
            cx = self.spin_const_x.value()
            cy = self.spin_const_y.value()
            lv.constellation = LevelElement(ElementType.ITEM, (cx, cy), code)
            # BESK互換: 星座がタイルセットを決定、spinboxを無効化
            forced_tileset = (code - c.ITEM_CONSTELLATION_MIN) // 4
            self._meta_loading = True
            lv.tileset_no = forced_tileset
            self._set_tileset_radio(forced_tileset)
            self._meta_loading = False
            self._set_tileset_enabled(False)
        self._refresh_view()

    def _on_meta_const_pos_changed(self, _val):
        if self._meta_loading or not self.levels:
            return
        if self._reject_read_only_edit():
            return
        lv = self.levels[self.current_level_no]
        if lv.has_constellation():
            self._push_undo()
            cn = lv.get_constellation_no()
            cx = self.spin_const_x.value()
            cy = self.spin_const_y.value()
            lv.constellation = LevelElement(ElementType.ITEM, (cx, cy), cn)
            self._refresh_view()

    # ====== 全レベル統計 ======

    @staticmethod
    def _item_replace_state(lv, item):
        if item.position in getattr(lv, "visible_in_block_item_cells", set()):
            return c.ITEM_FLAG_VISIBLE_IN_BLOCK
        if (
            item.position in getattr(lv, "cracked_block_cells", set())
            and not item.is_white_in_block()
            and not item.is_in_block()
        ):
            return c.ITEM_FLAG_CRACKED_IN_BLOCK
        if item.is_white_in_block():
            return c.ITEM_FLAG_WHITE_IN_BLOCK
        if item.is_hidden():
            return c.ITEM_FLAG_HIDDEN
        if item.is_in_block():
            return c.ITEM_FLAG_IN_BLOCK
        return c.ITEM_FLAG_NORMAL

    @staticmethod
    def _item_replace_element_no(base_item: int, state: int) -> int:
        base = int(base_item) & 0x3F
        if state == c.ITEM_FLAG_HIDDEN:
            return base | c.ITEM_FLAG_HIDDEN
        if state == c.ITEM_FLAG_IN_BLOCK:
            return base | c.ITEM_FLAG_IN_BLOCK
        if state == c.ITEM_FLAG_WHITE_IN_BLOCK:
            return base | c.ITEM_FLAG_WHITE_IN_BLOCK
        return base

    def _item_replace_level_nos(self, scope):
        if scope == "all":
            return list(range(len(self.levels)))
        return [self.current_level_no]

    def _item_replace_tile_in_scope(self, pos, scope):
        if scope != "selection":
            return True
        bounds = self._get_selection_bounds()
        if bounds is None:
            return False
        x1, y1, x2, y2 = bounds
        x, y = pos
        return x1 <= x <= x2 and y1 <= y <= y2

    def _block_replace_kind_at(self, lv, tile):
        x, y = tile
        wall = lv.tiles[y][x]
        if wall == Wall.BROWN and tile in getattr(lv, "passable_brown_cells", set()):
            return BLOCK_PASSABLE_BROWN
        if wall == Wall.BROWN and tile in getattr(lv, "solid_brown_cells", set()):
            return BLOCK_SOLID_BROWN
        if wall == Wall.BROWN and tile in getattr(lv, "cracked_block_cells", set()):
            return BLOCK_CRACKED
        if wall == Wall.BROWN:
            return BLOCK_BROWN
        if wall == Wall.WHITE and tile in getattr(lv, "breakable_white_cells", set()):
            return BLOCK_BREAKABLE_WHITE
        if wall == Wall.WHITE and tile in getattr(lv, "passable_white_cells", set()):
            return BLOCK_PASSABLE_WHITE
        if wall == Wall.WHITE:
            return BLOCK_WHITE
        if wall == Wall.NONE and tile in getattr(lv, "invisible_breakable_cells", set()):
            return BLOCK_INVISIBLE_BREAKABLE
        if wall == Wall.NONE and tile in getattr(lv, "invisible_solid_cells", set()):
            return BLOCK_INVISIBLE_SOLID
        if wall == Wall.NONE:
            return BLOCK_NONE
        return None

    def _set_block_replace_kind(self, lv, tile, block_kind: str):
        if block_kind == BLOCK_NONE:
            lv.set_block(Wall.NONE, tile)
            lv.cracked_block_cells.discard(tile)
            lv.breakable_white_cells.discard(tile)
            lv.invisible_breakable_cells.discard(tile)
            lv.invisible_solid_cells.discard(tile)
            lv.passable_brown_cells.discard(tile)
            lv.solid_brown_cells.discard(tile)
        elif block_kind == BLOCK_BROWN:
            lv.set_block(Wall.BROWN, tile)
            lv.cracked_block_cells.discard(tile)
            lv.passable_brown_cells.discard(tile)
            lv.solid_brown_cells.discard(tile)
        elif block_kind == BLOCK_CRACKED:
            lv.set_block(Wall.BROWN, tile)
            lv.breakable_white_cells.discard(tile)
            lv.passable_white_cells.discard(tile)
            lv.invisible_breakable_cells.discard(tile)
            lv.invisible_solid_cells.discard(tile)
            lv.passable_brown_cells.discard(tile)
            lv.solid_brown_cells.discard(tile)
            lv.cracked_block_cells.add(tile)
        elif block_kind == BLOCK_WHITE:
            lv.set_block(Wall.WHITE, tile)
            lv.cracked_block_cells.discard(tile)
            lv.breakable_white_cells.discard(tile)
            lv.passable_white_cells.discard(tile)
            lv.passable_brown_cells.discard(tile)
            lv.solid_brown_cells.discard(tile)
        elif block_kind == BLOCK_BREAKABLE_WHITE:
            lv.set_block(Wall.WHITE, tile)
            lv.cracked_block_cells.discard(tile)
            lv.invisible_breakable_cells.discard(tile)
            lv.passable_white_cells.discard(tile)
            lv.passable_brown_cells.discard(tile)
            lv.solid_brown_cells.discard(tile)
            lv.breakable_white_cells.add(tile)
        elif block_kind == BLOCK_INVISIBLE_BREAKABLE:
            lv.set_block(Wall.NONE, tile)
            lv.cracked_block_cells.discard(tile)
            lv.breakable_white_cells.discard(tile)
            lv.invisible_solid_cells.discard(tile)
            lv.passable_white_cells.discard(tile)
            lv.passable_brown_cells.discard(tile)
            lv.solid_brown_cells.discard(tile)
            lv.invisible_breakable_cells.add(tile)
        elif block_kind == BLOCK_PASSABLE_WHITE:
            lv.set_block(Wall.WHITE, tile)
            lv.cracked_block_cells.discard(tile)
            lv.breakable_white_cells.discard(tile)
            lv.invisible_breakable_cells.discard(tile)
            lv.invisible_solid_cells.discard(tile)
            lv.passable_brown_cells.discard(tile)
            lv.solid_brown_cells.discard(tile)
            lv.passable_white_cells.add(tile)
        elif block_kind == BLOCK_INVISIBLE_SOLID:
            lv.set_block(Wall.NONE, tile)
            lv.cracked_block_cells.discard(tile)
            lv.breakable_white_cells.discard(tile)
            lv.invisible_breakable_cells.discard(tile)
            lv.passable_white_cells.discard(tile)
            lv.passable_brown_cells.discard(tile)
            lv.solid_brown_cells.discard(tile)
            lv.invisible_solid_cells.add(tile)
        elif block_kind == BLOCK_PASSABLE_BROWN:
            lv.set_block(Wall.BROWN, tile)
            lv.cracked_block_cells.discard(tile)
            lv.breakable_white_cells.discard(tile)
            lv.passable_white_cells.discard(tile)
            lv.invisible_breakable_cells.discard(tile)
            lv.invisible_solid_cells.discard(tile)
            lv.solid_brown_cells.discard(tile)
            lv.passable_brown_cells.add(tile)
        elif block_kind == BLOCK_SOLID_BROWN:
            lv.set_block(Wall.BROWN, tile)
            lv.cracked_block_cells.discard(tile)
            lv.breakable_white_cells.discard(tile)
            lv.passable_white_cells.discard(tile)
            lv.invisible_breakable_cells.discard(tile)
            lv.invisible_solid_cells.discard(tile)
            lv.passable_brown_cells.discard(tile)
            lv.solid_brown_cells.add(tile)

    def _block_replace_matches(self, lv, tile, opts):
        if not self._item_replace_tile_in_scope(tile, opts["scope"]):
            return False
        return self._block_replace_kind_at(lv, tile) == opts["from_block"]

    def _count_block_replacements(self, opts):
        total = 0
        changed_levels = []
        for level_no in self._item_replace_level_nos(opts["scope"]):
            lv = self.levels[level_no]
            count = 0
            for y in range(c.LEVEL_H):
                for x in range(c.LEVEL_W):
                    if self._block_replace_matches(lv, (x, y), opts):
                        count += 1
            if count:
                total += count
                changed_levels.append(level_no)
        return total, changed_levels

    def _apply_block_replacements(self, opts, changed_levels):
        self._push_undo_levels(changed_levels, focus_level_no=self.current_level_no)
        to_block = str(opts["to_block"])
        for level_no in changed_levels:
            lv = self.levels[level_no]
            for y in range(c.LEVEL_H):
                for x in range(c.LEVEL_W):
                    tile = (x, y)
                    if self._block_replace_matches(lv, tile, opts):
                        self._set_block_replace_kind(lv, tile, to_block)
        self._refresh_changed_stages(changed_levels)

    def _item_replace_matches(self, lv, item, opts):
        if self._is_protected_open_door_item(lv, item):
            return False
        if not self._item_replace_tile_in_scope(item.position, opts["scope"]):
            return False
        if item.get_item_no() != opts["from_item"]:
            return False
        if opts["match_state"]:
            return self._item_replace_state(lv, item) == opts["from_state"]
        return True

    def _count_item_replacements(self, opts):
        total = 0
        changed_levels = []
        for level_no in self._item_replace_level_nos(opts["scope"]):
            lv = self.levels[level_no]
            count = sum(
                1 for item in lv.items
                if self._item_replace_matches(lv, item, opts)
            )
            if count:
                total += count
                changed_levels.append(level_no)
        return total, changed_levels

    def _apply_item_replacements(self, opts, changed_levels):
        self._push_undo_levels(changed_levels, focus_level_no=self.current_level_no)
        to_state = int(opts["to_state"])
        to_item = int(opts["to_item"])
        for level_no in changed_levels:
            lv = self.levels[level_no]
            if not hasattr(lv, "visible_in_block_item_cells"):
                lv.visible_in_block_item_cells = set()
            visible_cells = lv.visible_in_block_item_cells
            if not hasattr(lv, "cracked_block_cells"):
                lv.cracked_block_cells = set()
            cracked_cells = lv.cracked_block_cells
            for item in lv.items:
                if not self._item_replace_matches(lv, item, opts):
                    continue
                was_cracked = (
                    item.position in cracked_cells
                    and not item.is_white_in_block()
                    and not item.is_in_block()
                )
                if to_state == c.ITEM_FLAG_VISIBLE_IN_BLOCK:
                    item.element_no = self._item_replace_element_no(to_item, c.ITEM_FLAG_NORMAL)
                    visible_cells.add(item.position)
                    if was_cracked:
                        lv.set_block(Wall.NONE, item.position)
                elif to_state == c.ITEM_FLAG_CRACKED_IN_BLOCK:
                    item.element_no = self._item_replace_element_no(to_item, c.ITEM_FLAG_NORMAL)
                    visible_cells.discard(item.position)
                    lv.set_block(Wall.BROWN, item.position)
                    cracked_cells.add(item.position)
                else:
                    item.element_no = self._item_replace_element_no(to_item, to_state)
                    visible_cells.discard(item.position)
                    if was_cracked:
                        lv.set_block(Wall.NONE, item.position)
        self._refresh_changed_stages(changed_levels)

    def _enemy_replace_matches(self, lv, enemy, opts):
        if not self._item_replace_tile_in_scope(enemy.position, opts["scope"]):
            return False
        return int(enemy.element_no) == int(opts["from_enemy"])

    def _count_enemy_replacements(self, opts):
        total = 0
        changed_levels = []
        for level_no in self._item_replace_level_nos(opts["scope"]):
            lv = self.levels[level_no]
            count = sum(
                1 for enemy in lv.enemies
                if self._enemy_replace_matches(lv, enemy, opts)
            )
            if count:
                total += count
                changed_levels.append(level_no)
        return total, changed_levels

    def _apply_enemy_replacements(self, opts, changed_levels):
        self._push_undo_levels(changed_levels, focus_level_no=self.current_level_no)
        to_enemy = int(opts["to_enemy"]) & 0xFF
        for level_no in changed_levels:
            lv = self.levels[level_no]
            for enemy in lv.enemies:
                if self._enemy_replace_matches(lv, enemy, opts):
                    enemy.element_no = to_enemy
        self._refresh_changed_stages(changed_levels)

    def _on_show_item_replace(self):
        if not self.levels:
            return
        if self._reject_read_only_edit():
            return
        from .item_replace_dialog import ItemReplaceDialog

        def current_picker_replace_spec(show_warning=True, fallback=False):
            mode, value = self.picker.get_current()
            if mode == MODE_BLOCK and value in DEFAULT_BLOCK_PICKER_ORDER:
                return MODE_BLOCK, str(value), c.ITEM_FLAG_NORMAL
            if mode == MODE_ITEM:
                return MODE_ITEM, int(value), int(self.picker.get_item_flag())
            if mode == MODE_ENEMY:
                enemy_no = apply_enemy_speed(
                    int(value),
                    int(getattr(self.picker, "current_enemy_speed", 1)),
                )
                return MODE_ENEMY, int(enemy_no), c.ITEM_FLAG_NORMAL
            if fallback and ITEMS_LIST:
                return MODE_ITEM, int(ITEMS_LIST[0]), c.ITEM_FLAG_NORMAL
            if fallback and DEFAULT_BLOCK_PICKER_ORDER:
                return MODE_BLOCK, str(DEFAULT_BLOCK_PICKER_ORDER[0]), c.ITEM_FLAG_NORMAL
            if fallback and ENEMIES_LIST:
                return MODE_ENEMY, int(ENEMIES_LIST[0][0]), c.ITEM_FLAG_NORMAL
            if show_warning:
                self.statusBar().showMessage(
                    "ピッカーでブロック、アイテム、モンスターを選択してから指定してください", 2500
                )
            return None

        def enemy_name(code):
            if self.config is not None:
                return self.config.enemy_desc.get(int(code), f"0x{int(code):02X}")
            return f"0x{int(code):02X}"

        def block_name(kind):
            return BLOCK_PICKER_LABELS.get(str(kind), str(kind))

        dlg = getattr(self, "_item_replace_dialog", None)
        is_new_dialog = dlg is None or not dlg.isVisible()
        if is_new_dialog:
            dlg = ItemReplaceDialog(
                item_name_resolver=lambda code: item_name(code, self.config),
                item_icon_provider=lambda code: self.picker._make_item_icon(code),
                enemy_name_resolver=enemy_name,
                enemy_icon_provider=lambda code: self.picker._make_enemy_icon(code),
                block_name_resolver=block_name,
                block_icon_provider=lambda kind: self.picker._make_block_icon(kind),
                selection_available=self._get_selection_bounds() is not None,
                parent=self,
                app_config=self._app_config,
            )
            dlg.replace_requested.connect(self._perform_item_replace_from_dialog)
            self._item_replace_dialog = dlg
        else:
            dlg.set_selection_available(self._get_selection_bounds() is not None)
        if is_new_dialog:
            spec = current_picker_replace_spec(show_warning=False, fallback=True)
            if spec is not None:
                dlg.set_initial_from_spec(spec)
                dlg.set_initial_to_spec(spec)
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def _perform_item_replace_from_dialog(self, opts):
        if not self.levels:
            return
        if opts.get("mode") == MODE_BLOCK:
            count, changed_levels = self._count_block_replacements(opts)
            if count <= 0:
                QMessageBox.information(self, "ブロック一括置換", "置換対象はありませんでした。")
                return
            scope_label = {
                "selection": "選択範囲",
                "current": "現在ステージ",
                "all": "全ステージ",
            }.get(opts["scope"], "対象範囲")
            reply = QMessageBox.question(
                self,
                "ブロック一括置換",
                f"{scope_label}で {count} 件のブロックを置換します。\n\n"
                "実行後も Undo で戻せます。続行しますか？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
            self._apply_block_replacements(opts, changed_levels)
            self.statusBar().showMessage(
                f"ブロック一括置換: {count} 件 / {len(changed_levels)} ステージ", 4000
            )
            self._log(
                f"ブロック一括置換: {count}件 / scope={opts['scope']} / "
                f"from={opts['from_block']} to={opts['to_block']}"
            )
            return
        if opts.get("mode") == MODE_ENEMY:
            count, changed_levels = self._count_enemy_replacements(opts)
            if count <= 0:
                QMessageBox.information(self, "モンスター一括置換", "置換対象はありませんでした。")
                return
            scope_label = {
                "selection": "選択範囲",
                "current": "現在ステージ",
                "all": "全ステージ",
            }.get(opts["scope"], "対象範囲")
            reply = QMessageBox.question(
                self,
                "モンスター一括置換",
                f"{scope_label}で {count} 件のモンスターを置換します。\n\n"
                "実行後も Undo で戻せます。続行しますか？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
            self._apply_enemy_replacements(opts, changed_levels)
            self.statusBar().showMessage(
                f"モンスター一括置換: {count} 件 / {len(changed_levels)} ステージ", 4000
            )
            self._log(
                f"モンスター一括置換: {count}件 / scope={opts['scope']} / "
                f"from=0x{opts['from_enemy']:02X} to=0x{opts['to_enemy']:02X}"
            )
            return
        if (
            opts["to_state"] == c.ITEM_FLAG_WHITE_IN_BLOCK and
            opts["to_item"] > c.ITEM_WHITE_IN_BLOCK_MAX_BASE
        ):
            QMessageBox.warning(
                self,
                "アイテム一括置換",
                "このアイテムは白ブロック内アイテムとして保存できません。",
            )
            return
        count, changed_levels = self._count_item_replacements(opts)
        if count <= 0:
            QMessageBox.information(self, "アイテム一括置換", "置換対象はありませんでした。")
            return
        scope_label = {
            "selection": "選択範囲",
            "current": "現在ステージ",
            "all": "全ステージ",
        }.get(opts["scope"], "対象範囲")
        reply = QMessageBox.question(
            self,
            "アイテム一括置換",
            f"{scope_label}で {count} 件のアイテムを置換します。\n\n"
            "実行後も Undo で戻せます。続行しますか？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._apply_item_replacements(opts, changed_levels)
        self.statusBar().showMessage(
            f"アイテム一括置換: {count} 件 / {len(changed_levels)} ステージ", 4000
        )
        self._log(
            f"アイテム一括置換: {count}件 / scope={opts['scope']} / "
            f"from=0x{opts['from_item']:02X} to=0x{opts['to_item']:02X}"
        )

    def _on_show_stats(self):
        if not self.levels:
            return
        if getattr(self, "_stats_dialog", None) is not None and self._stats_dialog.isVisible():
            self._stats_dialog.raise_()
            self._stats_dialog.activateWindow()
            return
        from .stats_dialog import StatsDialog
        item_desc = self.config.item_desc if self.config else {}
        dlg = StatsDialog(self.levels, item_desc=item_desc,
                          config=self.config,
                          tile_renderer=self.tile_renderer,
                          app_config=self._app_config,
                          rom=self.rom, parent=self)
        self._stats_dialog = dlg
        dlg.finished.connect(lambda _result: setattr(self, "_stats_dialog", None))
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def _on_show_rom_diff(self):
        self._open_rom_diff_dialog()

    def _open_rom_diff_dialog(self):
        from .rom_diff_dialog import RomDiffDialog
        dlg = getattr(self, "_rom_diff_dialog", None)
        if dlg is not None and dlg.isVisible():
            dlg.raise_()
            dlg.activateWindow()
            return dlg
        dlg = RomDiffDialog(parent=self, app_config=self._app_config)
        self._rom_diff_dialog = dlg
        dlg.finished.connect(lambda _result: setattr(self, "_rom_diff_dialog", None))
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()
        return dlg

    def _on_show_rom_diff_for_paths(self, left_path: str, right_path: str):
        dlg = self._open_rom_diff_dialog()
        dlg.set_compare_paths(left_path, right_path)

    # ====== ゲーム挙動改造 ======

    def _on_show_hack(self):
        if not self.rom:
            return
        if self._reject_read_only_edit():
            return
        from .hack_dialog import HackDialog
        # 変更前のスナップショット
        before = bytes(self.rom.data)
        before_wall = self._read_wall_color_values()
        before_palette = self._main_palette_bytes()
        dlg = HackDialog(
            self.rom,
            parent=self,
            app_config=self._app_config,
            initial_level_no=self.current_level_no,
            tile_renderer=self.tile_renderer,
            config=self.config,
            levels=self.levels,
        )
        dlg.exec_()
        # 変更があれば未保存マーク
        if bytes(self.rom.data) != before:
            self._set_dirty(True)
            self._log("ゲーム挙動改造: ROMバイト変更あり")
            self._update_time_dr_hint()
            if self._main_palette_bytes() != before_palette:
                self._on_palette_changed()
            elif self._read_wall_color_values() != before_wall:
                self._on_hack_dialog_applied()

    def _on_show_enemy_hack(self):
        if not self.rom:
            return
        if self._reject_read_only_edit():
            return
        from .hack_dialog import HackDialog
        before = bytes(self.rom.data)
        before_palette = self._main_palette_bytes()
        dlg = HackDialog(
            self.rom,
            parent=self,
            app_config=self._app_config,
            initial_level_no=self.current_level_no,
            view_mode="enemy",
            tile_renderer=self.tile_renderer,
            config=self.config,
        )
        dlg.exec_()
        if bytes(self.rom.data) != before:
            self._set_dirty(True)
            self._log("敵設定: ROMバイト変更あり")
            if self._main_palette_bytes() != before_palette:
                self._on_palette_changed()

    def _on_show_palette(self):
        """パレット編集ダイアログを開く"""
        if not self.rom:
            return
        if self._reject_read_only_edit():
            return
        from .palette_dialog import PaletteDialog, PALETTE_OFFSET
        before = bytes(self.rom.data[PALETTE_OFFSET:PALETTE_OFFSET + 32])
        dlg = PaletteDialog(
            self.rom.data,
            parent=self,
            tile_renderer=self.tile_renderer,
            app_config=self._app_config,
        )
        dlg.exec_()
        after = bytes(self.rom.data[PALETTE_OFFSET:PALETTE_OFFSET + 32])
        if after != before:
            self._set_dirty(True)
            self._log("パレット編集: 0xED4 から 32バイト書換")

    def _on_show_enemy_drop(self):
        """敵ドロップ効果表 編集ダイアログ (グローバル)"""
        if not self.rom:
            return
        if self._reject_read_only_edit():
            return
        from .enemy_drop_dialog import EnemyDropDialog
        from ..core import enemy_drop as _ed
        o, n = _ed.OFF_C293, _ed.LEN_C293
        before = bytes(self.rom.data[o:o + n])
        try:
            dlg = EnemyDropDialog(
                self.rom.data,
                parent=self,
                tile_renderer=self.tile_renderer,
                config=self.config,
                app_config=self._app_config,
            )
        except _ed.EnemyDropError as e:
            QMessageBox.critical(self, "敵ドロップ編集 不可", str(e))
            return
        dlg.exec_()
        if bytes(self.rom.data[o:o + n]) != before:
            self._set_dirty(True)
            self._log("敵ドロップ効果表 $C293 書換")

    def _on_show_demo_input(self):
        """デモ操作編集ダイアログ (34step固定・JP)"""
        if not self.rom:
            return
        if self._reject_read_only_edit():
            return
        from .demo_input_dialog import DemoInputDialog
        from ..core import demo_input as _di
        o0, o1 = _di.OFF_WAIT, _di.OFF_JOY + _di.STEPS
        before = bytes(self.rom.data[o0:o1])
        try:
            dlg = DemoInputDialog(
                self.rom.data,
                parent=self,
                app_config=self._app_config,
            )
        except _di.DemoInputError as e:
            QMessageBox.critical(self, "デモ操作編集 不可", str(e))
            return
        dlg.exec_()
        if bytes(self.rom.data[o0:o1]) != before:
            self._set_dirty(True)
            self._log("デモ操作データ ($CF9A/$CFBC) 書換")

    def _on_show_clear_message(self):
        """クリア画面メッセージ編集 (同字数・JP)"""
        if not self.rom:
            return
        if self._reject_read_only_edit():
            return
        from .clear_message_dialog import ClearMessageDialog
        from ..core import clear_message as _cm
        o0 = _cm.MESSAGES[0]["off"]
        last = _cm.MESSAGES[-1]
        o1 = last["off"] + 3 + last["count"] + 1
        before = bytes(self.rom.data[o0:o1])
        try:
            dlg = ClearMessageDialog(
                self.rom.data,
                parent=self,
                app_config=self._app_config,
            )
        except _cm.ClearMessageError as e:
            QMessageBox.critical(self, "クリア画面メッセージ編集 不可",
                                 str(e))
            return
        dlg.exec_()
        if bytes(self.rom.data[o0:o1]) != before:
            self._set_dirty(True)
            self._log("クリア画面メッセージ ($94DB/$94ED/$9507) 書換")

    def _on_show_title_screen(self):
        """タイトル画面 抽出/差し替え (CHR bank3 + 描画領域、R196)"""
        if not self.rom:
            return
        if self._reject_read_only_edit():
            return
        from .title_screen_dialog import TitleScreenDialog
        from ..core import title_screen as _ts
        before = bytes(self.rom.data)
        try:
            dlg = TitleScreenDialog(
                self.rom.data,
                parent=self,
                app_config=self._app_config,
            )
        except _ts.TitleScreenError as e:
            QMessageBox.critical(self, "タイトル画面 操作不可", str(e))
            return
        dlg.exec_()
        if bytes(self.rom.data) != before:
            self._set_dirty(True)
            self._log("タイトル画面 (CHR bank3 / 描画領域) 書換")

    def _on_show_special_process(self):
        """特殊処理ビューア (Phase 1, 読込専用)"""
        if not self.rom:
            return
        from .special_process_dialog import SpecialProcessDialog
        dlg = SpecialProcessDialog(
            self.rom,
            initial_level_no=self.current_level_no,
            parent=self,
            app_config=self._app_config,
        )
        dlg.exec_()

    def _reload_chr_renderers(self):
        """Rebuild renderers after direct CHR-ROM edits."""
        if not self.rom or self.config is None:
            return
        from ..core.constants import ROM_OFFSETS
        gfx_offset = ROM_OFFSETS[self.rom.base_region()]["gfx"]
        if self.rom.is_expanded():
            gfx_offset = 0x10010
        nes_tiles = load_chr_tiles(bytes(self.rom.data), gfx_offset, c.NES_TILE_COUNT)
        self.tile_renderer = TileRenderer(self.config, nes_tiles)
        self.level_renderer = LevelRenderer(self.tile_renderer, self.config)
        self._apply_renderer_marker_settings()
        self._sync_wall_color_preview()
        if self.picker is not None:
            self.picker.set_tile_renderer(self.tile_renderer, self.config)

    def _on_show_pixel_editor(self):
        """16x16 sprite pixel editor (writes CHR-ROM tiles)."""
        if not self.rom:
            return
        if self._reject_read_only_edit():
            return
        from .pixel_editor_dialog import PixelEditorDialog
        before = bytes(self.rom.data)
        dlg = PixelEditorDialog(self.rom, parent=self, app_config=self._app_config)
        dlg.exec_()
        if bytes(self.rom.data) != before:
            self._reload_chr_renderers()
            self._set_dirty(True)
            self._refresh_view()
            self._generate_all_thumbnails()
            self.statusBar().showMessage("16x16ピクセル編集: CHRを書き換えました", 4000)
            self._log("16x16ピクセル編集: CHR書換")

    def _on_show_sound_viewer(self):
        """サウンドデータ表示 (読取専用)."""
        if not self.rom:
            return
        from .sound_viewer import SoundViewer
        try:
            dlg = SoundViewer(
                self.rom,
                parent=self,
                app_config=self._app_config,
            )
        except Exception as e:
            QMessageBox.critical(self, "音楽データ表示 不可", f"{type(e).__name__}: {e}")
            return
        dlg.exec_()

    def _on_show_sprite_viewer(self):
        """スプライトビューア (CHR-ROM 全タイル、編集画面へ接続可)"""
        if not self.rom:
            return
        if self._reject_read_only_edit():
            return
        from .sprite_viewer import SpriteViewer
        before = bytes(self.rom.data)
        self._sprite_viewer_rom_changed_seen = False
        dlg = SpriteViewer(self.rom, tile_renderer=self.tile_renderer,
                           config=self.config, app_config=self._app_config,
                           parent=self)
        dlg.rom_changed.connect(self._on_sprite_viewer_rom_changed)
        dlg.exec_()
        if bytes(self.rom.data) != before and not self._sprite_viewer_rom_changed_seen:
            self._on_sprite_viewer_rom_changed()
        self._sprite_viewer_rom_changed_seen = False

    def _on_sprite_viewer_rom_changed(self):
        if self._reject_read_only_edit():
            return
        self._sprite_viewer_rom_changed_seen = True
        self._reload_chr_renderers()
        self._set_dirty(True)
        self._refresh_view()
        self._generate_all_thumbnails()
        self.statusBar().showMessage("スプライトビューア経由: CHRを書き換えました", 4000)
        self._log("スプライトビューア経由: CHR書換")

    def _on_show_mirror(self):
        """ミラー詳細設定ダイアログ"""
        if not self.rom or not self.levels:
            return
        if self._reject_read_only_edit():
            return
        from .mirror_dialog import MirrorDialog
        lv = self.levels[self.current_level_no]
        before = bytes(self.rom.data)
        dlg = MirrorDialog(
            self.rom,
            lv,
            self.current_level_no,
            parent=self,
            app_config=self._app_config,
        )
        dlg.exec_()
        if bytes(self.rom.data) != before:
            self._set_dirty(True)
            self._log(f"ミラー詳細設定: L{self.current_level_no + 1} を変更")

    def _on_clear_mirror_schedules(self):
        if not self.rom or not self.levels:
            return
        if self._reject_read_only_edit():
            return
        if not self.rom.is_expanded():
            QMessageBox.information(
                self,
                "ミラーOFF",
                "拡張ROMを読み込んだ状態で使用できます。"
            )
            return
        ans = QMessageBox.question(
            self,
            "ミラー出現タイミングをOFF",
            f"Stage {self.current_level_no + 1} のミラー1/2の出現タイミングをすべてOFFにしますか？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if ans != QMessageBox.Yes:
            return
        from ..core import m66
        ln = self.current_level_no
        lv = self.levels[ln]
        changed = False
        for mirror_no in range(2):
            sched_off = m66.OFFSET_M66_DROP_SCHED_DATA + (ln * 2 + mirror_no) * 8
            if any(self.rom.data[sched_off + i] != 0 for i in range(8)):
                changed = True
            if mirror_no < len(lv.demon_mirrors):
                sched = getattr(lv.demon_mirrors[mirror_no], "schedule_data", []) or []
                if any(int(v) != 0 for v in list(sched)[:8]):
                    changed = True
        if not changed:
            self.statusBar().showMessage("ミラー1/2はすでに全OFFです", 3000)
            return
        self._push_undo()
        for mirror_no in range(2):
            sched_off = m66.OFFSET_M66_DROP_SCHED_DATA + (ln * 2 + mirror_no) * 8
            for i in range(8):
                self.rom.data[sched_off + i] = 0
            if mirror_no < len(lv.demon_mirrors):
                lv.demon_mirrors[mirror_no].schedule_data = [0] * 8
        self._sync_mirror_panel()
        self._refresh_view()
        self._set_dirty(True)
        self._log(f"ミラー出現OFF: L{ln + 1} のミラー1/2を全OFF")
        self.statusBar().showMessage("ミラー1/2の出現タイミングを全OFFにしました", 3000)

    def _mirror_schedule_offset(self, level_no: int, mirror_no: int) -> int:
        from ..core import m66
        return m66.OFFSET_M66_DROP_SCHED_DATA + (level_no * 2 + mirror_no) * 8

    def _mirror_schedule_bytes_for_gap(self, gap: int = 6) -> list[int]:
        period = max(1, int(gap) + 1)
        bits = [
            i >= 2 and ((i - 2) % period == 0)
            for i in range(64)
        ]
        out = []
        for byte_index in range(8):
            byte = 0
            for shift in range(7, -1, -1):
                if bits[byte_index * 8 + (7 - shift)]:
                    byte |= (1 << shift)
            out.append(byte)
        return out

    def _mirror_schedule_is_active(self, level_no: int, mirror_no: int) -> bool:
        off = self._mirror_schedule_offset(level_no, mirror_no)
        for i in range(8):
            byte = self.rom.data[off + i]
            if i == 0:
                byte &= 0x3F
            if byte:
                return True
        return False

    def _set_mirror_schedule_bytes(self, level_no: int, mirror_no: int, values: list[int]):
        off = self._mirror_schedule_offset(level_no, mirror_no)
        lv = self.levels[level_no]
        values = [(int(v) & 0xFF) for v in list(values)[:8]]
        while len(values) < 8:
            values.append(0)
        for i, value in enumerate(values):
            self.rom.data[off + i] = value
        if mirror_no < len(lv.demon_mirrors):
            lv.demon_mirrors[mirror_no].schedule_data = list(values)

    def _on_toggle_mirror_schedule(self, mirror_no: int):
        if not self.rom or not self.levels:
            return
        if self._reject_read_only_edit():
            return
        if not self.rom.is_expanded():
            self.statusBar().showMessage("拡張ROMを読み込んだ状態で使用できます。", 3000)
            return
        if mirror_no not in (0, 1):
            return
        ln = self.current_level_no
        self._push_undo()
        if self._mirror_schedule_is_active(ln, mirror_no):
            self._set_mirror_schedule_bytes(ln, mirror_no, [0] * 8)
            state_text = "OFF"
        else:
            self._set_mirror_schedule_bytes(ln, mirror_no, self._mirror_schedule_bytes_for_gap(6))
            state_text = "ON（6空け）"
        self._sync_mirror_panel()
        self._refresh_view()
        self._set_dirty(True)
        self._log(f"ミラー出現切替: L{ln + 1} M{mirror_no + 1} -> {state_text}")
        self.statusBar().showMessage(
            f"ミラー{mirror_no + 1}の出現タイミングを{state_text}にしました",
            3000,
        )

    def _on_mirror_changed(self):
        """ミラーダイアログの Apply からコールバック"""
        if self._reject_read_only_edit():
            return
        self._set_dirty(True)
        self._sync_mirror_panel()
        self._refresh_view()

    def _sync_mirror_panel(self):
        """ミラー敵セットパネルに現在レベルのデータを反映"""
        if not self.rom or not self.levels:
            return
        if not self.rom.is_expanded():
            self.picker.mirror_panel.load_enemies([], [])
            self.picker.mirror_panel.set_mirror_active_states([False, False])
            return
        from ..core import m66
        ln = self.current_level_no
        codes = [[], []]
        active = [False, False]
        for mirror_no in range(2):
            if mirror_no == 0:
                local = m66.OFFSET_M66_LOCAL_SCHED_ENEMY_1_DATA
            else:
                local = m66.OFFSET_M66_LOCAL_SCHED_ENEMY_2_DATA
            off = m66.OFFSET_M66_LVL_DATA + 256 * ln + local
            for i in range(7):
                b = self.rom.data[off + i]
                if b == 0x90:
                    break
                codes[mirror_no].append(b)
            while len(codes[mirror_no]) < 7:
                codes[mirror_no].append(0)
            sched_off = m66.OFFSET_M66_DROP_SCHED_DATA + (ln * 2 + mirror_no) * 8
            for i in range(8):
                byte = self.rom.data[sched_off + i]
                if i == 0:
                    byte &= 0x3F
                if byte:
                    active[mirror_no] = True
                    break
        self.picker.mirror_panel.load_enemies(codes[0], codes[1])
        self.picker.mirror_panel.set_mirror_active_states(active)

    def _sync_enemy_codes_from_rom(self, level_no: int):
        """ROMのミラー実データ（敵セット＋スケジュール）をLevelに同期（エクスポート前に呼ぶ）"""
        if not self.rom or not self.levels:
            return
        if not self.rom.is_expanded():
            return
        from ..core import m66
        lv = self.levels[level_no]
        for mirror_no in range(2):
            # 敵セット実データ
            local = (m66.OFFSET_M66_LOCAL_SCHED_ENEMY_1_DATA if mirror_no == 0
                     else m66.OFFSET_M66_LOCAL_SCHED_ENEMY_2_DATA)
            off = m66.OFFSET_M66_LVL_DATA + 256 * level_no + local
            codes = []
            for i in range(7):
                b = self.rom.data[off + i]
                if b == 0x90:
                    break
                codes.append(b)
            lv.demon_mirrors[mirror_no].enemy_codes = codes
            # ドロップスケジュール実データ（8バイト）
            sched_off = m66.OFFSET_M66_DROP_SCHED_DATA + (level_no * 2 + mirror_no) * 8
            sched = []
            for i in range(8):
                sched.append(self.rom.data[sched_off + i])
            lv.demon_mirrors[mirror_no].schedule_data = sched

    def _write_mirror_data_to_rom(self, level_no: int):
        """Levelのミラー実データ（敵セット＋スケジュール）をROMに書き戻す（インポート後に呼ぶ）"""
        if not self.rom or not self.levels:
            return
        if self._reject_read_only_edit():
            return
        if not self.rom.is_expanded():
            return
        from ..core import m66
        lv = self.levels[level_no]
        for mirror_no in range(2):
            # 敵セット実データ
            codes = lv.demon_mirrors[mirror_no].enemy_codes
            if codes:
                local = (m66.OFFSET_M66_LOCAL_SCHED_ENEMY_1_DATA if mirror_no == 0
                         else m66.OFFSET_M66_LOCAL_SCHED_ENEMY_2_DATA)
                off = m66.OFFSET_M66_LVL_DATA + 256 * level_no + local
                for i, c in enumerate(codes[:7]):
                    self.rom.data[off + i] = c
                self.rom.data[off + len(codes[:7])] = 0x90
                for i in range(len(codes[:7]) + 1, 8):
                    self.rom.data[off + i] = 0x00
            # ドロップスケジュール実データ
            sched = lv.demon_mirrors[mirror_no].schedule_data
            if sched:
                sched_off = m66.OFFSET_M66_DROP_SCHED_DATA + (level_no * 2 + mirror_no) * 8
                for i in range(8):
                    self.rom.data[sched_off + i] = sched[i] if i < len(sched) else 0

    def _on_mirror_panel_changed(self):
        """ミラー敵セットパネルのコンボが変更された"""
        if not self.rom or not self.levels:
            return
        if self._reject_read_only_edit():
            return
        if not self.rom.is_expanded():
            return
        from ..core import m66
        ln = self.current_level_no
        for mirror_no in range(2):
            codes = self.picker.mirror_panel.get_enemies(mirror_no)
            if mirror_no == 0:
                local = m66.OFFSET_M66_LOCAL_SCHED_ENEMY_1_DATA
            else:
                local = m66.OFFSET_M66_LOCAL_SCHED_ENEMY_2_DATA
            off = m66.OFFSET_M66_LVL_DATA + 256 * ln + local
            valid = [c for c in codes if c != 0]
            for i, c in enumerate(valid):
                self.rom.data[off + i] = c
            if len(valid) < 8:
                self.rom.data[off + len(valid)] = 0x90
            for i in range(len(valid) + 1, 8):
                self.rom.data[off + i] = 0x00
        self._set_dirty(True)

    def _on_bonus_panel_items_changed(self, new_codes: list):
        """ピッカー下部のボーナスパネルでD&Dによりアイテムが変更された"""
        if not self.rom or self.current_level_no != 50:
            return
        if self._reject_read_only_edit():
            return
        from ..core.constants import ROM_OFFSETS
        region = self.rom.base_region()
        offsets = ROM_OFFSETS.get(region, ROM_OFFSETS["JP"])
        item_addr = offsets.get("bonus_items", 0x1975)
        for i in range(min(16, len(new_codes))):
            self.rom.data[item_addr + i] = new_codes[i]
        self._set_dirty(True)
        self._load_bonus_stage_table(self.rom)
        self._refresh_view()
        self._log("ボーナスアイテムテーブルを変更")

    def _sync_bonus_panel(self):
        """ボーナスパネルにROMの現在のアイテムテーブルを反映"""
        if not self.rom:
            return
        from ..core.constants import ROM_OFFSETS
        region = self.rom.base_region()
        offsets = ROM_OFFSETS.get(region, ROM_OFFSETS["JP"])
        item_addr = offsets.get("bonus_items", 0x1975)
        item_bytes = self.rom.data[item_addr:item_addr + 16]
        self.picker.set_bonus_mode(True, item_bytes)

    def _main_palette_bytes(self):
        if not self.rom:
            return None
        from .palette_dialog import PALETTE_OFFSET, BYTES_PER_PALETTE, PALETTE_COUNT
        start = PALETTE_OFFSET
        end = start + BYTES_PER_PALETTE * PALETTE_COUNT
        return bytes(self.rom.data[start:end])

    def _sync_main_palette_to_config(self):
        """ROM内メインパレットを描画用configへ反映する。

        ROM の 0xED4 にある 8パレット × 4バイト = 32バイトの値を読み出して、
        config.palettes (XML由来の40パレット) に反映する。

        XMLの40パレット = 5グループ (red/cyan/purple/dgreen/gray) × 8パレット (BG4 + SPR4)
        - BGパレット (0-3): グループごとにslot 0(背景主色)が異なるが、slot 1/2 は共通
        - SPRパレット (4-7): 全グループで完全に同じ値
        """
        if not self.config or not self.rom:
            return False

        from .palette_dialog import PALETTE_OFFSET, BYTES_PER_PALETTE, PALETTE_COUNT
        group_offsets = [0, 8, 16, 24, 32]
        changed = False

        # XML形式: 各パレット 3バイト [c1, c2, c3] (SubPalette が先頭に 0x0F を補完する)
        # ROM形式: [c1, c2, c3, separator] の4バイト
        # よって ROM の先頭3バイトだけを取って XML に流す
        for p in range(PALETTE_COUNT):
            rom_off = PALETTE_OFFSET + p * BYTES_PER_PALETTE
            c1 = self.rom.data[rom_off + 0]
            c2 = self.rom.data[rom_off + 1]
            c3 = self.rom.data[rom_off + 2]
            for go in group_offsets:
                target = p + go
                if target >= len(self.config.palettes):
                    continue
                if p < 4:
                    # BGパレット
                    #  ・slot 0 (背景主色) はグループごとに違うので red のみ反映
                    #  ・slot 1, 2 は全グループで共通として全部反映
                    if go == 0:
                        new_palette = [c1, c2, c3]
                    else:
                        # 既存のslot 0 (=グループ固有の主色) を保持し、c2/c3 だけ更新
                        old = self.config.palettes[target]
                        keep0 = old[0] if len(old) >= 1 else 0x0f
                        new_palette = [keep0, c2, c3]
                else:
                    # SPRパレット: 全グループで完全共通
                    new_palette = [c1, c2, c3]
                if self.config.palettes[target] != new_palette:
                    self.config.palettes[target] = new_palette
                    changed = True
        return changed

    def _on_palette_changed(self):
        """パレットダイアログの Apply からコールバック"""
        if self._reject_read_only_edit():
            return
        self._set_dirty(True)
        self._sync_main_palette_to_config()

        # tile_renderer のキャッシュをクリアして再描画
        if self.tile_renderer is not None:
            self.tile_renderer.clear_cache()
        self._sync_wall_color_preview()
        # ピッカーのアイコンも作り直す（タイルセット番号変えずに再描画させる）
        if self.picker is not None and self.tile_renderer is not None:
            wall_color = None
            if self.level_renderer is not None:
                wall_color = self.level_renderer.get_wall_color(self.current_level_no)
            self.picker.set_current_level_context(
                self.current_level_no,
                self.picker.current_tileset_no,
                wall_color,
            )
            self.picker._populate_all()
        self._refresh_view()
        self._generate_all_thumbnails()

    # ====== レベルクリア ======

    def _on_clear_level(self, mode: str):
        """現在レベルから要素を削除（Undo可能）

        mode:
          "all"     すべて（鍵/扉/スタート/ミラー/星座 は保持）
          "blocks"  ブロックのみ
          "items"   アイテムのみ
          "enemies" モンスターのみ
        """
        if not self.levels:
            return
        if self._reject_read_only_edit():
            return

        labels = {
            "all": "すべての編集対象（ブロック/アイテム/敵）",
            "blocks": "ブロック",
            "items": "アイテム",
            "enemies": "モンスター",
        }
        label = labels.get(mode, "?")
        ans = QMessageBox.question(
            self, "確認",
            f"L{self.current_level_no + 1} の{label}を削除します。よろしいですか？\n"
            f"（Undo可能）",
            QMessageBox.Yes | QMessageBox.No
        )
        if ans != QMessageBox.Yes:
            return

        lv = self.levels[self.current_level_no]
        can_edit_col15 = self.chk_edit_col15.isChecked()
        if mode in ("all", "enemies") and self._key_enemy_is_required_for_exit(lv):
            self.statusBar().showMessage(
                "鍵メタが無いため、鍵持ち敵を含むモンスター削除はできません", 3000
            )
            return

        self._push_undo()

        if mode in ("all", "blocks"):
            for y in range(c.LEVEL_H):
                for x in range(c.LEVEL_W):
                    if x == 15 and not can_edit_col15:
                        continue
                    lv.tiles[y][x] = Wall.NONE
        if mode in ("all", "items"):
            if can_edit_col15:
                lv.items = [
                    item for item in lv.items
                    if self._is_protected_open_door_item(lv, item)
                ]
                lv.visible_in_block_item_cells = {
                    pos for pos in getattr(lv, "visible_in_block_item_cells", set())
                    if any(
                        item.position == pos and self._is_protected_open_door_item(lv, item)
                        for item in lv.items
                    )
                }
            else:
                lv.items = [
                    item for item in lv.items
                    if item.position[0] == 15 or self._is_protected_open_door_item(lv, item)
                ]
                lv.visible_in_block_item_cells = {
                    pos for pos in getattr(lv, "visible_in_block_item_cells", set())
                    if pos[0] == 15 or any(
                        item.position == pos and self._is_protected_open_door_item(lv, item)
                        for item in lv.items
                    )
                }
        if mode in ("all", "enemies"):
            if can_edit_col15:
                lv.enemies = []
            else:
                lv.enemies = [enemy for enemy in lv.enemies if enemy.position[0] == 15]
            self._refresh_key_enemy_spin_range(warn=True)
            self._refresh_fairy_enemy_spin_range(warn=True)

        self._log(f"ステージクリア: S{self.current_level_no + 1} / {label}")
        self._refresh_view()
        self.statusBar().showMessage(
            f"L{self.current_level_no + 1}: {label}をクリア（Ctrl+Zで戻せます）", 4000
        )

    # ====== Undo / Redo ======

    def _push_undo(self):
        """編集前に呼び出して、現在のレベルのスナップショットをスタックに積む

        ドラッグ塗り/消し中は _suppress_next_undo フラグでスキップ。
        """
        self._push_undo_levels([self.current_level_no], focus_level_no=self.current_level_no)

    def _push_undo_levels(self, level_nos, focus_level_no=None):
        if not self.levels:
            return
        if self._is_read_only():
            self.statusBar().showMessage(
                "編集不可: 閲覧/ステージ出力専用ROMです", 3000
            )
            return
        if getattr(self, '_suppress_next_undo', False):
            return
        valid_level_nos = sorted({
            int(level_no)
            for level_no in level_nos
            if 0 <= int(level_no) < len(self.levels)
        })
        if not valid_level_nos:
            return
        if focus_level_no not in valid_level_nos:
            focus_level_no = valid_level_nos[0]
        entry = {
            "focus_level_no": int(focus_level_no),
            "levels": {
                level_no: copy.deepcopy(self.levels[level_no])
                for level_no in valid_level_nos
            },
        }
        if self.rom is not None:
            entry["rom_data"] = bytes(self.rom.data)
        self._undo_stack.append(entry)
        if len(self._undo_stack) > self._undo_limit:
            self._undo_stack.pop(0)
        # 新規編集時は redo はクリア
        self._redo_stack.clear()
        # 未保存マーク
        self._set_dirty(True)

    def _set_dirty(self, dirty: bool):
        """未保存フラグを更新してタイトルバーに反映"""
        if dirty and self._is_read_only():
            self.statusBar().showMessage(
                "編集不可: 閲覧/ステージ出力専用ROMです", 3000
            )
            return
        # クリーン → 編集状態に切り替わった瞬間のみログを残す
        if dirty and not self._dirty:
            lv = (self.current_level_no + 1) if self.levels else "?"
            self._log(f"編集開始: L{lv}")
        self._dirty = dirty
        self._update_title()

    def _update_title(self):
        base = f"{APP_DISPLAY_NAME} v{__version__}"
        if self._dirty:
            mark = self._app_config.get("dirty_mark", "●")
            self.setWindowTitle(f"{mark} {base}")
        else:
            self.setWindowTitle(base)

    def _on_undo(self):
        if not self._undo_stack or not self.levels:
            self.statusBar().showMessage("Undo履歴なし", 2000)
            return
        entry = self._undo_stack.pop()
        # 現在状態を redo に push
        self._redo_stack.append(self._snapshot_current_for_undo_entry(entry))
        if len(self._redo_stack) > self._undo_limit:
            self._redo_stack.pop(0)
        focus_level_no, label = self._restore_undo_entry(entry)
        # 該当レベルへ移動して再描画
        if focus_level_no != self.current_level_no:
            self.spin_level.setValue(focus_level_no + 1)
        else:
            self._refresh_view()
        self.statusBar().showMessage(
            f"Undo: {label} (履歴 {len(self._undo_stack)} 件)", 2500
        )

    def _on_redo(self):
        if not self._redo_stack or not self.levels:
            self.statusBar().showMessage("Redo履歴なし", 2000)
            return
        entry = self._redo_stack.pop()
        self._undo_stack.append(self._snapshot_current_for_undo_entry(entry))
        if len(self._undo_stack) > self._undo_limit:
            self._undo_stack.pop(0)
        focus_level_no, label = self._restore_undo_entry(entry)
        if focus_level_no != self.current_level_no:
            self.spin_level.setValue(focus_level_no + 1)
        else:
            self._refresh_view()
        self.statusBar().showMessage(
            f"Redo: {label} (履歴 {len(self._redo_stack)} 件)", 2500
        )

    def _clear_undo_history(self):
        """ROM読込/XML読込時にUndo履歴をリセット"""
        self._undo_stack.clear()
        self._redo_stack.clear()

    def _undo_entry_levels(self, entry):
        if isinstance(entry, dict) and "levels" in entry:
            return {
                int(level_no): snap
                for level_no, snap in entry["levels"].items()
                if 0 <= int(level_no) < len(self.levels)
            }
        level_no, snap = entry
        if 0 <= int(level_no) < len(self.levels):
            return {int(level_no): snap}
        return {}

    def _undo_entry_focus_level_no(self, entry, level_nos):
        if isinstance(entry, dict) and "focus_level_no" in entry:
            focus_level_no = int(entry["focus_level_no"])
            if focus_level_no in level_nos:
                return focus_level_no
        return level_nos[0] if level_nos else self.current_level_no

    def _undo_entry_label(self, level_nos):
        labels = [self._stage_label(level_no) for level_no in sorted(level_nos)]
        if len(labels) <= 2:
            return ", ".join(labels)
        return f"{labels[0]} ほか{len(labels) - 1}面"

    def _snapshot_current_for_undo_entry(self, entry):
        levels = self._undo_entry_levels(entry)
        level_nos = sorted(levels.keys())
        focus_level_no = self._undo_entry_focus_level_no(entry, level_nos)
        snapshot = {
            "focus_level_no": focus_level_no,
            "levels": {
                level_no: copy.deepcopy(self.levels[level_no])
                for level_no in level_nos
            },
        }
        if self.rom is not None:
            snapshot["rom_data"] = bytes(self.rom.data)
        return snapshot

    def _sync_rom_backed_level_meta_positions(self):
        if self.rom is None or self.config is None:
            return
        from ..core.element import position_from_byte
        for mi in getattr(self.config, "level_meta_items", []) or []:
            rom_offset = int(getattr(mi, "rom_offset", -1))
            if 0 <= rom_offset < len(self.rom.data):
                mi.position = position_from_byte(self.rom.data[rom_offset])

    def _restore_undo_entry(self, entry):
        levels = self._undo_entry_levels(entry)
        level_nos = sorted(levels.keys())
        focus_level_no = self._undo_entry_focus_level_no(entry, level_nos)
        if (
            isinstance(entry, dict)
            and "rom_data" in entry
            and self.rom is not None
        ):
            self.rom.data = bytearray(entry["rom_data"])
            self._sync_rom_backed_level_meta_positions()
        for level_no in level_nos:
            self.levels[level_no] = copy.deepcopy(levels[level_no])
            self._write_mirror_data_to_rom(level_no)
            self._refresh_thumbnail(level_no)
        self._sync_mirror_panel()
        return focus_level_no, self._undo_entry_label(level_nos)

    def _show_keymap(self):
        def sc(action: str) -> str:
            return escape(self._shortcut_text(action))

        gamepad_labels = dict(GAMEPAD_BUTTON_OPTIONS)

        def pad(action: str) -> str:
            shortcuts = normalize_gamepad_shortcuts(
                self._app_config.get("gamepad_shortcuts")
            )
            button = shortcuts.get(action, DEFAULT_GAMEPAD_SHORTCUTS.get(action, ""))
            return escape(gamepad_labels.get(button, "未割当"))

        msg = f"""<b>基本</b><br>
{sc("help")}: このヘルプ<br>
{sc("settings")}: 設定画面<br>
{sc("test_play")} / パッド {pad("test_play")}: テストプレイ<br>
{sc("stage_prev")} / {sc("stage_next")} / パッド {pad("stage_prev")} / {pad("stage_next")}: ステージ切替<br>
{sc("grid")}: グリッド表示切替<br>
{sc("undo")}: Undo<br>
{sc("redo")} / {sc("redo_alt")}: Redo<br>
<br>
<b>マウス操作</b><br>
左クリック: 選択中の要素を配置<br>
右クリック: そのマスの要素を削除<br>
左ドラッグ: 連続配置<br>
右ドラッグ: 連続削除<br>
Ctrl+左ドラッグ: 既存要素を移動<br>
Shift+左ドラッグ: 範囲選択<br>
Alt+左クリック: スポイト（そのマスの要素をピッカーに取り込む）<br>
<br>
<b>ホバー位置のクイック操作</b><br>
{sc("delete_hover_or_selection")} / {sc("delete_hover_or_selection_alt")}: ホバー位置を削除<br>
{sc("hover_enemy_left")} / {sc("hover_enemy_right")} / {sc("hover_enemy_up")} / {sc("hover_enemy_down")}: ホバー位置の敵を対応する向きに変更<br>
{sc("hover_enemy_speed")}: ホバー位置の敵スピードを循環変更<br>
{sc("hover_info")}: ホバー情報ポップアップの表示/非表示<br>
<br>
<b>アイテムフラグ</b><br>
{sc("item_flag_toggle")}: ホバー位置のアイテム/鍵/扉状態を順に切替<br>
{sc("item_flag_toggle_reverse")}: ホバー位置のアイテム/鍵/扉状態を逆順に切替<br>
{sc("hover_item_normal")}: ホバー位置のアイテム/鍵/扉を通常に変更<br>
{sc("hover_item_hidden")}: ホバー位置のアイテム/鍵/扉を隠しに変更（デーモンミラー上では隠しアイテム0x48を配置）<br>
{sc("hover_item_in_block")}: ホバー位置のアイテム/鍵/扉をブロック内に変更<br>
{sc("hover_item_white_in_block")}: ホバー位置のアイテム/鍵/扉を白ブロック内に変更<br>
{sc("hover_item_visible_in_block")}: ホバー位置のアイテム/鍵を透明ブロック内に変更<br>
{sc("hover_item_cracked_in_block")}: ホバー位置のアイテムをひび割れブロック内に変更<br>
<br>
<b>範囲編集</b><br>
{sc("select_all")}: 編集エリア全体を選択（0,0）-（14,11）<br>
{sc("copy_selection")}: コピー<br>
{sc("clear_selection")}: 選択解除<br>
{sc("paste_selection")}: ペースト（選択範囲またはホバー位置を起点）<br>
{sc("cut_selection")}: 切り取り<br>
{sc("item_replace")}: オブジェクト一括置換<br>
{sc("delete_hover_or_selection")} / {sc("delete_hover_or_selection_alt")}: 範囲内を削除<br>
{sc("flip_horizontal")}: 左右反転<br>
{sc("flip_vertical")}: 上下反転<br>
{sc("clear_selection_escape")}: 選択解除<br>
{sc("favorite_1")}〜{sc("favorite_9")} / {sc("favorite_0")}: お気に入りスロット選択<br>
<br>
左右反転は、地形・アイテム・敵・敵の左右向き・スタート・鍵・扉・星座パネル・ミラー・六芒星などのメタ項目も反転します。<br>
<br>
<b>ファイル読込</b><br>
.nes / .zip をウィンドウにドラッグ&ドロップできます。<br>
コマンドライン例: python SOLOMON_CUSTOMIZER.py path/to/rom.nes<br>
"""
        QMessageBox.information(self, "ショートカット", msg)

    # ====== Drag & Drop ======

    def dragEnterEvent(self, event):
        """D&D 開始時 - .nes / .zip なら受け入れ。内部D&D(ピッカー→お気に入り)も通す"""
        from .element_picker import PICKER_MIME
        # 内部D&Dは MainWindow では何もしないが、子ウィジェットへ伝播させるため accept する
        if event.mimeData().hasFormat(PICKER_MIME):
            event.acceptProposedAction()
            return
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                if url.isLocalFile():
                    path = url.toLocalFile().lower()
                    if path.endswith('.nes') or path.endswith('.zip'):
                        event.acceptProposedAction()
                        return
        event.ignore()

    def dragMoveEvent(self, event):
        """ドラッグ中"""
        from .element_picker import PICKER_MIME
        if event.mimeData().hasFormat(PICKER_MIME) or event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        """ドロップ時 - 2ROMならROM比較、1ROMなら読み込み（内部D&Dは子で処理）"""
        from .element_picker import PICKER_MIME
        if event.mimeData().hasFormat(PICKER_MIME):
            # 子ウィジェットで処理されなかった内部D&Dは無視
            event.ignore()
            return
        if not event.mimeData().hasUrls():
            event.ignore()
            return

        paths = []
        for url in event.mimeData().urls():
            if not url.isLocalFile():
                continue
            path = url.toLocalFile()
            lower = path.lower()
            if lower.endswith('.nes') or lower.endswith('.zip'):
                paths.append(path)

        if len(paths) >= 2:
            event.acceptProposedAction()
            self._on_show_rom_diff_for_paths(paths[0], paths[1])
            return
        if len(paths) == 1 and (paths[0].lower().endswith('.nes') or paths[0].lower().endswith('.zip')):
            event.acceptProposedAction()
            self._on_rom_dropped(paths[0])
            return

        event.ignore()
