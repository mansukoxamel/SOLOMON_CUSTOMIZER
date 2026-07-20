"""ROM内サウンドデータの読取専用テキストビューア."""
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QHBoxLayout, QLabel, QPushButton, QPlainTextEdit, QVBoxLayout
)
from PyQt5.QtGui import QFont, QTextCursor

from ..core import sound
from ..core.i18n import t
from .dialog_geometry import restore_dialog_geometry, save_dialog_geometry
from .dialog_buttons import localize_dialog_buttons


class SoundViewer(QDialog):
    """Display decoded sound/music sequence data as text."""

    def __init__(self, rom, parent=None, app_config=None):
        super().__init__(parent)
        if parent is not None:
            self.setFont(parent.font())
        self.setWindowTitle(t("sound_viewer.title", "音楽データ表示"))
        self.resize(920, 760)
        self._app_config = app_config
        self.rom = rom
        self.songs = sound.read_sound_songs(self.rom.data)

        layout = QVBoxLayout(self)

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel(t("sound_viewer.song.label", "曲:")))
        self.song_combo = QComboBox()
        for song in self.songs:
            self.song_combo.addItem(sound.combo_label(song), song.sound_id)
        self.song_combo.currentIndexChanged.connect(self._refresh_text)
        ctrl.addWidget(self.song_combo, 1)

        self.chk_expand_calls = QCheckBox(t("sound_viewer.expand_calls", "CALL先を展開"))
        self.chk_expand_calls.setChecked(True)
        self.chk_expand_calls.stateChanged.connect(self._refresh_text)
        ctrl.addWidget(self.chk_expand_calls)

        self.btn_copy = QPushButton(t("sound_viewer.copy", "コピー"))
        self.btn_copy.clicked.connect(self._copy_text)
        ctrl.addWidget(self.btn_copy)
        layout.addLayout(ctrl)

        self.info_label = QLabel(t("sound_viewer.info"))
        layout.addWidget(self.info_label)

        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.text.setFont(QFont("Consolas", 10))
        layout.addWidget(self.text, 1)

        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(self.reject)
        bb.accepted.connect(self.accept)
        localize_dialog_buttons(bb)
        layout.addWidget(bb)

        self._refresh_text()
        restore_dialog_geometry(self, self._app_config, "sound_viewer_dlg")

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

    def done(self, r):
        save_dialog_geometry(self, self._app_config, "sound_viewer_dlg")
        super().done(r)
