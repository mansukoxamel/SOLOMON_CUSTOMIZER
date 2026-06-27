"""ROM validation result dialog shared by the main app and standalone tool."""

from __future__ import annotations

import re
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)

from ..core.i18n import t


STAGE_RE = re.compile(r"Stage\s+(\d+)")
POS_RE = re.compile(r"\((\d+)\s*,\s*(\d+)\)")


def stage_from_warning(message: str) -> str:
    match = STAGE_RE.search(str(message))
    return match.group(1) if match else ""


def position_from_warning(message: str):
    match = POS_RE.search(str(message))
    if not match:
        return None
    return (int(match.group(1)), int(match.group(2)))


def support_note(rom) -> str:
    parts = [
        f"file: {getattr(rom, 'display_name', '') or Path(getattr(rom, 'path', '')).name}",
        f"region: {getattr(rom, 'region', '')}",
        f"mapper: {rom.ines_mapper_no()}",
        f"CRC32: {rom.get_crc32_hex()}",
        f"size: {len(rom.data)} bytes",
    ]
    if not rom.is_expanded():
        parts.append("note: 通常ROMは原作特殊処理由来の配置があるため、ROMから復元できる範囲だけをチェックします。")
    elif rom.base_region() != "JP":
        parts.append("note: JP以外のmapper66 ROMは、ステージデータ中心の限定チェックです。")
    return "\n".join(parts)


class RomValidationDialog(QDialog):
    def __init__(
        self,
        rom,
        warnings: list[str],
        parent=None,
        title: str | None = None,
        jump_callback=None,
    ) -> None:
        super().__init__(parent)
        self._rom = rom
        self._warnings = list(warnings or [])
        self._jump_callback = jump_callback
        self.setWindowTitle(title or t("rom_validation.title", "ROM不整合"))
        self.setModal(False)
        self.resize(900, 560)

        status = (
            t("rom_validation.status.ok", "問題なし")
            if not self._warnings
            else t("rom_validation.status.warning_count", "不整合 {count} 件").format(
                count=len(self._warnings)
            )
        )
        self.summary = QTextEdit()
        self.summary.setReadOnly(True)
        self.summary.setMaximumHeight(120)
        self.summary.setPlainText(f"{status}\n{support_note(rom)}")

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["No", "Stage", t("rom_validation.column.content", "内容")])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self._on_row_double_clicked)
        self._populate_table()

        copy_btn = QPushButton(t("rom_validation.copy", "結果コピー"))
        copy_btn.clicked.connect(self.copy_results)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.addButton(copy_btn, QDialogButtonBox.ActionRole)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        if not self._warnings:
            label = QLabel(t("rom_validation.no_issues", "不整合は見つかりませんでした。"))
            layout.addWidget(label)
        layout.addWidget(self.summary)
        layout.addWidget(self.table, 1)
        layout.addWidget(buttons)

    def _populate_table(self) -> None:
        self.table.setRowCount(len(self._warnings))
        for row, message in enumerate(self._warnings):
            no_item = QTableWidgetItem(str(row + 1))
            no_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            stage_item = QTableWidgetItem(stage_from_warning(message))
            stage_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            msg_item = QTableWidgetItem(message)
            self.table.setItem(row, 0, no_item)
            self.table.setItem(row, 1, stage_item)
            self.table.setItem(row, 2, msg_item)

    def _on_row_double_clicked(self, row: int, column: int) -> None:
        if self._jump_callback is None or not (0 <= row < len(self._warnings)):
            return
        message = self._warnings[row]
        stage_text = stage_from_warning(message)
        if not stage_text:
            return
        self._jump_callback(int(stage_text), position_from_warning(message))

    def copy_results(self) -> None:
        lines = [self.summary.toPlainText().strip(), ""]
        for row in range(self.table.rowCount()):
            no = self.table.item(row, 0).text()
            msg = self.table.item(row, 2).text()
            lines.append(f"{no}. {msg}")
        QApplication.clipboard().setText("\n".join(lines).rstrip())
