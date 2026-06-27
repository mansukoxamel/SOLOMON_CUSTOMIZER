"""デモ(attract mode)操作データ 編集ダイアログ (固定34step・JP)

各 step = 入力(A/B/上下左右のチェック) + 継続フレーム数。原作値を
初期表示し、$CF9A/$CFBC へ同サイズ書き戻す(録画不要・原作方式手入力)。
60フレーム≒1秒。Start/Select はデモ中断判定のため選択不可。
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QCheckBox,
    QSpinBox, QPushButton, QDialogButtonBox, QScrollArea, QWidget,
    QMessageBox,
)
from PyQt5.QtCore import Qt
from ..core import demo_input as DI
from ..core.i18n import get_language, t
from .dialog_geometry import restore_dialog_geometry, save_dialog_geometry


_BUTTON_LABEL_KEYS = {
    "上": "demo_input.button.up",
    "下": "demo_input.button.down",
    "左": "demo_input.button.left",
    "右": "demo_input.button.right",
}


def format_demo_input_error(error) -> str:
    msg = str(error)
    if get_language() != "en":
        return msg
    if "ROM が小さすぎます" in msg:
        return t("demo_input.error.rom_too_small", msg)
    if "$CBEC 署名不一致" in msg:
        return t("demo_input.error.signature", msg)
    if "$CBF6 ステップ数" in msg:
        return t("demo_input.error.step_count", msg)
    if "step 数不正" in msg:
        return t("demo_input.error.invalid_step_count", msg)
    return msg


class DemoInputDialog(QDialog):
    def __init__(self, rom_data: bytearray, parent=None, app_config=None):
        super().__init__(parent)
        if parent is not None:
            self.setFont(parent.font())
        self.setWindowTitle(t("demo_input.title", "デモ操作編集 (34ステップ固定)"))
        self._rom = rom_data
        self._app_config = app_config
        self.resize(560, 720)

        steps = DI.read_steps(rom_data)   # [(joy, frames)] ×34

        root = QVBoxLayout(self)
        head = QLabel(t("demo_input.description"))
        head.setWordWrap(True)
        root.addWidget(head)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        inner = QWidget()
        g = QGridLayout(inner)
        g.setContentsMargins(4, 4, 4, 4)
        g.setHorizontalSpacing(6)
        g.setVerticalSpacing(3)
        g.addWidget(QLabel(t("demo_input.column.step", "#")), 0, 0)
        for ci, (nm, _b) in enumerate(DI.BTN):
            g.addWidget(QLabel(t(_BUTTON_LABEL_KEYS.get(nm, ""), nm)), 0, 1 + ci)
        g.addWidget(
            QLabel(t("demo_input.column.frames", "フレーム")),
            0,
            1 + len(DI.BTN),
        )

        self._rows = []   # [(checkboxes[], spin)]
        for i, (joy, frames) in enumerate(steps):
            g.addWidget(QLabel(f"{i:2d}"), i + 1, 0)
            cbs = []
            for ci, (nm, bit) in enumerate(DI.BTN):
                cb = QCheckBox()
                cb.setChecked(bool(joy & bit))
                g.addWidget(cb, i + 1, 1 + ci)
                cbs.append((cb, bit))
            sp = QSpinBox()
            sp.setRange(1, 256)
            sp.setValue(frames)
            sp.setSuffix(" F")
            g.addWidget(sp, i + 1, 1 + len(DI.BTN))
            self._rows.append((cbs, sp))
        scroll.setWidget(inner)
        root.addWidget(scroll, 1)

        btnrow = QHBoxLayout()
        b_rest = QPushButton(t("demo_input.restore_original", "原作に戻す"))
        b_rest.clicked.connect(self._on_restore)
        btnrow.addWidget(b_rest)
        btnrow.addStretch()
        root.addLayout(btnrow)

        bb = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
            | QDialogButtonBox.Apply)
        bb.accepted.connect(self._apply_and_close)
        bb.rejected.connect(self.reject)
        bb.button(QDialogButtonBox.Apply).clicked.connect(self._apply)
        bb.button(QDialogButtonBox.Ok).setText(t("common.ok", "OK"))
        bb.button(QDialogButtonBox.Cancel).setText(t("common.cancel", "キャンセル"))
        bb.button(QDialogButtonBox.Apply).setText(t("common.apply", "適用"))
        root.addWidget(bb)
        restore_dialog_geometry(self, self._app_config, "demo_input_dlg")

    def _collect(self) -> list:
        out = []
        for cbs, sp in self._rows:
            joy = 0
            for cb, bit in cbs:
                if cb.isChecked():
                    joy |= bit
            out.append((joy, sp.value()))
        return out

    def _on_restore(self):
        flat_w, flat_j = DI.ORIG_WAIT, DI.ORIG_JOY
        for i, (cbs, sp) in enumerate(self._rows):
            joy = flat_j[i]
            for cb, bit in cbs:
                cb.setChecked(bool(joy & bit))
            sp.setValue(flat_w[i] + 1)   # frames = wait+1

    def _apply(self) -> bool:
        try:
            DI.write_steps(self._rom, self._collect())
        except DI.DemoInputError as e:
            QMessageBox.critical(
                self,
                t("demo_input.apply_failed", "デモ操作編集失敗"),
                format_demo_input_error(e),
            )
            return False
        return True

    def _apply_and_close(self):
        if self._apply():
            self.accept()

    def done(self, r):
        save_dialog_geometry(self, self._app_config, "demo_input_dlg")
        super().done(r)
