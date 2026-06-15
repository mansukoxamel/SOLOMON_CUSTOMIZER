"""設定ダイアログ (F9)"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QComboBox, QLabel, QDialogButtonBox, QPushButton, QLineEdit,
    QSpinBox, QWidget, QFontComboBox, QCheckBox, QColorDialog,
    QTabWidget, QScrollArea, QKeySequenceEdit, QMessageBox
)
from PyQt5.QtGui import QFont, QColor, QKeySequence
from PyQt5.QtCore import Qt
from .theme import (
    DEFAULT_THEME_GRAY, MIN_THEME_GRAY, MAX_THEME_GRAY, normalize_theme_gray,
)
from ..core.config import (
    DEFAULT_AUTOSAVE_KEEP_COUNT,
    DEFAULT_HOVER_INFO_POPUP_FONT_SIZE,
    DEFAULT_ICON_PATH,
    DEFAULT_UNDO_LIMIT,
    MAX_HOVER_INFO_POPUP_FONT_SIZE,
    MAX_AUTOSAVE_KEEP_COUNT,
    MAX_UNDO_LIMIT,
    MIN_HOVER_INFO_POPUP_FONT_SIZE,
    MIN_AUTOSAVE_KEEP_COUNT,
    MIN_UNDO_LIMIT,
    SHORTCUT_DEFINITIONS,
    DEFAULT_SHORTCUTS,
    GAMEPAD_BUTTON_OPTIONS,
    DEFAULT_GAMEPAD_SHORTCUTS,
    normalize_int_setting,
    normalize_gamepad_shortcuts,
    normalize_shortcuts,
)
from .level_view import (
    DEFAULT_MARKER_COLORS,
    DEFAULT_MARKER_SHAPES,
    MARKER_SHAPE_OPTIONS,
)


MARKER_COLOR_ROWS = [
    ("bonus_marker_color", "ボーナス菱形"),
    ("hidden_marker_color", "隠し要素"),
    ("visible_in_block_marker_color", "透明ブロック内アイテム"),
    ("breakable_white_marker_color", "壊せる白ブロック"),
    ("invisible_breakable_marker_color", "透明壊せるブロック"),
    ("passable_marker_color", "すり抜けブロック"),
    ("solid_marker_color", "壊せない特殊ブロック"),
    ("mirror1_marker_color", "ミラー1"),
    ("mirror2_marker_color", "ミラー2"),
    ("special_empty_marker_color", "特殊処理: 強制空"),
    ("special_trigger_marker_color", "特殊処理: トリガー"),
    ("special_link_marker_color", "特殊処理: リンク線"),
    ("selection_marker_color", "選択範囲"),
    ("hover_marker_color", "ホバー枠"),
]

MARKER_SHAPE_ROWS = [
    ("breakable_white_marker_shape", "壊せる白ブロック"),
    ("invisible_breakable_marker_shape", "透明壊せるブロック"),
    ("passable_marker_shape", "すり抜けブロック"),
    ("solid_marker_shape", "壊せない特殊ブロック"),
]

MARKER_SHAPE_BY_COLOR = {
    "breakable_white_marker_color": "breakable_white_marker_shape",
    "invisible_breakable_marker_color": "invisible_breakable_marker_shape",
    "passable_marker_color": "passable_marker_shape",
    "solid_marker_color": "solid_marker_shape",
}


class SettingsDialog(QDialog):
    """アプリケーション設定ダイアログ"""

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        if parent is not None:
            self.setFont(parent.font())
        self.setWindowTitle("設定 (F9)")
        self.config = dict(config)  # 編集用コピー
        self.config["shortcuts"] = normalize_shortcuts(self.config.get("shortcuts"))
        self.config["gamepad_shortcuts"] = normalize_gamepad_shortcuts(
            self.config.get("gamepad_shortcuts")
        )

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)

        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)
        colors_tab = QWidget()
        colors_layout = QVBoxLayout(colors_tab)
        shortcuts_tab = QWidget()
        shortcuts_layout = QVBoxLayout(shortcuts_tab)
        self.tabs.addTab(general_tab, "一般")
        self.tabs.addTab(colors_tab, "色・表示")
        self.tabs.addTab(shortcuts_tab, "ショートカット")

        # ====== 表示 ======
        disp_group = QGroupBox("表示")
        df = QFormLayout(disp_group)

        self.cmb_dirty_mark = QComboBox()
        self.cmb_dirty_mark.setEditable(True)
        for mark in ["●", "*", "[未保存]", "♦", "•", "✱", "[edited]"]:
            self.cmb_dirty_mark.addItem(mark)
        cur_mark = self.config.get("dirty_mark", "●")
        idx = self.cmb_dirty_mark.findText(cur_mark)
        if idx >= 0:
            self.cmb_dirty_mark.setCurrentIndex(idx)
        else:
            self.cmb_dirty_mark.setCurrentText(cur_mark)
        df.addRow("未保存マーク:", self.cmb_dirty_mark)

        # フォントファミリー（空 = デフォルト）
        font_wrap = QWidget()
        font_row = QHBoxLayout(font_wrap)
        font_row.setContentsMargins(0, 0, 0, 0)
        self.cmb_font_family = QFontComboBox()
        cur_family = self.config.get("font_family", "")
        if cur_family:
            self.cmb_font_family.setCurrentFont(QFont(cur_family))
        self.cmb_font_family.currentFontChanged.connect(
            lambda *_: setattr(self, "_font_family_default", False))
        font_row.addWidget(self.cmb_font_family, 1)
        btn_font_default = QPushButton("既定に戻す")
        btn_font_default.clicked.connect(self._reset_font_family)
        font_row.addWidget(btn_font_default)
        df.addRow("フォント:", font_wrap)
        self._font_family_default = (cur_family == "")

        self.spin_font_size = QSpinBox()
        self.spin_font_size.setRange(0, 999)
        self.spin_font_size.setSpecialValueText("デフォルト")
        self.spin_font_size.setSuffix(" pt")
        self.spin_font_size.setValue(self.config.get("font_size", 0))
        df.addRow("フォントサイズ:", self.spin_font_size)

        self.spin_hover_popup_font_size = QSpinBox()
        self.spin_hover_popup_font_size.setRange(
            MIN_HOVER_INFO_POPUP_FONT_SIZE,
            MAX_HOVER_INFO_POPUP_FONT_SIZE,
        )
        self.spin_hover_popup_font_size.setSuffix(" px")
        self.spin_hover_popup_font_size.setValue(
            normalize_int_setting(
                self.config.get("hover_info_popup_font_size"),
                DEFAULT_HOVER_INFO_POPUP_FONT_SIZE,
                MIN_HOVER_INFO_POPUP_FONT_SIZE,
                MAX_HOVER_INFO_POPUP_FONT_SIZE,
            )
        )
        self.spin_hover_popup_font_size.setToolTip(
            "Iキーで表示するホバー情報ポップアップだけの文字サイズです。"
        )
        df.addRow("ホバー情報文字サイズ:", self.spin_hover_popup_font_size)

        self.spin_enemy_meter_slot_size = QSpinBox()
        self.spin_enemy_meter_slot_size.setRange(10, 32)
        self.spin_enemy_meter_slot_size.setSuffix(" px")
        self.spin_enemy_meter_slot_size.setValue(
            normalize_int_setting(
                self.config.get("enemy_count_meter_slot_size"),
                18,
                10,
                32,
            )
        )
        self.spin_enemy_meter_slot_size.setToolTip(
            "キャンバス上部の敵数メーターの1マスサイズです。"
            "鍵持ち敵/妖精化敵の表示画像も同じ大きさで拡大縮小します。"
        )
        df.addRow("敵数メーター1マス:", self.spin_enemy_meter_slot_size)

        self.chk_font_bold = QCheckBox("太字")
        self.chk_font_bold.setChecked(bool(self.config.get("font_bold", False)))
        df.addRow("太字:", self.chk_font_bold)

        general_layout.addWidget(disp_group)

        # ====== 色・マーカー ======
        color_group = QGroupBox("色・マーカー")
        cf = QFormLayout(color_group)

        self.spin_theme_gray = QSpinBox()
        self.spin_theme_gray.setRange(MIN_THEME_GRAY, MAX_THEME_GRAY)
        self.spin_theme_gray.setValue(
            normalize_theme_gray(self.config.get("theme_gray", DEFAULT_THEME_GRAY))
        )
        self.spin_theme_gray.setToolTip(
            "黒テーマの明るさです。小さいほど黒く、大きいほど明るくなります。"
        )
        cf.addRow("黒テーマ明度:", self.spin_theme_gray)

        self.cmb_marker_overlay_scale = QComboBox()
        for value in (3, 4, 5):
            self.cmb_marker_overlay_scale.addItem(f"{value}倍", value)
        cur_scale = int(self.config.get("marker_overlay_scale", 3) or 3)
        idx = self.cmb_marker_overlay_scale.findData(cur_scale)
        self.cmb_marker_overlay_scale.setCurrentIndex(idx if idx >= 0 else 0)
        self.cmb_marker_overlay_scale.setToolTip(
            "キャンバス上の隠し要素枠や特殊処理マーカーなどの線幅倍率です。"
        )
        cf.addRow("編集用マーカー線幅:", self.cmb_marker_overlay_scale)

        self._color_edits = {}
        self._color_buttons = {}
        self._shape_combos = {}
        for key, label in MARKER_COLOR_ROWS:
            cf.addRow(f"{label}色:", self._make_color_row(key))

        color_scroll = QScrollArea()
        color_scroll.setWidgetResizable(True)
        color_scroll.setWidget(color_group)
        colors_layout.addWidget(color_scroll)

        # アイコンパス
        icon_wrap = QWidget()
        icon_row = QHBoxLayout(icon_wrap)
        icon_row.setContentsMargins(0, 0, 0, 0)
        self.edit_icon = QLineEdit(self.config.get("icon_path", ""))
        self.edit_icon.setPlaceholderText(DEFAULT_ICON_PATH)
        icon_row.addWidget(self.edit_icon, 1)
        btn_icon = QPushButton("参照...")
        btn_icon.clicked.connect(self._browse_icon)
        icon_row.addWidget(btn_icon)
        df.addRow("アイコン:", icon_wrap)

        # ====== 連携 ======
        link_group = QGroupBox("外部連携")
        lf = QFormLayout(link_group)
        emu_wrap = QWidget()
        emu_row = QHBoxLayout(emu_wrap)
        emu_row.setContentsMargins(0, 0, 0, 0)
        self.edit_emu = QLineEdit(self.config.get("emulator_path", ""))
        self.edit_emu.setPlaceholderText("例: D:/emu/fceux/fceux.exe")
        emu_row.addWidget(self.edit_emu, 1)
        btn_browse = QPushButton("参照...")
        btn_browse.clicked.connect(self._browse_emu)
        emu_row.addWidget(btn_browse)
        lf.addRow("エミュレータ:", emu_wrap)
        general_layout.addWidget(link_group)

        # ====== 履歴・自動保存 ======
        history_group = QGroupBox("履歴・自動保存")
        hf = QFormLayout(history_group)

        self.spin_autosave_keep_count = QSpinBox()
        self.spin_autosave_keep_count.setRange(
            MIN_AUTOSAVE_KEEP_COUNT,
            MAX_AUTOSAVE_KEEP_COUNT,
        )
        self.spin_autosave_keep_count.setSuffix(" 世代")
        self.spin_autosave_keep_count.setValue(normalize_int_setting(
            self.config.get("autosave_keep_count"),
            DEFAULT_AUTOSAVE_KEEP_COUNT,
            MIN_AUTOSAVE_KEEP_COUNT,
            MAX_AUTOSAVE_KEEP_COUNT,
        ))
        self.spin_autosave_keep_count.setToolTip(
            "終了時に保存する作業状態の保持数です。既定は10世代です。"
        )
        hf.addRow("作業状態自動保存:", self.spin_autosave_keep_count)

        self.spin_undo_limit = QSpinBox()
        self.spin_undo_limit.setRange(MIN_UNDO_LIMIT, MAX_UNDO_LIMIT)
        self.spin_undo_limit.setSuffix(" 件")
        self.spin_undo_limit.setValue(normalize_int_setting(
            self.config.get("undo_limit"),
            DEFAULT_UNDO_LIMIT,
            MIN_UNDO_LIMIT,
            MAX_UNDO_LIMIT,
        ))
        self.spin_undo_limit.setToolTip(
            "ステージ編集のUndo/Redo履歴上限です。既定は200件、最大999件です。"
        )
        hf.addRow("Undo履歴上限:", self.spin_undo_limit)

        general_layout.addWidget(history_group)

        # ====== TODO（今後実装） ======
        todo_group = QGroupBox("今後追加予定の項目")
        tl = QVBoxLayout(todo_group)
        for label in [
            "・通知音ファイル + 音量",
            "・クラウドバックアップ先フォルダ",
        ]:
            lbl = QLabel(f"<small style='color:#888'>{label}</small>")
            tl.addWidget(lbl)
        general_layout.addWidget(todo_group)
        general_layout.addStretch(1)

        # ====== ショートカット ======
        shortcut_group = QGroupBox("ショートカット")
        sf = QFormLayout(shortcut_group)
        self._shortcut_edits = {}
        self._gamepad_combos = {}
        for key, label, default in SHORTCUT_DEFINITIONS:
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.addWidget(QLabel("キー"))
            edit = QKeySequenceEdit(QKeySequence(
                self.config["shortcuts"].get(key, default)
            ))
            btn = QPushButton("既定")
            btn.clicked.connect(lambda _=None, k=key, d=default: self._reset_shortcut(k, d))
            rl.addWidget(edit, 2)
            rl.addWidget(btn)
            rl.addWidget(QLabel("パッド"))
            combo = QComboBox()
            for value, button_label in GAMEPAD_BUTTON_OPTIONS:
                combo.addItem(button_label, value)
            pad_default = DEFAULT_GAMEPAD_SHORTCUTS.get(key, "")
            pad_value = self.config["gamepad_shortcuts"].get(key, pad_default)
            idx = combo.findData(pad_value)
            combo.setCurrentIndex(idx if idx >= 0 else 0)
            pad_btn = QPushButton("既定")
            pad_btn.clicked.connect(
                lambda _=None, k=key, d=pad_default: self._reset_gamepad_shortcut(k, d)
            )
            rl.addWidget(combo, 1)
            rl.addWidget(pad_btn)
            self._shortcut_edits[key] = edit
            self._gamepad_combos[key] = combo
            sf.addRow(label + ":", row)
        shortcut_scroll = QScrollArea()
        shortcut_scroll.setWidgetResizable(True)
        shortcut_scroll.setWidget(shortcut_group)
        shortcuts_layout.addWidget(shortcut_scroll)

        # ====== ボタン ======
        btnbox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply
        )
        btnbox.accepted.connect(self._apply_and_close)
        btnbox.rejected.connect(self.reject)
        btnbox.button(QDialogButtonBox.Apply).clicked.connect(self._apply)
        layout.addWidget(btnbox)
        self._restore_dialog_state()

    def _restore_dialog_state(self):
        w = int(self.config.get("settings_dialog_w", 700) or 700)
        h = int(self.config.get("settings_dialog_h", 780) or 780)
        self.resize(max(520, w), max(420, h))
        x = int(self.config.get("settings_dialog_x", -1) or -1)
        y = int(self.config.get("settings_dialog_y", -1) or -1)
        if x >= 0 and y >= 0:
            self.move(x, y)
        tab = int(self.config.get("settings_dialog_tab", 0) or 0)
        tab = max(0, min(self.tabs.count() - 1, tab))
        self.tabs.setCurrentIndex(tab)

    def _save_dialog_state_to_config(self):
        geo = self.frameGeometry()
        self.config["settings_dialog_x"] = int(geo.x())
        self.config["settings_dialog_y"] = int(geo.y())
        self.config["settings_dialog_w"] = int(self.width())
        self.config["settings_dialog_h"] = int(self.height())
        self.config["settings_dialog_tab"] = int(self.tabs.currentIndex())

    def done(self, result: int):
        self._save_dialog_state_to_config()
        parent = self.parent()
        if parent and hasattr(parent, "_save_settings_dialog_state"):
            parent._save_settings_dialog_state(dict(self.config))
        super().done(result)

    def _reset_font_family(self):
        """フォントファミリーを既定（アプリ標準）に戻す"""
        self._font_family_default = True

    def _reset_shortcut(self, key: str, default: str):
        edit = self._shortcut_edits.get(key)
        if edit is not None:
            edit.setKeySequence(QKeySequence(default))

    def _reset_gamepad_shortcut(self, key: str, default: str):
        combo = self._gamepad_combos.get(key)
        if combo is not None:
            idx = combo.findData(default)
            combo.setCurrentIndex(idx if idx >= 0 else 0)

    def _validate_shortcut_conflicts(self) -> bool:
        conflicts = []
        key_owner = {}
        pad_owner = {}
        labels_by_key = {
            key: label for key, label, _default in SHORTCUT_DEFINITIONS
        }
        for key, _label, _default in SHORTCUT_DEFINITIONS:
            text = self._shortcut_edits[key].keySequence().toString(
                QKeySequence.PortableText
            ).strip()
            if text:
                owner = key_owner.get(text)
                if owner is not None:
                    conflicts.append(
                        f"キー {text}: {labels_by_key[owner]} / {labels_by_key[key]}"
                    )
                else:
                    key_owner[text] = key
            pad = str(self._gamepad_combos[key].currentData() or "")
            if pad:
                owner = pad_owner.get(pad)
                if owner is not None:
                    conflicts.append(
                        f"パッド {pad}: {labels_by_key[owner]} / {labels_by_key[key]}"
                    )
                else:
                    pad_owner[pad] = key
        if not conflicts:
            return True
        QMessageBox.warning(
            self,
            "ショートカット重複",
            "同じショートカットが複数の操作に割り当てられています。\n"
            "重複を解消してから適用してください。\n\n"
            + "\n".join(conflicts[:12]),
        )
        return False

    @staticmethod
    def _normalize_color(value, default="#FFC800"):
        color = QColor(str(value or default))
        if not color.isValid():
            color = QColor(default)
        return color.name().upper()

    def _make_color_row(self, key: str):
        wrap = QWidget()
        row = QHBoxLayout(wrap)
        row.setContentsMargins(0, 0, 0, 0)
        default = DEFAULT_MARKER_COLORS[key]
        edit = QLineEdit(self._normalize_color(self.config.get(key, default), default))
        edit.setPlaceholderText(default)
        button = QPushButton("色選択...")
        self._color_edits[key] = edit
        self._color_buttons[key] = button
        edit.textChanged.connect(lambda _=None, k=key: self._sync_color_button(k))
        button.clicked.connect(lambda _=None, k=key: self._choose_marker_color(k))
        row.addWidget(edit, 1)
        shape_key = MARKER_SHAPE_BY_COLOR.get(key)
        if shape_key is not None:
            row.addWidget(self._make_shape_combo(shape_key))
        row.addWidget(button)
        self._sync_color_button(key)
        return wrap

    def _make_shape_combo(self, key: str):
        combo = QComboBox()
        combo.setMinimumWidth(92)
        for value, label in MARKER_SHAPE_OPTIONS:
            combo.addItem(label, value)
        default = DEFAULT_MARKER_SHAPES[key]
        current = str(self.config.get(key, default))
        idx = combo.findData(current)
        combo.setCurrentIndex(idx if idx >= 0 else combo.findData(default))
        self._shape_combos[key] = combo
        return combo

    def _sync_color_button(self, key: str):
        edit = self._color_edits[key]
        default = DEFAULT_MARKER_COLORS[key]
        color = QColor(edit.text().strip())
        if not color.isValid():
            color = QColor(default)
        text_color = "#000000" if color.lightness() > 140 else "#FFFFFF"
        self._color_buttons[key].setStyleSheet(
            f"background: {color.name()}; color: {text_color};"
        )

    def _choose_marker_color(self, key: str):
        edit = self._color_edits[key]
        default = DEFAULT_MARKER_COLORS[key]
        current = QColor(edit.text().strip())
        if not current.isValid():
            current = QColor(default)
        color = QColorDialog.getColor(current, self, "マーカー色")
        if color.isValid():
            edit.setText(color.name().upper())

    def _browse_icon(self):
        from .file_dialog_compat import get_file
        path = get_file(
            self,
            title="アイコンを選択",
            filter="Images (*.png *.ico *.jpg *.bmp);;All files (*)",
            directory=self.edit_icon.text(),
        )
        if path:
            self.edit_icon.setText(path)

    def _browse_emu(self):
        from .file_dialog_compat import get_file
        path = get_file(
            self,
            title="エミュレータを選択",
            filter="Executables (*.exe);;All files (*)",
            directory=self.edit_emu.text(),
        )
        if path:
            self.edit_emu.setText(path)

    def _gather(self):
        """UIから config dict を更新"""
        self._save_dialog_state_to_config()
        for spin in (
            self.spin_font_size,
            self.spin_hover_popup_font_size,
            self.spin_enemy_meter_slot_size,
            self.spin_theme_gray,
            self.spin_autosave_keep_count,
            self.spin_undo_limit,
        ):
            spin.interpretText()
        mark = self.cmb_dirty_mark.currentText().strip()
        if not mark:
            mark = "●"
        self.config["dirty_mark"] = mark
        self.config["emulator_path"] = self.edit_emu.text().strip()
        self.config["font_size"] = self.spin_font_size.value()
        self.config["hover_info_popup_font_size"] = (
            self.spin_hover_popup_font_size.value()
        )
        self.config["enemy_count_meter_slot_size"] = (
            self.spin_enemy_meter_slot_size.value()
        )
        if self._font_family_default:
            self.config["font_family"] = ""
        else:
            self.config["font_family"] = \
                self.cmb_font_family.currentFont().family()
        self.config["font_bold"] = self.chk_font_bold.isChecked()
        self.config["theme_gray"] = self.spin_theme_gray.value()
        self.config["marker_overlay_scale"] = int(
            self.cmb_marker_overlay_scale.currentData()
        )
        self.config["autosave_keep_count"] = self.spin_autosave_keep_count.value()
        self.config["undo_limit"] = self.spin_undo_limit.value()
        for key, _label in MARKER_COLOR_ROWS:
            self.config[key] = self._normalize_color(
                self._color_edits[key].text().strip(),
                DEFAULT_MARKER_COLORS[key],
            )
        for key, _label in MARKER_SHAPE_ROWS:
            self.config[key] = str(self._shape_combos[key].currentData())
        self.config["icon_path"] = self.edit_icon.text().strip()
        shortcuts = {}
        for key, _label, default in SHORTCUT_DEFINITIONS:
            edit = self._shortcut_edits[key]
            text = edit.keySequence().toString(QKeySequence.PortableText).strip()
            shortcuts[key] = text
        self.config["shortcuts"] = normalize_shortcuts(shortcuts)
        gamepad_shortcuts = {}
        for key, _label, _default in SHORTCUT_DEFINITIONS:
            combo = self._gamepad_combos[key]
            gamepad_shortcuts[key] = str(combo.currentData() or "")
        self.config["gamepad_shortcuts"] = normalize_gamepad_shortcuts(
            gamepad_shortcuts
        )

    def _apply(self):
        """親に通知して即時反映（閉じない）"""
        if not self._validate_shortcut_conflicts():
            return False
        self._gather()
        parent = self.parent()
        if parent and hasattr(parent, "_apply_settings"):
            parent._apply_settings(dict(self.config))
        return True

    def _apply_and_close(self):
        if self._apply():
            self.accept()

    def get_config(self) -> dict:
        return dict(self.config)
