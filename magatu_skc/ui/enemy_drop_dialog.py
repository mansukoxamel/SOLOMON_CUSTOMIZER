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
from ..core import enemy_drop as ED


class EnemyDropDialog(QDialog):
    def __init__(self, rom_data: bytearray, parent=None):
        super().__init__(parent)
        if parent is not None:
            self.setFont(parent.font())
        self.setWindowTitle("敵ドロップ効果表 編集")
        self._rom = rom_data

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
            row_combos = []
            for si in range(ED.ROW_LEN):
                cb = QComboBox()
                cb.addItems(self._labels)
                cb.setCurrentIndex(self._values.index(self._rows[ri][si]))
                cb.currentIndexChanged.connect(
                    lambda _idx, r=ri, s=si: self._on_change(r, s))
                gl.addWidget(cb, 0, si)
                row_combos.append(cb)
            self._combos.append(row_combos)
            pl = QLabel()
            pl.setWordWrap(True)
            self._prob_lbls.append(pl)
            gl.addWidget(pl, 1, 0, 1, ED.ROW_LEN)
            grid.addWidget(gb)
            self._update_prob(ri)
        scroll.setWidget(inner)
        root.addWidget(scroll, 1)

        btnrow = QHBoxLayout()
        btn_restore = QPushButton("原作に戻す")
        btn_restore.clicked.connect(self._on_restore)
        btnrow.addWidget(btn_restore)
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
        self.resize(720, 600)

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
