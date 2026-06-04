"""ROM内サウンドデータの読取専用テキストビューア."""
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QHBoxLayout, QLabel, QPushButton, QPlainTextEdit, QVBoxLayout
)
from PyQt5.QtGui import QFont, QTextCursor

from ..core import sound


class SoundViewer(QDialog):
    """Display decoded sound/music sequence data as text."""

    def __init__(self, rom, parent=None):
        super().__init__(parent)
        if parent is not None:
            self.setFont(parent.font())
        self.setWindowTitle("音楽データ表示")
        self.resize(920, 760)
        self.rom = rom
        self.songs = sound.read_sound_songs(self.rom.data)

        layout = QVBoxLayout(self)

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("曲:"))
        self.song_combo = QComboBox()
        for song in self.songs:
            self.song_combo.addItem(sound.combo_label(song), song.sound_id)
        self.song_combo.currentIndexChanged.connect(self._refresh_text)
        ctrl.addWidget(self.song_combo, 1)

        self.chk_expand_calls = QCheckBox("CALL先を展開")
        self.chk_expand_calls.setChecked(True)
        self.chk_expand_calls.stateChanged.connect(self._refresh_text)
        ctrl.addWidget(self.chk_expand_calls)

        self.btn_copy = QPushButton("コピー")
        self.btn_copy.clicked.connect(self._copy_text)
        ctrl.addWidget(self.btn_copy)
        layout.addLayout(ctrl)

        self.info_label = QLabel(
            "読取専用。raw byte と ASM解釈を並べて表示します。"
        )
        layout.addWidget(self.info_label)

        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.text.setFont(QFont("Consolas", 10))
        layout.addWidget(self.text, 1)

        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(self.reject)
        bb.accepted.connect(self.accept)
        layout.addWidget(bb)

        self._refresh_text()

    def _selected_song(self):
        idx = self.song_combo.currentIndex()
        if idx < 0:
            return None
        return self.songs[idx]

    def _refresh_text(self):
        song = self._selected_song()
        if song is None:
            self.text.setPlainText("")
            return
        try:
            text = sound.format_song_text(
                self.rom.data,
                song,
                expand_calls=self.chk_expand_calls.isChecked(),
            )
        except Exception as exc:
            text = f"{type(exc).__name__}: {exc}"
        self.text.setPlainText(text)
        self.text.moveCursor(QTextCursor.Start)

    def _copy_text(self):
        QApplication.clipboard().setText(self.text.toPlainText())
