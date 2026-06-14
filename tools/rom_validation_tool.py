#!/usr/bin/env python3
"""Standalone PyQt5 ROM validation/audit tool for Solomon no Kagi hacks."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from magatu_skc.core.level import load_all_levels
from magatu_skc.core.rom import Rom
from magatu_skc.core import save_validation
from magatu_skc.nes.config_loader import SkcConfig
from magatu_skc.ui.rom_validation_dialog import stage_from_warning, support_note


class RomDropLineEdit(QLineEdit):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setPlaceholderText("Drop a .nes/.zip ROM here, or choose Browse")

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:  # noqa: N802
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            self.setText(urls[0].toLocalFile())
            event.acceptProposedAction()
        else:
            event.ignore()


def _load_level_meta_items(rom: Rom):
    config_path = ROOT / "magatu_skc" / "skc_config.xml"
    try:
        cfg = SkcConfig.load(str(config_path), bytes(rom.data), rom.region)
        return getattr(cfg, "level_meta_items", [])
    except Exception:
        return None


class RomValidationWindow(QWidget):
    def __init__(self, rom_path: Path | None = None) -> None:
        super().__init__()
        self.setWindowTitle("Solomon ROM 不整合チェック")
        self.setMinimumSize(900, 560)
        self.setAcceptDrops(True)

        self.rom_edit = RomDropLineEdit()
        self.browse_btn = QPushButton("参照...")
        self.run_btn = QPushButton("チェック")
        self.copy_btn = QPushButton("結果コピー")
        self.summary = QTextEdit()
        self.summary.setReadOnly(True)
        self.summary.setMaximumHeight(120)
        from PyQt5.QtWidgets import QHeaderView, QTableWidget

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["No", "Stage", "内容"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        self._build_layout()
        self._connect()

        if rom_path is not None:
            self.rom_edit.setText(str(rom_path))
            self._run_check()
        else:
            self.summary.setPlainText(
                "誰かが作った改造ROMを読み込み、保存前チェックと同じ観点で不整合らしき配置を一覧表示します。\n"
                ".nes または .zip をドラッグ&ドロップできます。"
            )

    def _build_layout(self) -> None:
        top = QHBoxLayout()
        top.addWidget(QLabel("ROM/ZIP:"))
        top.addWidget(self.rom_edit, 1)
        top.addWidget(self.browse_btn)
        top.addWidget(self.run_btn)
        top.addWidget(self.copy_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.summary)
        layout.addWidget(self.table, 1)

    def _connect(self) -> None:
        self.browse_btn.clicked.connect(self._browse)
        self.run_btn.clicked.connect(self._run_check)
        self.copy_btn.clicked.connect(self._copy_results)
        self.rom_edit.returnPressed.connect(self._run_check)

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:  # noqa: N802
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            self.rom_edit.setText(urls[0].toLocalFile())
            self._run_check()
            event.acceptProposedAction()
        else:
            event.ignore()

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "検証するROM/ZIPを選択",
            "",
            "NES ROMs / ZIP (*.nes *.zip);;NES ROMs (*.nes);;ZIP archives (*.zip);;All files (*)",
        )
        if path:
            self.rom_edit.setText(path)
            self._run_check()

    def _run_check(self) -> None:
        path_text = self.rom_edit.text().strip()
        if not path_text:
            QMessageBox.warning(self, "ROM未選択", "検証するROMまたはZIPを選択してください。")
            return
        try:
            rom = Rom.load(path_text)
            levels = load_all_levels(rom)
            meta_items = _load_level_meta_items(rom)
            warnings = save_validation.collect_save_warnings(
                rom,
                levels,
                level_meta_items=meta_items,
            )
        except Exception as exc:
            self.table.setRowCount(0)
            message = f"{type(exc).__name__}: {exc}"
            self.summary.setPlainText(message)
            QMessageBox.critical(self, "チェック失敗", message)
            return

        status = "問題なし" if not warnings else f"不整合 {len(warnings)} 件"
        self.summary.setPlainText(f"{status}\n{support_note(rom)}")
        self._populate_table(warnings)

    def _populate_table(self, warnings: list[str]) -> None:
        self.table.setRowCount(len(warnings))
        for row, message in enumerate(warnings):
            from PyQt5.QtWidgets import QTableWidgetItem

            no_item = QTableWidgetItem(str(row + 1))
            no_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            stage_item = QTableWidgetItem(stage_from_warning(message))
            stage_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            msg_item = QTableWidgetItem(message)
            self.table.setItem(row, 0, no_item)
            self.table.setItem(row, 1, stage_item)
            self.table.setItem(row, 2, msg_item)

    def _copy_results(self) -> None:
        lines = [self.summary.toPlainText().strip(), ""]
        for row in range(self.table.rowCount()):
            no = self.table.item(row, 0).text()
            msg = self.table.item(row, 2).text()
            lines.append(f"{no}. {msg}")
        QApplication.clipboard().setText("\n".join(lines).rstrip())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Open a standalone GUI that validates Solomon no Kagi ROM/stage safety."
    )
    parser.add_argument("rom", nargs="?", type=Path, help=".nes or .zip ROM to check")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    app = QApplication(sys.argv[:1])
    window = RomValidationWindow(args.rom)
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
