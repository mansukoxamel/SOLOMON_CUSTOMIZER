"""クリア画面(おめでとう画面)メッセージ編集ダイアログ

ステージクリア後の3行(原作 "THANK YOU DANA" / "YOU RELEASED THIS
ROOM" / "TRY NEXT ROOM")を編集。★同字数置換のみ(R135の安全方式)。
英大文字 A-Z とスペースのみ。各行の最大文字数は原作と同じ(超過不可、
不足はスペース詰め)。位置+署名 二重検証(JP専用、不一致は中止)。
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QPushButton, QDialogButtonBox, QMessageBox,
)
from PyQt5.QtCore import QRegExp
from PyQt5.QtGui import QRegExpValidator
from ..core import clear_message as CM
from .dialog_geometry import restore_dialog_geometry, save_dialog_geometry


class ClearMessageDialog(QDialog):
    def __init__(self, rom_data: bytearray, parent=None, app_config=None):
        super().__init__(parent)
        if parent is not None:
            self.setFont(parent.font())
        self.setWindowTitle("クリア画面メッセージ編集 (同字数・JP)")
        self._rom = rom_data
        self._app_config = app_config
        self.resize(560, 320)

        rows = CM.read_messages(rom_data)   # [(name, cur, count, orig)] ×3

        root = QVBoxLayout(self)
        head = QLabel(
            "ステージクリア後の『おめでとう画面』3行を編集します。"
            "英大文字 A-Z とスペースのみ。<b>原作と同じ文字数まで</b>"
            "(長くはできません。短い分はスペースで埋まります)。"
            "原作は THANK YOU DANA / YOU RELEASED THIS ROOM / "
            "TRY NEXT ROOM。")
        head.setWordWrap(True)
        root.addWidget(head)

        g = QGridLayout()
        g.setHorizontalSpacing(8)
        g.setVerticalSpacing(6)
        g.addWidget(QLabel("行"), 0, 0)
        g.addWidget(QLabel("文字"), 0, 1)
        g.addWidget(QLabel("字数"), 0, 2)
        g.addWidget(QLabel("原作"), 0, 3)

        # A-Z と space のみ許可
        rx = QRegExpValidator(QRegExp("[A-Za-z ]*"))
        self._edits = []
        for i, (name, cur, count, orig) in enumerate(rows):
            g.addWidget(QLabel(f"{name}"), i + 1, 0)
            le = QLineEdit(cur.rstrip())
            le.setMaxLength(count)
            le.setValidator(rx)
            cnt_lbl = QLabel()
            cnt_lbl.setMinimumWidth(56)
            le.textChanged.connect(
                lambda _t, e=le, c=count, lb=cnt_lbl: self._on_text(e, c, lb))
            g.addWidget(le, i + 1, 1)
            g.addWidget(cnt_lbl, i + 1, 2)
            g.addWidget(QLabel(f"{orig}  ({count}字)"), i + 1, 3)
            self._edits.append(le)
            self._on_text(le, count, cnt_lbl)   # 初期表示
        root.addLayout(g)

        btnrow = QHBoxLayout()
        b_rest = QPushButton("原作に戻す")
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
        root.addWidget(bb)
        restore_dialog_geometry(self, self._app_config, "clear_message_dlg")

    def _on_text(self, le, count, cnt_lbl):
        """大文字化 + 入力字数をリアルタイム表示 (現在 / 最大)。"""
        up = le.text().upper()
        if le.text() != up:
            le.setText(up)          # 再 textChanged → 再帰はここで停止
            return
        n = len(le.text())
        cnt_lbl.setText(f"{n} / {count}")
        if n >= count:
            cnt_lbl.setStyleSheet("color:#c33;")   # 上限到達
        elif n == 0:
            cnt_lbl.setStyleSheet("color:#888;")
        else:
            cnt_lbl.setStyleSheet("")

    def _on_restore(self):
        for le, m in zip(self._edits, CM.MESSAGES):
            le.setText(m["orig"])

    def _apply(self) -> bool:
        try:
            CM.write_messages(
                self._rom, [e.text() for e in self._edits])
        except CM.ClearMessageError as e:
            QMessageBox.critical(self, "クリア画面メッセージ編集失敗",
                                 str(e))
            return False
        return True

    def _apply_and_close(self):
        if self._apply():
            self.accept()

    def done(self, r):
        save_dialog_geometry(self, self._app_config, "clear_message_dlg")
        super().done(r)
