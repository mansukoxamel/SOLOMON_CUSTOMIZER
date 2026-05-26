"""ボーナスステージ (Stage 51) 出現位置テーブル編集ダイアログ

ROM内のボーナスステージ専用・出現位置テーブルを編集する:
- 出現位置テーブル (32要素、各1バイト = NES座標エンコード)

アイテム種類(16種)の編集はピッカー下部のボーナスアイテムパネルで行う。
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QLabel,
    QDialogButtonBox, QGroupBox, QSpinBox
)
from PyQt5.QtCore import Qt

from ..core import constants as c
from ..core.element import position_from_byte, byte_from_position


BONUS_POS_COUNT = 32
BONUS_ITEM_COUNT = 16


class BonusStageDialog(QDialog):

    def __init__(self, rom, parent=None):
        super().__init__(parent)
        if parent is not None:
            self.setFont(parent.font())
        self.setWindowTitle("ボーナスステージ (Stage 51) 出現位置編集")
        self.rom = rom

        region = rom.base_region()
        offsets = c.ROM_OFFSETS.get(region, c.ROM_OFFSETS["JP"])
        self._pos_addr = offsets.get("bonus_pos", 0x1955)

        self._pos_bytes = list(rom.data[self._pos_addr:self._pos_addr + BONUS_POS_COUNT])

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # 位置テーブル (32箇所)
        pos_grp = QGroupBox(f"出現位置 ({BONUS_POS_COUNT}箇所)")
        pg = QGridLayout(pos_grp)
        self._pos_x_spins = []
        self._pos_y_spins = []
        cols = 4
        for i in range(BONUS_POS_COUNT):
            row = i // cols
            col_base = (i % cols) * 4
            pos = position_from_byte(self._pos_bytes[i])
            item_idx = i % BONUS_ITEM_COUNT

            lbl = QLabel(f"[{i}] (→#{item_idx})")
            lbl.setToolTip(f"位置{i}: アイテム#{item_idx}を配置")
            pg.addWidget(lbl, row, col_base)

            sx = QSpinBox()
            sx.setRange(0, c.LEVEL_W - 1)
            sx.setValue(pos[0])
            sx.setPrefix("X:")
            pg.addWidget(sx, row, col_base + 1)
            self._pos_x_spins.append(sx)

            sy = QSpinBox()
            sy.setRange(0, c.LEVEL_H - 1)
            sy.setValue(pos[1])
            sy.setPrefix("Y:")
            pg.addWidget(sy, row, col_base + 2)
            self._pos_y_spins.append(sy)

            spacer = QLabel("")
            spacer.setFixedWidth(10)
            pg.addWidget(spacer, row, col_base + 3)

        layout.addWidget(pos_grp)

        # OK / Cancel / Apply
        btnbox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply
        )
        btnbox.accepted.connect(self._apply_and_close)
        btnbox.rejected.connect(self.reject)
        btnbox.button(QDialogButtonBox.Apply).clicked.connect(self._apply)
        layout.addWidget(btnbox)

    def _apply(self):
        for i in range(BONUS_POS_COUNT):
            x = self._pos_x_spins[i].value()
            y = self._pos_y_spins[i].value()
            self._pos_bytes[i] = byte_from_position((x, y))

        for i in range(BONUS_POS_COUNT):
            self.rom.data[self._pos_addr + i] = self._pos_bytes[i]

        parent = self.parent()
        if parent is not None and hasattr(parent, "_on_bonus_table_changed"):
            parent._on_bonus_table_changed()

    def _apply_and_close(self):
        self._apply()
        self.accept()
