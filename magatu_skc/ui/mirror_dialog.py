"""ミラー詳細設定ダイアログ

現在ステージの 2つのミラーについて
- ドロップスケジュール (8バイト = 64ビット, Phase1 + Phase2 ループ)
- スポーン敵の TTL (Saramander/Demon Head 用)
を編集する。敵セットはメインウィンドウのミラーパネルで編集。

拡張ROM (mapper 66) のレイアウトに直接読み書きする:
- スケジュール: OFFSET_M66_DROP_SCHED_DATA + (2*level + spawn) * 8 から 8バイト
- TTL:         level.spawn_enemy_lifetime (ROM側は OFFSET_M66_LOCAL_ENEMY_DATA の先頭バイトを再エンコード)
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDialogButtonBox, QGroupBox, QCheckBox, QSpinBox
)
from PyQt5.QtCore import Qt

from ..core import m66


SCHEDULE_BITS = 64
PHASE1_BITS = 32
PHASE2_BITS = 32
# ゲーム側の初期化処理により先頭2tickは「処理済み」判定でスキップされる (6502: $A0CF BEQ)
DEAD_TICKS = 2


class MirrorDialog(QDialog):
    """現在ステージの 2ミラー(spawn0=demon_mirrors[0], spawn1=demon_mirrors[1]) を編集"""

    def __init__(self, rom, level, level_no, parent=None):
        super().__init__(parent)
        if parent is not None:
            self.setFont(parent.font())
        self.setWindowTitle(f"ミラー詳細設定 - Stage {level_no + 1}")
        self.rom = rom
        self.level = level
        self.level_no = level_no

        # 作業バッファ
        self._sched_bits = [None, None]   # [mirror_no] -> list[64] of bool
        self._ttl = level.spawn_enemy_lifetime

        # ROMから現在値を読み込み
        for m in range(2):
            self._sched_bits[m] = self._read_schedule(m)

        self._build_ui()

    # ===== ROM 読み書きヘルパ =====

    def _schedule_offset(self, mirror_no: int) -> int:
        return m66.OFFSET_M66_DROP_SCHED_DATA + (2 * self.level_no + mirror_no) * 8

    def _read_schedule(self, mirror_no: int) -> list:
        off = self._schedule_offset(mirror_no)
        bits = []
        for i in range(8):
            b = self.rom.data[off + i]
            for shift in range(7, -1, -1):
                bits.append(bool((b >> shift) & 1))
        return bits

    def _write_schedule(self, mirror_no: int, bits: list):
        off = self._schedule_offset(mirror_no)
        for i in range(8):
            byte = 0
            for shift in range(7, -1, -1):
                if bits[i * 8 + (7 - shift)]:
                    byte |= (1 << shift)
            self.rom.data[off + i] = byte

    # ===== UI 構築 =====

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # TTL
        ttl_row = QHBoxLayout()
        ttl_row.addWidget(QLabel("スポーン敵の生存時間:"))
        self.spin_ttl = QSpinBox()
        self.spin_ttl.setRange(0, 255)
        self.spin_ttl.setValue(self._ttl)
        self.spin_ttl.setToolTip(
            "Saramander / DemonHead 系のスポーン敵に使われます。\n"
            "目安: 約0.5秒 × 値 (例: 16=約8秒、30=約16秒)"
        )
        self.spin_ttl.valueChanged.connect(self._update_ttl_seconds_label)
        ttl_row.addWidget(self.spin_ttl)
        self.lbl_ttl_seconds = QLabel()
        self.lbl_ttl_seconds.setMinimumWidth(70)
        ttl_row.addWidget(self.lbl_ttl_seconds)
        ttl_row.addStretch()
        layout.addLayout(ttl_row)
        self._update_ttl_seconds_label(self.spin_ttl.value())

        # 各ミラー
        self._sched_checks = [[None] * SCHEDULE_BITS, [None] * SCHEDULE_BITS]

        for m in range(2):
            grp = QGroupBox(f"ミラー {m + 1}  (位置: {self.level.demon_mirrors[m].position})")
            gl = QVBoxLayout(grp)

            # スケジュール
            gl.addWidget(QLabel(
                "<b>出現タイミング</b> (左から順に時間経過)"
                "　<span style='color:gray;'>※先頭2tickはゲーム側で無視される</span>"
            ))

            LABEL_W = 110

            phase1_row = QHBoxLayout()
            phase1_row.setSpacing(0)
            lbl_p1 = QLabel("Phase 1:")
            lbl_p1.setFixedWidth(LABEL_W)
            phase1_row.addWidget(lbl_p1)
            for i in range(PHASE1_BITS):
                cb = QCheckBox()
                cb.setChecked(self._sched_bits[m][i])
                cb.setFixedSize(18, 22)
                if i < DEAD_TICKS:
                    cb.setEnabled(False)
                    cb.setToolTip(f"tick {i} (ゲーム側で無視される)")
                else:
                    cb.setToolTip(f"tick {i}")
                phase1_row.addWidget(cb)
                self._sched_checks[m][i] = cb
            phase1_row.addStretch()
            gl.addLayout(phase1_row)

            phase2_row = QHBoxLayout()
            phase2_row.setSpacing(0)
            lbl_p2 = QLabel("Phase 2 (ループ):")
            lbl_p2.setFixedWidth(LABEL_W)
            phase2_row.addWidget(lbl_p2)
            for i in range(PHASE2_BITS):
                idx = PHASE1_BITS + i
                cb = QCheckBox()
                cb.setChecked(self._sched_bits[m][idx])
                cb.setFixedSize(18, 22)
                cb.setToolTip(f"tick {idx}")
                phase2_row.addWidget(cb)
                self._sched_checks[m][idx] = cb
            phase2_row.addStretch()
            gl.addLayout(phase2_row)

            # クイック操作
            quick_row = QHBoxLayout()
            btn_fill_sched = QPushButton("スケジュール全ON")
            btn_fill_sched.clicked.connect(lambda _, mm=m: self._fill_schedule(mm))
            btn_clear_sched = QPushButton("スケジュール全クリア")
            btn_clear_sched.clicked.connect(lambda _, mm=m: self._clear_schedule(mm))
            quick_row.addWidget(btn_fill_sched)
            quick_row.addWidget(btn_clear_sched)
            quick_row.addStretch()
            gl.addLayout(quick_row)

            layout.addWidget(grp)

        # OK / Cancel / Apply
        btnbox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply
        )
        btnbox.accepted.connect(self._apply_and_close)
        btnbox.rejected.connect(self.reject)
        btnbox.button(QDialogButtonBox.Apply).clicked.connect(self._apply)
        layout.addWidget(btnbox)

    def _update_ttl_seconds_label(self, val):
        seconds = val * 0.5
        if seconds.is_integer():
            seconds_text = str(int(seconds))
        else:
            seconds_text = f"{seconds:.1f}"
        self.lbl_ttl_seconds.setText(f"約{seconds_text}秒")

    # ===== クイック操作 =====

    def _clear_schedule(self, mirror_no: int):
        for cb in self._sched_checks[mirror_no]:
            cb.setChecked(False)

    def _fill_schedule(self, mirror_no: int):
        for cb in self._sched_checks[mirror_no]:
            cb.setChecked(True)

    # ===== 適用 =====

    def _gather(self):
        for m in range(2):
            self._sched_bits[m] = [self._sched_checks[m][i].isChecked()
                                   for i in range(SCHEDULE_BITS)]
        self._ttl = self.spin_ttl.value()

    def _apply(self):
        self._gather()
        # ROM書込
        for m in range(2):
            self._write_schedule(m, self._sched_bits[m])
        # TTL: levelに反映 (m66 saver が level.spawn_enemy_lifetime をエンコードして書き込む)
        self.level.spawn_enemy_lifetime = self._ttl
        # 敵データ先頭バイトを直接更新（次回保存まで再描画一致のため）
        ttl_byte = ((self._ttl >> 3) | ((self._ttl & 7) << 5)) & 0xff
        enemy_off = (m66.OFFSET_M66_LVL_DATA + 256 * self.level_no
                     + m66.OFFSET_M66_LOCAL_ENEMY_DATA)
        self.rom.data[enemy_off] = ttl_byte
        # 親に通知
        parent = self.parent()
        if parent is not None and hasattr(parent, "_on_mirror_changed"):
            parent._on_mirror_changed()

    def _apply_and_close(self):
        self._apply()
        self.accept()
