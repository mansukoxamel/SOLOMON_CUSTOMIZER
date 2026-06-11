#!/usr/bin/env python3
"""GUI tool to patch only the start-stage bytes in a JP original ROM."""

from __future__ import annotations

import argparse
import sys
import zlib
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


MIN_STAGE = 1
MAX_STAGE = 53

OFFSET_START_STAGE = 0x1145
OFFSET_STAGE_SELECT_COMMON1 = 0x1149
OFFSET_STAGE_SELECT_COMMON2 = 0x114B
PATCH_OFFSETS = (
    OFFSET_START_STAGE,
    OFFSET_STAGE_SELECT_COMMON1,
    OFFSET_STAGE_SELECT_COMMON2,
)

# CRC32 values include the 16-byte iNES header.
KNOWN_JP_ORIGINAL_CRC32 = {
    "013ED497",
    "5B49FEDB",
    "2FE9E2CA",
}


class PatchError(Exception):
    """User-facing patch failure."""


def crc32_hex(data: bytes) -> str:
    return f"{zlib.crc32(data) & 0xFFFFFFFF:08X}"


def parse_stage(value: str) -> int:
    try:
        stage = int(value, 10)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("stage must be a decimal number") from exc
    if not MIN_STAGE <= stage <= MAX_STAGE:
        raise argparse.ArgumentTypeError(f"stage must be {MIN_STAGE}-{MAX_STAGE}")
    return stage


def default_output_path(input_path: Path, stage: int) -> Path:
    return input_path.with_name(f"{input_path.stem}_stage{stage:02d}{input_path.suffix}")


def validate_input_rom(data: bytes, *, force: bool) -> str:
    if len(data) <= max(PATCH_OFFSETS):
        raise PatchError(
            f"ROM is too short: need file offset 0x{max(PATCH_OFFSETS):04X}"
        )
    if data[:4] != b"NES\x1A":
        raise PatchError("input is not an iNES ROM (missing NES header)")

    crc = crc32_hex(data)
    if crc not in KNOWN_JP_ORIGINAL_CRC32 and not force:
        known = ", ".join(sorted(KNOWN_JP_ORIGINAL_CRC32))
        raise PatchError(
            f"CRC32={crc} is not a known JP original Solomon no Kagi ROM. "
            f"Known CRC32: {known}. Enable force only for local investigation."
        )
    return crc


def patched_data_for_stage(data: bytes, stage: int) -> bytearray:
    patched = bytearray(data)
    if stage == 1:
        patched[OFFSET_START_STAGE] = 0x00
        patched[OFFSET_STAGE_SELECT_COMMON1] = 0x8D
        patched[OFFSET_STAGE_SELECT_COMMON2] = 0x04
    else:
        patched[OFFSET_START_STAGE] = (stage - 1) & 0xFF
        patched[OFFSET_STAGE_SELECT_COMMON1] = 0xAD
        patched[OFFSET_STAGE_SELECT_COMMON2] = 0x93
    return patched


def format_patch_lines(before: bytes, after: bytes) -> list[str]:
    lines = []
    for offset in PATCH_OFFSETS:
        old = before[offset]
        new = after[offset]
        if old == new:
            lines.append(f"0x{offset:04X}: {old:02X} (unchanged)")
        else:
            lines.append(f"0x{offset:04X}: {old:02X} -> {new:02X}")
    return lines


def write_output(path: Path, data: bytes, *, input_path: Path, overwrite: bool) -> None:
    output_resolved = path.resolve()
    input_resolved = input_path.resolve()

    if output_resolved == input_resolved:
        raise PatchError("output path is the input ROM; choose another output path")
    if path.exists() and not overwrite:
        raise PatchError(f"output already exists: {path}")
    if not path.parent.exists():
        raise PatchError(f"output directory does not exist: {path.parent}")

    try:
        path.write_bytes(data)
    except OSError as exc:
        raise PatchError(f"failed to write output: {exc}") from exc


class RomDropLineEdit(QLineEdit):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setPlaceholderText("Drop a .nes ROM here, or choose Browse")

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


class StartStagePatchWindow(QWidget):
    def __init__(self, rom_path: Path | None = None, stage: int = MIN_STAGE) -> None:
        super().__init__()
        self._manual_output = False
        self.setWindowTitle("Solomon Start Stage Patcher")
        self.setMinimumWidth(620)
        self.setAcceptDrops(True)

        self.rom_edit = RomDropLineEdit()
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Output ROM path")
        self.stage_spin = QSpinBox()
        self.stage_spin.setRange(MIN_STAGE, MAX_STAGE)
        self.stage_spin.setValue(stage)
        self.overwrite_check = QCheckBox("Overwrite existing output")
        self.force_check = QCheckBox("Force unknown CRC32")
        self.force_check.setToolTip(
            "Use only when investigating a local dump whose CRC is not in the known JP original list."
        )
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(140)

        self._build_layout()
        self._connect_signals()

        if rom_path is not None:
            self.rom_edit.setText(str(rom_path))
            self._update_default_output()
        else:
            self._update_default_output()

    def _build_layout(self) -> None:
        intro = QLabel(
            "JP original ROM only. This writes a new ROM copy and changes only "
            "the start-stage patch bytes."
        )
        intro.setWordWrap(True)

        browse_rom_btn = QPushButton("Browse")
        browse_rom_btn.clicked.connect(self._browse_rom)
        self.browse_rom_btn = browse_rom_btn

        rom_row = QHBoxLayout()
        rom_row.addWidget(self.rom_edit, 1)
        rom_row.addWidget(browse_rom_btn)

        browse_output_btn = QPushButton("Save As")
        browse_output_btn.clicked.connect(self._browse_output)
        self.browse_output_btn = browse_output_btn

        output_row = QHBoxLayout()
        output_row.addWidget(self.output_edit, 1)
        output_row.addWidget(browse_output_btn)

        form = QFormLayout()
        form.addRow("Input ROM:", rom_row)
        form.addRow("Start stage:", self.stage_spin)
        form.addRow("Output ROM:", output_row)
        form.addRow("", self.overwrite_check)
        form.addRow("", self.force_check)

        run_btn = QPushButton("Create ROM")
        run_btn.clicked.connect(self._run_patch)
        self.run_btn = run_btn

        layout = QVBoxLayout(self)
        layout.addWidget(intro)
        layout.addLayout(form)
        layout.addWidget(run_btn, alignment=Qt.AlignRight)
        layout.addWidget(self.log)

    def _connect_signals(self) -> None:
        self.rom_edit.textChanged.connect(self._update_default_output)
        self.stage_spin.valueChanged.connect(self._update_default_output)
        self.output_edit.textEdited.connect(self._mark_manual_output)

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
            event.acceptProposedAction()
        else:
            event.ignore()

    def _browse_rom(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select JP original ROM",
            "",
            "NES ROM (*.nes);;All files (*)",
        )
        if path:
            self.rom_edit.setText(path)

    def _browse_output(self) -> None:
        start = self.output_edit.text().strip()
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save patched ROM",
            start,
            "NES ROM (*.nes);;All files (*)",
        )
        if path:
            self._manual_output = True
            self.output_edit.setText(path)

    def _mark_manual_output(self) -> None:
        self._manual_output = bool(self.output_edit.text().strip())

    def _update_default_output(self) -> None:
        if self._manual_output:
            return
        text = self.rom_edit.text().strip()
        if not text:
            self.output_edit.clear()
            return
        self.output_edit.setText(str(default_output_path(Path(text), self.stage_spin.value())))

    def _run_patch(self) -> None:
        try:
            input_path = Path(self.rom_edit.text().strip())
            output_path = Path(self.output_edit.text().strip())
            if not str(input_path):
                raise PatchError("choose an input ROM")
            if not str(output_path):
                raise PatchError("choose an output ROM")
            data = input_path.read_bytes()
            crc = validate_input_rom(data, force=self.force_check.isChecked())
            patched = patched_data_for_stage(data, self.stage_spin.value())
            write_output(
                output_path,
                patched,
                input_path=input_path,
                overwrite=self.overwrite_check.isChecked(),
            )
        except OSError as exc:
            self._show_error(f"failed to read input ROM: {exc}")
            return
        except PatchError as exc:
            self._show_error(str(exc))
            return

        lines = [
            f"Input : {input_path}",
            f"CRC32 : {crc}",
            f"Stage : {self.stage_spin.value()}",
            f"Output: {output_path}",
            "Changed bytes:",
            *format_patch_lines(data, patched),
        ]
        message = "\n".join(lines)
        self.log.setPlainText(message)
        QMessageBox.information(self, "Created ROM", message)

    def _show_error(self, message: str) -> None:
        self.log.setPlainText(message)
        QMessageBox.critical(self, "Patch failed", message)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Open a small window for creating a JP Solomon no Kagi ROM copy "
            "with only the start-stage patch bytes changed."
        )
    )
    parser.add_argument("rom", nargs="?", type=Path, help="input JP original .nes ROM")
    parser.add_argument(
        "stage",
        nargs="?",
        type=parse_stage,
        default=MIN_STAGE,
        help=f"initial start stage shown in the window ({MIN_STAGE}-{MAX_STAGE})",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    app = QApplication(sys.argv[:1])
    window = StartStagePatchWindow(args.rom, args.stage)
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
