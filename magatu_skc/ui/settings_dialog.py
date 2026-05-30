"""設定ダイアログ (F9)"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QComboBox, QLabel, QDialogButtonBox, QPushButton, QLineEdit,
    QSpinBox, QWidget, QFontComboBox, QCheckBox
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from .theme import (
    DEFAULT_THEME_GRAY, MIN_THEME_GRAY, MAX_THEME_GRAY, normalize_theme_gray,
)


class SettingsDialog(QDialog):
    """アプリケーション設定ダイアログ"""

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        if parent is not None:
            self.setFont(parent.font())
        self.setWindowTitle("設定 (F9)")
        self.resize(520, 480)
        self.config = dict(config)  # 編集用コピー

        layout = QVBoxLayout(self)

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

        self.chk_font_bold = QCheckBox("太字")
        self.chk_font_bold.setChecked(bool(self.config.get("font_bold", False)))
        df.addRow("太字:", self.chk_font_bold)

        self.spin_theme_gray = QSpinBox()
        self.spin_theme_gray.setRange(MIN_THEME_GRAY, MAX_THEME_GRAY)
        self.spin_theme_gray.setValue(
            normalize_theme_gray(self.config.get("theme_gray", DEFAULT_THEME_GRAY))
        )
        self.spin_theme_gray.setToolTip(
            "黒テーマの明るさです。小さいほど黒く、大きいほど明るくなります。"
        )
        df.addRow("黒テーマ明度:", self.spin_theme_gray)

        # アイコンパス
        icon_wrap = QWidget()
        icon_row = QHBoxLayout(icon_wrap)
        icon_row.setContentsMargins(0, 0, 0, 0)
        self.edit_icon = QLineEdit(self.config.get("icon_path", ""))
        self.edit_icon.setPlaceholderText("例: D:\\material\\Icons\\dana.png")
        icon_row.addWidget(self.edit_icon, 1)
        btn_icon = QPushButton("参照...")
        btn_icon.clicked.connect(self._browse_icon)
        icon_row.addWidget(btn_icon)
        df.addRow("アイコン:", icon_wrap)

        layout.addWidget(disp_group)

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
        layout.addWidget(link_group)

        # ====== TODO（今後実装） ======
        todo_group = QGroupBox("今後追加予定の項目")
        tl = QVBoxLayout(todo_group)
        for label in [
            "・通知音ファイル + 音量",
            "・クラウドバックアップ先フォルダ",
        ]:
            lbl = QLabel(f"<small style='color:#888'>{label}</small>")
            tl.addWidget(lbl)
        layout.addWidget(todo_group)

        # ====== ボタン ======
        btnbox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply
        )
        btnbox.accepted.connect(self._apply_and_close)
        btnbox.rejected.connect(self.reject)
        btnbox.button(QDialogButtonBox.Apply).clicked.connect(self._apply)
        layout.addWidget(btnbox)

    def _reset_font_family(self):
        """フォントファミリーを既定（アプリ標準）に戻す"""
        self._font_family_default = True

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
        for spin in (self.spin_font_size, self.spin_theme_gray):
            spin.interpretText()
        mark = self.cmb_dirty_mark.currentText().strip()
        if not mark:
            mark = "●"
        self.config["dirty_mark"] = mark
        self.config["emulator_path"] = self.edit_emu.text().strip()
        self.config["font_size"] = self.spin_font_size.value()
        if self._font_family_default:
            self.config["font_family"] = ""
        else:
            self.config["font_family"] = \
                self.cmb_font_family.currentFont().family()
        self.config["font_bold"] = self.chk_font_bold.isChecked()
        self.config["theme_gray"] = self.spin_theme_gray.value()
        self.config["icon_path"] = self.edit_icon.text().strip()

    def _apply(self):
        """親に通知して即時反映（閉じない）"""
        self._gather()
        parent = self.parent()
        if parent and hasattr(parent, "_apply_settings"):
            parent._apply_settings(dict(self.config))

    def _apply_and_close(self):
        self._apply()
        self.accept()

    def get_config(self) -> dict:
        return dict(self.config)
