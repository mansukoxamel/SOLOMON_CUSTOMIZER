"""メインウィンドウ - PyQt5 GUI"""
import copy
import os
from pathlib import Path

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QSpinBox, QFileDialog, QMessageBox, QSplitter,
    QGroupBox, QComboBox, QCheckBox, QListWidget, QApplication,
    QToolBar, QAction, QRadioButton, QButtonGroup
)
from PyQt5.QtCore import Qt, QSize, QEvent
from PyQt5.QtGui import QPixmap, QKeySequence, QCursor, QColor, QPainter, QPen

from .. import __version__
from ..core.rom import Rom, KNOWN_CRC32
from ..core.level import Level, load_all_levels
from ..core.element import Wall, ElementType, LevelElement
from ..core import constants as c
from ..core.config import resolve_project_path, save_config
from ..core import saver, ips, wall_color_hack
from ..gfx.tile_renderer import TileRenderer
from ..gfx.level_renderer import LevelRenderer
from ..nes.config_loader import SkcConfig
from ..nes.tile import load_chr_tiles
from .level_view import LevelView
from .element_picker import (
    ElementPicker, MODE_BLOCK, MODE_ITEM, MODE_ENEMY, MODE_META,
    BLOCK_NONE, BLOCK_BROWN, BLOCK_WHITE, BLOCK_BROWN_WHITE,
    BLOCK_BREAKABLE_WHITE, BLOCK_INVISIBLE_BREAKABLE,
    BLOCK_PASSABLE_WHITE, BLOCK_INVISIBLE_SOLID,
    BLOCK_PASSABLE_BROWN, BLOCK_SOLID_BROWN,
)

APP_DISPLAY_NAME = "SOLOMON_CUSTOMIZER"


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
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedHeight(28)
        self.setMinimumWidth(92)
        self.setToolTip("敵配置数 0/15")

    def set_count(self, count: int, maximum: int = c.ENEMY_COUNT_MAX):
        self._count = max(0, int(count))
        self._maximum = max(1, int(maximum))
        self.setToolTip(f"敵配置数 {self._count}/{self._maximum}")
        self.update()

    def _slot_color(self, index: int) -> QColor:
        if index >= 13:
            return QColor(self._DANGER_COLOR)
        if index >= 9:
            return QColor(self._WARN_COLOR)
        return QColor(self._SAFE_COLOR)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        x = 4
        y = 5
        slot_h = 18
        label_w = 52 if self.width() >= 260 else 0
        gap = 4 if self.width() >= 260 else 2
        slot_area_w = max(self._maximum * 3, self.width() - 8 - label_w)
        slot_w = max(3, (slot_area_w - gap * (self._maximum - 1)) // self._maximum)
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
            x += slot_w + gap

        if label_w:
            text_color = self._slot_color(min(max(self._count, 1), self._maximum))
            painter.setPen(text_color)
            painter.drawText(x + 4, 5, label_w, 18, Qt.AlignVCenter | Qt.AlignLeft, f"{self._count}/{self._maximum}")


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
        self._stage_clipboard = None
        self._stage_swap_source_no = None
        self.show_grid = False
        self.show_object_labels = False
        # Ctrl+クリックでの要素移動: 1回目で掴む、2回目で移動先
        # None または {"kind": "item|enemy|meta", "src": (x,y), "data": ...}
        self._move_pending = None
        # ROM読み込み履歴
        self.last_loaded_path: str = ""
        self._history: list = self._load_history()
        # Undo/Redo: (level_no, deepcopy(Level)) のスタック、上限50件
        self._undo_stack: list = []
        self._redo_stack: list = []
        self._undo_limit = 50

        # 操作ログ（メモリ上に蓄積、closeEventで保存）
        from datetime import datetime
        self._session_log = []
        self._session_start = datetime.now()

        from PyQt5.QtWidgets import QApplication
        self._default_font_size = QApplication.font().pointSize()
        self._default_font_family = QApplication.font().family()

        self._build_ui()

        # 起動時にフォントサイズを反映
        self._apply_font_size()

        # ドラッグ&ドロップ受け入れ
        self.setAcceptDrops(True)

        # ウィンドウ位置・サイズを復元
        self._restore_window_state()
        self._log("セッション開始")

    def _log(self, msg: str):
        """操作ログをメモリに追記（closeEventでファイルに書き出す）"""
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        self._session_log.append(f"[{ts}] {msg}")

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
        """設定からウィンドウ位置・サイズ・最大化状態を復元"""
        cfg = self._app_config
        w = cfg.get("window_w", 1400)
        h = cfg.get("window_h", 800)
        x = cfg.get("window_x", -1)
        y = cfg.get("window_y", -1)
        if isinstance(w, int) and isinstance(h, int) and w > 100 and h > 100:
            self.resize(w, h)
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
                        break
        if cfg.get("window_maximized", False):
            self.showMaximized()

    def _save_window_state(self):
        """現在のウィンドウ状態を設定に保存"""
        cfg = self._app_config
        cfg["window_maximized"] = self.isMaximized()
        if not self.isMaximized():
            # 通常時のみ位置・サイズを記録（最大化状態のサイズは記録しない）
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

    def _build_ui(self):
        # 中央ウィジェット
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        # アプリ設定
        from ..core.config import load_config
        self._app_config = load_config()

        # 左サイド
        left_widget = self._build_left_panel()

        # 最右: レベル選択（サムネイル付き）
        self.levelselect_widget = self._build_levelselect_panel()

        # 中右: 要素ピッカー
        self.picker = ElementPicker()
        self.picker.selection_changed.connect(self._on_picker_selection_changed)
        # お気に入りの永続化
        self.picker.favorites.favorites_changed.connect(self._on_favorites_changed)
        # ボーナスパネルからのアイテム変更
        self.picker.bonus_panel.items_changed.connect(self._on_bonus_panel_items_changed)
        # ミラー敵セット変更
        self.picker.mirror_panel.enemies_changed.connect(self._on_mirror_panel_changed)
        self.btn_mirror = QPushButton("ミラー詳細設定")
        self.btn_mirror.setToolTip(
            "現在ステージの2つのミラーについて、出現タイミング(64ビット)とTTLを編集"
        )
        self.btn_mirror.clicked.connect(self._on_show_mirror)
        self.picker.set_mirror_detail_button(self.btn_mirror)
        self.picker.set_extra_panel_widget(self._build_panel_variant_panel())

        # 中央: レベルビュー
        self.level_view = LevelView(self)
        self.level_view.tile_clicked.connect(self._on_tile_clicked)
        self.level_view.tile_right_clicked.connect(self._on_tile_right_clicked)
        # Ctrl+左ドラッグでの要素移動
        self.level_view.drag_start.connect(self._on_drag_start)
        self.level_view.drag_move.connect(self._on_drag_move)
        self.level_view.drag_end.connect(self._on_drag_end)
        # ホバーハイライト
        self.level_view.tile_hovered.connect(self._on_tile_hovered)
        self._hover_tile = None
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
        self.level_view.rom_dropped.connect(self.load_rom)
        self.level_view.stage_png_dropped.connect(self._on_stage_png_dropped)
        self.enemy_count_indicator = _EnemyCountIndicator(self.level_view.viewport())
        self.enemy_count_indicator.hide()
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
            self._position_enemy_count_indicator()
        return super().eventFilter(obj, event)

    def _position_enemy_count_indicator(self):
        if not hasattr(self, "enemy_count_indicator"):
            return
        indicator = self.enemy_count_indicator
        viewport = self.level_view.viewport()
        h = indicator.height()
        w = min(356, max(indicator.minimumWidth(), viewport.width() - 8))
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

    def _update_enemy_count_indicator(self):
        if not hasattr(self, "enemy_count_indicator"):
            return
        if not self.levels or not (0 <= self.current_level_no < len(self.levels)):
            self.enemy_count_indicator.hide()
            return
        level = self.levels[self.current_level_no]
        count = len(getattr(level, "enemies", []) or [])
        self.enemy_count_indicator.set_count(count, c.ENEMY_COUNT_MAX)
        self.enemy_count_indicator.show()
        self._position_enemy_count_indicator()

    def _build_left_panel(self) -> QWidget:
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        # ファイル操作
        file_group = QGroupBox("ファイル")
        fl = QVBoxLayout(file_group)
        self.btn_open = QPushButton("ROMを開く")
        self.btn_open.clicked.connect(self._on_open_rom)
        fl.addWidget(self.btn_open)

        # 再読込・履歴ボタン（2列）
        btn_row = QHBoxLayout()
        self.btn_reload = QPushButton("再読込")
        self.btn_reload.setToolTip("現在のROMを再読み込み（編集を破棄）")
        self.btn_reload.clicked.connect(self._on_reload_rom)
        self.btn_reload.setEnabled(False)
        btn_row.addWidget(self.btn_reload)

        self.btn_history = QPushButton("履歴")
        self.btn_history.setToolTip("最近開いたROMから選択")
        self.btn_history.clicked.connect(self._on_show_history)
        btn_row.addWidget(self.btn_history)
        fl.addLayout(btn_row)

        self.lbl_rom = QLabel("(未読込)")
        self.lbl_rom.setWordWrap(True)
        fl.addWidget(self.lbl_rom)

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
        el.addWidget(self.btn_sound_viewer, 4, 0, 1, 2)

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

        self.chk_hidden_door = QCheckBox("扉を隠す")
        self.chk_hidden_door.setToolTip(
            "エディタで設定した扉位置のマスを『隠し』化。開始前画面に扉が\n"
            "出ず、ゲーム中も見えませんが、その上の石を壊すと扉が現れます\n"
            "(原作の隠し鍵と同じ仕組み)。扉位置を動かせば追従します"
        )
        self.chk_hidden_door.toggled.connect(self._on_meta_hidden_door_toggled)
        form.addRow("", self.chk_hidden_door)

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
        from PyQt5.QtWidgets import QFormLayout

        wrap = QWidget()
        wrap_layout = QVBoxLayout(wrap)
        wrap_layout.setContentsMargins(0, 0, 0, 0)
        wrap_layout.setSpacing(4)

        group = QGroupBox("強化パネルモンスター設定")
        group.setToolTip("A/B/Cパネルモンスターの弾速度と発射間隔をステージごとに設定")
        layout = QFormLayout(group)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)

        self._panel_variant_controls = {}
        for key, label in (("a", "A"), ("b", "B"), ("c", "C")):
            row = QHBoxLayout()
            combo = QComboBox()
            combo.addItem("1/4", 0)
            combo.addItem("1/2", 1)
            combo.addItem("2x", 2)
            combo.addItem("3x", 3)
            combo.currentIndexChanged.connect(
                lambda _idx, k=key: self._on_panel_variant_setting_changed(k)
            )
            spin = QSpinBox()
            spin.setRange(1, 255)
            spin.valueChanged.connect(
                lambda _val, k=key: self._on_panel_variant_setting_changed(k)
            )
            row.addWidget(combo, 1)
            row.addWidget(QLabel("間隔"))
            row.addWidget(spin, 1)
            layout.addRow(label, row)
            self._panel_variant_controls[key] = (combo, spin)

        group.setEnabled(False)
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

        title = QLabel("ステージ選択")
        title.setObjectName("stageSelectTitle")
        v.addWidget(title)

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
        v.addWidget(self.spin_level)

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

        self.list_levels = _StageListWidget(self)
        # サムネイル表示用のサイズ設定（画像のみ・テキストなし）
        self._thumb_size = QSize(160, 120)  # 16:12 比率
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
        item_size = QSize(self._thumb_size.width() + 8, self._thumb_size.height() + 8)
        for i in range(c.LEVEL_COUNT):
            item = QListWidgetItem()
            item.setToolTip(f"Stage {i+1}")
            item.setSizeHint(item_size)
            self.list_levels.addItem(item)
        self.list_levels.currentRowChanged.connect(self._on_list_changed)
        v.addWidget(self.list_levels, 1)

        return w

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
            show_border=True,
            bonus_items=bonus,
        )
        pix = QPixmap.fromImage(img).scaled(
            self._thumb_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        item = self.list_levels.item(level_no)
        if item is not None:
            item.setIcon(QIcon(pix))

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
        self.load_rom(path)

    def load_rom(self, path: str):
        try:
            rom = Rom.load(path)
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

            # ボーナスステージテーブル読み込み（拡張前のアドレスで読む必要がある）
            self._load_bonus_stage_table(rom, allow_mutation=False)

            # 通常ROM (mapper 3) なら自動的に拡張ROM (mapper 66) に変換
            # 容量制約 (敵726B/アイテム1402B) を回避するため
            auto_expanded = False
            self.original_rom_data = loaded_rom_data
            if not read_only_mode and not rom.is_expanded():
                from ..core import m66_expander
                m66_expander.expand_rom(rom, levels)
                auto_expanded = True

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
            self.tile_renderer = TileRenderer(config, nes_tiles)
            self.level_renderer = LevelRenderer(self.tile_renderer, config)
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
            info_html = (
                f"<b>{rom.display_name}</b><br>"
                f"[{rom.region}, {len(rom)/1024:.0f}KB]<br>"
                f"CRC32: <code>{crc_hex}</code> {verify_mark}"
                f"{version_note}"
                f"{expand_note}"
                f"{readonly_note}"
            )
            if known:
                info_html += f"<br><span style='color:#aaa'>{known}</span>"
            self.lbl_rom.setText(info_html)
            self.lbl_rom.setTextFormat(Qt.RichText)
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
            self.btn_test_play.setEnabled(edit_enabled)
            self.btn_test_play_right.setEnabled(edit_enabled)
            self.meta_group.setEnabled(edit_enabled)
            self.picker.setEnabled(edit_enabled)
            self.chk_edit_col15.setEnabled(edit_enabled)
            self.spin_level.setValue(1)
            self._refresh_view()
            # 全レベルのサムネイル生成（53枚、約1〜3秒）
            self.statusBar().showMessage("サムネイル生成中...")
            QApplication.processEvents()
            self._generate_all_thumbnails()
            status_suffix = " (編集不可)" if read_only_mode else ""
            self.statusBar().showMessage(f"読み込み完了: {len(levels)}ステージ{status_suffix}")
            # 読込成功 → 再読込ボタンを有効化、履歴に追加、Undo履歴クリア、未保存マーククリア
            self.last_loaded_path = path
            self.btn_reload.setEnabled(True)
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

    # ====== 再読込・履歴 ======

    def _history_file(self) -> Path:
        """履歴を保存するJSONファイルパス"""
        return Path(__file__).parent.parent.parent / "config" / "rom_history.json"

    def _load_history(self) -> list:
        import json
        try:
            with open(self._history_file(), "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("history", [])[:15]
        except Exception:
            return []

    def _save_history(self):
        import json
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

    def _on_reload_rom(self):
        if not self.last_loaded_path:
            return
        self.load_rom(self.last_loaded_path)

    def _on_show_history(self):
        from PyQt5.QtWidgets import QMenu
        menu = QMenu(self)
        if not self._history:
            menu.addAction("(履歴なし)").setEnabled(False)
        else:
            for path in self._history:
                # 表示はファイル名 + 親フォルダ
                p = Path(path)
                label = f"{p.name}  ({p.parent.name})"
                action = menu.addAction(label)
                action.setToolTip(path)
                action.triggered.connect(lambda checked, pp=path: self.load_rom(pp))
            menu.addSeparator()
            clr = menu.addAction("履歴をクリア")
            clr.triggered.connect(self._on_clear_history)
        # ボタンの真下に表示
        btn = self.btn_history
        menu.exec_(btn.mapToGlobal(btn.rect().bottomLeft()))

    def _on_clear_history(self):
        self._history = []
        self._save_history()
        self.statusBar().showMessage("履歴をクリアしました", 2000)

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

    def _on_save_rom(self):
        if not self.rom:
            return
        if self._reject_read_only_edit():
            return
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
            return
        try:
            saved_data = saver.build_saved_rom_data(self.rom, self.levels)
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
        except Exception as e:
            self._show_save_failure("保存失敗", e, "ROM保存失敗")

    def _on_test_play(self):
        """現在の編集状態 + ステージ選択(現在レベル) で一時ROMを生成しエミュ起動"""
        if not self.rom or not self.levels:
            return
        if self._reject_read_only_edit():
            return
        emu_path = self._app_config.get("emulator_path", "")
        if not emu_path or not os.path.exists(emu_path):
            QMessageBox.warning(
                self, "エミュレータ未設定",
                "F9 設定画面で『エミュレータ』のパスを指定してください"
            )
            return

        from ..core import hack_data
        import tempfile
        import subprocess

        # rom.dataを破壊しないよう、作業前のコピーを取っておく
        original_data = bytearray(self.rom.data)
        tmp_rom = None
        stage_no = self.current_level_no + 1

        try:
            try:
                # レベルを反映
                saver.save_levels_to_rom(self.rom, self.levels)
                # ステージ選択: 現在レベルから開始
                if stage_no == 1:
                    self.rom.data[0x1145] = 0x00
                    self.rom.data[0x1149] = 0x8D
                    self.rom.data[0x114B] = 0x04
                else:
                    stage_byte = (stage_no - 1) & 0xff
                    self.rom.data[0x1145] = stage_byte
                    self.rom.data[0x1149] = 0xAD
                    self.rom.data[0x114B] = 0x93

                # F9 testplay-only fast start. These bytes match the accepted
                # raw-JP test ROM:
                # TEST_OrigJP_MinTitleSkip_CBB3_SkipStartWaits_9066_9082_9315.
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

                # 一時ファイルへ書き出し
                tmpdir = Path(tempfile.gettempdir()) / "magatu_skc_testplay"
                tmpdir.mkdir(parents=True, exist_ok=True)
                tmp_rom = tmpdir / "testplay.nes"
                saver.write_rom_file(self.rom, str(tmp_rom))
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
            self._log(f"テストプレイ起動: Stage {stage_no} → {tmp_rom}")
        except Exception as e:
            QMessageBox.critical(self, "エミュ起動失敗", f"{type(e).__name__}: {e}")
            self._log(f"テストプレイ失敗: {type(e).__name__}: {e}")

    def _on_save_ips(self):
        if not self.rom:
            return
        if self._reject_read_only_edit():
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
            modified_data = saver.build_saved_rom_data(self.rom, self.levels)
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
            self._save_png_with_xml(img, level, stage_dir / f"level_{i + 1:02d}.png")
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

    def _save_png_with_xml(self, img, level, path):
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
        xml_str = level_to_magatu_xml(level)
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
        self._save_png_with_xml(img, level, path)
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
            self._save_png_with_xml(img, level, path)
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

    def _on_level_changed(self, value: int):
        new_no = value - 1
        if new_no == self.current_level_no:
            return
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
            self._update_enemy_count_indicator()
            return
        if not (0 <= self.current_level_no < len(self.levels)):
            self._update_enemy_count_indicator()
            return
        level = self.levels[self.current_level_no]
        # ピッカーのアイコンを現在レベルのタイルセットで再描画（skchain互換）
        ts_no = self.level_renderer.get_actual_tileset_no(self.current_level_no, level.tileset_no)
        self.picker.set_current_tileset_no(ts_no)
        # 特殊処理マーカーを抽出（表示ONかつ ROM対応リージョンの場合のみ）
        sp_marks = self._get_special_marks()
        img = self.level_renderer.render(
            level,
            level_no=self.current_level_no,
            show_grid=self.show_grid,
            show_hidden_overlay=self.chk_hidden.isChecked(),
            hover_tile=self._hover_tile,
            show_col15=True,
            selection_rect=self._selection_rect,
            special_marks=sp_marks,
            show_border=True,
            bonus_items=self._get_bonus_items(),
        )
        self.level_view.set_image(img)
        self._update_enemy_count_indicator()
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
        try:
            from ..core import special_process as sp
            region = self.rom.base_region()
            return sp.find_marks_for_level(
                bytes(self.rom.data), region, target_level_no
            )
        except Exception:
            return None

    def _on_picker_selection_changed(self, mode, value):
        """ピッカー選択変更時 → カーソル形状を選択中アイコンに"""
        self._update_cursor_from_picker()
        # 鍵選択時: 現在レベルの key_status を配置フラグに反映
        if mode == MODE_META and value == "key" and self.levels:
            from ..core import constants as cc
            lv = self.levels[self.current_level_no]
            if lv.key_status == cc.KEY_STATUS_HIDDEN:
                self.picker.rb_flag_hidden.setChecked(True)
            elif lv.key_status == cc.KEY_STATUS_IN_BLOCK:
                self.picker.rb_flag_in_block.setChecked(True)
            else:
                self.picker.rb_flag_normal.setChecked(True)

    def _update_cursor_from_picker(self):
        """ピッカーで選択中のアイコンを LevelView のカーソル形状に設定"""
        items = self.picker.get_selected_items()
        if not items:
            self.level_view.unsetCursor()
            return
        icon = items[0].icon()
        if icon.isNull():
            self.level_view.unsetCursor()
            return
        # 32x32 のカーソル（小さすぎず大きすぎず）
        pixmap = icon.pixmap(32, 32)
        if pixmap.isNull():
            self.level_view.unsetCursor()
            return
        # ホットスポットは中央
        cursor = QCursor(pixmap, 16, 16)
        self.level_view.setCursor(cursor)

    def _on_tile_hovered(self, tile):
        """ホバー位置変化時の処理 - 軽量再描画 + ステータスバー更新"""
        if self._hover_tile == tile:
            return
        self._hover_tile = tile
        # 描画だけ更新（_update_info は呼ばない）
        if self.levels and self.level_renderer is not None:
            level = self.levels[self.current_level_no]
            img = self.level_renderer.render(
                level,
                level_no=self.current_level_no,
                show_grid=self.show_grid,
                show_hidden_overlay=self.chk_hidden.isChecked(),
                hover_tile=self._hover_tile,
                show_col15=True,
                selection_rect=self._selection_rect,
                special_marks=self._get_special_marks(),
                show_border=True,
                bonus_items=self._get_bonus_items(),
            )
            self.level_view.set_image(img)
            self._sync_object_labels()
        # ステータスバーのホバー情報を更新
        self._update_hover_info(tile)

    def _update_hover_info(self, tile):
        """マウス下部のタイル中身をステータスバーに表示"""
        if tile is None or not self.levels:
            self.lbl_hover_info.setText("")
            return
        x, y = tile
        lv = self.levels[self.current_level_no]
        parts = [f"({x:2d},{y:2d})"]

        # ブロック
        wall = lv.tiles[y][x]
        if wall == Wall.BROWN and tile in getattr(lv, "passable_brown_cells", set()):
            parts.append("すり抜け土色壁")
        elif wall == Wall.BROWN and tile in getattr(lv, "solid_brown_cells", set()):
            parts.append("壊せない土色壁")
        elif wall == Wall.BROWN:
            parts.append("茶ブロック")
        elif wall == Wall.WHITE and tile in getattr(lv, "breakable_white_cells", set()):
            parts.append("壊せる白壁")
        elif wall == Wall.WHITE:
            parts.append("白ブロック")
        # BROWN_WHITE は v0.1.99 で廃止 (読込時に WHITE へ正規化)

        # アイテム
        item_idx = lv.get_item_index(tile)
        if item_idx >= 0:
            it = lv.items[item_idx]
            base = it.element_no & 0x3F
            flag = it.element_no & 0xC0
            desc = self.config.item_desc.get(base, f"item 0x{base:02x}") if self.config else f"0x{base:02x}"
            tag = ""
            if flag == 0x40: tag = "[隠し]"
            elif flag == 0x80: tag = "[in_block]"
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
            parts.append("[鍵]")
        if not lv.is_door_removed() and lv.fixed_door_pos == tile:
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

        self.lbl_hover_info.setText(" / ".join(parts))

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

            # 扉位置にブロックは置けない（出られない）
            if value not in passable_block_values and not lv.is_door_removed() and lv.fixed_door_pos == tile:
                self.statusBar().showMessage(
                    f"扉位置にブロックは置けません {tile}", 2500
                )
                restore_rejected_click_edit()
                return

            # 白ブロック（壊せない）にアイテムが既にあると、そのアイテムは取れなくなるので拒否
            if value in (
                BLOCK_WHITE, BLOCK_BREAKABLE_WHITE, BLOCK_PASSABLE_WHITE,
                BLOCK_PASSABLE_BROWN, BLOCK_SOLID_BROWN,
            ) and lv.get_item_index(tile) >= 0:
                self.statusBar().showMessage(
                    f"アイテムがある位置に特殊壁は置けません（取れなくなる） {tile}", 3000
                )
                restore_rejected_click_edit()
                return

            # ブロック（茶 or 壊せる白）+ アイテム → アイテムに in_block フラグを自動付与
            if value in (BLOCK_BROWN, BLOCK_BROWN_WHITE):
                idx = lv.get_item_index(tile)
                if idx >= 0:
                    item = lv.items[idx]
                    base = item.element_no & 0x3F
                    item.element_no = base | 0x80
                    self.statusBar().showMessage(
                        f"アイテムを in_block フラグ付きに自動変換 {tile}", 2500
                    )

            if value == BLOCK_NONE:
                lv.set_block(Wall.NONE, tile)
                lv.invisible_breakable_cells.discard(tile)
                lv.invisible_solid_cells.discard(tile)
                lv.passable_brown_cells.discard(tile)
                lv.solid_brown_cells.discard(tile)
            elif value == BLOCK_BROWN:
                lv.set_block(Wall.BROWN, tile)
                lv.passable_brown_cells.discard(tile)
                lv.solid_brown_cells.discard(tile)
            elif value == BLOCK_WHITE:
                lv.set_block(Wall.WHITE, tile)
                lv.breakable_white_cells.discard(tile)
                lv.passable_white_cells.discard(tile)
                lv.passable_brown_cells.discard(tile)
                lv.solid_brown_cells.discard(tile)
            elif value == BLOCK_BREAKABLE_WHITE:
                lv.set_block(Wall.WHITE, tile)
                lv.invisible_breakable_cells.discard(tile)
                lv.passable_white_cells.discard(tile)
                lv.passable_brown_cells.discard(tile)
                lv.solid_brown_cells.discard(tile)
                lv.breakable_white_cells.add(tile)
            elif value == BLOCK_INVISIBLE_BREAKABLE:
                lv.set_block(Wall.NONE, tile)
                lv.breakable_white_cells.discard(tile)
                lv.invisible_solid_cells.discard(tile)
                lv.passable_white_cells.discard(tile)
                lv.passable_brown_cells.discard(tile)
                lv.solid_brown_cells.discard(tile)
                lv.invisible_breakable_cells.add(tile)
            elif value == BLOCK_PASSABLE_WHITE:
                lv.set_block(Wall.WHITE, tile)
                lv.breakable_white_cells.discard(tile)
                lv.invisible_breakable_cells.discard(tile)
                lv.invisible_solid_cells.discard(tile)
                lv.passable_brown_cells.discard(tile)
                lv.solid_brown_cells.discard(tile)
                lv.passable_white_cells.add(tile)
            elif value == BLOCK_INVISIBLE_SOLID:
                lv.set_block(Wall.NONE, tile)
                lv.breakable_white_cells.discard(tile)
                lv.invisible_breakable_cells.discard(tile)
                lv.passable_white_cells.discard(tile)
                lv.passable_brown_cells.discard(tile)
                lv.solid_brown_cells.discard(tile)
                lv.invisible_solid_cells.add(tile)
            elif value == BLOCK_PASSABLE_BROWN:
                lv.set_block(Wall.BROWN, tile)
                lv.breakable_white_cells.discard(tile)
                lv.passable_white_cells.discard(tile)
                lv.invisible_breakable_cells.discard(tile)
                lv.invisible_solid_cells.discard(tile)
                lv.solid_brown_cells.discard(tile)
                lv.passable_brown_cells.add(tile)
            elif value == BLOCK_SOLID_BROWN:
                lv.set_block(Wall.BROWN, tile)
                lv.breakable_white_cells.discard(tile)
                lv.passable_white_cells.discard(tile)
                lv.invisible_breakable_cells.discard(tile)
                lv.invisible_solid_cells.discard(tile)
                lv.passable_brown_cells.discard(tile)
                lv.solid_brown_cells.add(tile)
            elif value == BLOCK_BROWN_WHITE:
                lv.set_block(Wall.BROWN_WHITE, tile)
                lv.passable_brown_cells.discard(tile)
                lv.solid_brown_cells.discard(tile)
        elif mode == MODE_ITEM:
            tx, ty = tile

            if (tile in getattr(lv, "invisible_breakable_cells", set()) or
                    tile in getattr(lv, "invisible_solid_cells", set())):
                self.statusBar().showMessage(
                    f"透明な壊せる壁にはアイテムを配置できません {tile}", 3000
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

            # 白ブロック内アイテム禁止（取れなくなる）
            if lv.tiles[ty][tx] == Wall.WHITE:
                self.statusBar().showMessage(
                    f"白ブロック内にはアイテムを配置できません {tile}", 3000
                )
                restore_rejected_click_edit()
                return

            # アイテム × アイテム 重複禁止 → 置換
            existing = lv.get_item_index(tile)
            if existing >= 0:
                lv.delete_item(existing)
                self.statusBar().showMessage(
                    f"既存アイテムを置換 {tile}", 2500
                )

            # フラグ決定:
            # - タイルが茶 or 壊せる白 → 強制 in_block (0x80)
            # - タイルが空 → ピッカーで選択中のフラグを使用
            picker_flag = self.picker.get_item_flag()
            if lv.tiles[ty][tx] in (Wall.BROWN, Wall.BROWN_WHITE):
                flag = 0x80
                if picker_flag != 0x80:
                    self.statusBar().showMessage(
                        f"ブロック内のため自動で in_block フラグON {tile}", 2500
                    )
            else:
                flag = picker_flag

            lv.add_item(value | flag, tile)
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
        elif mode == MODE_META:
            if value == "start":
                lv.fixed_start_pos = tile
            elif value == "key":
                lv.fixed_key_pos = tile
                # 配置フラグを key_status に反映（通常/隠し/ブロック内）
                from ..core import constants as cc
                picker_flag = self.picker.get_item_flag()
                flag_map = {
                    0x00: cc.KEY_STATUS_NORMAL,
                    0x40: cc.KEY_STATUS_HIDDEN,
                    0x80: cc.KEY_STATUS_IN_BLOCK,
                }
                lv.key_status = flag_map.get(picker_flag, cc.KEY_STATUS_NORMAL)
            elif value == "door":
                lv.fixed_door_pos = tile
            elif value == "mirror1":
                lv.demon_mirrors[0].position = tile
            elif value == "mirror2":
                lv.demon_mirrors[1].position = tile

        self._refresh_view()

    # ====== Ctrl+左ドラッグでの要素移動 ======

    def _on_drag_start(self, tile: tuple):
        """Ctrl+左クリックで要素を掴む。掴んだ element の参照を保持"""
        if not self.levels:
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
                if drag_clip is not None and (drag_clip["blocks"] or drag_clip["items"] or drag_clip["enemies"]):
                    self._push_undo()
                    # 元位置を空にする（self._delete_in_selection は undo を積むので直接実行）
                    for y in range(y1, y2 + 1):
                        for x in range(x1, x2 + 1):
                            lv.tiles[y][x] = Wall.NONE
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

        # 優先順位: item > enemy > meta（key/door/start/mirror1/mirror2）
        idx = lv.get_item_index(tile)
        if idx >= 0:
            self._push_undo()
            self._move_pending = {"kind": "item", "ref": lv.items[idx]}
            self.statusBar().showMessage(f"アイテムを掴み中 → ドラッグで移動", 0)
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

        if lv.fixed_key_pos == tile and not lv.is_key_removed():
            self._move_pending = {"kind": "meta", "sub": "key"}
        elif lv.fixed_door_pos == tile and not lv.is_door_removed():
            self._move_pending = {"kind": "meta", "sub": "door"}
        elif lv.fixed_start_pos == tile:
            self._move_pending = {"kind": "meta", "sub": "start"}
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
            self.statusBar().showMessage(
                f"{self._move_pending['sub']} を掴み中 → ドラッグで移動", 0
            )
            return

        # ブロックを掴む（最後の優先順位、他の要素が無い場合のみ）
        tx, ty = tile
        wall = lv.tiles[ty][tx]
        if wall != Wall.NONE:
            self._push_undo()
            self._move_pending = {
                "kind": "block",
                "wall_type": wall,
                "current_pos": tile,
                # 現在位置に「元々あった壁」（drag_moveで復元するため）
                # 元位置は今クリアしたので NONE
                "prev_wall_at_current": Wall.NONE,
            }
            # 元位置を空白に
            lv.tiles[ty][tx] = Wall.NONE
            label = {Wall.BROWN: "茶ブロック", Wall.WHITE: "白ブロック",
                     Wall.BROWN_WHITE: "壊せる白"}.get(wall, "ブロック")
            self.statusBar().showMessage(f"{label} を掴み中 → ドラッグで移動", 0)
            self._refresh_view()

    def _on_drag_move(self, tile: tuple):
        """ドラッグ中、掴んでいる要素を tile に追従させる"""
        if not self.levels or self._move_pending is None:
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
            selection_target = (clip, ox, oy)
        elif self._is_locked_col15_tile(tile):
            self._show_col15_locked_message("16列目へは移動できません（「16列目を編集」をONにしてください）")
            return

        if kind in ("item", "enemy"):
            mp["ref"].position = tile
        elif kind == "meta":
            sub = mp["sub"]
            if sub == "key":
                lv.fixed_key_pos = tile
            elif sub == "door":
                lv.fixed_door_pos = tile
            elif sub == "start":
                lv.fixed_start_pos = tile
            elif sub == "mirror1":
                lv.demon_mirrors[0].position = tile
            elif sub == "mirror2":
                lv.demon_mirrors[1].position = tile
        elif kind == "seal":
            mp["ref"].position = tile
        elif kind == "bonus":
            bi = mp["index"]
            self._bonus_positions[bi] = tile
            # _bonus_items も再構築（レンダラー用）
            self._rebuild_bonus_items_from_positions()
        elif kind == "block":
            # 通り過ぎたタイルの「元の壁」を復元してから新位置にブロック配置
            cx, cy = mp["current_pos"]
            # 現在位置を元に戻す
            lv.tiles[cy][cx] = mp["prev_wall_at_current"]
            # 新位置の元の壁を保存
            tx, ty = tile
            mp["prev_wall_at_current"] = lv.tiles[ty][tx]
            # 新位置にブロック配置
            lv.tiles[ty][tx] = mp["wall_type"]
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
            elif kind == "bonus":
                self._write_bonus_positions_to_rom()
                self.statusBar().showMessage("ボーナススポット移動完了", 2000)
            elif kind == "seal":
                mi = self._move_pending["ref"]
                if self.rom and mi.rom_offset >= 0 and mi.rom_offset < len(self.rom.data):
                    from ..core.element import byte_from_position
                    self.rom.data[mi.rom_offset] = byte_from_position(mi.position)
                self.statusBar().showMessage(
                    f"{mi.description} 移動完了 → {mi.position}", 2000)
            else:
                self.statusBar().showMessage("移動完了", 2000)
        self._move_pending = None

    def _on_tile_right_clicked(self, tile: tuple):
        """右クリック: そのタイルの全要素を削除（編集モード非依存）

        優先順位は気にせず、その位置に存在するもの全て削除:
          - アイテム / 敵 / ブロック を順に消す
          - メタ要素（鍵/扉/スタート/ミラー）は移動が原則なので削除対象外
        """
        if not self.levels:
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
            "invisible_breakable_cells",
            "passable_white_cells",
            "invisible_solid_cells",
            "passable_brown_cells",
            "solid_brown_cells",
        )
        has_runtime_marker = any(tile in getattr(lv, name, set()) for name in marker_names)
        if (
            lv.get_item_index(tile) < 0
            and lv.get_enemy_index(tile) < 0
            and lv.tiles[tile[1]][tile[0]] == Wall.NONE
            and not has_runtime_marker
        ):
            return

        self._push_undo()
        if not getattr(self, '_suppress_next_undo', False):
            self._right_drag_has_undo = True

        deleted = []

        # アイテム削除（同位置に複数ある場合に備えてループ）
        while True:
            idx = lv.get_item_index(tile)
            if idx < 0:
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
        return False

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
        }
        for y in range(y1, y2 + 1):
            for x in range(x1, x2 + 1):
                w = lv.tiles[y][x]
                if w != Wall.NONE:
                    clip["blocks"][(x - x1, y - y1)] = w
        for name in (
            "breakable_white_cells",
            "invisible_breakable_cells",
            "passable_white_cells",
            "invisible_solid_cells",
            "passable_brown_cells",
            "solid_brown_cells",
        ):
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
        return clip

    def _copy_selection(self):
        """選択範囲を内部クリップボードへコピー"""
        clip = self._build_clipboard_from_selection()
        if clip is None:
            self.statusBar().showMessage("選択範囲がありません", 1500)
            return
        self._clipboard = clip
        total = len(clip["blocks"]) + len(clip["items"]) + len(clip["enemies"])
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
                idx = lv.get_item_index((tx, ty))
                if idx >= 0:
                    lv.delete_item(idx)
                lv.items.append(LevelElement(ElementType.ITEM, (tx, ty), it_data["element_no"]))
        for en_data in clip["enemies"]:
            rx, ry = en_data["rel_pos"]
            tx, ty = ox + rx, oy + ry
            if self._can_edit_tile_pos(tx, ty):
                lv.enemies.append(LevelElement(ElementType.ENEMY, (tx, ty), en_data["element_no"]))

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

        self._push_undo()
        self._paste_clipboard_at(self._clipboard, ox, oy)
        self._refresh_key_enemy_spin_range()
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
        self._push_undo()
        lv = self.levels[self.current_level_no]
        # ブロック
        for y in range(y1, y2 + 1):
            for x in range(x1, x2 + 1):
                lv.tiles[y][x] = Wall.NONE
        for name in (
            "breakable_white_cells",
            "invisible_breakable_cells",
            "passable_white_cells",
            "invisible_solid_cells",
            "passable_brown_cells",
            "solid_brown_cells",
        ):
            cells = getattr(lv, name, set())
            setattr(lv, name, {
                pos for pos in cells
                if not (x1 <= pos[0] <= x2 and y1 <= pos[1] <= y2)
            })
        # アイテム
        lv.items = [it for it in lv.items
                    if not (x1 <= it.position[0] <= x2 and y1 <= it.position[1] <= y2)]
        # 敵
        old_enemy_count = len(lv.enemies)
        lv.enemies = [en for en in lv.enemies
                      if not (x1 <= en.position[0] <= x2 and y1 <= en.position[1] <= y2)]
        if len(lv.enemies) != old_enemy_count:
            self._refresh_key_enemy_spin_range(warn=True)
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
            flip_marker_set("breakable_white_cells", flip_x)
            flip_marker_set("invisible_breakable_cells", flip_x)
            flip_marker_set("passable_white_cells", flip_x)
            flip_marker_set("invisible_solid_cells", flip_x)
            flip_marker_set("passable_brown_cells", flip_x)
            flip_marker_set("solid_brown_cells", flip_x)
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
            flip_marker_set("breakable_white_cells", flip_y)
            flip_marker_set("invisible_breakable_cells", flip_y)
            flip_marker_set("passable_white_cells", flip_y)
            flip_marker_set("invisible_solid_cells", flip_y)
            flip_marker_set("passable_brown_cells", flip_y)
            flip_marker_set("solid_brown_cells", flip_y)
            self.statusBar().showMessage("上下反転", 2000)

        self._refresh_view()

    def _on_tile_picked(self, tile: tuple):
        """Alt+左クリック: スポイト — その位置の要素をピッカーに取り込む

        優先順: 敵 > アイテム > メタ要素 > ブロック
        """
        if not self.levels:
            return
        from .element_picker import (
            MODE_BLOCK, MODE_ITEM, MODE_ENEMY, MODE_META,
            BLOCK_BROWN, BLOCK_WHITE, BLOCK_BROWN_WHITE, BLOCK_BREAKABLE_WHITE,
            BLOCK_INVISIBLE_BREAKABLE, BLOCK_PASSABLE_WHITE, BLOCK_INVISIBLE_SOLID,
            BLOCK_PASSABLE_BROWN, BLOCK_SOLID_BROWN,
            ITEM_FLAG_NORMAL, ITEM_FLAG_HIDDEN, ITEM_FLAG_IN_BLOCK,
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
            if flag == 0x40:
                self.picker.rb_flag_hidden.setChecked(True)
            elif flag == 0x80:
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

    def _show_settings(self):
        from .settings_dialog import SettingsDialog
        dlg = SettingsDialog(self._app_config, parent=self)
        dlg.exec_()

    def _apply_settings(self, new_config: dict):
        """設定ダイアログから呼び出される。即時反映 + JSON保存"""
        self._app_config = dict(new_config)
        from ..core.config import save_config
        save_config(self._app_config)
        self._update_title()
        self._apply_theme()
        self._apply_font_size()
        self._apply_icon()

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

    def closeEvent(self, event):
        """ウィンドウを閉じる時、未保存の変更があれば確認"""
        if self._dirty:
            ans = QMessageBox.question(
                self, "未保存の変更",
                "保存していない変更があります。\n本当に終了しますか？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if ans != QMessageBox.Yes:
                event.ignore()
                return
        # ウィンドウ状態を保存してから閉じる
        self._save_window_state()
        self._log("セッション終了")
        event.accept()

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
        mods = event.modifiers()
        # Undo / Redo / 選択範囲操作
        if mods & Qt.ControlModifier:
            if key == Qt.Key_Z and (mods & Qt.ShiftModifier):
                self._on_redo()
                return
            if key == Qt.Key_Z:
                self._on_undo()
                return
            if key == Qt.Key_Y:
                self._on_redo()
                return
            if key == Qt.Key_C:
                self._copy_selection()
                return
            if key == Qt.Key_V:
                self._paste_clipboard()
                return
            if key == Qt.Key_X:
                self._cut_selection()
                return
        if key == Qt.Key_F1:
            self._show_keymap()
        elif key == Qt.Key_F9:
            self._show_settings()
        elif key == Qt.Key_PageDown:
            self.spin_level.setValue(min(c.LEVEL_COUNT, self.spin_level.value() + 1))
        elif key == Qt.Key_PageUp:
            self.spin_level.setValue(max(1, self.spin_level.value() - 1))
        elif key == Qt.Key_G:
            self.chk_grid.toggle()
        elif key == Qt.Key_Escape:
            # Esc → 選択範囲解除
            if self._selection_rect is not None:
                self._on_selection_cleared()
        elif key in (Qt.Key_Delete, Qt.Key_Backspace):
            # Delete/Backspace → 選択範囲があればその範囲、なければホバー位置を削除
            if self._selection_rect is not None:
                self._delete_in_selection()
            elif self._hover_tile is not None and self.levels:
                self._on_tile_right_clicked(self._hover_tile)
        elif key == Qt.Key_H:
            # H → アイテムフラグを「隠し」に
            self.picker.rb_flag_hidden.setChecked(True)
            self.statusBar().showMessage("アイテムフラグ: 隠し (0x40)", 1500)
        elif key == Qt.Key_B:
            # B → アイテムフラグを「ブロック内」に
            self.picker.rb_flag_in_block.setChecked(True)
            self.statusBar().showMessage("アイテムフラグ: ブロック内 (0x80)", 1500)
        elif key == Qt.Key_N:
            # N → アイテムフラグを「通常」に
            self.picker.rb_flag_normal.setChecked(True)
            self.statusBar().showMessage("アイテムフラグ: 通常", 1500)
        elif key == Qt.Key_P:
            self._on_test_play()
        elif key == Qt.Key_F:
            # F → 選択範囲を左右反転（Shift+Fで上下反転）
            if mods & Qt.ShiftModifier:
                self._flip_selection_vertical()
            else:
                self._flip_selection_horizontal()
        elif Qt.Key_0 <= key <= Qt.Key_9:
            # 数字キー 1〜9, 0 → ピッカーのお気に入りスロット選択
            n = key - Qt.Key_0
            if not self.picker.trigger_favorite_key(n):
                self.statusBar().showMessage(
                    f"お気に入りスロット {n} は空です", 1500
                )
            else:
                self.statusBar().showMessage(
                    f"お気に入りスロット {n} を選択", 1500
                )
        else:
            super().keyPressEvent(event)

    def _quick_place_at_hover(self, n: int):
        """数字キー 0-9 でホバー位置にクイック配置

        モード別:
          BLOCK: 0=消去, 1=茶, 2=白, 3=壊せる白
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
            BLOCK_BREAKABLE_WHITE, BLOCK_INVISIBLE_BREAKABLE,
            BLOCK_PASSABLE_WHITE, BLOCK_INVISIBLE_SOLID,
            BLOCK_PASSABLE_BROWN, BLOCK_SOLID_BROWN,
            MODE_BLOCK, MODE_ITEM, MODE_ENEMY, MODE_META,
            ITEMS_LIST, ENEMIES_LIST,
        )

        if mode == MODE_BLOCK:
            block_map = {0: BLOCK_NONE, 1: BLOCK_BROWN, 2: BLOCK_WHITE,
                         3: BLOCK_BROWN_WHITE, 4: BLOCK_BREAKABLE_WHITE,
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
        current = _se.get_key_enemy_number(lv)
        display_current = current
        if current > max_enemy:
            if self._is_read_only():
                display_current = 0
            else:
                _se.set_key_enemy_number(lv, 0)
                display_current = 0
                self._set_dirty(True)
            if warn and not self._is_read_only():
                QMessageBox.warning(
                    self,
                    "鍵持ち敵設定を解除",
                    "鍵持ち敵に指定していた番号が、このステージの敵数を超えたため解除しました。"
                )
        old_block = self.spin_key_enemy.blockSignals(True)
        self.spin_key_enemy.setRange(0, max_enemy)
        self.spin_key_enemy.setValue(display_current)
        self.spin_key_enemy.blockSignals(old_block)
        self.spin_key_enemy.setToolTip(
            f"0=なし。1から{max_enemy}は初期配置敵の順番です。このステージの敵数: {len(lv.enemies)}"
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
            self.chk_hidden_door.setChecked(
                bool(lv.room_flags & _rf.BIT_HIDDEN_DOOR))
            self.chk_dark.setChecked(bool(lv.room_flags & _rf.BIT_DARK))
            from ..core import stage_ext as _se
            self.chk_fire_reset.setChecked(_se.fire_reset_enabled(lv))
            self._refresh_key_enemy_spin_range()
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
        if not hasattr(self, "_panel_variant_controls"):
            return
        from ..core import panel_monster_stage_variant as _pmsv
        _pmsv.init_level_defaults(level)
        values = {
            "a": (
                getattr(level, "panel_variant_a_speed"),
                getattr(level, "panel_variant_a_interval"),
            ),
            "b": (
                getattr(level, "panel_variant_b_speed"),
                getattr(level, "panel_variant_b_interval"),
            ),
            "c": (
                getattr(level, "panel_variant_c_speed"),
                getattr(level, "panel_variant_c_interval"),
            ),
        }
        for key, (speed, interval) in values.items():
            combo, spin = self._panel_variant_controls[key]
            combo.blockSignals(True)
            spin.blockSignals(True)
            idx = combo.findData(int(speed) & 0xFF)
            combo.setCurrentIndex(idx if idx >= 0 else 0)
            spin.setValue(max(1, min(255, int(interval) & 0xFF)))
            spin.blockSignals(False)
            combo.blockSignals(False)
        self.panel_variant_group.setEnabled(True)

    def _on_panel_variant_setting_changed(self, key):
        if self._meta_loading or not self.levels:
            return
        if self._reject_read_only_edit():
            return
        if key not in getattr(self, "_panel_variant_controls", {}):
            return
        self._push_undo()
        combo, spin = self._panel_variant_controls[key]
        speed = int(combo.currentData())
        interval = int(spin.value()) & 0xFF
        lv = self.levels[self.current_level_no]
        setattr(lv, f"panel_variant_{key}_speed", speed)
        setattr(lv, f"panel_variant_{key}_interval", interval)
        self._set_dirty(True)
        self._update_info()

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

    def _on_meta_hidden_door_toggled(self, checked):
        if self._meta_loading or not self.levels:
            return
        if self._reject_read_only_edit():
            return
        self._push_undo()
        from ..core import room_flags as _rf
        lv = self.levels[self.current_level_no]
        if checked:
            lv.room_flags |= _rf.BIT_HIDDEN_DOOR
        else:
            lv.room_flags &= ~_rf.BIT_HIDDEN_DOOR
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
            return
        self._push_undo()
        from ..core import stage_ext as _se
        lv = self.levels[self.current_level_no]
        _se.set_key_enemy_number(lv, enemy_number)
        self._set_dirty(True)
        self._update_info()

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

    def _on_show_stats(self):
        if not self.levels:
            return
        from .stats_dialog import StatsDialog
        item_desc = self.config.item_desc if self.config else {}
        dlg = StatsDialog(self.levels, item_desc=item_desc,
                          config=self.config,
                          tile_renderer=self.tile_renderer,
                          app_config=self._app_config,
                          rom=self.rom, parent=self)
        dlg.exec_()

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
        dlg = PaletteDialog(self.rom.data, parent=self, tile_renderer=self.tile_renderer)
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
            dlg = DemoInputDialog(self.rom.data, parent=self)
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
            dlg = ClearMessageDialog(self.rom.data, parent=self)
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
            dlg = TitleScreenDialog(self.rom.data, parent=self)
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
        dlg = PixelEditorDialog(self.rom, parent=self)
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
            dlg = SoundViewer(self.rom, parent=self)
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
                           config=self.config, parent=self)
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
        dlg = MirrorDialog(self.rom, lv, self.current_level_no, parent=self)
        dlg.exec_()
        if bytes(self.rom.data) != before:
            self._set_dirty(True)
            self._log(f"ミラー詳細設定: L{self.current_level_no + 1} を変更")

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

    def _on_palette_changed(self):
        """パレットダイアログの Apply からコールバック

        ROM の 0xED4 にある 8パレット × 4バイト = 32バイトの値を読み出して、
        config.palettes (XML由来の40パレット) に反映してエディタを再描画する。

        XMLの40パレット = 5グループ (red/cyan/purple/dgreen/gray) × 8パレット (BG4 + SPR4)
        - BGパレット (0-3): グループごとにslot 0(背景主色)が異なるが、slot 1/2 は共通
        - SPRパレット (4-7): 全グループで完全に同じ値
        """
        if self._reject_read_only_edit():
            return
        self._set_dirty(True)
        if not self.config or not self.rom:
            return

        from .palette_dialog import PALETTE_OFFSET, BYTES_PER_PALETTE, PALETTE_COUNT
        group_offsets = [0, 8, 16, 24, 32]

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
                        self.config.palettes[target] = [c1, c2, c3]
                    else:
                        # 既存のslot 0 (=グループ固有の主色) を保持し、c2/c3 だけ更新
                        old = self.config.palettes[target]
                        keep0 = old[0] if len(old) >= 1 else 0x0f
                        self.config.palettes[target] = [keep0, c2, c3]
                else:
                    # SPRパレット: 全グループで完全共通
                    self.config.palettes[target] = [c1, c2, c3]

        # tile_renderer のキャッシュをクリアして再描画
        if self.tile_renderer is not None:
            self.tile_renderer.clear_cache()
        self._sync_wall_color_preview()
        # ピッカーのアイコンも作り直す（タイルセット番号変えずに再描画させる）
        if self.picker is not None and self.tile_renderer is not None:
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

        self._push_undo()
        lv = self.levels[self.current_level_no]
        can_edit_col15 = self.chk_edit_col15.isChecked()

        if mode in ("all", "blocks"):
            for y in range(c.LEVEL_H):
                for x in range(c.LEVEL_W):
                    if x == 15 and not can_edit_col15:
                        continue
                    lv.tiles[y][x] = Wall.NONE
        if mode in ("all", "items"):
            if can_edit_col15:
                lv.items = []
            else:
                lv.items = [item for item in lv.items if item.position[0] == 15]
        if mode in ("all", "enemies"):
            if can_edit_col15:
                lv.enemies = []
            else:
                lv.enemies = [enemy for enemy in lv.enemies if enemy.position[0] == 15]
            self._refresh_key_enemy_spin_range(warn=True)

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
        return {
            "focus_level_no": focus_level_no,
            "levels": {
                level_no: copy.deepcopy(self.levels[level_no])
                for level_no in level_nos
            },
        }

    def _restore_undo_entry(self, entry):
        levels = self._undo_entry_levels(entry)
        level_nos = sorted(levels.keys())
        focus_level_no = self._undo_entry_focus_level_no(entry, level_nos)
        for level_no in level_nos:
            self.levels[level_no] = copy.deepcopy(levels[level_no])
            self._write_mirror_data_to_rom(level_no)
            self._refresh_thumbnail(level_no)
        self._sync_mirror_panel()
        return focus_level_no, self._undo_entry_label(level_nos)

    def _show_keymap(self):
        msg = """<b>基本</b><br>
F1: このヘルプ<br>
F9: 設定画面<br>
P: テストプレイ<br>
PageUp / PageDown: ステージ切替<br>
G: グリッド表示切替<br>
Ctrl+Z: Undo<br>
Ctrl+Y / Ctrl+Shift+Z: Redo<br>
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
<b>ホバー位置のクイック配置</b><br>
Delete / Backspace: ホバー位置を削除<br>
ブロックモード: 0=消去 / 1=茶 / 2=白 / 3=壊せる白 / 5=透明壊せる壁<br>
アイテム/敵モード: 1-9=ピッカー先頭から配置 / 0=削除<br>
メタモード: 1=スタート / 2=鍵 / 3=扉 / 4=ミラー1 / 5=ミラー2<br>
<br>
<b>アイテムフラグ</b><br>
N: 通常<br>
H: 隠し (0x40)<br>
B: ブロック内 (0x80)<br>
<br>
<b>範囲編集</b><br>
Ctrl+C: コピー<br>
Ctrl+V: ペースト（選択範囲またはホバー位置を起点）<br>
Ctrl+X: 切り取り<br>
Delete / Backspace: 範囲内を削除<br>
F: 左右反転<br>
Shift+F: 上下反転<br>
Esc: 選択解除<br>
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
        """ドロップ時 - 最初の .nes / .zip ファイルを読み込み（内部D&Dは子で処理）"""
        from .element_picker import PICKER_MIME
        if event.mimeData().hasFormat(PICKER_MIME):
            # 子ウィジェットで処理されなかった内部D&Dは無視
            event.ignore()
            return
        if not event.mimeData().hasUrls():
            event.ignore()
            return

        for url in event.mimeData().urls():
            if not url.isLocalFile():
                continue
            path = url.toLocalFile()
            lower = path.lower()
            if lower.endswith('.nes') or lower.endswith('.zip'):
                event.acceptProposedAction()
                self.load_rom(path)
                return

        event.ignore()
