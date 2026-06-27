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
    QDialogButtonBox, QGroupBox, QCheckBox, QSpinBox,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt5.QtCore import Qt

from ..core import m66
from ..core.i18n import t
from .dialog_geometry import restore_dialog_geometry, save_dialog_geometry


SCHEDULE_BITS = 64
PHASE1_BITS = 32
PHASE2_BITS = 32
# ゲーム側の初期化処理により先頭2tickは「処理済み」判定でスキップされる (6502: $A0CF BEQ)
DEAD_TICKS = 2


def _read_schedule_bits(rom_data, level_no: int, mirror_no: int) -> list:
    off = m66.OFFSET_M66_DROP_SCHED_DATA + (2 * level_no + mirror_no) * 8
    bits = []
    for i in range(8):
        b = rom_data[off + i]
        for shift in range(7, -1, -1):
            bits.append(bool((b >> shift) & 1))
    return bits


def _schedule_pattern(bits: list, start: int, length: int) -> str:
    chars = []
    for idx in range(start, start + length):
        if idx < DEAD_TICKS:
            chars.append("-")
        else:
            chars.append("X" if bits[idx] else ".")
    return "".join(chars)


def _active_tick_count(bits: list) -> int:
    return sum(1 for i, bit in enumerate(bits) if i >= DEAD_TICKS and bit)


def _read_mirror_enemy_codes(rom_data, level_no: int, mirror_no: int) -> list:
    local = (m66.OFFSET_M66_LOCAL_SCHED_ENEMY_1_DATA if mirror_no == 0
             else m66.OFFSET_M66_LOCAL_SCHED_ENEMY_2_DATA)
    off = m66.OFFSET_M66_LVL_DATA + 256 * level_no + local
    codes = []
    for i in range(7):
        b = rom_data[off + i]
        if b == 0x90:
            break
        if b:
            codes.append(b)
    return codes


class MirrorDialog(QDialog):
    """現在ステージの 2ミラー(spawn0=demon_mirrors[0], spawn1=demon_mirrors[1]) を編集"""

    def __init__(self, rom, level, level_no, parent=None, app_config=None):
        super().__init__(parent)
        if parent is not None:
            self.setFont(parent.font())
        self.setWindowTitle(t(
            "mirror_dialog.title",
            "ミラー詳細設定 - Stage {stage}",
        ).format(stage=level_no + 1))
        self._app_config = app_config
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
        restore_dialog_geometry(self, self._app_config, "mirror_dlg")

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
        ttl_row.addWidget(QLabel(t(
            "mirror_dialog.ttl.label",
            "スポーン敵の生存時間:",
        )))
        self.spin_ttl = QSpinBox()
        self.spin_ttl.setRange(0, 255)
        self.spin_ttl.setValue(self._ttl)
        self.spin_ttl.setToolTip(t(
            "mirror_dialog.ttl.tooltip",
            "Saramander / DemonHead 系のスポーン敵に使われます。\n"
            "目安: 約0.5秒 × 値 (例: 16=約8秒、30=約16秒)",
        ))
        self.spin_ttl.valueChanged.connect(self._update_ttl_seconds_label)
        ttl_row.addWidget(self.spin_ttl)
        self.lbl_ttl_seconds = QLabel()
        self.lbl_ttl_seconds.setMinimumWidth(70)
        ttl_row.addWidget(self.lbl_ttl_seconds)
        ttl_row.addStretch()
        layout.addLayout(ttl_row)
        self._update_ttl_seconds_label(self.spin_ttl.value())

        overview_row = QHBoxLayout()
        overview_row.addStretch()
        btn_overview = QPushButton(t(
            "mirror_dialog.overview.button",
            "ミラー出現一覧",
        ))
        btn_overview.setToolTip(t(
            "mirror_dialog.overview.tooltip",
            "全ステージのミラー敵セットと出現タイミングを読取専用で一覧表示します。",
        ))
        btn_overview.clicked.connect(self._show_overview)
        overview_row.addWidget(btn_overview)
        layout.addLayout(overview_row)

        # 各ミラー
        self._sched_checks = [[None] * SCHEDULE_BITS, [None] * SCHEDULE_BITS]

        for m in range(2):
            grp = QGroupBox(t(
                "mirror_dialog.mirror.group",
                "ミラー {mirror}  (位置: {position})",
            ).format(mirror=m + 1, position=self.level.demon_mirrors[m].position))
            gl = QVBoxLayout(grp)

            # スケジュール
            gl.addWidget(QLabel(t(
                "mirror_dialog.schedule.label_html",
                "<b>出現タイミング</b> (左から順に時間経過)"
                "　<span style='color:gray;'>※先頭2tickはゲーム側で無視される</span>",
            )))

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
                    cb.setToolTip(t(
                        "mirror_dialog.tick.ignored.tooltip",
                        "tick {tick} (ゲーム側で無視される)",
                    ).format(tick=i))
                else:
                    cb.setToolTip(f"tick {i}")
                phase1_row.addWidget(cb)
                self._sched_checks[m][i] = cb
            phase1_row.addStretch()
            gl.addLayout(phase1_row)

            phase2_row = QHBoxLayout()
            phase2_row.setSpacing(0)
            lbl_p2 = QLabel(t(
                "mirror_dialog.phase2.label",
                "Phase 2 (ループ):",
            ))
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
            btn_fill_sched = QPushButton(t("mirror_dialog.all_on.button", "全ON"))
            btn_fill_sched.setToolTip(t(
                "mirror_dialog.all_on.tooltip",
                "有効tickをすべてONにします。",
            ))
            btn_fill_sched.clicked.connect(lambda _, mm=m: self._fill_schedule(mm))
            btn_clear_sched = QPushButton(t("mirror_dialog.all_off.button", "全OFF"))
            btn_clear_sched.setToolTip(t(
                "mirror_dialog.all_off.tooltip",
                "出現タイミングをすべてOFFにします。",
            ))
            btn_clear_sched.clicked.connect(lambda _, mm=m: self._clear_schedule(mm))
            quick_row.addWidget(btn_fill_sched)
            quick_row.addWidget(btn_clear_sched)
            for gap, text in (
                (1, "1空け"), (2, "2空け"), (3, "3空け"),
                (4, "4空け"), (5, "5空け"), (6, "6空け"),
            ):
                btn = QPushButton(t(
                    f"mirror_dialog.gap.button.{gap}",
                    text,
                ))
                btn.setToolTip(t(
                    "mirror_dialog.gap.tooltip",
                    "tick {start} から、{gap}個空けて出現タイミングをONにします。",
                ).format(start=DEAD_TICKS, gap=gap))
                btn.clicked.connect(lambda _, mm=m, g=gap: self._set_schedule_gap(mm, g))
                quick_row.addWidget(btn)
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
        self.lbl_ttl_seconds.setText(t(
            "mirror_dialog.ttl.seconds",
            "約{seconds}秒",
        ).format(seconds=seconds_text))

    # ===== クイック操作 =====

    def _clear_schedule(self, mirror_no: int):
        for cb in self._sched_checks[mirror_no]:
            cb.setChecked(False)

    def _fill_schedule(self, mirror_no: int):
        for i, cb in enumerate(self._sched_checks[mirror_no]):
            cb.setChecked(i >= DEAD_TICKS)

    def _set_schedule_gap(self, mirror_no: int, gap: int):
        period = max(1, int(gap) + 1)
        for i, cb in enumerate(self._sched_checks[mirror_no]):
            cb.setChecked(i >= DEAD_TICKS and ((i - DEAD_TICKS) % period == 0))

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

    def _show_overview(self):
        parent = self.parent()
        levels = getattr(parent, "levels", None)
        config = getattr(parent, "config", None)
        if not levels:
            return
        dlg = MirrorScheduleOverviewDialog(
            self.rom, levels, config=config, parent=self,
            app_config=self._app_config
        )
        dlg.exec_()

    def done(self, r):
        save_dialog_geometry(self, self._app_config, "mirror_dlg")
        super().done(r)


class MirrorScheduleOverviewDialog(QDialog):
    """全ステージのミラー出現タイミングを読取専用で一覧表示する"""

    COLUMNS = (
        ("mirror_overview.column.level", "Lv", 38),
        ("mirror_overview.column.ttl", "TTL", 48),
        ("mirror_overview.column.m1_pos", "M1位置", 64),
        ("mirror_overview.column.m1_enemy", "M1敵", 230),
        ("mirror_overview.column.m1_count", "M1数", 48),
        ("", "M1 Phase1", 245),
        ("", "M1 Phase2", 245),
        ("mirror_overview.column.m2_pos", "M2位置", 64),
        ("mirror_overview.column.m2_enemy", "M2敵", 230),
        ("mirror_overview.column.m2_count", "M2数", 48),
        ("", "M2 Phase1", 245),
        ("", "M2 Phase2", 245),
    )

    def __init__(self, rom, levels, config=None, parent=None, app_config=None):
        super().__init__(parent)
        if parent is not None:
            self.setFont(parent.font())
        self.setWindowTitle(t(
            "mirror_overview.title",
            "ミラー出現パターン一覧",
        ))
        self.resize(1280, 720)
        self._app_config = app_config
        self.rom = rom
        self.levels = levels
        self.config = config

        layout = QVBoxLayout(self)
        info = QLabel(t(
            "mirror_overview.info",
            "全ステージのミラー敵セットと64tick出現パターンを表示します。"
            "X=出現、.=なし、-=ゲーム側で無視される先頭tick。",
        ))
        info.setWordWrap(True)
        layout.addWidget(info)

        self.table = QTableWidget(len(levels), len(self.COLUMNS), self)
        self.table.setHorizontalHeaderLabels([
            t(key, default) if key else default
            for key, default, _width in self.COLUMNS
        ])
        for i, (_key, _default, width) in enumerate(self.COLUMNS):
            self.table.setColumnWidth(i, width)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setTextElideMode(Qt.ElideNone)
        self.table.setWordWrap(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self._populate()
        layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_close = QPushButton(t("common.close", "閉じる"))
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)
        restore_dialog_geometry(self, self._app_config, "mirror_overview_dlg")

    def _enemy_name(self, code: int) -> str:
        if self.config is not None:
            return self.config.enemy_desc.get(code, f"${code:02X}")
        return f"${code:02X}"

    def _enemy_text(self, codes: list) -> str:
        if not codes:
            return ""
        return " / ".join(f"${code:02X} {self._enemy_name(code)}" for code in codes)

    def _set_item(self, row: int, col: int, text: str, align=None):
        item = QTableWidgetItem(text)
        if align is not None:
            item.setTextAlignment(align)
        self.table.setItem(row, col, item)
        return item

    def _populate(self):
        for row, level in enumerate(self.levels):
            self._set_item(row, 0, str(row + 1), Qt.AlignCenter)
            self._set_item(row, 1, str(getattr(level, "spawn_enemy_lifetime", 0)), Qt.AlignCenter)

            for mirror_no in range(2):
                base_col = 2 if mirror_no == 0 else 7
                mirror = level.demon_mirrors[mirror_no]
                self._set_item(row, base_col, str(mirror.position), Qt.AlignCenter)

                codes = _read_mirror_enemy_codes(self.rom.data, row, mirror_no)
                enemy_text = self._enemy_text(codes)
                enemy_item = self._set_item(row, base_col + 1, enemy_text)
                enemy_item.setToolTip(enemy_text.replace(" / ", "\n"))

                bits = _read_schedule_bits(self.rom.data, row, mirror_no)
                active = _active_tick_count(bits)
                self._set_item(row, base_col + 2, str(active), Qt.AlignCenter)
                p1 = _schedule_pattern(bits, 0, PHASE1_BITS)
                p2 = _schedule_pattern(bits, PHASE1_BITS, PHASE2_BITS)
                p1_item = self._set_item(row, base_col + 3, p1)
                p2_item = self._set_item(row, base_col + 4, p2)
                p1_item.setToolTip("Phase 1 tick 0-31")
                p2_item.setToolTip("Phase 2 tick 32-63")

    def done(self, r):
        save_dialog_geometry(self, self._app_config, "mirror_overview_dlg")
        super().done(r)
