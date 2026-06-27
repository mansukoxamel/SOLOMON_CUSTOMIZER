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
from ..core.i18n import get_language, t
from .dialog_geometry import restore_dialog_geometry, save_dialog_geometry


def format_clear_message_error(error) -> str:
    msg = str(error)
    if get_language() != "en":
        return msg
    if "ROM が小さすぎます" in msg:
        return t("clear_message.error.rom_too_small", msg)
    if "ヘッダ署名不一致" in msg:
        return t("clear_message.error.header", msg)
    if "終端($00)不一致" in msg:
        return t("clear_message.error.terminator", msg)
    if "未知の文字tile" in msg:
        return t("clear_message.error.unknown_tile", msg)
    if "使えない文字" in msg:
        return t("clear_message.error.invalid_char", msg)
    if "長すぎます" in msg:
        return t("clear_message.error.too_long", msg)
    if "行数不正" in msg:
        return t("clear_message.error.invalid_line_count", msg)
    return msg


class ClearMessageDialog(QDialog):
    def __init__(self, rom_data: bytearray, parent=None, app_config=None):
        super().__init__(parent)
        if parent is not None:
            self.setFont(parent.font())
        self.setWindowTitle(t("clear_message.title", "クリア画面メッセージ編集 (同字数・JP)"))
        self._rom = rom_data
        self._app_config = app_config
        self.resize(560, 320)

        rows = CM.read_messages(rom_data)   # [(name, cur, count, orig)] ×3

        root = QVBoxLayout(self)
        head = QLabel(t("clear_message.description"))
        head.setWordWrap(True)
        root.addWidget(head)

        g = QGridLayout()
        g.setHorizontalSpacing(8)
        g.setVerticalSpacing(6)
        g.addWidget(QLabel(t("clear_message.column.line", "行")), 0, 0)
        g.addWidget(QLabel(t("clear_message.column.text", "文字")), 0, 1)
        g.addWidget(QLabel(t("clear_message.column.count", "字数")), 0, 2)
        g.addWidget(QLabel(t("clear_message.column.original", "原作")), 0, 3)

        # A-Z と space のみ許可
        rx = QRegExpValidator(QRegExp("[A-Za-z ]*"))
        self._edits = []
        for i, (_name, cur, count, orig) in enumerate(rows):
            line_label = t("clear_message.line_label", "{index}行目").format(index=i + 1)
            count_label = t("clear_message.count_suffix", "{count}字").format(count=count)
            g.addWidget(QLabel(line_label), i + 1, 0)
            le = QLineEdit(cur.rstrip())
            le.setMaxLength(count)
            le.setValidator(rx)
            cnt_lbl = QLabel()
            cnt_lbl.setMinimumWidth(56)
            le.textChanged.connect(
                lambda _t, e=le, c=count, lb=cnt_lbl: self._on_text(e, c, lb))
            g.addWidget(le, i + 1, 1)
            g.addWidget(cnt_lbl, i + 1, 2)
            g.addWidget(QLabel(f"{orig}  ({count_label})"), i + 1, 3)
            self._edits.append(le)
            self._on_text(le, count, cnt_lbl)   # 初期表示
        root.addLayout(g)

        btnrow = QHBoxLayout()
        b_rest = QPushButton(t("clear_message.restore_original", "原作に戻す"))
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
            QMessageBox.critical(
                self,
                t("clear_message.apply_failed", "クリア画面メッセージ編集失敗"),
                format_clear_message_error(e),
            )
            return False
        return True

    def _apply_and_close(self):
        if self._apply():
            self.accept()

    def done(self, r):
        save_dialog_geometry(self, self._app_config, "clear_message_dlg")
        super().done(r)
