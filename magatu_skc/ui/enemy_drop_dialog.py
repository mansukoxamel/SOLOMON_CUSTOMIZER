"""敵ドロップ効果表 編集ダイアログ (グローバル)

core.enemy_drop の $C293 (10行×8枠) を編集する。値は DROP_EFFECTS
(なし/特殊/スコア各種/1UP/ファイア距離+/妖精予約) のみ。確率は枠数/8。
行は複数の敵グループで共有される (ROW_USERS を各行に明示)。

注意: ここで設定するのは「拾得AI のドロップ効果値」であって通常の
床アイテムID ではない ($06=1UP であって鍵ではない)。
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QComboBox,
    QPushButton, QDialogButtonBox, QScrollArea, QWidget, QGroupBox,
    QMessageBox,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor
from ..core import enemy_drop as ED
from .element_picker import (
    ENEMIES_LIST, ENHANCED_ENEMY_CODES, PANEL_VARIANT_VISUAL_SOURCE,
)
from .dialog_geometry import restore_dialog_geometry, save_dialog_geometry


ENEMY_THUMB = 28
ENEMY_GAP = 4


class EnemyDropDialog(QDialog):
    def __init__(self, rom_data: bytearray, parent=None,
                 tile_renderer=None, config=None, app_config=None):
        super().__init__(parent)
        if parent is not None:
            self.setFont(parent.font())
        self.setWindowTitle("敵ドロップ効果表 編集")
        self._rom = rom_data
        self.tile_renderer = tile_renderer
        self.config = config
        self._app_config = app_config
        self._enemy_cache = {}

        # 作業バッファ (OK/Apply で rom_data へ反映)
        self._rows = [list(r) for r in ED.read_rows(rom_data)]

        # 効果値の選択肢 (値順)
        self._values = sorted(ED.DROP_EFFECTS)
        self._labels = [f"${v:02X} {ED.DROP_EFFECTS[v][0]}" for v in self._values]

        root = QVBoxLayout(self)
        head = QLabel(
            "敵を炎で倒した時に出る効果を行ごとに編集します。確率＝8枠中の"
            "出現数。<b>値は効果値であり通常アイテムIDではありません</b>"
            "（$06=1UP で鍵ではない）。行は複数の敵で共有されます。"
        )
        head.setWordWrap(True)
        root.addWidget(head)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        grid = QVBoxLayout(inner)
        self._combos = []   # [row][slot] = QComboBox
        self._prob_lbls = []
        for ri in range(ED.ROW_COUNT):
            off = ri * 8
            gb = QGroupBox(f"行 {ED.ROW_LABELS[ri]}  — 使用: "
                           f"{ED.ROW_USERS.get(off, '?')}")
            gl = QGridLayout(gb)
            enemy_strip = QLabel()
            enemy_strip.setPixmap(self._compose_enemy_strip(off))
            enemy_strip.setToolTip(self._enemy_tooltip(off))
            gl.addWidget(enemy_strip, 0, 0, 1, ED.ROW_LEN)
            row_combos = []
            for si in range(ED.ROW_LEN):
                cb = QComboBox()
                cb.addItems(self._labels)
                cb.setCurrentIndex(self._values.index(self._rows[ri][si]))
                cb.currentIndexChanged.connect(
                    lambda _idx, r=ri, s=si: self._on_change(r, s))
                gl.addWidget(cb, 1, si)
                row_combos.append(cb)
            self._combos.append(row_combos)
            pl = QLabel()
            pl.setWordWrap(True)
            self._prob_lbls.append(pl)
            gl.addWidget(pl, 2, 0, 1, ED.ROW_LEN)
            grid.addWidget(gb)
            self._update_prob(ri)
        scroll.setWidget(inner)
        root.addWidget(scroll, 1)

        btnrow = QHBoxLayout()
        btn_restore = QPushButton("原作に戻す")
        btn_restore.clicked.connect(self._on_restore)
        btnrow.addWidget(btn_restore)
        btn_clear = QPushButton("すべてなしにする")
        btn_clear.clicked.connect(self._on_clear_all)
        btnrow.addWidget(btn_clear)
        btnrow.addStretch()
        root.addLayout(btnrow)

        bb = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
            | QDialogButtonBox.Apply
        )
        bb.accepted.connect(self._apply_and_close)
        bb.rejected.connect(self.reject)
        bb.button(QDialogButtonBox.Apply).clicked.connect(self._apply)
        root.addWidget(bb)
        self.resize(840, 680)
        restore_dialog_geometry(self, self._app_config, "enemy_drop_dlg")

    @staticmethod
    def _drop_row_for_enemy_code(code: int):
        idx = (int(code) >> 2) - 6
        if 0 <= idx < len(ED.ORIG_C278):
            return ED.ORIG_C278[idx]
        return None

    def _enemy_entries_for_row(self, row_offset: int):
        return [
            (code, name)
            for code, name in ENEMIES_LIST
            if self._drop_row_for_enemy_code(code) == row_offset
        ]

    def _enemy_tooltip(self, row_offset: int) -> str:
        entries = self._enemy_entries_for_row(row_offset)
        if not entries:
            return ED.ROW_USERS.get(row_offset, "")
        return "\n".join(f"${code:02X} {name}" for code, name in entries)

    def _enemy_pixmap(self, code: int) -> QPixmap:
        if code in self._enemy_cache:
            return self._enemy_cache[code]
        if self.tile_renderer is None or self.config is None:
            return QPixmap()
        try:
            visual_code = PANEL_VARIANT_VISUAL_SOURCE.get(code, code)
            anim = self.config.enemy_map.get(visual_code, 0)
            sprite = self.tile_renderer.get_tile_image(anim, 0, transparent=True)
            bg = QImage(ENEMY_THUMB, ENEMY_THUMB, QImage.Format_ARGB32)
            bg.fill(QColor(20, 20, 20))
            p = QPainter(bg)
            scaled = sprite.scaled(
                ENEMY_THUMB, ENEMY_THUMB,
                Qt.KeepAspectRatio, Qt.FastTransformation,
            )
            ox = (ENEMY_THUMB - scaled.width()) // 2
            oy = (ENEMY_THUMB - scaled.height()) // 2
            p.drawImage(ox, oy, scaled)
            if code in PANEL_VARIANT_VISUAL_SOURCE:
                p.fillRect(0, 0, ENEMY_THUMB, ENEMY_THUMB, QColor(55, 135, 255, 70))
            elif code in ENHANCED_ENEMY_CODES:
                p.fillRect(0, 0, ENEMY_THUMB, ENEMY_THUMB, QColor(245, 220, 80, 45))
            p.setPen(QColor(90, 90, 90))
            p.drawRect(0, 0, ENEMY_THUMB - 1, ENEMY_THUMB - 1)
            p.end()
            pm = QPixmap.fromImage(bg)
        except Exception:
            pm = QPixmap()
        self._enemy_cache[code] = pm
        return pm

    def _compose_enemy_strip(self, row_offset: int) -> QPixmap:
        entries = self._enemy_entries_for_row(row_offset)
        if not entries:
            return QPixmap()
        strip_w = len(entries) * ENEMY_THUMB + (len(entries) - 1) * ENEMY_GAP
        strip = QImage(strip_w, ENEMY_THUMB, QImage.Format_ARGB32)
        strip.fill(QColor(0, 0, 0, 0))
        p = QPainter(strip)
        x = 0
        for code, _name in entries:
            pm = self._enemy_pixmap(code)
            if not pm.isNull():
                p.drawPixmap(x, 0, pm)
            x += ENEMY_THUMB + ENEMY_GAP
        p.end()
        return QPixmap.fromImage(strip)

    def _on_change(self, ri, si):
        self._rows[ri][si] = self._values[self._combos[ri][si].currentIndex()]
        self._update_prob(ri)

    def _update_prob(self, ri):
        prob = ED.probabilities(self._rows[ri])
        parts = []
        for v in sorted(prob, key=lambda k: -prob[k]):
            n = prob[v]
            parts.append(f"{ED.DROP_EFFECTS[v][0]}×{n}={n*100//8}.{(n*1000//8)%10}%")
        self._prob_lbls[ri].setText("確率: " + " / ".join(parts))

    def _set_all_rows(self, value: int):
        self._rows = [[value for _ in range(ED.ROW_LEN)] for _ in range(ED.ROW_COUNT)]
        for ri in range(ED.ROW_COUNT):
            for si in range(ED.ROW_LEN):
                cb = self._combos[ri][si]
                cb.blockSignals(True)
                cb.setCurrentIndex(self._values.index(self._rows[ri][si]))
                cb.blockSignals(False)
            self._update_prob(ri)

    def _on_clear_all(self):
        self._set_all_rows(0x00)

    def _on_restore(self):
        flat = list(ED.ORIG_C293)
        self._rows = [flat[i * 8:(i + 1) * 8] for i in range(ED.ROW_COUNT)]
        for ri in range(ED.ROW_COUNT):
            for si in range(ED.ROW_LEN):
                cb = self._combos[ri][si]
                cb.blockSignals(True)
                cb.setCurrentIndex(self._values.index(self._rows[ri][si]))
                cb.blockSignals(False)
            self._update_prob(ri)

    def _apply(self) -> bool:
        try:
            changed = ED.write_rows(self._rom, self._rows)
        except ED.EnemyDropError as e:
            QMessageBox.critical(self, "敵ドロップ改造 失敗", str(e))
            return False
        if changed:
            self.setWindowTitle("敵ドロップ効果表 編集  (適用済)")
        return True

    def _apply_and_close(self):
        if self._apply():
            self.accept()

    def done(self, r):
        save_dialog_geometry(self, self._app_config, "enemy_drop_dlg")
        super().done(r)
