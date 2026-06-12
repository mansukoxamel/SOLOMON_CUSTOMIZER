"""16x16 sprite pixel editor for ROM-derived frame graphics."""

from __future__ import annotations

from dataclasses import dataclass
from math import inf

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QImage, QPainter, QPen
from PyQt5.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QDialog, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

from ..nes import palette as pal
from ..nes.tile import NES_GFX_TILE_BYTE_SIZE, NesTile
from .file_dialog_compat import get_file, get_path


PALETTE_OFFSET = 0xED4
PALETTE_LABELS = [
    "SPR #0 主人公", "SPR #1 サラマンダー",
    "SPR #2 ガーゴイル", "SPR #3 ゴブリン",
]
TILES_PER_BANK = 512
DEFAULT_CHR_BANK = 2
FRAME_DATA_LO = 0xD600
FRAME_DATA_HI = 0xDA00


@dataclass(frozen=True)
class FrameEntry:
    group: int
    state: int
    frame: int
    left_tile: int
    right_tile: int
    attr: int


class PixelCanvas(QWidget):
    edit_started = pyqtSignal()
    edit_finished = pyqtSignal()
    pixel_changed = pyqtSignal(int, int, int)
    pixel_picked = pyqtSignal(int)
    selection_changed = pyqtSignal(object, object)
    selection_cleared = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._zoom = 24
        self._brush = 1
        self._pixels = [[0 for _ in range(16)] for _ in range(16)]
        self._palettes = [
            [QColor(0, 0, 0), QColor(85, 85, 85), QColor(170, 170, 170), QColor(255, 255, 255)],
            [QColor(0, 0, 0), QColor(85, 85, 85), QColor(170, 170, 170), QColor(255, 255, 255)],
        ]
        self._selecting = False
        self._select_start = None
        self._select_end = None
        self._editing_pixels = False
        self.setMouseTracking(True)
        self._update_fixed_size()

    def _update_fixed_size(self):
        size = 16 * self._zoom + 1
        self.setMinimumSize(size, size)
        self.setMaximumSize(size, size)

    def set_zoom(self, zoom: int):
        self._zoom = max(8, min(40, int(zoom)))
        self._update_fixed_size()
        self.update()

    def set_brush(self, value: int):
        self._brush = max(0, min(3, int(value)))

    def set_pixels(self, pixels: list[list[int]], clear_selection: bool = True):
        self._pixels = [[int(v) & 3 for v in row[:16]] for row in pixels[:16]]
        while len(self._pixels) < 16:
            self._pixels.append([0 for _ in range(16)])
        for y, row in enumerate(self._pixels):
            if len(row) < 16:
                self._pixels[y] = row + [0 for _ in range(16 - len(row))]
        if clear_selection:
            self.clear_selection(emit=False)
        self.update()

    def pixels(self) -> list[list[int]]:
        return [list(row) for row in self._pixels]

    def has_selection(self) -> bool:
        return self._select_start is not None and self._select_end is not None

    def selection_bounds(self) -> tuple[int, int, int, int] | None:
        if not self.has_selection():
            return None
        sx, sy = self._select_start
        ex, ey = self._select_end
        return min(sx, ex), min(sy, ey), max(sx, ex), max(sy, ey)

    def clear_selection(self, emit: bool = True):
        had_selection = self.has_selection()
        self._selecting = False
        self._select_start = None
        self._select_end = None
        if had_selection:
            self.update()
            if emit:
                self.selection_cleared.emit()

    def set_palettes(self, palettes: list[list[tuple[int, int, int]]]):
        out = []
        for colors in palettes[:2]:
            qcolors = [
                QColor(0, 0, 0, 0) if rgb is None else QColor(*rgb)
                for rgb in colors[:4]
            ]
            while len(qcolors) < 4:
                qcolors.append(QColor(0, 0, 0))
            out.append(qcolors)
        while len(out) < 2:
            out.append(list(out[0]) if out else [QColor(0, 0, 0)] * 4)
        self._palettes = out
        self.update()

    def _event_cell(self, event):
        x = event.pos().x() // self._zoom
        y = event.pos().y() // self._zoom
        if 0 <= x < 16 and 0 <= y < 16:
            return int(x), int(y)
        return None

    def _set_selection(self, start, end):
        self._select_start = start
        self._select_end = end
        self.selection_changed.emit(start, end)
        self.update()

    def _begin_pixel_edit(self):
        if self._editing_pixels:
            return
        self._editing_pixels = True
        self.edit_started.emit()

    def _end_pixel_edit(self):
        if not self._editing_pixels:
            return
        self._editing_pixels = False
        self.edit_finished.emit()

    def _paint_at_event(self, event):
        cell = self._event_cell(event)
        if cell is None:
            return
        x, y = cell
        if event.buttons() & Qt.RightButton:
            value = 0
        elif event.buttons() & Qt.LeftButton:
            value = self._brush
        else:
            return
        if self._pixels[y][x] == value:
            return
        self._pixels[y][x] = value
        self.pixel_changed.emit(x, y, value)
        self.update()

    def mousePressEvent(self, event):
        cell = self._event_cell(event)
        if cell is None:
            return
        x, y = cell
        if event.button() == Qt.LeftButton:
            if event.modifiers() & Qt.AltModifier:
                self.pixel_picked.emit(self._pixels[y][x] & 3)
                event.accept()
                return
            if event.modifiers() & Qt.ShiftModifier:
                self._selecting = True
                self._set_selection(cell, cell)
                event.accept()
                return
            if self.has_selection():
                self.clear_selection()
            self._begin_pixel_edit()
        elif event.button() == Qt.RightButton:
            self._begin_pixel_edit()
        self._paint_at_event(event)

    def mouseMoveEvent(self, event):
        if self._selecting:
            cell = self._event_cell(event)
            if cell is not None and cell != self._select_end:
                self._set_selection(self._select_start, cell)
            event.accept()
            return
        if event.buttons() & (Qt.LeftButton | Qt.RightButton):
            self._begin_pixel_edit()
        self._paint_at_event(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._selecting:
            self._selecting = False
            event.accept()
            return
        if event.button() in (Qt.LeftButton, Qt.RightButton):
            self._end_pixel_edit()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        cell = self._zoom
        for y in range(16):
            for x in range(16):
                value = self._pixels[y][x] & 3
                rect_x = x * cell
                rect_y = y * cell
                if value == 0:
                    shade = 58 if ((x + y) & 1) else 86
                    painter.fillRect(rect_x, rect_y, cell, cell, QColor(shade, shade, shade))
                else:
                    half = 0 if x < 8 else 1
                    painter.fillRect(rect_x, rect_y, cell, cell, self._palettes[half][value])

        painter.setPen(QPen(QColor(45, 45, 45), 1))
        for i in range(17):
            pos = i * cell
            painter.drawLine(pos, 0, pos, 16 * cell)
            painter.drawLine(0, pos, 16 * cell, pos)
        painter.setPen(QPen(QColor(230, 230, 230), 2))
        painter.drawLine(8 * cell, 0, 8 * cell, 16 * cell)
        bounds = self.selection_bounds()
        if bounds is not None:
            x1, y1, x2, y2 = bounds
            painter.fillRect(
                x1 * cell,
                y1 * cell,
                (x2 - x1 + 1) * cell,
                (y2 - y1 + 1) * cell,
                QColor(33, 255, 54, 52),
            )
            painter.setPen(QPen(QColor(33, 255, 54), 2))
            painter.drawRect(
                x1 * cell,
                y1 * cell,
                (x2 - x1 + 1) * cell - 1,
                (y2 - y1 + 1) * cell - 1,
            )
        painter.end()


class PixelEditorDialog(QDialog):
    """Edit ROM frame CHR as one on-screen 16x16 sprite."""

    rom_changed = pyqtSignal()

    GROUP_NAMES = {
        0: "system/Dana", 1: "system/Dana", 2: "system/Dana",
        3: "action", 4: "action", 5: "item/effect",
        6: "bonus/seal", 7: "fairy/seal/zodiac",
        8: "Bullet", 9: "Panel Monster",
        10: "Spark Ball slow", 11: "Spark Ball fast",
        12: "Neul s0", 13: "Ghost s0", 14: "Neul s1", 15: "Ghost s1",
        16: "Neul s2", 17: "Ghost s2", 18: "Neul s3", 19: "Ghost s3",
        20: "Demonhead s0", 21: "Demonhead s1", 22: "Demonhead s2",
        23: "Saramandor s0", 24: "Saramandor s1", 25: "Saramandor s2",
        26: "Dragon s0", 27: "Dragon s1", 28: "Golem s0", 29: "Golem s1",
        30: "Gargoyle s0", 31: "Gargoyle s1",
    }

    def __init__(
        self,
        rom,
        parent=None,
        initial_key: tuple[int, int, int] | None = None,
        initial_bank: int | None = None,
        app_config=None,
    ):
        super().__init__(parent)
        if parent is not None:
            self.setFont(parent.font())
        self.setWindowTitle("16x16ピクセル編集")
        self.resize(760, 620)
        self.rom = rom
        self._app_config = app_config
        self._all_entries = self._romframe_items()
        self._entry_ref_counts = self._build_entry_ref_counts(self._all_entries)
        self._entries = self._dedupe_entries(self._all_entries)
        self._entry: FrameEntry | None = None
        self._pixels = [[0 for _ in range(16)] for _ in range(16)]
        self._loaded_pixels = self._copy_pixels(self._pixels)
        self._changed = False
        self._undo_stack: list[list[list[int]]] = []
        self._redo_stack: list[list[list[int]]] = []
        self._pending_undo_pixels = None
        self._pending_edit_changed = False
        self._history_limit = 100

        data = rom.data
        self.chr_start = 16 + data[4] * 0x4000
        chr_size = data[5] * 0x2000
        if chr_size <= 0 or self.chr_start + chr_size > len(data):
            chr_size = max(0, len(data) - self.chr_start)
        self.total_tiles = chr_size // NES_GFX_TILE_BYTE_SIZE
        self.bank_count = max(1, (self.total_tiles + TILES_PER_BANK - 1) // TILES_PER_BANK)
        self._chr_bank = min(DEFAULT_CHR_BANK, self.bank_count - 1)
        if initial_bank is not None:
            self._chr_bank = max(0, min(int(initial_bank), self.bank_count - 1))

        self._build_ui()
        if initial_key is not None:
            self._select_entry_by_key(initial_key)
        self._load_current_frame()
        self._restore_geometry()

    def _restore_geometry(self):
        cfg = self._app_config
        if not cfg:
            return
        w = int(cfg.get("pixel_editor_w", -1))
        h = int(cfg.get("pixel_editor_h", -1))
        x = int(cfg.get("pixel_editor_x", -1))
        y = int(cfg.get("pixel_editor_y", -1))
        if w > 100 and h > 100:
            self.resize(w, h)
        if x >= 0 and y >= 0:
            self.move(x, y)

    def _save_geometry(self):
        cfg = self._app_config
        if cfg is None:
            return
        try:
            from ..core.config import save_config
            cfg["pixel_editor_x"] = max(0, self.x())
            cfg["pixel_editor_y"] = max(0, self.y())
            cfg["pixel_editor_w"] = self.width()
            cfg["pixel_editor_h"] = self.height()
            save_config(cfg)
        except Exception:
            pass

    def done(self, r):
        self._save_geometry()
        super().done(r)

    @staticmethod
    def _copy_pixels(pixels: list[list[int]]) -> list[list[int]]:
        return [list(row) for row in pixels]

    def _normalize_pixels(self, pixels: list[list[int]]) -> list[list[int]]:
        out = [[int(v) & 3 for v in row[:16]] for row in pixels[:16]]
        while len(out) < 16:
            out.append([0 for _ in range(16)])
        for y, row in enumerate(out):
            if len(row) < 16:
                out[y] = row + [0 for _ in range(16 - len(row))]
        return out

    def _set_working_pixels(self, pixels: list[list[int]], clear_selection: bool = True):
        self._pixels = self._normalize_pixels(pixels)
        self.canvas.set_pixels(self._pixels, clear_selection=clear_selection)
        self._update_history_buttons()

    def _reset_history(self):
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._pending_undo_pixels = None
        self._pending_edit_changed = False
        self._update_history_buttons()

    def _update_history_buttons(self):
        if hasattr(self, "undo_btn"):
            self.undo_btn.setEnabled(bool(self._undo_stack))
        if hasattr(self, "redo_btn"):
            self.redo_btn.setEnabled(bool(self._redo_stack))

    def _append_undo_snapshot(self, before_pixels: list[list[int]]):
        before = self._copy_pixels(before_pixels)
        if before == self._pixels:
            return
        self._undo_stack.append(before)
        if len(self._undo_stack) > self._history_limit:
            del self._undo_stack[0]
        self._redo_stack.clear()
        self._update_history_buttons()

    def _commit_pixels(
        self,
        pixels: list[list[int]],
        prefix: str = "",
        clear_selection: bool = True,
    ) -> bool:
        new_pixels = self._normalize_pixels(pixels)
        if new_pixels == self._pixels:
            return False
        before = self._copy_pixels(self._pixels)
        self._set_working_pixels(new_pixels, clear_selection=clear_selection)
        self._append_undo_snapshot(before)
        self._refresh_info(prefix)
        return True

    def _build_ui(self):
        root = QVBoxLayout(self)

        top = QHBoxLayout()
        top.addWidget(QLabel("フレーム:"))
        self.frame_combo = QComboBox()
        self.frame_combo.setMinimumWidth(380)
        self._populate_frame_combo()
        self.frame_combo.currentIndexChanged.connect(self._on_frame_changed)
        top.addWidget(self.frame_combo, 1)

        self.duplicates_chk = QCheckBox("重複参照も表示")
        self.duplicates_chk.setToolTip("同じleft/right/attrを参照するROMフレームも個別に表示")
        self.duplicates_chk.toggled.connect(self._on_duplicate_mode_changed)
        top.addWidget(self.duplicates_chk)

        top.addWidget(QLabel("CHRバンク:"))
        self.bank_combo = QComboBox()
        for bank in range(self.bank_count):
            self.bank_combo.addItem(f"Bank {bank}", bank)
        self.bank_combo.setCurrentIndex(self._chr_bank)
        self.bank_combo.currentIndexChanged.connect(self._on_bank_changed)
        top.addWidget(self.bank_combo)

        top.addWidget(QLabel("表示パレット:"))
        self.palette_combo = QComboBox()
        self.palette_combo.addItem("属性から自動")
        for label in PALETTE_LABELS:
            self.palette_combo.addItem(label)
        self.palette_combo.currentIndexChanged.connect(self._refresh_palette_ui)
        top.addWidget(self.palette_combo)

        top.addWidget(QLabel("拡大:"))
        self.zoom_spin = QSpinBox()
        self.zoom_spin.setRange(12, 36)
        self.zoom_spin.setValue(24)
        self.zoom_spin.setSuffix(" x")
        self.zoom_spin.valueChanged.connect(self._on_zoom_changed)
        top.addWidget(self.zoom_spin)
        root.addLayout(top)

        main = QHBoxLayout()
        self.canvas = PixelCanvas(self)
        self.canvas.edit_started.connect(self._begin_canvas_edit)
        self.canvas.edit_finished.connect(self._end_canvas_edit)
        self.canvas.pixel_changed.connect(self._on_canvas_pixel_changed)
        self.canvas.pixel_picked.connect(self._on_canvas_pixel_picked)
        self.canvas.selection_changed.connect(self._on_canvas_selection_changed)
        self.canvas.selection_cleared.connect(self._on_canvas_selection_cleared)
        main.addWidget(self.canvas, 0, Qt.AlignTop)

        side = QVBoxLayout()
        side.addWidget(QLabel("ペン:"))
        brush_row = QHBoxLayout()
        self.brush_group = QButtonGroup(self)
        self.brush_buttons = []
        for idx in range(4):
            btn = QPushButton(str(idx))
            btn.setCheckable(True)
            btn.setMinimumSize(44, 34)
            btn.setToolTip(f"パレットインデックス {idx} で描く")
            btn.clicked.connect(lambda _checked=False, value=idx: self._set_brush(value))
            self.brush_group.addButton(btn, idx)
            self.brush_buttons.append(btn)
            brush_row.addWidget(btn)
        self.brush_buttons[1].setChecked(True)
        side.addLayout(brush_row)

        self.info_label = QLabel("")
        self.info_label.setWordWrap(True)
        side.addWidget(self.info_label)

        history_row = QHBoxLayout()
        self.undo_btn = QPushButton("元に戻す")
        self.undo_btn.setToolTip("直前の編集を戻す (Ctrl+Z)")
        self.undo_btn.clicked.connect(self._undo)
        history_row.addWidget(self.undo_btn)
        self.redo_btn = QPushButton("やり直し")
        self.redo_btn.setToolTip("戻した編集をやり直す (Ctrl+Y / Ctrl+Shift+Z)")
        self.redo_btn.clicked.connect(self._redo)
        history_row.addWidget(self.redo_btn)
        side.addLayout(history_row)

        flip_row = QHBoxLayout()
        self.flip_h_btn = QPushButton("左右反転")
        self.flip_h_btn.setToolTip("選択範囲があれば範囲内、なければ16x16全体を左右反転")
        self.flip_h_btn.clicked.connect(self._flip_horizontal)
        flip_row.addWidget(self.flip_h_btn)
        self.flip_v_btn = QPushButton("上下反転")
        self.flip_v_btn.setToolTip("選択範囲があれば範囲内、なければ16x16全体を上下反転")
        self.flip_v_btn.clicked.connect(self._flip_vertical)
        flip_row.addWidget(self.flip_v_btn)
        side.addLayout(flip_row)

        import_btn = QPushButton("画像取込...")
        import_btn.setToolTip("画像を16x16へ縮小し、現在の表示パレットの最寄り色へ変換")
        import_btn.clicked.connect(self._import_image)
        side.addWidget(import_btn)

        export_btn = QPushButton("PNG保存...")
        export_btn.setToolTip("現在の16x16作業内容をPNGで保存")
        export_btn.clicked.connect(self._export_png)
        side.addWidget(export_btn)

        clear_btn = QPushButton("クリア")
        clear_btn.setToolTip("作業中の16x16をパレットインデックス0で消去")
        clear_btn.clicked.connect(self._clear_pixels)
        side.addWidget(clear_btn)

        reload_btn = QPushButton("ROMから再読込")
        reload_btn.setToolTip("選択フレームの現在のROM内容を読み直す")
        reload_btn.clicked.connect(self._reload_frame)
        side.addWidget(reload_btn)

        apply_btn = QPushButton("ROMへ書込")
        apply_btn.setToolTip("作業中の16x16を対応CHRタイルへ書き込む")
        apply_btn.clicked.connect(self._apply_to_rom)
        side.addWidget(apply_btn)

        side.addStretch()
        close_btn = QPushButton("閉じる")
        close_btn.clicked.connect(self.reject)
        side.addWidget(close_btn)
        main.addLayout(side, 1)
        root.addLayout(main)

        if not self._all_entries:
            self.frame_combo.setEnabled(False)
            import_btn.setEnabled(False)
            export_btn.setEnabled(False)
            clear_btn.setEnabled(False)
            reload_btn.setEnabled(False)
            apply_btn.setEnabled(False)
            self.undo_btn.setEnabled(False)
            self.redo_btn.setEnabled(False)
            self.flip_h_btn.setEnabled(False)
            self.flip_v_btn.setEnabled(False)
            self.info_label.setText("編集できる16x16 ROMフレームが見つかりません。")
        self._update_history_buttons()

    @staticmethod
    def _entry_key(entry: FrameEntry) -> tuple[int, int, int]:
        return entry.left_tile, entry.right_tile, entry.attr

    def _select_entry_by_key(self, key: tuple[int, int, int]):
        key = tuple(int(v) & 0xFF for v in key)
        for i, entry in enumerate(self._entries):
            if self._entry_key(entry) == key:
                self.frame_combo.setCurrentIndex(i)
                return

    def _build_entry_ref_counts(self, entries: list[FrameEntry]) -> dict[tuple[int, int, int], int]:
        counts = {}
        for entry in entries:
            key = self._entry_key(entry)
            counts[key] = counts.get(key, 0) + 1
        return counts

    def _dedupe_entries(self, entries: list[FrameEntry]) -> list[FrameEntry]:
        seen = set()
        out = []
        for entry in entries:
            key = self._entry_key(entry)
            if key in seen:
                continue
            seen.add(key)
            out.append(entry)
        return out

    def _populate_frame_combo(self):
        current = self.frame_combo.currentData() if hasattr(self, "frame_combo") else None
        del current
        self.frame_combo.blockSignals(True)
        self.frame_combo.clear()
        for i, entry in enumerate(self._entries):
            self.frame_combo.addItem(self._frame_label(i, entry), i)
        self.frame_combo.blockSignals(False)

    def _frame_label(self, index: int, entry: FrameEntry) -> str:
        name = self.GROUP_NAMES.get(entry.group, f"grp{entry.group:02X}")
        refs = self._entry_ref_counts.get(self._entry_key(entry), 1)
        ref_text = f" x{refs}" if refs > 1 else ""
        return (
            f"{index:03d} {name} "
            f"g{entry.group:02X}s{entry.state:02X}f{entry.frame} "
            f"t{entry.left_tile:02X}/{entry.right_tile:02X} a{entry.attr:02X}{ref_text}"
        )

    def _cf(self, cpu: int) -> int:
        return 0x10 + (cpu - 0x8000)

    def _rom_byte_cpu(self, cpu: int) -> int:
        off = self._cf(cpu)
        if 0 <= off < len(self.rom.data):
            return self.rom.data[off]
        return 0

    def _romframe_items(self) -> list[FrameEntry]:
        rom = self.rom.data
        if len(rom) < self._cf(0xD600):
            return []
        gptrs = [
            self._rom_byte_cpu(0xD0E8 + i * 2)
            | (self._rom_byte_cpu(0xD0E8 + i * 2 + 1) << 8)
            for i in range(32)
        ]
        uniq = sorted(set(gptrs))
        bound = {p: (uniq[i + 1] if i + 1 < len(uniq) else 0xD600) for i, p in enumerate(uniq)}
        items = []
        for group in range(32):
            base = gptrs[group]
            nstates = min(max(0, (bound.get(base, base + 4) - base) // 4), 64)
            for state in range(nstates):
                entry_addr = base + state * 4
                phase = self._rom_byte_cpu(entry_addr)
                ref_info = self._rom_byte_cpu(entry_addr + 1)
                ptr = self._rom_byte_cpu(entry_addr + 2) | (self._rom_byte_cpu(entry_addr + 3) << 8)
                frames = (phase & 0x0F) + 1
                if ref_info & 1:
                    if not (0xD000 <= ptr <= 0xD600):
                        continue
                    final = self._rom_byte_cpu(ptr) | (self._rom_byte_cpu(ptr + 1) << 8)
                else:
                    final = ptr
                if not (FRAME_DATA_LO <= final < FRAME_DATA_HI):
                    continue
                for frame in range(min(frames, 8)):
                    addr = final + frame * 3
                    if not (FRAME_DATA_LO <= addr < FRAME_DATA_HI):
                        break
                    items.append(FrameEntry(
                        group=group,
                        state=state,
                        frame=frame,
                        left_tile=self._rom_byte_cpu(addr),
                        right_tile=self._rom_byte_cpu(addr + 1),
                        attr=self._rom_byte_cpu(addr + 2),
                    ))
        return items

    def _current_entry(self) -> FrameEntry | None:
        idx = self.frame_combo.currentData()
        if idx is None:
            return None
        try:
            return self._entries[int(idx)]
        except (IndexError, TypeError, ValueError):
            return None

    def _on_frame_changed(self):
        if self._has_pending_changes():
            ans = QMessageBox.question(
                self, "未書込の編集",
                "現在の作業内容はまだROMへ書き込まれていません。破棄してフレームを切り替えますか？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if ans != QMessageBox.Yes:
                self.frame_combo.blockSignals(True)
                old_idx = self._entries.index(self._entry) if self._entry in self._entries else 0
                self.frame_combo.setCurrentIndex(old_idx)
                self.frame_combo.blockSignals(False)
                return
        self._load_current_frame()

    def _on_duplicate_mode_changed(self, checked: bool):
        if self._has_pending_changes():
            ans = QMessageBox.question(
                self, "未書込の編集",
                "現在の作業内容はまだROMへ書き込まれていません。破棄して表示形式を切り替えますか？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if ans != QMessageBox.Yes:
                self.duplicates_chk.blockSignals(True)
                self.duplicates_chk.setChecked(not checked)
                self.duplicates_chk.blockSignals(False)
                return
        current_key = self._entry_key(self._entry) if self._entry is not None else None
        self._entries = list(self._all_entries) if checked else self._dedupe_entries(self._all_entries)
        self._populate_frame_combo()
        if current_key is not None:
            for i, entry in enumerate(self._entries):
                if self._entry_key(entry) == current_key:
                    self.frame_combo.setCurrentIndex(i)
                    break
        self._load_current_frame()

    def _on_bank_changed(self, index: int):
        index = int(index)
        if index == self._chr_bank:
            return
        if self._has_pending_changes():
            ans = QMessageBox.question(
                self, "未書込の編集",
                "現在の作業内容はまだROMへ書き込まれていません。破棄してCHRバンクを切り替えますか？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if ans != QMessageBox.Yes:
                self.bank_combo.blockSignals(True)
                self.bank_combo.setCurrentIndex(self._chr_bank)
                self.bank_combo.blockSignals(False)
                return
        self._chr_bank = index
        self._load_current_frame()

    def _on_zoom_changed(self, value: int):
        self.canvas.set_zoom(value)

    def _set_brush(self, value: int):
        self.canvas.set_brush(value)
        for i, btn in enumerate(self.brush_buttons):
            btn.setChecked(i == value)

    def _begin_canvas_edit(self):
        self._pending_undo_pixels = self._copy_pixels(self._pixels)
        self._pending_edit_changed = False

    def _end_canvas_edit(self):
        if self._pending_undo_pixels is not None and self._pending_edit_changed:
            self._append_undo_snapshot(self._pending_undo_pixels)
        self._pending_undo_pixels = None
        self._pending_edit_changed = False

    def _on_canvas_pixel_changed(self, x: int, y: int, value: int):
        del x, y, value
        self._pixels = self.canvas.pixels()
        self._pending_edit_changed = True
        self._refresh_info()

    def _on_canvas_pixel_picked(self, value: int):
        self._set_brush(value)
        self._refresh_info(f"スポイト: ペン{value}を選択")

    def _on_canvas_selection_changed(self, start, end):
        del start, end
        self._refresh_info()

    def _on_canvas_selection_cleared(self):
        self._refresh_info()

    def _undo(self):
        if not self._undo_stack:
            return
        current = self._copy_pixels(self._pixels)
        previous = self._undo_stack.pop()
        self._redo_stack.append(current)
        self._set_working_pixels(previous)
        self._refresh_info("元に戻しました。")

    def _redo(self):
        if not self._redo_stack:
            return
        current = self._copy_pixels(self._pixels)
        next_pixels = self._redo_stack.pop()
        self._undo_stack.append(current)
        if len(self._undo_stack) > self._history_limit:
            del self._undo_stack[0]
        self._set_working_pixels(next_pixels)
        self._refresh_info("やり直しました。")

    def _selection_or_full_bounds(self) -> tuple[int, int, int, int]:
        bounds = self.canvas.selection_bounds()
        if bounds is not None:
            return bounds
        return 0, 0, 15, 15

    def _flip_horizontal(self):
        x1, y1, x2, y2 = self._selection_or_full_bounds()
        new_pixels = self._copy_pixels(self._pixels)
        for y in range(y1, y2 + 1):
            new_pixels[y][x1:x2 + 1] = reversed(new_pixels[y][x1:x2 + 1])
        self._commit_pixels(new_pixels, "左右反転しました。", clear_selection=False)

    def _flip_vertical(self):
        x1, y1, x2, y2 = self._selection_or_full_bounds()
        new_pixels = self._copy_pixels(self._pixels)
        rows = [new_pixels[y][x1:x2 + 1] for y in range(y1, y2 + 1)]
        for row_offset, row in enumerate(reversed(rows)):
            new_pixels[y1 + row_offset][x1:x2 + 1] = row
        self._commit_pixels(new_pixels, "上下反転しました。", clear_selection=False)

    def _tile_pair(self, byte_idx: int) -> tuple[int, int]:
        half = 256 if (byte_idx & 1) else 0
        top = half + (byte_idx & 0xFE)
        base = self._chr_bank * TILES_PER_BANK
        return base + top, base + top + 1

    @staticmethod
    def _screen_to_raw(local_x: int, local_y: int, hflip: bool, vflip: bool) -> tuple[int, int, int]:
        raw_x = 7 - local_x if hflip else local_x
        screen_sub = local_y // 8
        screen_y = local_y % 8
        if vflip:
            sub = 1 - screen_sub
            raw_y = 7 - screen_y
        else:
            sub = screen_sub
            raw_y = screen_y
        return sub, raw_x, raw_y

    def _tile_pixels(self, tile_no: int) -> list[list[int]]:
        start = self.chr_start + tile_no * NES_GFX_TILE_BYTE_SIZE
        data = bytes(self.rom.data[start:start + NES_GFX_TILE_BYTE_SIZE])
        if len(data) < NES_GFX_TILE_BYTE_SIZE:
            return [[0 for _ in range(8)] for _ in range(8)]
        return [list(row) for row in NesTile(data).pixels]

    def _decode_entry_pixels(self, entry: FrameEntry) -> list[list[int]]:
        out = [[0 for _ in range(16)] for _ in range(16)]
        left_tiles = self._tile_pair(entry.left_tile)
        right_tiles = self._tile_pair(entry.right_tile)
        hflips = [bool((entry.attr >> 4) & 1), bool((entry.attr >> 1) & 1)]
        vflips = [bool((entry.attr >> 5) & 1), bool((entry.attr >> 0) & 1)]
        tile_cache = {}
        for side, tile_pair in enumerate((left_tiles, right_tiles)):
            for sy in range(16):
                for lx in range(8):
                    sub, raw_x, raw_y = self._screen_to_raw(lx, sy, hflips[side], vflips[side])
                    tile_no = tile_pair[sub]
                    if tile_no not in tile_cache:
                        tile_cache[tile_no] = self._tile_pixels(tile_no)
                    out[sy][side * 8 + lx] = tile_cache[tile_no][raw_y][raw_x] & 3
        return out

    @staticmethod
    def _encode_tile(pixels: list[list[int]]) -> bytes:
        plane0 = []
        plane1 = []
        for y in range(8):
            lo = 0
            hi = 0
            for x in range(8):
                value = pixels[y][x] & 3
                bit = 7 - x
                lo |= (value & 1) << bit
                hi |= ((value >> 1) & 1) << bit
            plane0.append(lo)
            plane1.append(hi)
        return bytes(plane0 + plane1)

    def _write_entry_pixels(self, entry: FrameEntry):
        left_tiles = self._tile_pair(entry.left_tile)
        right_tiles = self._tile_pair(entry.right_tile)
        hflips = [bool((entry.attr >> 4) & 1), bool((entry.attr >> 1) & 1)]
        vflips = [bool((entry.attr >> 5) & 1), bool((entry.attr >> 0) & 1)]
        tile_cache = {}
        for side, tile_pair in enumerate((left_tiles, right_tiles)):
            for sy in range(16):
                for lx in range(8):
                    sub, raw_x, raw_y = self._screen_to_raw(lx, sy, hflips[side], vflips[side])
                    tile_no = tile_pair[sub]
                    if tile_no not in tile_cache:
                        tile_cache[tile_no] = self._tile_pixels(tile_no)
                    tile_cache[tile_no][raw_y][raw_x] = self._pixels[sy][side * 8 + lx] & 3

        for tile_no, pixels in sorted(tile_cache.items()):
            start = self.chr_start + tile_no * NES_GFX_TILE_BYTE_SIZE
            end = start + NES_GFX_TILE_BYTE_SIZE
            if start < 0 or end > len(self.rom.data):
                raise ValueError(f"CHR tile {tile_no} is outside ROM")
            self.rom.data[start:end] = self._encode_tile(pixels)

    def _load_subpalette(self, sprite_palette_no: int) -> list[tuple[int, int, int] | None]:
        off = PALETTE_OFFSET + (4 + sprite_palette_no) * 4
        try:
            colors = [self.rom.data[off + i] & 0x3F for i in range(3)]
        except Exception:
            colors = [0x00, 0x10, 0x30]
        return [None] + [pal.get_nes_color(idx) for idx in colors]

    def _palette_numbers_for_entry(self, entry: FrameEntry | None) -> tuple[int, int]:
        fixed = self.palette_combo.currentIndex() - 1
        if fixed >= 0:
            return fixed, fixed
        if entry is None:
            return 0, 0
        return (entry.attr >> 6) & 3, (entry.attr >> 2) & 3

    def _palette_colors_for_entry(self, entry: FrameEntry | None) -> list[list[tuple[int, int, int]]]:
        left, right = self._palette_numbers_for_entry(entry)
        return [self._load_subpalette(left), self._load_subpalette(right)]

    def _refresh_palette_ui(self):
        colors = self._palette_colors_for_entry(self._entry)
        self.canvas.set_palettes(colors)
        swatch_colors = colors[0]
        for idx, btn in enumerate(self.brush_buttons):
            if idx == 0 or swatch_colors[idx] is None:
                qc = QColor(58, 58, 58)
                text = "#f5f5f5"
                background = (
                    "qlineargradient(x1:0, y1:0, x2:1, y2:1, "
                    "stop:0 #444444, stop:0.49 #444444, "
                    "stop:0.5 #777777, stop:1 #777777)"
                )
            else:
                rgb = swatch_colors[idx]
                qc = QColor(*rgb)
                luminance = (rgb[0] * 299 + rgb[1] * 587 + rgb[2] * 114) // 1000
                text = "#111111" if luminance > 140 else "#f5f5f5"
                background = qc.name()
            btn.setStyleSheet(
                "QPushButton {"
                f"background: {background}; color: {text};"
                "border: 1px solid #555; font-weight: bold;"
                "}"
                "QPushButton:checked { border: 3px solid #facc15; }"
            )
        self._refresh_info()

    def _load_current_frame(self):
        self._entry = self._current_entry()
        if self._entry is None:
            return
        self._pixels = self._decode_entry_pixels(self._entry)
        self._loaded_pixels = self._copy_pixels(self._pixels)
        self.canvas.set_pixels(self._pixels)
        self._reset_history()
        self._refresh_palette_ui()

    def _reload_frame(self):
        if self._has_pending_changes():
            ans = QMessageBox.question(
                self, "再読込",
                "現在の作業内容を破棄してROMから読み直しますか？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if ans != QMessageBox.Yes:
                return
        self._load_current_frame()

    def _clear_pixels(self):
        self._commit_pixels(
            [[0 for _ in range(16)] for _ in range(16)],
            "クリアしました。",
        )

    def _nearest_palette_index(self, color: QColor, colors: list[tuple[int, int, int] | None]) -> int:
        best_idx = 0
        best_dist = inf
        for idx, rgb in enumerate(colors):
            if idx == 0 or rgb is None:
                continue
            dr = color.red() - rgb[0]
            dg = color.green() - rgb[1]
            db = color.blue() - rgb[2]
            dist = dr * dr + dg * dg + db * db
            if dist < best_dist:
                best_dist = dist
                best_idx = idx
        return best_idx

    def _import_image(self):
        path = get_file(
            self,
            title="16x16画像を取り込み",
            filter="Images (*.png *.bmp *.jpg *.jpeg);;All files (*)",
        )
        if not path:
            return
        img = QImage(path)
        if img.isNull():
            QMessageBox.critical(self, "画像取込失敗", "画像を読み込めませんでした。")
            return
        img = img.convertToFormat(QImage.Format_ARGB32)
        if img.width() != 16 or img.height() != 16:
            img = img.scaled(16, 16, Qt.IgnoreAspectRatio, Qt.FastTransformation)

        colors = self._palette_colors_for_entry(self._entry)
        new_pixels = [[0 for _ in range(16)] for _ in range(16)]
        for y in range(16):
            for x in range(16):
                qc = img.pixelColor(x, y)
                if qc.alpha() < 128:
                    value = 0
                else:
                    value = self._nearest_palette_index(qc, colors[0 if x < 8 else 1])
                new_pixels[y][x] = value & 3
        self._commit_pixels(new_pixels, "画像を取り込みました。")

    def _export_png(self):
        path = get_path(
            self,
            title="16x16 PNGを保存",
            filter="PNG (*.png);;All files (*)",
            mode="save",
            directory="pixel_16x16.png",
        )
        if not path:
            return
        colors = self._palette_colors_for_entry(self._entry)
        img = QImage(16, 16, QImage.Format_ARGB32)
        for y in range(16):
            for x in range(16):
                value = self._pixels[y][x] & 3
                if value == 0:
                    img.setPixelColor(x, y, QColor(0, 0, 0, 0))
                else:
                    rgb = colors[0 if x < 8 else 1][value]
                    if rgb is None:
                        img.setPixelColor(x, y, QColor(0, 0, 0, 0))
                    else:
                        img.setPixelColor(x, y, QColor(*rgb))
        if not img.save(path, "PNG"):
            QMessageBox.critical(self, "PNG保存失敗", "PNGを書き出せませんでした。")

    def _apply_to_rom(self):
        if self._entry is None:
            return
        try:
            self._pixels = self.canvas.pixels()
            self._write_entry_pixels(self._entry)
        except Exception as exc:
            QMessageBox.critical(self, "書込失敗", f"{type(exc).__name__}: {exc}")
            return
        self._loaded_pixels = self._copy_pixels(self._pixels)
        self._changed = True
        self.rom_changed.emit()
        self._refresh_info("ROMへ書き込みました。")

    def _has_pending_changes(self) -> bool:
        return self._pixels != self._loaded_pixels

    def _refresh_info(self, prefix: str = ""):
        if self._entry is None:
            return
        left_tiles = self._tile_pair(self._entry.left_tile)
        right_tiles = self._tile_pair(self._entry.right_tile)
        left_pal, right_pal = self._palette_numbers_for_entry(self._entry)
        refs = self._entry_ref_counts.get(self._entry_key(self._entry), 1)
        dirty = " / 未書込" if self._has_pending_changes() else ""
        selection_text = ""
        if hasattr(self, "canvas"):
            bounds = self.canvas.selection_bounds()
            if bounds is not None:
                x1, y1, x2, y2 = bounds
                selection_text = (
                    f"選択範囲: ({x1},{y1})-({x2},{y2}) "
                    f"{x2 - x1 + 1}x{y2 - y1 + 1}<br>"
                )
        msg = (
            f"CHR bank: {self._chr_bank}<br>"
            f"左CHR: {left_tiles[0]}, {left_tiles[1]} / "
            f"右CHR: {right_tiles[0]}, {right_tiles[1]}<br>"
            f"{selection_text}"
            f"表示SPRパレット: 左#{left_pal} 右#{right_pal} / "
            f"attr=${self._entry.attr:02X} / 参照数:{refs}{dirty}<br>"
            "右クリックまたはペン0で透明色。CHR共有タイルを使う別フレームも同時に見た目が変わります。"
        )
        if prefix:
            msg = f"<b>{prefix}</b><br>" + msg
        self.info_label.setText(msg)

    def keyPressEvent(self, event):
        key = event.key()
        mods = event.modifiers()
        if mods & Qt.ControlModifier:
            if key == Qt.Key_Z and mods & Qt.ShiftModifier:
                self._redo()
                return
            if key == Qt.Key_Z:
                self._undo()
                return
            if key == Qt.Key_Y:
                self._redo()
                return
        if event.key() == Qt.Key_Escape and self.canvas.has_selection():
            self.canvas.clear_selection()
            return
        super().keyPressEvent(event)

    def reject(self):
        if self._has_pending_changes():
            ans = QMessageBox.question(
                self, "閉じる",
                "ROMへ書き込んでいない作業内容があります。破棄して閉じますか？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if ans != QMessageBox.Yes:
                return
        super().reject()
