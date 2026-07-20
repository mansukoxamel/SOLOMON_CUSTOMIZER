"""タイトル画面編集ダイアログ (R196)

タイトルの配置、色区分、CHRタイル、文字、キャラクター、パレットを
プレビューしながら編集する。上部ロゴ領域は画像として保存・読込できる。

キャンセル時は開いた時点の ROM へ復元。
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDialogButtonBox, QMessageBox, QScrollArea, QWidget, QComboBox,
    QFileDialog, QInputDialog, QGridLayout, QGroupBox, QLineEdit,
    QSpinBox, QRadioButton, QButtonGroup, QSizePolicy, QCheckBox,
    QTabWidget, QFormLayout,
)
from PyQt5.QtCore import Qt, pyqtSignal, QRegExp
from PyQt5.QtGui import (
    QImage, QPixmap, QPainter, QColor, QPen, QRegExpValidator,
)
from ..core import title_screen as TS
from ..core import clearscreen_hack
from ..core import clear_message as CM
from ..core.config import save_config
from ..core.i18n import t
from ..nes.palette import NES_COLORS
from ..nes.tile import NesTile, NES_TILE_W, NES_GFX_TILE_BYTE_SIZE
from .dialog_geometry import restore_dialog_geometry, save_dialog_geometry
from collections import Counter
from itertools import permutations
import json
import os
import re
from datetime import datetime

# 実タイトル画面 = 32x30 タイル = 256x240px。色は未確定ゆえ
# 暗背景の4階調 (idx0 ≒ 黒 = 原作の黒背景に近い見え方)。
_GRAY = (0x10, 0x68, 0xB0, 0xF8)
_NT_W = 32
_IMG_W = 256                        # 32*8
_IMG_H = 240                        # 30*8
_DISPLAY_SCROLL_X = 8               # rendered -> preview display correction
_DISPLAY_SCROLL_Y = 1
_TOP_Y = 6 * 8 + 1                  # display-corrected title logo/banner band
_TOP_H = 8 * 8                      # rows 6..13, 256x64
_TOP_SIDE_FORMAT = "solomon_customizer_title_top_sidecar"
_STAMP_RE = re.compile(r"\d{8}_\d{6}")
_TITLE_PALETTE_SCRIPT_OFF = 0x10 + (0x958A - 0x8000)
_TITLE_FIXED_TEXT_PALETTE_OFF = 0x10 + (0x94C7 - 0x8000)
_TITLE_ATTR_JP_OFF = 0x4D68
_TITLE_ATTR_US_OFF = 0x4CBF
_TITLE_ATTR_EXTRA_JP_OFF = 0x10 + (0xCDF5 - 0x8000)
_SPRITE_PALETTE_OFFSET = 0xED4
# bg パターンテーブル = CHR bank3 上位 4KB (tiles 256-511、ロゴ域 R196)
_BG_BASE = 256
_TITLE_TILE_PICKER_COLS = 16
_TITLE_TILE_PICKER_PALETTE_LABELS = (
    "BG #0", "BG #1", "BG #2", "BG #3",
    "SPR #0 主人公", "SPR #1 サラマンダー", "SPR #2 ガーゴイル", "SPR #3 ゴブリン",
)
_TITLE_FIXED_TEXT_SCRIPT_CPU = (0x953F, 0x955C, 0x9571)
_TITLE_FIXED_PUSH_TEXT_CPU = 0x955C
_TITLE_FIXED_VALUE_LINES = (
    (0x2880, "       0"),
    (0x288B, "  100000"),
    (0x2898, "47"),
)
_TITLE_PUSH_TEXT_PRESETS = (
    "PUSH START BUTTON",
    "SEEK THE KEY",
    "OPEN THE BOOK",
    "DO NOT DESPAIR",
    "TRY YOUR BRAIN",
)


class TitlePngColorGuardError(ValueError):
    def __init__(self, message, bad_blocks=None, image=None, display_top_y=None):
        super().__init__(message)
        self.bad_blocks = list(bad_blocks or [])
        self.image = image.copy() if image is not None else None
        self.display_top_y = display_top_y


def _ppu_pixel_to_display(x, y):
    return ((int(x) + _DISPLAY_SCROLL_X) % _IMG_W,
            (int(y) + _DISPLAY_SCROLL_Y) % _IMG_H)


def _display_pixel_to_ppu(x, y):
    return ((int(x) - _DISPLAY_SCROLL_X) % _IMG_W,
            (int(y) - _DISPLAY_SCROLL_Y) % _IMG_H)


class TitlePreviewLabel(QLabel):
    tile_hovered = pyqtSignal(int, int, int, int, int, int)
    tile_left = pyqtSignal()
    tile_clicked = pyqtSignal(int, int, int)
    attr_block_clicked = pyqtSignal(int, int)
    zoom_wheel = pyqtSignal(int)
    character_drag_start = pyqtSignal(int, int, int)
    character_drag_move = pyqtSignal(int, int)
    character_drag_end = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._zoom = 1
        self._grid = []
        self._chr_start = 0
        self._dragging_character = False
        self._last_drag_cell = None
        self.setMouseTracking(True)

    def set_title_context(self, zoom, grid, chr_start):
        self._zoom = max(1, int(zoom or 1))
        self._grid = list(grid or [])
        self._chr_start = int(chr_start or 0)

    def mouseMoveEvent(self, event):
        if not self._grid:
            self.tile_left.emit()
            super().mouseMoveEvent(event)
            return
        px = event.pos().x() // self._zoom
        py = event.pos().y() // self._zoom
        if px < 0 or py < 0 or px >= _IMG_W or py >= _IMG_H:
            self.tile_left.emit()
            super().mouseMoveEvent(event)
            return

        src_x, src_y = _display_pixel_to_ppu(px, py)
        col = src_x // 8
        row = src_y // 8
        cell = row * _NT_W + col
        if not (0 <= cell < len(self._grid)):
            self.tile_left.emit()
            super().mouseMoveEvent(event)
            return
        if self._dragging_character:
            if event.modifiers() & Qt.ControlModifier:
                cell = (row, col)
                if cell != self._last_drag_cell:
                    self._last_drag_cell = cell
                    self.character_drag_move.emit(row, col)
            else:
                self._dragging_character = False
                self._last_drag_cell = None
                self.character_drag_end.emit()
            super().mouseMoveEvent(event)
            return
        stream = int(self._grid[cell]) & 0xFF
        bank_tile = (_BG_BASE + stream) & 0x1FF
        file_start = self._chr_start + bank_tile * 0x10
        file_end = file_start + 0x0F
        self.tile_hovered.emit(row, col, stream, bank_tile, file_start, file_end)
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.tile_left.emit()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() in (Qt.LeftButton, Qt.RightButton) and self._grid:
            px = event.pos().x() // self._zoom
            py = event.pos().y() // self._zoom
            if 0 <= px < _IMG_W and 0 <= py < _IMG_H:
                src_x, src_y = _display_pixel_to_ppu(px, py)
                row = src_y // 8
                col = src_x // 8
                if event.button() == Qt.RightButton:
                    self.attr_block_clicked.emit((row // 2) * 2, (col // 2) * 2)
                elif event.modifiers() & Qt.ControlModifier:
                    self._dragging_character = True
                    self._last_drag_cell = (row, col)
                    self.character_drag_start.emit(row, col, int(event.modifiers()))
                else:
                    self.tile_clicked.emit(row, col, int(event.modifiers()))
                return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self._dragging_character:
            self._dragging_character = False
            self._last_drag_cell = None
            self.character_drag_end.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            self.zoom_wheel.emit(1 if event.angleDelta().y() > 0 else -1)
            event.accept()
            return
        super().wheelEvent(event)


class EndingPreviewLabel(QLabel):
    zoom_wheel = pyqtSignal(int)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            self.zoom_wheel.emit(1 if event.angleDelta().y() > 0 else -1)
            event.accept()
            return
        super().wheelEvent(event)


class ClearPreviewLabel(QLabel):
    zoom_wheel = pyqtSignal(int)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            self.zoom_wheel.emit(1 if event.angleDelta().y() > 0 else -1)
            event.accept()
            return
        super().wheelEvent(event)


class TitleChrTilePickerLabel(QLabel):
    tile_selected = pyqtSignal(int)
    tile_hovered = pyqtSignal(int)
    tile_left = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cell = NES_TILE_W * 4
        self._gap = 1
        self._cols = _TITLE_TILE_PICKER_COLS
        self._selected = 0
        self.setMouseTracking(True)
        self.setAlignment(Qt.AlignTop | Qt.AlignLeft)

    def set_tiles(self, rom_data, selected_stream=0, rgb=None, zoom=4, show_grid=True):
        self._selected = int(selected_stream) & 0xFF
        zoom = max(1, int(zoom))
        self._cell = NES_TILE_W * zoom
        self._gap = 1 if show_grid else 0
        cell = self._cell
        gap = self._gap
        cols = self._cols
        rows = 16
        img_w = cols * cell + (cols + 1) * gap
        img_h = rows * cell + (rows + 1) * gap
        img = QImage(img_w, img_h, QImage.Format_ARGB32)
        img.fill(QColor(40, 40, 40) if show_grid else QColor(0, 0, 0))
        chr_off = TS.chr_bank3_offset(rom_data)
        colors = rgb or [QColor(v, v, v).rgb() for v in _GRAY]
        for stream in range(256):
            tx = stream % cols
            ty = stream // cols
            ox = gap + tx * (cell + gap)
            oy = gap + ty * (cell + gap)
            pos = chr_off + (_BG_BASE + stream) * NES_GFX_TILE_BYTE_SIZE
            if pos + NES_GFX_TILE_BYTE_SIZE <= len(rom_data):
                tile = NesTile(bytes(rom_data[pos:pos + NES_GFX_TILE_BYTE_SIZE]))
                for py in range(8):
                    for px in range(8):
                        color = colors[tile.pixels[py][px] & 0x03]
                        if color is None:
                            continue
                        px0 = ox + px * zoom
                        py0 = oy + py * zoom
                        for dy in range(zoom):
                            for dx in range(zoom):
                                img.setPixel(px0 + dx, py0 + dy, color)
        painter = QPainter(img)
        for stream in range(256):
            tx = stream % cols
            ty = stream // cols
            ox = gap + tx * (cell + gap)
            oy = gap + ty * (cell + gap)
            if stream == self._selected:
                pen = QPen(QColor(255, 40, 40))
                pen.setWidth(2)
                painter.setPen(pen)
                painter.drawRect(ox, oy, max(0, cell - 1), max(0, cell - 1))
        painter.end()
        self.setPixmap(QPixmap.fromImage(img))
        self.setFixedSize(img.size())

    def _stream_at_pos(self, pos):
        stride = self._cell + self._gap
        if self._cols <= 0 or self._cell <= 0 or stride <= 0:
            return None
        x = int(pos.x()) - self._gap
        y = int(pos.y()) - self._gap
        if x < 0 or y < 0:
            return None
        col = x // stride
        row = y // stride
        local_x = x % stride
        local_y = y % stride
        idx = int(row * self._cols + col)
        if (
            col < 0 or col >= self._cols
            or local_x >= self._cell or local_y >= self._cell
            or idx < 0 or idx >= 256
        ):
            return None
        return idx

    def mouseMoveEvent(self, event):
        idx = self._stream_at_pos(event.pos())
        if idx is None:
            self.tile_left.emit()
        else:
            self.tile_hovered.emit(int(idx))
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.tile_left.emit()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            idx = self._stream_at_pos(event.pos())
            if idx is not None:
                self.tile_selected.emit(int(idx))
                event.accept()
                return
        super().mousePressEvent(event)


class HexSpinBox(QSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDisplayIntegerBase(16)

    def textFromValue(self, value):
        return f"0x{int(value):03X}"

    def valueFromText(self, text):
        s = str(text).strip().lower()
        if s.startswith("0x"):
            s = s[2:]
        return int(s or "0", 16)


def _encode_tile_2bpp(pixels) -> bytes:
    out = bytearray(16)
    for y in range(8):
        lo = 0
        hi = 0
        row = pixels[y]
        for x in range(8):
            bit = 7 - x
            value = int(row[x]) & 0x03
            lo |= (value & 1) << bit
            hi |= ((value >> 1) & 1) << bit
        out[y] = lo
        out[y + 8] = hi
    return bytes(out)


class TitleTileCanvas(QWidget):
    pixel_changed = pyqtSignal(int, int, int)
    pixel_picked = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._zoom = 28
        self._brush = 1
        self._pixels = [[0 for _ in range(8)] for _ in range(8)]
        self._colors = [
            QColor(40, 40, 40),
            QColor(110, 110, 110),
            QColor(180, 180, 180),
            QColor(245, 245, 245),
        ]
        self.setMouseTracking(True)
        self._update_fixed_size()

    def _update_fixed_size(self):
        size = 8 * self._zoom + 1
        self.setMinimumSize(size, size)
        self.setMaximumSize(size, size)

    def set_zoom(self, zoom):
        self._zoom = max(16, min(48, int(zoom)))
        self._update_fixed_size()
        self.update()

    def set_brush(self, value):
        self._brush = max(0, min(3, int(value)))

    def set_colors(self, colors):
        qcolors = []
        for rgb in list(colors or [])[:4]:
            qcolors.append(QColor(*rgb))
        while len(qcolors) < 4:
            qcolors.append(QColor(0, 0, 0))
        self._colors = qcolors
        self.update()

    def set_pixels(self, pixels):
        out = [[0 for _ in range(8)] for _ in range(8)]
        for y, row in enumerate(list(pixels or [])[:8]):
            for x, value in enumerate(list(row or [])[:8]):
                out[y][x] = int(value) & 0x03
        self._pixels = out
        self.update()

    def pixels(self):
        return [list(row) for row in self._pixels]

    def _event_cell(self, event):
        x = event.pos().x() // self._zoom
        y = event.pos().y() // self._zoom
        if 0 <= x < 8 and 0 <= y < 8:
            return int(x), int(y)
        return None

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
        if event.button() == Qt.LeftButton and event.modifiers() & Qt.AltModifier:
            self.pixel_picked.emit(self._pixels[y][x] & 3)
            event.accept()
            return
        if event.button() in (Qt.LeftButton, Qt.RightButton):
            self._paint_at_event(event)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & (Qt.LeftButton | Qt.RightButton):
            self._paint_at_event(event)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        cell = self._zoom
        for y in range(8):
            for x in range(8):
                painter.fillRect(
                    x * cell,
                    y * cell,
                    cell,
                    cell,
                    self._colors[self._pixels[y][x] & 3],
                )
        painter.setPen(QPen(QColor(40, 40, 40), 1))
        for i in range(9):
            pos = i * cell
            painter.drawLine(pos, 0, pos, 8 * cell)
            painter.drawLine(0, pos, 8 * cell, pos)
        painter.end()


class TitleTileEditorDialog(QDialog):
    def __init__(self, pixels, colors, title, info_text, parent=None,
                 live_callback=None):
        super().__init__(parent)
        if parent is not None:
            self.setFont(parent.font())
        self.setWindowTitle(title)
        self._pixels = [list(row) for row in pixels]
        self._initial_pixels = [list(row) for row in pixels]
        self._live_callback = live_callback
        self._changed = False

        root = QVBoxLayout(self)
        info = QLabel(info_text)
        info.setWordWrap(True)
        root.addWidget(info)

        top = QHBoxLayout()
        top.addWidget(QLabel("Zoom:"))
        self._zoom = QSpinBox()
        self._zoom.setRange(16, 48)
        self._zoom.setValue(28)
        self._zoom.setSuffix(" x")
        top.addWidget(self._zoom)
        top.addStretch()
        root.addLayout(top)

        body = QHBoxLayout()
        self._canvas = TitleTileCanvas(self)
        self._canvas.set_colors(colors)
        self._canvas.set_pixels(self._pixels)
        self._canvas.pixel_changed.connect(self._on_pixel_changed)
        self._canvas.pixel_picked.connect(self._set_brush)
        self._zoom.valueChanged.connect(self._canvas.set_zoom)
        body.addWidget(self._canvas, 0, Qt.AlignTop)

        side = QVBoxLayout()
        side.addWidget(QLabel(t("title_screen.tile_editor.pen", "ペン:")))
        brush_row = QHBoxLayout()
        self._brush_group = QButtonGroup(self)
        self._brush_buttons = []
        for idx in range(4):
            btn = QPushButton(str(idx))
            btn.setCheckable(True)
            btn.setMinimumSize(42, 34)
            btn.setToolTip(
                t(
                    "title_screen.tile_editor.brush.tooltip",
                    "パレットインデックス {index} で描く。Alt+クリックでスポイト。",
                ).format(index=idx))
            btn.clicked.connect(lambda _checked=False, value=idx: self._set_brush(value))
            self._brush_group.addButton(btn, idx)
            self._brush_buttons.append(btn)
            brush_row.addWidget(btn)
        self._brush_buttons[1].setChecked(True)
        side.addLayout(brush_row)

        clear_btn = QPushButton(t("common.clear", "クリア"))
        clear_btn.setToolTip(
            t(
                "title_screen.tile_editor.clear.tooltip",
                "8x8タイルをパレットインデックス0で消去",
            )
        )
        clear_btn.clicked.connect(self._clear)
        side.addWidget(clear_btn)
        reload_btn = QPushButton(t("title_screen.revert_initial", "開いた時点へ戻す"))
        reload_btn.clicked.connect(self._restore_initial)
        side.addWidget(reload_btn)
        side.addStretch()
        body.addLayout(side, 1)
        root.addLayout(body)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self._on_cancel)
        root.addWidget(bb)

    def pixels(self):
        return [list(row) for row in self._pixels]

    def _set_brush(self, value):
        value = max(0, min(3, int(value)))
        self._canvas.set_brush(value)
        if 0 <= value < len(self._brush_buttons):
            self._brush_buttons[value].setChecked(True)

    def _apply_live(self):
        if self._live_callback is not None:
            self._live_callback(self.pixels())

    def _on_pixel_changed(self, x, y, value):
        self._pixels[y][x] = int(value) & 0x03
        self._changed = True
        self._apply_live()

    def _set_pixels(self, pixels):
        self._pixels = [list(row) for row in pixels]
        self._canvas.set_pixels(self._pixels)
        self._changed = True
        self._apply_live()

    def _clear(self):
        self._set_pixels([[0 for _ in range(8)] for _ in range(8)])

    def _restore_initial(self):
        self._set_pixels([list(row) for row in self._initial_pixels])

    def _on_cancel(self):
        if self._changed:
            self._pixels = [list(row) for row in self._initial_pixels]
            self._apply_live()
        self.reject()


class TitlePaletteDialog(QDialog):
    def __init__(self, colors, parent=None, apply_callback=None,
                 group_select_enabled=False, current_group=0,
                 group_callback=None, live_apply=False):
        super().__init__(parent)
        self.setWindowTitle(t("title_screen.palette_dialog.title", "タイトル色編集"))
        self._initial_colors = [c & 0x3F for c in colors]
        self._colors = [c & 0x3F for c in colors]
        self._apply_callback = apply_callback
        self._group_select_enabled = bool(group_select_enabled)
        self._group_callback = group_callback
        self._live_apply = bool(live_apply)
        self._current_group = int(current_group) & 0x03
        self._initial_group = self._current_group
        self._sel = 0
        self._swatches = []
        self._color_buttons = []
        self._group_radios = []

        root = QVBoxLayout(self)
        note = QLabel(
            t(
                "title_screen.palette_dialog.note",
                "タイトル画面のBGパレット16色を編集します。"
                "各値はROMに書かれるNES色番号($00-$3F)です。",
            )
        )
        note.setWordWrap(True)
        root.addWidget(note)

        g = QGroupBox(t("title_screen.palette.group", "タイトルパレット $3F00-$3F0F"))
        gl = QGridLayout(g)
        labels = [
            "$3F00", "$3F01", "$3F02", "$3F03",
            "$3F04", "$3F05", "$3F06", "$3F07",
            "$3F08", "$3F09", "$3F0A", "$3F0B",
            "$3F0C", "$3F0D", "$3F0E", "$3F0F",
        ]
        for group in range(4):
            rb = QRadioButton(
                t("title_screen.palette.index", "パレット {index}").format(index=group)
            )
            rb.setChecked(group == self._current_group)
            rb.setEnabled(self._group_select_enabled)
            rb.toggled.connect(lambda checked, idx=group: self._select_group(idx, checked))
            self._group_radios.append(rb)
            gl.addWidget(rb, group * 2, 0)
        for i in range(16):
            gl.addWidget(QLabel(labels[i]), (i // 4) * 2, (i % 4) + 1)
            b = QPushButton()
            b.setFixedSize(72, 30)
            b.clicked.connect(lambda _, idx=i: self._select_slot(idx))
            self._swatches.append(b)
            gl.addWidget(b, (i // 4) * 2 + 1, (i % 4) + 1)
        root.addWidget(g)

        picker = QGroupBox("NES 64 Colors")
        pg = QGridLayout(picker)
        for i in range(64):
            b = QPushButton(f"{i:02X}")
            b.setFixedSize(38, 28)
            b.clicked.connect(lambda _, idx=i: self._set_selected_color(idx))
            self._color_buttons.append(b)
            pg.addWidget(b, i // 16, i % 16)
        root.addWidget(picker)

        bb = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
            | QDialogButtonBox.Apply)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self._on_cancel)
        bb.button(QDialogButtonBox.Apply).clicked.connect(self._on_apply)
        root.addWidget(bb)
        self._refresh_all()

    def colors(self):
        return list(self._colors)

    def selected_group(self):
        return self._current_group

    @staticmethod
    def _button_style(nes_idx, selected=False):
        r, g, b = NES_COLORS[nes_idx & 0x3F]
        border = "3px solid #ff0000" if selected else "1px solid #333"
        fg = "#fff" if (r + g + b) < 300 else "#000"
        return (
            f"background: rgb({r},{g},{b}); color: {fg}; "
            f"border: {border}; font-weight: bold;"
        )

    def _select_slot(self, idx):
        self._sel = idx
        self._refresh_all()

    def _select_group(self, group, checked):
        if not checked:
            return
        self._current_group = int(group) & 0x03
        if self._group_callback is not None:
            self._group_callback(self._current_group)

    def _set_selected_color(self, nes_idx):
        self._colors[self._sel] = nes_idx & 0x3F
        self._refresh_all()
        if self._live_apply:
            self._on_apply()

    def _refresh_all(self):
        for i, b in enumerate(self._swatches):
            val = self._colors[i] & 0x3F
            b.setText(f"${val:02X}")
            b.setToolTip(f"slot {i} = ${val:02X}")
            b.setStyleSheet(self._button_style(val, i == self._sel))
        for i, b in enumerate(self._color_buttons):
            b.setStyleSheet(self._button_style(i, self._colors[self._sel] == i))

    def _on_apply(self):
        if self._apply_callback is not None:
            try:
                self._apply_callback(self.colors())
            except Exception as e:
                QMessageBox.critical(
                    self,
                    t("title_screen.palette_panel.change_unavailable", "タイトル色変更不可"),
                    t(
                        "title_screen.palette_panel.write_failed",
                        "タイトルパレットを書き換えられませんでした:\n{error}",
                    ).format(error=f"{type(e).__name__}: {e}"))

    def _on_cancel(self):
        if self._apply_callback is not None:
            try:
                self._apply_callback(list(self._initial_colors))
            except Exception:
                pass
        if self._group_callback is not None:
            try:
                self._group_callback(self._initial_group)
            except Exception:
                pass
        self.reject()


class TitleCharacterGridLabel(QLabel):
    frame_clicked = pyqtSignal(int)
    frame_double_clicked = pyqtSignal(int)

    def __init__(self, item_count, cols, cell_w, cell_h, gap, parent=None):
        super().__init__(parent)
        self._item_count = int(item_count)
        self._cols = int(cols)
        self._cell_w = int(cell_w)
        self._cell_h = int(cell_h)
        self._gap = int(gap)

    def _index_at(self, pos):
        stride_w = self._cell_w + self._gap
        stride_h = self._cell_h + self._gap
        x = pos.x() - self._gap
        y = pos.y() - self._gap
        if x < 0 or y < 0 or stride_w <= 0 or stride_h <= 0:
            return None
        col = x // stride_w
        row = y // stride_h
        local_x = x % stride_w
        local_y = y % stride_h
        if col >= self._cols or local_x >= self._cell_w or local_y >= self._cell_h:
            return None
        idx = int(row * self._cols + col)
        if 0 <= idx < self._item_count:
            return idx
        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            idx = self._index_at(event.pos())
            if idx is not None:
                self.frame_clicked.emit(idx)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            idx = self._index_at(event.pos())
            if idx is not None:
                self.frame_double_clicked.emit(idx)
                event.accept()
                return
        super().mouseDoubleClickEvent(event)


class TitleCharacterPickerDialog(QDialog):
    def __init__(self, rom_data, parent=None):
        super().__init__(parent)
        if parent is not None:
            self.setFont(parent.font())
        self._rom = rom_data
        self._items = self._dedupe_romframe_items(self._romframe_items())
        self._selected_index = 0
        self.setWindowTitle(
            t("title_screen.character_picker.title", "タイトルキャラクター追加")
        )
        self.resize(760, 560)

        root = QVBoxLayout(self)
        prow = QHBoxLayout()
        prow.addWidget(QLabel(t("title_screen.label.color", "色:")))
        self._palette = QComboBox()
        for i in range(4):
            self._palette.addItem(f"SPR {i}", i)
        self._palette.currentIndexChanged.connect(self._refresh_all)
        prow.addWidget(self._palette)
        self._selection_label = QLabel("")
        prow.addWidget(self._selection_label, 1)
        prow.addStretch()
        root.addLayout(prow)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(False)
        root.addWidget(self._scroll, 1)

        note = QLabel(
            t(
                "title_screen.character_picker.note",
                "一覧をクリックして選択、ダブルクリックで確定。OK後、"
                "タイトルプレビューをクリックして配置します。最大 {max} 体。",
            ).format(max=TS.title_character_max())
        )
        note.setWordWrap(True)
        root.addWidget(note)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        root.addWidget(bb)
        self._refresh_all()

    def selected_character(self):
        if not self._items:
            raise ValueError("ROMフレームが見つかりません。")
        idx = max(0, min(len(self._items) - 1, int(self._selected_index)))
        g, s, fi, t1, t2, attr = self._items[idx]
        return {
            "group": g,
            "state": s,
            "frame": fi,
            "tile1": t1,
            "tile2": t2,
            "attr": attr,
            "palette": int(self._palette.currentData()) & 0x03,
        }

    def _sprite_palette_qcolors(self, sprite_palette_no):
        off = _SPRITE_PALETTE_OFFSET + (4 + (int(sprite_palette_no) & 3)) * 4
        vals = [0x00, 0x10, 0x30]
        if off + 3 <= len(self._rom):
            vals = [self._rom[off + i] & 0x3F for i in range(3)]
        return [None] + [QColor(*NES_COLORS[v & 0x3F]) for v in vals]

    def _draw_8x16(self, painter, zoom, ox, oy, tile_byte, oam_attr):
        pal = self._sprite_palette_qcolors(oam_attr & 0x03)
        hflip = bool(oam_attr & 0x40)
        vflip = bool(oam_attr & 0x80)
        half = 256 if (int(tile_byte) & 1) else 0
        top = half + (int(tile_byte) & 0xFE)
        chr_off = TS.chr_bank3_offset(self._rom)
        for sub, tile_no in ((0, top), (1, top + 1)):
            pos = chr_off + tile_no * NES_GFX_TILE_BYTE_SIZE
            if pos + NES_GFX_TILE_BYTE_SIZE > len(self._rom):
                continue
            tile = NesTile(bytes(self._rom[pos:pos + NES_GFX_TILE_BYTE_SIZE]))
            for py in range(8):
                for px in range(8):
                    pi = tile.pixels[py][px] & 0x03
                    color = pal[pi]
                    if color is None:
                        continue
                    dx = 7 - px if hflip else px
                    sy = sub * 8 + py
                    dy = 15 - sy if vflip else sy
                    painter.fillRect(
                        ox + dx * zoom, oy + dy * zoom,
                        zoom, zoom, color)

    def _draw_frame_to_image(self, img, zoom, ox, oy, tile1, tile2, frame_attr,
                             palette):
        entry = TS.title_character_entry(0, 0, tile1, tile2, frame_attr, palette)
        attr1, attr2 = TS.title_character_oam_attrs(entry[5])
        painter = QPainter(img)
        self._draw_8x16(painter, zoom, ox, oy, entry[3], attr1)
        self._draw_8x16(painter, zoom, ox + 8 * zoom, oy, entry[4], attr2)
        painter.end()

    def _refresh_all(self, *_):
        old_v = self._scroll.verticalScrollBar().value() \
            if getattr(self, "_scroll", None) is not None else 0
        old_h = self._scroll.horizontalScrollBar().value() \
            if getattr(self, "_scroll", None) is not None else 0
        if not self._items:
            lbl = QLabel(
                t("title_screen.character_picker.no_frames", "ROMフレームが見つかりません。")
            )
            lbl.setAlignment(Qt.AlignCenter)
            self._scroll.setWidget(lbl)
            return
        cols = 10
        zoom = 3
        cell_w = 16 * zoom + 12
        cell_h = 16 * zoom + 18
        gap = 6
        rows = (len(self._items) + cols - 1) // cols
        img = QImage(cols * (cell_w + gap) + gap,
                     rows * (cell_h + gap) + gap,
                     QImage.Format_ARGB32)
        img.fill(QColor(28, 28, 28))
        pal = int(self._palette.currentData()) & 0x03
        for i, (g, s, fi, t1, t2, attr) in enumerate(self._items):
            ox = gap + (i % cols) * (cell_w + gap) + 6
            oy = gap + (i // cols) * (cell_h + gap) + 4
            self._draw_frame_to_image(img, zoom, ox, oy, t1, t2, attr, pal)
        painter = QPainter(img)
        painter.setPen(QColor(190, 190, 190))
        for i, (g, s, fi, _t1, _t2, _attr) in enumerate(self._items):
            x = gap + (i % cols) * (cell_w + gap)
            y = gap + (i // cols) * (cell_h + gap)
            painter.drawText(x + 3, y + cell_h - 4, f"g{g:02X}s{s:02X}f{fi}")
            if i == self._selected_index:
                pen = QPen(QColor(255, 230, 60), 3)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(x, y, cell_w - 1, cell_h - 1)
                painter.setPen(QColor(190, 190, 190))
        painter.end()
        lbl = TitleCharacterGridLabel(len(self._items), cols, cell_w, cell_h, gap)
        lbl.setPixmap(QPixmap.fromImage(img))
        lbl.frame_clicked.connect(self._select_index)
        lbl.frame_double_clicked.connect(self._accept_index)
        self._scroll.setWidget(lbl)
        self._scroll.verticalScrollBar().setValue(old_v)
        self._scroll.horizontalScrollBar().setValue(old_h)
        self._refresh_selection_label()

    def _refresh_selection_label(self):
        if not self._items:
            self._selection_label.setText("")
            return
        g, s, fi, t1, t2, attr = self._items[self._selected_index]
        self._selection_label.setText(
            t(
                "title_screen.character_picker.selection",
                "選択: g{group:02X} s{state:02X} f{frame} / "
                "tile ${tile1:02X},${tile2:02X} attr ${attr:02X}",
            ).format(group=g, state=s, frame=fi, tile1=t1, tile2=t2, attr=attr))

    def _select_index(self, index):
        if not (0 <= int(index) < len(self._items)):
            return
        self._selected_index = int(index)
        self._refresh_all()

    def _accept_index(self, index):
        self._select_index(index)
        self.accept()

    @staticmethod
    def _cf(cpu):
        return 0x10 + (cpu - 0x8000)

    @staticmethod
    def _romframe_items_for_rom(rom):
        cf = TitleCharacterPickerDialog._cf
        if len(rom) <= cf(0xDA00):
            return []
        gptrs = [
            rom[cf(0xD0E8 + i * 2)] | (rom[cf(0xD0E8 + i * 2 + 1)] << 8)
            for i in range(32)
        ]
        uniq = sorted(set(gptrs))
        bound = {}
        for i, p in enumerate(uniq):
            bound[p] = uniq[i + 1] if i + 1 < len(uniq) else 0xD600
        items = []
        for g in range(32):
            base = gptrs[g]
            nstates = min(max(0, (bound.get(base, base + 4) - base) // 4), 64)
            for s in range(nstates):
                e = base + s * 4
                phase = rom[cf(e)]
                ri = rom[cf(e + 1)]
                ptr = rom[cf(e + 2)] | (rom[cf(e + 3)] << 8)
                frames = (phase & 0x0F) + 1
                if ri & 1:
                    if not (0xD000 <= ptr <= 0xD600):
                        continue
                    final = rom[cf(ptr)] | (rom[cf(ptr + 1)] << 8)
                else:
                    final = ptr
                if not (0xD600 <= final < 0xDA00):
                    continue
                for fi in range(min(frames, 8)):
                    a = final + fi * 3
                    if not (0xD600 <= a < 0xDA00):
                        break
                    items.append((g, s, fi, rom[cf(a)],
                                  rom[cf(a + 1)], rom[cf(a + 2)]))
        return items

    def _romframe_items(self):
        return self._romframe_items_for_rom(self._rom)

    @staticmethod
    def _dedupe_romframe_items(items):
        seen = set()
        out = []
        for item in items:
            key = item[3], item[4], item[5]
            if key in seen:
                continue
            seen.add(key)
            out.append(item)
        return out


class TitlePngColorGuardDialog(QDialog):
    def __init__(self, error, parent=None):
        super().__init__(parent)
        if parent is not None:
            self.setFont(parent.font())
        self.setWindowTitle(t("title_screen.png_guard.title", "PNG取り込み不可"))
        root = QVBoxLayout(self)
        msg = QLabel(str(error))
        msg.setWordWrap(True)
        root.addWidget(msg)

        grid = QGridLayout()
        image = error.image
        for i, block in enumerate(error.bad_blocks[:12]):
            bx, by, n, sx, sy = block
            cell = QVBoxLayout()
            title = QLabel(
                t("title_screen.png_guard.block", "attr ({x},{y}) / {count}色").format(
                    x=bx,
                    y=by,
                    count=n,
                )
            )
            cell.addWidget(title)
            preview = QLabel()
            preview.setFixedSize(96, 96)
            preview.setAlignment(Qt.AlignCenter)
            preview.setStyleSheet("background:#111; border:1px solid #555;")
            if image is not None:
                tile = image.copy(sx, sy, 16, 16)
                pm = QPixmap.fromImage(tile).scaled(
                    96, 96, Qt.KeepAspectRatio, Qt.FastTransformation)
                preview.setPixmap(pm)
            cell.addWidget(preview)
            wrap = QWidget()
            wrap.setLayout(cell)
            grid.addWidget(wrap, i // 4, i % 4)
        root.addLayout(grid)

        bb = QDialogButtonBox(QDialogButtonBox.Ok)
        bb.accepted.connect(self.accept)
        root.addWidget(bb)


class TitleScreenDialog(QDialog):
    def __init__(self, rom_data: bytearray, parent=None, app_config=None):
        super().__init__(parent)
        if parent is not None:
            self.setFont(parent.font())
        self.setWindowTitle(t("title_screen_dialog.title", "タイトル画面編集"))
        self._rom = rom_data
        self._app_config = app_config
        # 開いた時点の ROM 全体を退避 (キャンセル復元用)
        self._snap = bytes(rom_data)
        self._changed = False
        self.resize(620, 760)

        self._region = TS.region_of(rom_data)   # 非対応は例外 (呼び側catch)

        root = QVBoxLayout(self)
        tabs = QTabWidget()
        root.addWidget(tabs, 1)
        title_tab = QWidget()
        title_root = QVBoxLayout(title_tab)
        tabs.addTab(title_tab, t("title_screen_dialog.tab.title", "タイトル"))
        head = QLabel(
            t(
                "title_screen_dialog.title_tab.info_html",
                "タイトル画面の<b>配置(nametable)・色区分(attribute)・"
                "絵(CHR bank3)・文字・キャラクター・パレット</b>を編集します。"
                "<br>下のプレビューではCHRタイルと色区分を確認でき、"
                "上部ロゴ領域は画像として保存・読み込みできます。",
            ))
        head.setWordWrap(True)
        title_root.addWidget(head)

        self._info = QLabel()
        title_root.addWidget(self._info)

        # 倍率
        zr = QHBoxLayout()
        zr.addWidget(QLabel(t("title_screen_dialog.zoom.label", "表示倍率:")))
        self._zoom = QComboBox()
        for z in (1, 2, 3, 4, 5, 6, 7, 8):
            self._zoom.addItem(f"x{z}", z)
        self._zoom.setMinimumWidth(88)
        self._zoom.setMinimumHeight(26)
        saved_zoom = 2
        if isinstance(self._app_config, dict):
            try:
                saved_zoom = int(self._app_config.get("title_screen_dlg_zoom", 2))
            except Exception:
                saved_zoom = 2
        self._zoom.setCurrentIndex(max(0, self._zoom.findData(saved_zoom)))
        self._zoom.currentIndexChanged.connect(self._refresh)
        zr.addWidget(self._zoom)
        zr.addSpacing(16)
        zr.addWidget(QLabel(t("title_screen_dialog.bank_offset.label", "bank内:")))
        self._highlight_tile = HexSpinBox()
        self._highlight_tile.setRange(0x100, 0x1FF)
        self._highlight_tile.setSingleStep(1)
        self._highlight_tile.setValue(0x130)
        self._highlight_tile.setMinimumWidth(98)
        self._highlight_tile.setMinimumHeight(26)
        self._highlight_tile.setToolTip(t("title_screen_dialog.highlight_tile.tooltip", "指定したCHR bank3内タイルをタイトルプレビュー上でピンク表示"))
        self._highlight_tile.valueChanged.connect(self._refresh)
        zr.addWidget(self._highlight_tile)
        zr.addSpacing(16)
        zr.addWidget(QLabel(t("title_screen_dialog.color_group_overlay.label", "色グループ表示:")))
        self._group_overlay = QComboBox()
        self._group_overlay.addItem(t("common.none", "なし"), -1)
        for i in range(4):
            self._group_overlay.addItem(str(i), i)
        self._group_overlay.setMinimumWidth(86)
        self._group_overlay.setMinimumHeight(26)
        self._group_overlay.setToolTip(t("title_screen_dialog.color_group_overlay.tooltip", "選択した色グループに属する16x16区画をプレビュー上で表示"))
        self._group_overlay.currentIndexChanged.connect(self._refresh)
        zr.addWidget(self._group_overlay)
        zr.addSpacing(10)
        self._group_from = QComboBox()
        self._group_to = QComboBox()
        for i in range(4):
            self._group_from.addItem(str(i), i)
            self._group_to.addItem(str(i), i)
        self._group_from.setMinimumWidth(54)
        self._group_to.setMinimumWidth(54)
        self._group_from.setMinimumHeight(26)
        self._group_to.setMinimumHeight(26)
        self._group_from.setToolTip(t("title_screen_dialog.color_group_from.tooltip", "一括置換元の色グループ"))
        self._group_to.setToolTip(t("title_screen_dialog.color_group_to.tooltip", "一括置換先の色グループ"))
        zr.addWidget(self._group_from)
        zr.addWidget(QLabel("→"))
        zr.addWidget(self._group_to)
        b_group_replace = QPushButton(t("title_screen_dialog.color_group_replace.button", "色G置換"))
        b_group_replace.setMinimumHeight(26)
        b_group_replace.setToolTip(t("title_screen_dialog.color_group_replace.tooltip", "選択した色グループを使う16x16区画を、別の色グループへ一括変更"))
        b_group_replace.clicked.connect(self._on_replace_attr_group)
        zr.addWidget(b_group_replace)
        zr.addStretch()
        title_root.addLayout(zr)

        # プレビュー (スクロール)
        self._canvas = TitlePreviewLabel()
        self._canvas.setAlignment(Qt.AlignCenter)
        self._canvas.setStyleSheet("background:#444;")
        self._canvas.setToolTip(
            t("title_screen_dialog.canvas.tooltip", "左クリック: 8x8 CHRタイル編集 / 右クリック: 16x16色グループ変更"))
        self._canvas.tile_hovered.connect(self._on_preview_tile_hovered)
        self._canvas.tile_left.connect(self._restore_preview_status)
        self._canvas.tile_clicked.connect(self._on_preview_tile_clicked)
        self._canvas.attr_block_clicked.connect(self._on_attr_block_clicked)
        self._canvas.zoom_wheel.connect(self._on_canvas_zoom_wheel)
        self._canvas.character_drag_start.connect(self._on_title_character_drag_start)
        self._canvas.character_drag_move.connect(self._on_title_character_drag_move)
        self._canvas.character_drag_end.connect(self._on_title_character_drag_end)
        sa = QScrollArea()
        sa.setWidgetResizable(True)
        wrap = QWidget()
        wl = QHBoxLayout(wrap)
        wl.addWidget(self._canvas, 0, Qt.AlignTop | Qt.AlignLeft)
        self._side_panel = QWidget()
        self._side_panel.setMinimumWidth(420)
        self._side_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._side_panel.setVisible(False)
        self._side_layout = QVBoxLayout(self._side_panel)
        wl.addWidget(self._side_panel, 1)
        sa.setWidget(wrap)
        title_root.addWidget(sa, 1)
        self._preview_status = QLabel("")
        title_root.addWidget(self._preview_status)
        self._pending_stamp = None
        self._pending_title_character = None
        self._pending_title_tile_stream = None
        self._selected_title_character_slot = None
        self._drag_title_character_slot = None

        # 操作ボタン
        br = QHBoxLayout()
        b_save_top = QPushButton(t("title_screen_dialog.save_top_png.button", "Top PNG保存..."))
        b_save_top.setToolTip(t("title_screen_dialog.save_top_png.tooltip", "タイトル上部ロゴ領域だけを256x64/4階調PNGで保存"))
        b_save_top.clicked.connect(self._on_save_top_image)
        br.addWidget(b_save_top)
        b_png_top = QPushButton(t("title_screen_dialog.load_top_png.button", "Top PNG読み込み..."))
        b_png_top.setToolTip(
            t(
                "title_screen_dialog.load_top_png.tooltip",
                "上部ロゴ領域のPNG/BMP/JPEGを読み込みます。"
                "256x64を超える画像は縮小し、4色へ減色します。",
            )
        )
        b_png_top.clicked.connect(self._on_import_top_png)
        br.addWidget(b_png_top)
        b_text = QPushButton(t("title_screen_dialog.text_edit.button", "文字編集..."))
        b_text.setToolTip(
            t(
                "title_screen_dialog.text_edit.tooltip",
                "タイトル中央付近の追加文字とPUSH START位置の固定文字を編集します。"
                "A-Z / 0-9 / スペース / , . \" が使えます。"
                "入力中にプレビューへ反映します。",
            ))
        b_text.clicked.connect(self._on_edit_title_texts)
        br.addWidget(b_text)
        b_tile_place = QPushButton(t("title_screen_dialog.tile_place.button", "タイル配置..."))
        b_tile_place.setToolTip(
            t("title_screen_dialog.tile_place.tooltip", "CHR bank3の8x8タイルを選び、タイトル背景の32x30マスへ配置します。"))
        b_tile_place.clicked.connect(self._on_show_title_tile_picker)
        br.addWidget(b_tile_place)
        b_char = QPushButton(t("title_screen_dialog.character.button", "キャラクター..."))
        b_char.setToolTip(
            t(
                "title_screen_dialog.character.tooltip",
                "$D0E8由来の16x16キャラを選び、タイトル上へ最大{count}体配置します。",
            ).format(count=TS.title_character_max()))
        b_char.clicked.connect(self._on_pick_title_character)
        br.addWidget(b_char)
        b_pal = QPushButton(t("title_screen_dialog.palette.button", "パレット変更..."))
        b_pal.setToolTip(t("title_screen_dialog.palette.tooltip", "タイトル画面のBGパレット16色($3F00-$3F0F)を編集します。"))
        b_pal.clicked.connect(self._on_edit_title_palette)
        br.addWidget(b_pal)
        b_revert = QPushButton(t("title_screen_dialog.revert.button", "変更を取り消す"))
        b_revert.setToolTip(t("title_screen_dialog.revert.tooltip", "このダイアログを開いた時点の ROM に戻す"))
        b_revert.clicked.connect(self._on_revert)
        br.addWidget(b_revert)
        title_root.addLayout(br)

        tabs.addTab(self._build_ending_text_tab(), t("title_screen_dialog.tab.ending", "エンディング"))
        tabs.addTab(self._build_clear_screen_tab(), t("title_screen_dialog.tab.clear_screen", "クリア画面"))

        bb = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
            | QDialogButtonBox.Apply)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self._on_cancel)
        bb.button(QDialogButtonBox.Apply).clicked.connect(self._on_apply)
        root.addWidget(bb)

        self._refresh()
        self._show_title_palette_panel()
        restore_dialog_geometry(self, self._app_config, "title_screen_dlg")

    def _build_clear_screen_tab(self):
        tab = QWidget()
        root = QVBoxLayout(tab)
        info = QLabel(
            t(
                "title_screen_dialog.clear_tab.info",
                "ステージクリア後の『おめでとう画面』に関係する設定です。"
                "ここでは既存のクリア画面キャラ差し替えとメッセージ編集を扱います。"
                "プレビューは実機エミュレーションではなく、文字位置確認用の簡易表示です。",
            ))
        info.setWordWrap(True)
        root.addWidget(info)

        body = QHBoxLayout()
        preview_col = QVBoxLayout()
        edit_col = QVBoxLayout()
        body.addLayout(preview_col, 3)
        body.addLayout(edit_col, 2)

        self._clear_preview = ClearPreviewLabel()
        self._clear_preview.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self._clear_preview.setStyleSheet("background:#000;")
        self._clear_preview.zoom_wheel.connect(self._on_clear_zoom_wheel)
        self._clear_zoom = 3
        clear_scroll = QScrollArea()
        clear_scroll.setWidgetResizable(True)
        clear_wrap = QWidget()
        clear_wrap_lay = QHBoxLayout(clear_wrap)
        clear_wrap_lay.addWidget(self._clear_preview, 0, Qt.AlignTop | Qt.AlignLeft)
        clear_wrap_lay.addStretch()
        clear_scroll.setWidget(clear_wrap)
        preview_col.addWidget(clear_scroll, 1)

        msg_group = QGroupBox(t("title_screen_dialog.clear_message.group", "クリア画面メッセージ"))
        msg_root = QVBoxLayout(msg_group)
        msg_hint = QLabel(
            t(
                "title_screen_dialog.clear_message.hint",
                "THANK YOU DANA / YOU RELEASED THIS ROOM / TRY NEXT ROOM の3行を編集します。"
                "英大文字 A-Z とスペースのみ、同字数置換です。",
            ))
        msg_hint.setWordWrap(True)
        msg_hint.setStyleSheet("color:#888; font-size:11px;")
        msg_root.addWidget(msg_hint)
        msg_grid = QGridLayout()
        msg_grid.setHorizontalSpacing(8)
        msg_grid.setVerticalSpacing(6)
        msg_grid.addWidget(QLabel(t("title_screen_dialog.clear_message.column.line", "行")), 0, 0)
        msg_grid.addWidget(QLabel(t("title_screen_dialog.clear_message.column.text", "文字")), 0, 1)
        msg_grid.addWidget(QLabel(t("title_screen_dialog.clear_message.column.count", "字数")), 0, 2)
        self._clear_message_edits = []
        self._clear_message_status = QLabel("")
        try:
            rows = CM.read_messages(self._rom)
            rx = QRegExpValidator(QRegExp("[A-Za-z ]*"))
            for i, (name, cur, count, _orig) in enumerate(rows):
                msg_grid.addWidget(QLabel(name), i + 1, 0)
                le = QLineEdit(cur.rstrip())
                le.setMaxLength(count)
                le.setValidator(rx)
                cnt = QLabel()
                cnt.setMinimumWidth(56)
                le.textChanged.connect(
                    lambda _t, e=le, c=count, lb=cnt:
                    self._on_clear_message_changed(e, c, lb))
                msg_grid.addWidget(le, i + 1, 1)
                msg_grid.addWidget(cnt, i + 1, 2)
                self._clear_message_edits.append(le)
                self._on_clear_message_count(le, count, cnt)
        except CM.ClearMessageError as e:
            msg_grid.addWidget(QLabel(t("title_screen_dialog.clear_message.unavailable", "編集不可: {error}").format(error=e)), 1, 0, 1, 3)
        msg_root.addLayout(msg_grid)
        self._clear_message_status.setStyleSheet("color:#888; font-size:11px;")
        msg_root.addWidget(self._clear_message_status)
        edit_col.addWidget(msg_group)

        group = QGroupBox(t("title_screen_dialog.clear_screen_char.group", "クリア画面のキャラ (おめでとう画面の2体)"))
        form = QFormLayout(group)
        self._clear_screen_combo = QComboBox()
        for preset_id, preset in clearscreen_hack.PRESET_DEFS.items():
            self._clear_screen_combo.addItem(preset["label"], preset_id)
        self._clear_screen_status = QLabel("")
        try:
            cur = clearscreen_hack.current_preset_id(self._rom)
            idx = self._clear_screen_combo.findData(cur)
            if idx >= 0:
                self._clear_screen_combo.setCurrentIndex(idx)
            self._clear_screen_ok = True
        except Exception as e:
            self._clear_screen_ok = False
            self._clear_screen_combo.setEnabled(False)
            self._clear_screen_status.setText(t("title_screen_dialog.clear_screen_char.unavailable", "使用不可: {type}: {error}").format(type=type(e).__name__, error=e))
        self._clear_screen_combo.currentIndexChanged.connect(
            self._on_clear_screen_preset_changed)
        form.addRow(t("title_screen_dialog.clear_screen_char.label", "表示キャラ:"), self._clear_screen_combo)
        hint = QLabel(
            t(
                "title_screen_dialog.clear_screen_char.hint",
                "ステージクリア画面で左右に出る2体を差し替えます。"
                "既存のゲーム挙動改造にあった設定と同じ処理です。",
            ))
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#888; font-size:11px;")
        form.addRow(hint)
        form.addRow(self._clear_screen_status)
        edit_col.addWidget(group)
        edit_col.addStretch()
        root.addLayout(body, 1)
        self._refresh_clear_preview()
        return tab

    def _build_ending_text_tab(self):
        tab = QWidget()
        root = QVBoxLayout(tab)
        info = QLabel(
            t(
                "title_screen_dialog.ending_tab.info",
                "エンディングの文字列だけを編集します。表示位置や改行などの"
                "制御データは維持します。英大文字 A-Z / スペース / , ' \" "
                "のみ使用できます。",
            ))
        info.setWordWrap(True)
        root.addWidget(info)
        try:
            rows = TS.read_ending_text_messages(self._rom)
        except (TS.EndingTextError, TS.TitleScreenError, ValueError) as e:
            msg = QLabel(t("title_screen_dialog.ending_tab.unavailable", "エンディング文字列を編集できません: {error}").format(error=e))
            msg.setWordWrap(True)
            root.addWidget(msg)
            root.addStretch()
            self._ending_text_edits = []
            self._ending_text_status = QLabel("")
            return tab

        body = QHBoxLayout()
        preview_col = QVBoxLayout()
        edit_col = QVBoxLayout()
        body.addLayout(preview_col, 3)
        body.addLayout(edit_col, 2)

        top = QHBoxLayout()
        top.addWidget(QLabel("View:"))
        self._ending_mode = QComboBox()
        self._ending_mode.addItem("True Ending", "PrincessTrue")
        self._ending_mode.addItem("Good Ending A", "PrincessNormal")
        self._ending_mode.addItem("Good Ending B", "PrincessBad")
        self._ending_mode.addItem("Bad Ending A", "True")
        self._ending_mode.addItem("Bad Ending B", "Normal")
        self._ending_mode.addItem("Worst Ending", "Bad")
        self._ending_mode.setCurrentIndex(5)
        self._ending_mode.currentIndexChanged.connect(
            self._on_ending_mode_changed)
        top.addWidget(self._ending_mode)
        self._ending_condition = QLabel("")
        self._ending_condition.setMinimumWidth(220)
        top.addWidget(self._ending_condition)
        top.addStretch()
        preview_col.addLayout(top)

        self._ending_preview = EndingPreviewLabel()
        self._ending_preview.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self._ending_preview.setStyleSheet("background:#000;")
        self._ending_preview.zoom_wheel.connect(self._on_ending_zoom_wheel)
        self._ending_zoom = 3
        ending_scroll = QScrollArea()
        ending_scroll.setWidgetResizable(True)
        ending_wrap = QWidget()
        ending_wrap_lay = QHBoxLayout(ending_wrap)
        ending_wrap_lay.addWidget(self._ending_preview, 0, Qt.AlignTop | Qt.AlignLeft)
        ending_wrap_lay.addStretch()
        ending_scroll.setWidget(ending_wrap)
        preview_col.addWidget(ending_scroll, 1)

        g = QGridLayout()
        g.setHorizontalSpacing(8)
        g.setVerticalSpacing(6)
        g.addWidget(QLabel("Line"), 0, 0)
        g.addWidget(QLabel("Text"), 0, 1)
        g.addWidget(QLabel("Count"), 0, 2)
        rx = QRegExpValidator(QRegExp("[A-Za-z ,'\\\"]*"))
        self._ending_text_edits = []
        self._ending_text_row_widgets = []
        for i, (name, cur, count, _orig) in enumerate(rows):
            name_lbl = QLabel(name)
            g.addWidget(name_lbl, i + 1, 0)
            le = QLineEdit(cur.rstrip())
            le.setMaxLength(count)
            le.setValidator(rx)
            cnt = QLabel()
            cnt.setMinimumWidth(56)
            le.textChanged.connect(
                lambda _t, e=le, c=count, lb=cnt:
                self._on_ending_text_changed(e, c, lb))
            g.addWidget(le, i + 1, 1)
            g.addWidget(cnt, i + 1, 2)
            self._ending_text_edits.append(le)
            self._ending_text_row_widgets.append((name_lbl, le, cnt))
            self._on_ending_text_count(le, count, cnt)
        edit_col.addLayout(g)
        self._ending_text_status = QLabel("")
        edit_col.addWidget(self._ending_text_status)
        edit_col.addStretch()
        root.addLayout(body, 1)
        self._on_ending_mode_changed()
        return tab

    def _build_ending_preview_image(self):
        mode = self._ending_mode.currentData()
        clear_background = mode in ("PrincessTrue", "True")
        grid = [] if clear_background else TS.decode_ending_base_grid(self._rom)
        entries = TS.ending_text_preview_entries(
            self._rom, mode)
        tiles = TS.get_chr_bank3_tiles(self._rom)
        pal = self._title_palette()
        attr = self._ending_attributes(clear_background)
        img = QImage(_IMG_W, _IMG_H, QImage.Format_RGB32)
        painter = None
        try:
            painter = QPainter(img)
            if clear_background:
                blank = tiles[(_BG_BASE + 0x24) & 0x1FF]
                for row in range(_IMG_H // 8):
                    for col in range(_NT_W):
                        self._draw_ending_tile(
                            painter, blank, col * 8, row * 8, pal, attr)
            else:
                for cell, stream in enumerate(grid):
                    row = cell // _NT_W
                    col = cell % _NT_W
                    ti = (_BG_BASE + int(stream)) & 0x1FF
                    self._draw_ending_tile(
                        painter, tiles[ti], col * 8, row * 8, pal, attr)
            for ppu_addr, text_tiles, _text_index in entries:
                idx = (int(ppu_addr) - 0x2800) & 0x03FF
                x = (idx % _NT_W) * 8
                y = (idx // _NT_W) * 8
                for stream in text_tiles:
                    ti = (_BG_BASE + int(stream)) & 0x1FF
                    self._draw_ending_tile(painter, tiles[ti], x, y, pal, attr)
                    x += 8
        finally:
            if painter is not None:
                painter.end()
        return self._shift_title_display_image(img)

    def _draw_ending_tile(self, painter, tile, x0, y0, pal, attr):
        for py in range(8):
            for px in range(8):
                pi = tile.pixels[py][px] & 0x03
                dx = int(x0) + px
                dy = int(y0) + py
                if not (0 <= dx < _IMG_W and 0 <= dy < _IMG_H):
                    continue
                pal_no = self._attr_palette_no(attr, dy // 8, dx // 8)
                nes_idx = pal[0] if pi == 0 else pal[pal_no * 4 + pi]
                painter.fillRect(dx, dy, 1, 1, QColor(*NES_COLORS[nes_idx & 0x3F]))

    def _ending_attributes(self, clear_background=False):
        """Use title colors except the top logo band used by ending text."""
        if clear_background:
            return [0] * 64
        attr = list(self._title_attributes())
        for row in range(6, 14):
            for col in range(_NT_W):
                ai = (row // 2) * 16 + (col // 2)
                if 0 <= ai < len(attr):
                    attr[ai] = 0
        return attr

    def _refresh_ending_preview(self):
        preview = getattr(self, "_ending_preview", None)
        if preview is None:
            return
        try:
            img = self._build_ending_preview_image()
        except Exception as e:
            preview.setText(f"Preview unavailable: {type(e).__name__}: {e}")
            return
        zoom = int(getattr(self, "_ending_zoom", 3))
        pm = QPixmap.fromImage(img).scaled(
            _IMG_W * zoom, _IMG_H * zoom, Qt.KeepAspectRatio, Qt.FastTransformation)
        self._draw_preview_grid(pm, zoom)
        preview.setPixmap(pm)
        preview.setFixedSize(pm.size())

    def _on_ending_zoom_wheel(self, step):
        cur = int(getattr(self, "_ending_zoom", 3))
        self._ending_zoom = max(1, min(8, cur + int(step)))
        self._refresh_ending_preview()

    def _on_ending_mode_changed(self, *_):
        conditions = {
            "PrincessTrue": "条件: 王女あり / 両方取得",
            "PrincessNormal": "条件: 王女あり / 片方取得",
            "PrincessBad": "条件: 王女あり / 取得なし",
            "True": "条件: 王女なし / 両方取得",
            "Normal": "条件: 王女なし / 片方取得",
            "Bad": "条件: 王女なし / 取得なし",
        }
        mode = self._ending_mode.currentData()
        label = getattr(self, "_ending_condition", None)
        if label is not None:
            label.setText(conditions.get(mode, ""))
        visible = set(TS.ending_text_edit_indices(self._ending_mode.currentData()))
        for i, widgets in enumerate(getattr(self, "_ending_text_row_widgets", [])):
            show = i in visible
            for widget in widgets:
                widget.setVisible(show)
        self._refresh_ending_preview()

    def _on_clear_screen_preset_changed(self, *_):
        if not getattr(self, "_clear_screen_ok", False):
            return
        combo = getattr(self, "_clear_screen_combo", None)
        if combo is None:
            return
        preset_id = combo.currentData()
        snap = bytes(self._rom)
        try:
            cur = clearscreen_hack.current_preset_id(self._rom)
            if preset_id == cur:
                if getattr(self, "_clear_screen_status", None) is not None:
                    self._clear_screen_status.setText("")
                return
            clearscreen_hack.apply_preset(self._rom, preset_id)
        except clearscreen_hack.ClearScreenHackError as e:
            self._rom[:] = snap
            QMessageBox.warning(
                self,
                t("title_screen.clear_screen.apply_failed", "クリア画面改造失敗"),
                str(e),
            )
            return
        self._changed = True
        if getattr(self, "_clear_screen_status", None) is not None:
            self._clear_screen_status.setText(
                t(
                    "title_screen.clear_screen.character_changed",
                    "表示キャラを {name} に変更しました",
                ).format(name=combo.currentText()))

    def _on_show_clear_message(self):
        from .clear_message_dialog import ClearMessageDialog, format_clear_message_error
        from ..core import clear_message as _cm

        snap = bytes(self._rom)
        try:
            dlg = ClearMessageDialog(
                self._rom, self, app_config=self._app_config)
        except _cm.ClearMessageError as e:
            from ..core.i18n import t
            QMessageBox.critical(
                self,
                t("clear_message.open_failed", "クリア画面メッセージ編集不可"),
                format_clear_message_error(e),
            )
            return
        dlg.exec_()
        if bytes(self._rom) != snap:
            self._changed = True
            if getattr(self, "_clear_screen_status", None) is not None:
                self._clear_screen_status.setText(
                    t(
                        "title_screen.clear_message.updated",
                        "クリア画面メッセージを更新しました",
                    )
                )

    def _build_clear_preview_image(self):
        img = QImage(_IMG_W, _IMG_H, QImage.Format_RGB32)
        painter = QPainter(img)
        try:
            painter.fillRect(0, 0, _IMG_W, _IMG_H, QColor(92, 28, 0))
            tiles = TS.get_chr_bank3_tiles(self._rom)
            for msg in CM.MESSAGES:
                idx = (int(msg["ppu"]) - 0x2000) & 0x03FF
                x = (idx % _NT_W) * 8
                y = (idx // _NT_W) * 8
                start = int(msg["off"]) + 3
                for k in range(int(msg["count"])):
                    stream = int(self._rom[start + k]) & 0xFF
                    ti = (_BG_BASE + stream) & 0x1FF
                    self._draw_clear_text_tile(painter, tiles[ti], x, y)
                    x += 8
        finally:
            painter.end()
        return img

    def _draw_clear_text_tile(self, painter, tile, x0, y0):
        clear_pal = (
            QColor(0, 0, 0),
            QColor(180, 180, 180),
            QColor(0, 0, 0),
            QColor(255, 255, 255),
        )
        for py in range(8):
            for px in range(8):
                pi = tile.pixels[py][px] & 0x03
                if pi == 1:
                    continue
                dx = int(x0) + px
                dy = int(y0) + py
                if 0 <= dx < _IMG_W and 0 <= dy < _IMG_H:
                    painter.fillRect(dx, dy, 1, 1, clear_pal[pi])

    def _refresh_clear_preview(self):
        preview = getattr(self, "_clear_preview", None)
        if preview is None:
            return
        try:
            img = self._build_clear_preview_image()
        except Exception as e:
            preview.setText(
                t(
                    "title_screen.preview.unavailable",
                    "プレビュー不可: {error}",
                ).format(error=f"{type(e).__name__}: {e}")
            )
            return
        zoom = int(getattr(self, "_clear_zoom", 3))
        pm = QPixmap.fromImage(img).scaled(
            _IMG_W * zoom, _IMG_H * zoom,
            Qt.KeepAspectRatio, Qt.FastTransformation)
        preview.setPixmap(pm)
        preview.setFixedSize(pm.size())

    def _on_clear_zoom_wheel(self, step):
        cur = int(getattr(self, "_clear_zoom", 3))
        self._clear_zoom = max(1, min(8, cur + int(step)))
        self._refresh_clear_preview()

    def _on_clear_message_count(self, le, count, cnt_lbl):
        n = len(le.text())
        cnt_lbl.setText(f"{n} / {count}")
        if n >= count:
            cnt_lbl.setStyleSheet("color:#c33;")
        elif n == 0:
            cnt_lbl.setStyleSheet("color:#888;")
        else:
            cnt_lbl.setStyleSheet("")

    def _on_clear_message_changed(self, le, count, cnt_lbl):
        up = le.text().upper()
        if le.text() != up:
            le.setText(up)
            return
        self._on_clear_message_count(le, count, cnt_lbl)
        edits = getattr(self, "_clear_message_edits", [])
        if not edits:
            return
        snap = bytes(self._rom)
        try:
            changes = CM.write_messages(self._rom, [e.text() for e in edits])
        except CM.ClearMessageError as e:
            self._rom[:] = snap
            if getattr(self, "_clear_message_status", None) is not None:
                self._clear_message_status.setText(
                    t("title_screen.input_error", "入力エラー: {error}").format(error=e)
                )
            return
        if changes:
            self._changed = True
            if getattr(self, "_clear_message_status", None) is not None:
                self._clear_message_status.setText(
                    t(
                        "title_screen.clear_message.applied",
                        "クリア画面メッセージを反映しました",
                    )
                )
        else:
            if getattr(self, "_clear_message_status", None) is not None:
                self._clear_message_status.setText("")
        self._refresh_clear_preview()

    @staticmethod
    def _shift_title_display_image(img: QImage) -> QImage:
        """Apply the same 8px/1px display correction used by title preview."""
        src = img.convertToFormat(QImage.Format_RGB32)
        out = QImage(_IMG_W, _IMG_H, QImage.Format_RGB32)
        painter = QPainter(out)
        try:
            painter.drawImage(0, 0, src, _IMG_W - 8, _IMG_H - 1, 8, 1)
            painter.drawImage(8, 0, src, 0, _IMG_H - 1, _IMG_W - 8, 1)
            painter.drawImage(0, 1, src, _IMG_W - 8, 0, 8, _IMG_H - 1)
            painter.drawImage(8, 1, src, 0, 0, _IMG_W - 8, _IMG_H - 1)
        finally:
            painter.end()
        return out

    def _on_ending_text_count(self, le, count, cnt_lbl):
        n = len(le.text())
        cnt_lbl.setText(f"{n} / {count}")
        if n >= count:
            cnt_lbl.setStyleSheet("color:#c33;")
        elif n == 0:
            cnt_lbl.setStyleSheet("color:#888;")
        else:
            cnt_lbl.setStyleSheet("")

    def _on_ending_text_changed(self, le, count, cnt_lbl):
        up = le.text().upper()
        if le.text() != up:
            le.setText(up)
            return
        self._on_ending_text_count(le, count, cnt_lbl)
        edits = getattr(self, "_ending_text_edits", [])
        if not edits:
            return
        snap = bytes(self._rom)
        try:
            changes = TS.write_ending_text_messages(
                self._rom, [e.text() for e in edits])
        except (TS.EndingTextError, TS.TitleScreenError, ValueError) as e:
            self._rom[:] = snap
            self._ending_text_status.setText(
                t("title_screen.input_error", "入力エラー: {error}").format(error=e)
            )
            return
        if changes:
            self._changed = True
            self._ending_text_status.setText(
                t("title_screen.ending_text.applied", "エンディング文字を反映しました")
            )
        else:
            self._ending_text_status.setText("")
        self._refresh_ending_preview()

    def _reload_ending_text_edits(self):
        edits = getattr(self, "_ending_text_edits", [])
        if not edits:
            return
        try:
            rows = TS.read_ending_text_messages(self._rom)
        except Exception:
            return
        for le, (_name, cur, _count, _orig) in zip(edits, rows):
            old = le.blockSignals(True)
            le.setText(cur.rstrip())
            le.blockSignals(old)
        self._refresh_ending_preview()

    # --- 描画 (実タイトル画面を合成) ---
    def _build_image(self, color: bool = True) -> QImage:
        if color:
            try:
                return self._build_color_image()
            except Exception:
                # 色情報が読めない改造ROMでも、従来の4階調表示へ戻す。
                pass
        return self._build_gray_image()

    def _draw_title_fixed_text_overlay(self, img: QImage, color: bool) -> QImage:
        """Draw original title routine text for collision/layout preview only."""
        out = img.convertToFormat(QImage.Format_RGB32) if color else img.copy()
        painter = None
        try:
            chr_off = TS.chr_bank3_offset(self._rom)
            pal = self._title_palette() if color else None
            attr = self._title_attributes() if color else None
            painter = QPainter(out)
            for x0, y0, stream, role in self._title_fixed_text_tiles():
                pos = chr_off + ((_BG_BASE + stream) & 0x1FF) * \
                    NES_GFX_TILE_BYTE_SIZE
                if pos + NES_GFX_TILE_BYTE_SIZE > len(self._rom):
                    continue
                tile = NesTile(bytes(self._rom[pos:pos + NES_GFX_TILE_BYTE_SIZE]))
                self._draw_title_fixed_text_tile(
                    painter, tile, int(x0), int(y0), color, pal, attr)
        except Exception:
            return img
        finally:
            if painter is not None:
                painter.end()
        return out

    def _title_fixed_text_palette(self):
        off = _TITLE_FIXED_TEXT_PALETTE_OFF
        if off + 19 <= len(self._rom):
            if self._rom[off] == 0x3F and self._rom[off + 1] == 0x00:
                ctrl = self._rom[off + 2]
                if ctrl & 0x40:
                    n = (ctrl & 0x3F) + 1
                    if n >= 16 and off + 3 + 16 <= len(self._rom):
                        return [self._rom[off + 3 + i] & 0x3F
                                for i in range(16)]
        return [
            0x0F, 0x0F, 0x10, 0x30,
            0x0F, 0x0F, 0x27, 0x30,
            0x0F, 0x0F, 0x16, 0x30,
            0x0F, 0x0F, 0x27, 0x38,
        ]

    def _title_fixed_text_tiles(self):
        out = []
        for cpu in _TITLE_FIXED_TEXT_SCRIPT_CPU:
            out.extend(self._title_script_tiles(cpu))
        for ppu_addr, text in _TITLE_FIXED_VALUE_LINES:
            x, y = self._title_ppu_addr_to_display_xy(ppu_addr)
            for ch in text:
                if ch != " ":
                    try:
                        out.append((x, y, TS._title_char_src_tile(ch), "value"))
                    except Exception:
                        pass
                x += 8
        return out

    def _title_grid_with_fixed_text(self, grid):
        out = list(grid or [])
        if len(out) < _NT_W * (_IMG_H // 8):
            return out
        for cell, stream in self._title_fixed_text_cells():
            if 0 <= cell < len(out):
                out[cell] = int(stream) & 0xFF
        return out

    def _title_fixed_text_cells(self):
        out = []
        for cpu in _TITLE_FIXED_TEXT_SCRIPT_CPU:
            out.extend(self._title_script_cells(cpu))
        for ppu_addr, text in _TITLE_FIXED_VALUE_LINES:
            cell = self._title_ppu_addr_to_cell(ppu_addr)
            for ch in text:
                if ch != " ":
                    try:
                        out.append((cell, TS._title_char_src_tile(ch)))
                    except Exception:
                        pass
                cell += 1
        return out

    def _title_script_cells(self, cpu):
        pos = 0x10 + (int(cpu) - 0x8000)
        if pos < 0 or pos + 3 > len(self._rom):
            return []
        out = []
        while pos + 3 <= len(self._rom):
            addr = (self._rom[pos] << 8) | self._rom[pos + 1]
            ctrl = self._rom[pos + 2] & 0xFF
            pos += 3
            count = (ctrl & 0x3F) + 1
            if not (0x2000 <= addr <= 0x2FFF) or pos + count > len(self._rom):
                break
            cell = self._title_ppu_addr_to_cell(addr)
            step = _NT_W if ctrl & 0x80 else 1
            if ctrl & 0x40:
                for i in range(count):
                    stream = self._rom[pos + i] & 0xFF
                    if stream != 0x24:
                        out.append((cell, stream))
                    cell += step
            pos += count
            if pos >= len(self._rom) or self._rom[pos] == 0:
                break
        return out

    def _title_script_tiles(self, cpu):
        pos = 0x10 + (int(cpu) - 0x8000)
        if pos < 0 or pos + 3 > len(self._rom):
            return []
        out = []
        role = "push" if int(cpu) == _TITLE_FIXED_PUSH_TEXT_CPU else "fixed"
        while pos + 3 <= len(self._rom):
            addr = (self._rom[pos] << 8) | self._rom[pos + 1]
            ctrl = self._rom[pos + 2] & 0xFF
            pos += 3
            count = (ctrl & 0x3F) + 1
            if not (0x2000 <= addr <= 0x2FFF) or pos + count > len(self._rom):
                break
            x, y = self._title_ppu_addr_to_display_xy(addr)
            if ctrl & 0x40:
                for i in range(count):
                    stream = self._rom[pos + i] & 0xFF
                    if stream != 0x24:
                        out.append((x, y, stream, role))
                    if ctrl & 0x80:
                        y += 8
                    else:
                        x += 8
            pos += count
            if pos >= len(self._rom) or self._rom[pos] == 0:
                break
        return out

    @staticmethod
    def _title_ppu_addr_to_display_xy(ppu_addr):
        idx = (int(ppu_addr) - 0x2000) & 0x03FF
        x = (idx % _NT_W) * 8
        y = (idx // _NT_W) * 8
        return _ppu_pixel_to_display(x, y)

    @staticmethod
    def _title_ppu_addr_to_cell(ppu_addr):
        return (int(ppu_addr) - 0x2000) & 0x03FF

    def _draw_title_fixed_text_tile(self, painter, tile, x0, y0, color, pal, attr):
        for py in range(8):
            for px in range(8):
                pi = tile.pixels[py][px] & 0x03
                if pi == 0:
                    continue
                dx = int(x0) + px
                dy = int(y0) + py
                if not (0 <= dx < _IMG_W and 0 <= dy < _IMG_H):
                    continue
                if color:
                    px0, py0 = _display_pixel_to_ppu(dx, dy)
                    pal_no = self._attr_palette_no(attr, py0 // 8, px0 // 8)
                    nes_idx = pal[pal_no * 4 + pi]
                    qcolor = QColor(*NES_COLORS[nes_idx & 0x3F])
                else:
                    v = _GRAY[pi]
                    qcolor = QColor(v, v, v)
                painter.fillRect(dx, dy, 1, 1, qcolor)

    def _build_gray_image(self) -> QImage:
        """nametable をデコードし CHR bank3 で実タイトルを合成。
        色は未確定ゆえ暗背景4階調 (形状確認用)。"""
        d = TS.decode_title_grid(self._rom)
        self._last_cells = d["cells"]
        tiles = TS.get_chr_bank3_tiles(self._rom)   # 512 NesTile
        grid = self._title_grid_with_fixed_text(d["grid"])
        buf = bytearray(_IMG_W * _IMG_H)
        for cell in range(len(grid)):
            row = cell // _NT_W
            col = cell % _NT_W
            ti = (_BG_BASE + grid[cell]) & 0x1FF
            px = tiles[ti].pixels
            ox = col * 8
            oy = row * 8
            for y in range(8):
                pr = px[y]
                bb = (oy + y) * _IMG_W + ox
                for x in range(8):
                    buf[bb + x] = _GRAY[pr[x]]
        # ★画像出力時の位置補正 (ROM内部ロジックは不変・画像I/Oのみ):
        #   右8px を左へ巡回 + 下1px を上へ巡回。
        #   result(x,y) = rendered((x-8)%W, (y-1)%H)
        W, H = _IMG_W, _IMG_H
        sbuf = bytearray(W * H)
        for y in range(H):
            sy = (y - 1) % H
            srow = buf[sy * W:(sy + 1) * W]
            sbuf[y * W:(y + 1) * W] = srow[W - 8:] + srow[:W - 8]
        # PyQt5: QImage はバッファ非所有。.copy() まで data 生存必須
        data = bytes(sbuf)
        img = QImage(data, W, H, W, QImage.Format_Grayscale8)
        return img.copy()

    def _title_palette(self):
        """タイトル用PPU palette $3F00-$3F0F をROM内scriptから読む。"""
        off = _TITLE_PALETTE_SCRIPT_OFF
        if off + 19 <= len(self._rom):
            # idx5 $958A: 3F 00 4F + 16 palette bytes + 00
            if self._rom[off] == 0x3F and self._rom[off + 1] == 0x00:
                ctrl = self._rom[off + 2]
                if ctrl & 0x40:
                    n = (ctrl & 0x3F) + 1
                    if n >= 16 and off + 3 + 16 <= len(self._rom):
                        return [self._rom[off + 3 + i] & 0x3F
                                for i in range(16)]
        return [
            0x0F, 0x0F, 0x10, 0x30,
            0x0F, 0x0F, 0x27, 0x30,
            0x0F, 0x0F, 0x16, 0x30,
            0x0F, 0x0F, 0x27, 0x38,
        ]

    def _set_title_palette(self, colors):
        """タイトル用palette script内の$3F00-$3F0F 16色を書き換える。"""
        off = _TITLE_PALETTE_SCRIPT_OFF
        if off + 19 > len(self._rom):
            raise ValueError("title palette script is outside ROM")
        if self._rom[off] != 0x3F or self._rom[off + 1] != 0x00:
            raise ValueError("title palette script signature mismatch")
        ctrl = self._rom[off + 2]
        if not (ctrl & 0x40) or (ctrl & 0x3F) + 1 < 16:
            raise ValueError("title palette script length is not 16 bytes")
        for i, c in enumerate(colors[:16]):
            val = c & 0x3F
            pos = off + 3 + i
            if (self._rom[pos] & 0x3F) != val:
                self._rom[pos] = val

    def _title_attributes(self):
        """タイトルattributeを実PPU側 $2BC0-$2BFF に展開する。"""
        return TS.read_title_attribute_expanded(self._rom)

    @staticmethod
    def _attr_palette_no(attr, row, col):
        ai = (row // 2) * 16 + (col // 2)
        if not (0 <= ai < len(attr)):
            return 0
        return attr[ai] & 0x03

    def _build_color_image(self) -> QImage:
        """タイトルプレビュー用。palette/attributeを反映したRGB画像を作る。"""
        d = TS.decode_title_grid(self._rom)
        self._last_cells = d["cells"]
        tiles = TS.get_chr_bank3_tiles(self._rom)
        grid = self._title_grid_with_fixed_text(d["grid"])
        pal = self._title_palette()
        attr = self._title_attributes()
        buf = bytearray(_IMG_W * _IMG_H * 3)
        for cell in range(len(grid)):
            row = cell // _NT_W
            col = cell % _NT_W
            ti = (_BG_BASE + grid[cell]) & 0x1FF
            px = tiles[ti].pixels
            pal_no = self._attr_palette_no(attr, row, col)
            ox = col * 8
            oy = row * 8
            for y in range(8):
                pr = px[y]
                bb = ((oy + y) * _IMG_W + ox) * 3
                for x in range(8):
                    pi = pr[x] & 0x03
                    nes_idx = pal[0] if pi == 0 else pal[pal_no * 4 + pi]
                    r, g, b = NES_COLORS[nes_idx & 0x3F]
                    p = bb + x * 3
                    buf[p:p + 3] = bytes((r, g, b))

        W, H = _IMG_W, _IMG_H
        stride = W * 3
        sbuf = bytearray(W * H * 3)
        for y in range(H):
            sy = (y - 1) % H
            srow = buf[sy * stride:(sy + 1) * stride]
            sbuf[y * stride:(y + 1) * stride] = \
                srow[(W - 8) * 3:] + srow[:(W - 8) * 3]
        data = bytes(sbuf)
        img = QImage(data, W, H, stride, QImage.Format_RGB888)
        return img.copy()

    def _refresh(self, *_):
        off = TS.chr_bank3_offset(self._rom)
        d = TS.decode_title_grid(self._rom)
        self._last_cells = d["cells"]
        grid = d["grid"]
        img = self._build_image(color=True)
        self._info.setText(
            f"region: <b>{self._region}</b>  /  実タイトル合成 "
            f"(nametable+CHR bank3 0x{off:X}, {_IMG_W}x{_IMG_H}, "
            f"{getattr(self, '_last_cells', 0)}セル)"
            + ("  /  <span style='color:#c33'>変更あり</span>"
               if self._changed else ""))
        z = self._zoom.currentData()
        pm = QPixmap.fromImage(img).scaled(
            _IMG_W * z, _IMG_H * z, Qt.KeepAspectRatio,
            Qt.FastTransformation)
        highlight_tile = self._highlight_tile.value()
        count = self._draw_preview_highlight(pm, z, grid, highlight_tile)
        self._draw_title_character_overlay(pm, z)
        self._draw_preview_grid(pm, z)
        self._draw_preview_attr_grid(pm, z)
        self._draw_preview_group_overlay(
            pm, z, self._title_attributes(), self._group_overlay.currentData())
        self._canvas.setPixmap(pm)
        self._canvas.setFixedSize(pm.size())
        self._canvas.set_title_context(z, grid, off)
        self._preview_status_text = (
            f"グリッド: 32x30 / CHR bank3開始 0x{off:X} / "
            f"bank内 0x{highlight_tile:03X}: {count}箇所 / "
            f"{self._update_title_character_count_labels()}")
        sel = getattr(self, "_selected_title_character_slot", None)
        if sel is not None:
            self._preview_status_text += f" / 選択キャラスロット {int(sel) + 1}"
        self._restore_preview_status()

    @staticmethod
    def _draw_preview_highlight(pm, zoom, grid, target_bank_tile):
        target_stream = (int(target_bank_tile) - _BG_BASE) & 0xFF
        painter = QPainter(pm)
        painter.setBrush(QColor(255, 0, 180, 82))
        painter.setPen(QPen(QColor(255, 70, 210), 2))
        count = 0
        for cell, stream in enumerate(grid):
            if (int(stream) & 0xFF) != target_stream:
                continue
            row = cell // _NT_W
            col = cell % _NT_W
            dx, dy = _ppu_pixel_to_display(col * 8, row * 8)
            painter.drawRect(
                dx * zoom,
                dy * zoom,
                max(0, 8 * zoom - 1),
                max(0, 8 * zoom - 1),
            )
            count += 1
        painter.end()
        return count

    @staticmethod
    def _draw_preview_grid(pm, zoom):
        painter = QPainter(pm)
        pen = QPen(QColor(255, 255, 255, 85))
        pen.setWidth(1)
        painter.setPen(pen)
        for x in range(0, _IMG_W + 1, 8):
            sx = _ppu_pixel_to_display(x, 0)[0] * zoom
            painter.drawLine(sx, 0, sx, _IMG_H * zoom)
        for y in range(0, _IMG_H + 1, 8):
            sy = _ppu_pixel_to_display(0, y)[1] * zoom
            painter.drawLine(0, sy, _IMG_W * zoom, sy)
        painter.end()

    @staticmethod
    def _draw_preview_attr_grid(pm, zoom):
        painter = QPainter(pm)
        pen = QPen(QColor(255, 220, 60, 150))
        pen.setWidth(max(1, zoom // 2))
        painter.setPen(pen)
        for x in range(0, _IMG_W + 1, 16):
            sx = _ppu_pixel_to_display(x, 0)[0] * zoom
            painter.drawLine(sx, 0, sx, _IMG_H * zoom)
        for y in range(0, _IMG_H + 1, 16):
            sy = _ppu_pixel_to_display(0, y)[1] * zoom
            painter.drawLine(0, sy, _IMG_W * zoom, sy)
        painter.end()

    @staticmethod
    def _draw_wrapped_rect(painter, x, y, w, h, zoom):
        xs = [x]
        ys = [y]
        if x + w > _IMG_W:
            xs.append(x - _IMG_W)
        if y + h > _IMG_H:
            ys.append(y - _IMG_H)
        for yy in ys:
            for xx in xs:
                painter.drawRect(
                    xx * zoom,
                    yy * zoom,
                    max(0, w * zoom - 1),
                    max(0, h * zoom - 1),
                )

    def _draw_preview_group_overlay(self, pm, zoom, attr, group):
        if group is None or int(group) < 0:
            return
        group = int(group) & 0x03
        colors = [
            QColor(255, 64, 64, 70),
            QColor(64, 255, 64, 70),
            QColor(64, 128, 255, 70),
            QColor(255, 64, 220, 70),
        ]
        border = [
            QColor(255, 64, 64, 210),
            QColor(64, 255, 64, 210),
            QColor(64, 128, 255, 210),
            QColor(255, 64, 220, 210),
        ]
        painter = QPainter(pm)
        painter.setBrush(colors[group])
        pen = QPen(border[group])
        pen.setWidth(max(1, zoom))
        painter.setPen(pen)
        for by in range(_IMG_H // 16):
            row = by * 2
            for bx in range(_IMG_W // 16):
                col = bx * 2
                if self._attr_palette_no(attr, row, col) != group:
                    continue
                dx, dy = _ppu_pixel_to_display(col * 8, row * 8)
                self._draw_wrapped_rect(painter, dx, dy, 16, 16, zoom)
        painter.end()

    def _sprite_palette_qcolors(self, sprite_palette_no):
        off = _SPRITE_PALETTE_OFFSET + (4 + (int(sprite_palette_no) & 3)) * 4
        vals = [0x00, 0x10, 0x30]
        if off + 3 <= len(self._rom):
            vals = [self._rom[off + i] & 0x3F for i in range(3)]
        return [None] + [QColor(*NES_COLORS[v & 0x3F]) for v in vals]

    def _draw_8x16_oam_sprite(self, painter, zoom, x, y, tile_byte, oam_attr):
        pal = self._sprite_palette_qcolors(oam_attr & 0x03)
        hflip = bool(oam_attr & 0x40)
        vflip = bool(oam_attr & 0x80)
        half = 256 if (int(tile_byte) & 1) else 0
        top = half + (int(tile_byte) & 0xFE)
        chr_off = TS.chr_bank3_offset(self._rom)
        for sub, tile_no in ((0, top), (1, top + 1)):
            pos = chr_off + tile_no * NES_GFX_TILE_BYTE_SIZE
            if pos + NES_GFX_TILE_BYTE_SIZE > len(self._rom):
                continue
            tile = NesTile(bytes(self._rom[pos:pos + NES_GFX_TILE_BYTE_SIZE]))
            for py in range(8):
                for px in range(8):
                    pi = tile.pixels[py][px] & 0x03
                    color = pal[pi]
                    if color is None:
                        continue
                    dx = 7 - px if hflip else px
                    sy = sub * 8 + py
                    dy = 15 - sy if vflip else sy
                    painter.fillRect(
                        (int(x) + dx) * zoom,
                        (int(y) + dy) * zoom,
                        zoom,
                        zoom,
                        color,
                    )

    def _draw_title_picker_frame(self, img, zoom, ox, oy, tile1, tile2,
                                 frame_attr, palette):
        entry = TS.title_character_entry(0, 0, tile1, tile2, frame_attr, palette)
        attr1, attr2 = TS.title_character_oam_attrs(entry[5])
        painter = QPainter(img)
        self._draw_8x16_oam_sprite(painter, zoom, ox // zoom, oy // zoom,
                                   entry[3], attr1)
        self._draw_8x16_oam_sprite(painter, zoom, (ox // zoom) + 8, oy // zoom,
                                   entry[4], attr2)
        painter.end()

    def _draw_title_character_overlay(self, pm, zoom):
        try:
            chars = TS.read_title_characters(self._rom)
        except Exception:
            return
        painter = QPainter(pm)
        selected = getattr(self, "_selected_title_character_slot", None)
        for ch in chars:
            if not ch.get("active"):
                continue
            x = int(ch.get("x", 0))
            y = int(ch.get("y", 0))
            self._draw_8x16_oam_sprite(
                painter, zoom, x, y,
                int(ch.get("tile1", 0)), int(ch.get("attr1", 0)))
            self._draw_8x16_oam_sprite(
                painter, zoom, x + 8, y,
                int(ch.get("tile2", 0)), int(ch.get("attr2", 0)))
            is_selected = selected is not None and int(selected) == int(ch.get("slot", -1))
            pen = QPen(
                QColor(255, 230, 60, 230) if is_selected else QColor(255, 255, 255, 180))
            pen.setWidth(max(2, zoom) if is_selected else max(1, zoom))
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(
                x * zoom, y * zoom, max(0, 16 * zoom - 1),
                max(0, 16 * zoom - 1))
        painter.end()

    def _title_character_at_display(self, x, y):
        try:
            chars = TS.read_title_characters(self._rom)
        except Exception:
            return None
        for ch in reversed(chars):
            if not ch.get("active"):
                continue
            cx = int(ch.get("x", 0))
            cy = int(ch.get("y", 0))
            if cx <= int(x) < cx + 16 and cy <= int(y) < cy + 16:
                return int(ch.get("slot", -1))
        return None

    def _active_title_character_slots(self):
        try:
            chars = TS.read_title_characters(self._rom)
        except Exception:
            return []
        return [int(ch.get("slot", -1)) for ch in chars if ch.get("active")]

    def _title_character_count_text(self):
        count = len(self._active_title_character_slots())
        return f"Characters {count}/{TS.title_character_max()}"

    def _update_title_character_count_labels(self):
        text = self._title_character_count_text()
        label = getattr(self, "_title_character_count_label", None)
        if label is not None:
            label.setText(f"Placed: {len(self._active_title_character_slots())}/{TS.title_character_max()}")
        return text

    def _select_title_character_slot(self, slot):
        if slot is None or int(slot) < 0:
            self._selected_title_character_slot = None
        else:
            self._selected_title_character_slot = int(slot)
        self._refresh()

    @staticmethod
    def _title_frame_key(item):
        return int(item[3]) & 0xFF, int(item[4]) & 0xFF

    def _title_picker_items(self):
        items = getattr(self, "_title_picker_items_cache", None)
        if items is not None:
            return items
        try:
            raw = TitleCharacterPickerDialog._romframe_items_for_rom(self._rom)
            items = TitleCharacterPickerDialog._dedupe_romframe_items(raw)
        except Exception:
            items = []
        self._title_picker_items_cache = items
        return items

    def _clear_side_panel(self):
        while self._side_layout.count():
            item = self._side_layout.takeAt(0)
            self._delete_layout_item(item)
        self._palette_context_block = None
        self._palette_extra = None
        self._palette_extra_layout = None
        self._title_tile_editor_canvas = None
        self._title_tile_editor_state = None
        self._title_character_count_label = None
        self._title_tile_picker = None
        self._title_tile_picker_status = None
        self._title_tile_picker_palette = None
        self._title_tile_picker_zoom = None
        self._title_tile_picker_grid = None
        self._pending_title_tile_stream = None

    def _delete_layout_item(self, item):
        w = item.widget()
        if w is not None:
            w.deleteLater()
            return
        lay = item.layout()
        if lay is None:
            return
        while lay.count():
            self._delete_layout_item(lay.takeAt(0))
        lay.deleteLater()

    def _show_title_character_picker_panel(self):
        self._clear_side_panel()
        title = QLabel(t("title_screen.character_panel.title", "キャラクター"))
        title.setStyleSheet("font-weight:bold;")
        head = QHBoxLayout()
        head.addWidget(title)
        self._title_character_count_label = QLabel("")
        self._title_character_count_label.setMinimumWidth(90)
        head.addStretch()
        head.addWidget(self._title_character_count_label)
        self._side_layout.addLayout(head)
        row = QHBoxLayout()
        row.addWidget(QLabel(t("title_screen.label.color", "色:")))
        self._picker_palette = QComboBox()
        for i in range(4):
            self._picker_palette.addItem(f"SPR {i}", i)
        self._picker_palette.setMinimumWidth(110)
        self._picker_palette.setMinimumHeight(26)
        self._picker_palette.currentIndexChanged.connect(self._refresh_picker_grid)
        row.addWidget(self._picker_palette)
        row.addStretch()
        b_clear = QPushButton(t("title_screen.character.clear_all", "全削除"))
        b_clear.setToolTip(
            t(
                "title_screen.character.clear_all.tooltip",
                "タイトル上に配置した静止キャラを全て消します。",
            )
        )
        b_clear.clicked.connect(self._on_clear_title_characters)
        row.addWidget(b_clear)
        self._side_layout.addLayout(row)
        self._picker_status = QLabel("")
        self._picker_status.setWordWrap(True)
        self._side_layout.addWidget(self._picker_status)
        self._picker_scroll = QScrollArea()
        self._picker_scroll.setWidgetResizable(False)
        self._picker_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._picker_scroll.setMinimumHeight(260)
        self._side_layout.addWidget(self._picker_scroll, 1)
        self._side_panel.setVisible(True)
        self._update_title_character_count_labels()
        self._refresh_picker_grid()

    def _show_title_tile_picker_panel(self):
        self._clear_side_panel()
        self._pending_title_tile_stream = 0
        title = QLabel(t("title_screen.tile_picker.title", "タイル配置"))
        title.setStyleSheet("font-weight:bold;")
        self._side_layout.addWidget(title)
        row = QHBoxLayout()
        row.addWidget(QLabel(t("title_screen.tile_picker.display_mode", "表示モード:")))
        mode = QLabel(t("title_screen.tile_picker.raw_chr", "生CHRタイル (8x8)"))
        mode.setMinimumHeight(26)
        row.addWidget(mode)
        row.addWidget(QLabel(t("title_screen.tile_picker.palette", "パレット:")))
        pal_combo = QComboBox()
        for label in _TITLE_TILE_PICKER_PALETTE_LABELS:
            pal_combo.addItem(label)
        pal_combo.setCurrentIndex(0)
        pal_combo.currentIndexChanged.connect(self._refresh_title_tile_picker)
        self._title_tile_picker_palette = pal_combo
        row.addWidget(pal_combo)
        row.addWidget(QLabel(t("title_screen.zoom.label", "拡大:")))
        zoom = QSpinBox()
        zoom.setRange(1, 16)
        zoom.setValue(4)
        zoom.setSuffix(" x")
        zoom.valueChanged.connect(self._refresh_title_tile_picker)
        self._title_tile_picker_zoom = zoom
        row.addWidget(zoom)
        grid = QCheckBox(t("title_screen.grid_lines", "グリッド線"))
        grid.setChecked(True)
        grid.stateChanged.connect(self._refresh_title_tile_picker)
        self._title_tile_picker_grid = grid
        row.addWidget(grid)
        row.addStretch()
        self._side_layout.addLayout(row)
        status = QLabel("")
        status.setWordWrap(True)
        self._title_tile_picker_status = status
        self._side_layout.addWidget(status)
        self._title_tile_picker = TitleChrTilePickerLabel()
        self._title_tile_picker.tile_selected.connect(self._select_title_tile_stream)
        self._title_tile_picker.tile_hovered.connect(self._on_title_tile_picker_hovered)
        self._title_tile_picker.tile_left.connect(self._restore_title_tile_picker_status)
        scroll = QScrollArea()
        scroll.setWidgetResizable(False)
        scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        scroll.setMinimumHeight(360)
        scroll.setWidget(self._title_tile_picker)
        self._side_layout.addWidget(scroll, 1)
        self._side_panel.setVisible(True)
        self._refresh_title_tile_picker()

    def _refresh_title_tile_picker(self):
        picker = getattr(self, "_title_tile_picker", None)
        if picker is None:
            return
        stream = int(getattr(self, "_pending_title_tile_stream", 0) or 0) & 0xFF
        pal_combo = getattr(self, "_title_tile_picker_palette", None)
        palette_index = pal_combo.currentIndex() if pal_combo is not None else 0
        zoom = getattr(self, "_title_tile_picker_zoom", None)
        zoom_value = zoom.value() if zoom is not None else 4
        grid = getattr(self, "_title_tile_picker_grid", None)
        show_grid = grid.isChecked() if grid is not None else True
        picker.set_tiles(
            self._rom, stream, self._title_tile_picker_rgb(palette_index),
            zoom_value, show_grid)
        self._restore_title_tile_picker_status()
        self._preview_status.setText(
            t(
                "title_screen.tile_picker.status",
                "タイル配置: stream ${stream:02X} / bank内 0x{bank:03X}",
            ).format(stream=stream, bank=(_BG_BASE + stream))
        )

    def _title_tile_picker_rgb(self, palette_index):
        idx = int(palette_index) & 7
        if idx < 4:
            colors = self._title_palette()
            base = idx * 4
            vals = [colors[(base + i) & 0x0F] & 0x3F for i in range(4)]
            return [QColor(*NES_COLORS[v]).rgb() for v in vals]
        off = _SPRITE_PALETTE_OFFSET + idx * 4
        vals = [0x00, 0x10, 0x30]
        if off + 3 <= len(self._rom):
            vals = [self._rom[off + i] & 0x3F for i in range(3)]
        return [None] + [QColor(*NES_COLORS[v & 0x3F]).rgb() for v in vals]

    def _restore_title_tile_picker_status(self):
        stream = int(getattr(self, "_pending_title_tile_stream", 0) or 0) & 0xFF
        status = getattr(self, "_title_tile_picker_status", None)
        if status is not None:
            status.setText(
                t(
                    "title_screen.tile_picker.selection_status",
                    "選択: stream ${stream:02X} / bank内 0x{bank:03X}\n"
                    "キャンバス上の8x8マスをクリックすると配置します。",
                ).format(stream=stream, bank=(_BG_BASE + stream)))

    def _on_title_tile_picker_hovered(self, stream):
        stream = int(stream) & 0xFF
        status = getattr(self, "_title_tile_picker_status", None)
        if status is not None:
            status.setText(
                t(
                    "title_screen.tile_picker.hover_status",
                    "選択: stream ${selected:02X}\n"
                    "カーソル: stream ${stream:02X} / bank内 0x{bank:03X}",
                ).format(
                    selected=int(getattr(self, "_pending_title_tile_stream", 0) or 0) & 0xFF,
                    stream=stream,
                    bank=(_BG_BASE + stream),
                ))

    def _select_title_tile_stream(self, stream):
        self._pending_title_tile_stream = int(stream) & 0xFF
        self._refresh_title_tile_picker()

    def _show_title_palette_panel(self, block_row=None, block_col=None):
        self._clear_side_panel()
        has_block = block_row is not None and block_col is not None
        self._palette_context_block = (
            (int(block_row), int(block_col)) if has_block else None)
        if has_block:
            current = self._attr_palette_no(
                self._title_attributes(), int(block_row), int(block_col))
            self._palette_panel_sel = current * 4 + 1
        else:
            current = None
            self._palette_panel_sel = 0
        self._palette_slot_buttons = []
        self._palette_color_buttons = []
        self._palette_group_radios = []
        title = QLabel(t("title_screen.palette_panel.title", "パレット変更"))
        title.setStyleSheet("font-weight:bold;")
        self._side_layout.addWidget(title)
        status = QLabel(
            t(
                "title_screen.palette_panel.target_block",
                "対象: x={x}, y={y} の16x16区画",
            ).format(x=int(block_col), y=int(block_row))
            if has_block else
            t(
                "title_screen.palette_panel.no_target",
                "対象区画なし: 色番号だけ変更できます。パレット番号の割当はキャンバスを右クリック。",
            ))
        status.setWordWrap(True)
        self._palette_context_label = status
        self._side_layout.addWidget(status)

        g = QGroupBox(t("title_screen.palette.group", "タイトルパレット $3F00-$3F0F"))
        gl = QGridLayout(g)
        for group in range(4):
            rb = QRadioButton(
                t("title_screen.palette.index", "パレット {index}").format(index=group + 1)
            )
            rb.setEnabled(has_block)
            rb.setChecked(current == group)
            rb.toggled.connect(
                lambda checked, idx=group: self._select_title_attr_group(idx, checked))
            self._palette_group_radios.append(rb)
            gl.addWidget(rb, group * 2, 0)
            for sub in range(4):
                i = group * 4 + sub
                gl.addWidget(QLabel(f"${0x3F00 + i:04X}"),
                             group * 2, sub + 1)
                b = QPushButton()
                b.setMinimumSize(72, 30)
                b.clicked.connect(
                    lambda _, idx=i: self._select_title_palette_slot(idx))
                self._palette_slot_buttons.append(b)
                gl.addWidget(b, group * 2 + 1, sub + 1)
        self._side_layout.addWidget(g)

        picker = QGroupBox(t("title_screen.palette.nes64", "NES 64色"))
        pg = QGridLayout(picker)
        for i in range(64):
            b = QPushButton(f"{i:02X}")
            b.setMinimumSize(30, 24)
            b.clicked.connect(lambda _, idx=i: self._set_title_palette_slot_color(idx))
            self._palette_color_buttons.append(b)
            pg.addWidget(b, i // 16, i % 16)
        self._side_layout.addWidget(picker)
        self._palette_extra = QWidget()
        self._palette_extra_layout = QVBoxLayout(self._palette_extra)
        self._palette_extra_layout.setContentsMargins(0, 0, 0, 0)
        self._side_layout.addWidget(self._palette_extra)
        self._side_layout.addStretch()
        self._side_panel.setVisible(True)
        self._refresh_title_palette_panel()

    def _refresh_title_palette_panel(self):
        if not hasattr(self, "_palette_slot_buttons"):
            return
        colors = self._title_palette()
        sel = int(getattr(self, "_palette_panel_sel", 0)) & 0x0F
        block = getattr(self, "_palette_context_block", None)
        current_group = None
        if block is not None:
            current_group = self._attr_palette_no(
                self._title_attributes(), block[0], block[1])
        for i, rb in enumerate(getattr(self, "_palette_group_radios", [])):
            rb.blockSignals(True)
            rb.setEnabled(block is not None)
            rb.setChecked(current_group == i)
            rb.blockSignals(False)
        for i, b in enumerate(self._palette_slot_buttons):
            val = colors[i] & 0x3F
            b.setText(f"${val:02X}")
            b.setToolTip(
                t(
                    "title_screen.palette.slot.tooltip",
                    "パレット {palette} / slot {slot} = ${value:02X}",
                ).format(palette=i // 4 + 1, slot=i % 4, value=val)
            )
            b.setStyleSheet(TitlePaletteDialog._button_style(val, i == sel))
        for i, b in enumerate(self._palette_color_buttons):
            b.setStyleSheet(
                TitlePaletteDialog._button_style(i, (colors[sel] & 0x3F) == i))
        self._refresh_title_tile_editor_colors()

    def _clear_palette_extra_panel(self):
        lay = getattr(self, "_palette_extra_layout", None)
        if lay is None:
            return
        try:
            while lay.count():
                self._delete_layout_item(lay.takeAt(0))
        except RuntimeError:
            self._palette_extra = None
            self._palette_extra_layout = None
        self._title_tile_editor_canvas = None
        self._title_tile_editor_state = None

    def _refresh_title_tile_editor_colors(self):
        canvas = getattr(self, "_title_tile_editor_canvas", None)
        state = getattr(self, "_title_tile_editor_state", None)
        if canvas is None or not state:
            return
        colors, _pal_no = self._title_tile_palette_colors(
            state["row"], state["col"])
        canvas.set_colors(colors)

    def _show_title_tile_editor_panel(self, row, col, grid, stream, bank_tile,
                                      pos, pixels, pal_no, ref_count):
        if getattr(self, "_palette_extra_layout", None) is None:
            self._show_title_palette_panel()
        self._clear_palette_extra_panel()
        initial = [list(r) for r in pixels]
        self._title_tile_editor_state = {
            "row": int(row),
            "col": int(col),
            "pos": int(pos),
            "initial": initial,
            "old_changed": self._changed,
            "bank_tile": int(bank_tile),
        }

        box = QGroupBox(
            t(
                "title_screen.tile_editor.group",
                "8x8 CHR編集 bank内 0x{bank:03X}",
            ).format(bank=int(bank_tile))
        )
        root = QVBoxLayout(box)
        info = QLabel(
            f"cell ({int(col)}, {int(row)}) / stream 0x{int(stream):02X} / "
            f"ROM 0x{int(pos):X}-0x{int(pos) + 0x0F:X}\n"
            +
            t(
                "title_screen.tile_editor.info_suffix",
                "色グループ {group} / 使用箇所: {count}",
            ).format(group=int(pal_no) + 1, count=int(ref_count)))
        info.setWordWrap(True)
        root.addWidget(info)

        top = QHBoxLayout()
        top.addWidget(QLabel(t("title_screen.zoom.label", "拡大:")))
        zoom = QSpinBox()
        zoom.setRange(16, 48)
        zoom.setValue(28)
        zoom.setSuffix(" x")
        top.addWidget(zoom)
        top.addStretch()
        root.addLayout(top)

        body = QHBoxLayout()
        canvas = TitleTileCanvas(self)
        colors, _pal_no = self._title_tile_palette_colors(row, col)
        canvas.set_colors(colors)
        canvas.set_pixels(pixels)
        zoom.valueChanged.connect(canvas.set_zoom)
        canvas.pixel_changed.connect(self._on_title_tile_panel_pixel_changed)
        canvas.pixel_picked.connect(self._set_title_tile_panel_brush)
        self._title_tile_editor_canvas = canvas
        body.addWidget(canvas, 0, Qt.AlignTop)

        side = QVBoxLayout()
        side.addWidget(QLabel(t("title_screen.tile_editor.pen", "ペン:")))
        brush_row = QHBoxLayout()
        self._title_tile_brush_buttons = []
        for idx in range(4):
            btn = QPushButton(str(idx))
            btn.setCheckable(True)
            btn.setMinimumSize(38, 30)
            btn.setToolTip(
                t(
                    "title_screen.tile_editor.brush.tooltip",
                    "パレットインデックス {index} で描く。Alt+クリックでスポイト。",
                ).format(index=idx))
            btn.clicked.connect(
                lambda _checked=False, value=idx: self._set_title_tile_panel_brush(value))
            self._title_tile_brush_buttons.append(btn)
            brush_row.addWidget(btn)
        side.addLayout(brush_row)
        self._set_title_tile_panel_brush(1)

        clear_btn = QPushButton(t("common.clear", "クリア"))
        clear_btn.setToolTip(
            t(
                "title_screen.tile_editor.clear.tooltip",
                "8x8タイルをパレットインデックス0で消去",
            )
        )
        clear_btn.clicked.connect(self._clear_title_tile_panel)
        side.addWidget(clear_btn)
        restore_btn = QPushButton(t("title_screen.revert_initial", "開いた時点へ戻す"))
        restore_btn.clicked.connect(self._restore_title_tile_panel_initial)
        side.addWidget(restore_btn)
        side.addStretch()
        body.addLayout(side, 1)
        root.addLayout(body)

        self._palette_extra_layout.addWidget(box)
        self._preview_status.setText(
            t(
                "title_screen.tile_editor.status",
                "8x8編集: cell ({col}, {row}) / bank内 0x{bank:03X}",
            ).format(col=int(col), row=int(row), bank=int(bank_tile))
        )

    def _set_title_tile_panel_brush(self, value):
        canvas = getattr(self, "_title_tile_editor_canvas", None)
        if canvas is None:
            return
        value = max(0, min(3, int(value)))
        canvas.set_brush(value)
        for i, btn in enumerate(getattr(self, "_title_tile_brush_buttons", [])):
            btn.setChecked(i == value)

    def _on_title_tile_panel_pixel_changed(self, x, y, value):
        state = getattr(self, "_title_tile_editor_state", None)
        canvas = getattr(self, "_title_tile_editor_canvas", None)
        if not state or canvas is None:
            return
        pixels = canvas.pixels()
        self._write_title_tile_pixels(state["pos"], pixels)
        self._changed = True
        self._refresh()
        self._preview_status.setText(
            t(
                "title_screen.tile_editor.editing_status",
                "8x8編集中: cell ({col}, {row}) / bank内 0x{bank:03X}",
            ).format(
                col=state["col"],
                row=state["row"],
                bank=state["bank_tile"],
            )
        )

    def _set_title_tile_panel_pixels(self, pixels, changed=True):
        state = getattr(self, "_title_tile_editor_state", None)
        canvas = getattr(self, "_title_tile_editor_canvas", None)
        if not state or canvas is None:
            return
        canvas.set_pixels(pixels)
        self._write_title_tile_pixels(state["pos"], canvas.pixels())
        self._changed = bool(changed)
        self._refresh()

    def _clear_title_tile_panel(self):
        self._set_title_tile_panel_pixels(
            [[0 for _ in range(8)] for _ in range(8)],
            changed=True)

    def _restore_title_tile_panel_initial(self):
        state = getattr(self, "_title_tile_editor_state", None)
        if not state:
            return
        self._set_title_tile_panel_pixels(
            [list(r) for r in state["initial"]],
            changed=state["old_changed"])

    def _cancel_palette_block_context(self):
        if getattr(self, "_palette_context_block", None) is None:
            return
        self._palette_context_block = None
        label = getattr(self, "_palette_context_label", None)
        if label is not None:
            label.setText(
                t(
                    "title_screen.palette_panel.no_target",
                    "対象区画なし: 色番号だけ変更できます。パレット番号の割当はキャンバスを右クリック。",
                ))
        self._refresh_title_palette_panel()

    def _select_title_palette_slot(self, idx):
        self._palette_panel_sel = int(idx) & 0x0F
        self._refresh_title_palette_panel()

    def _select_title_attr_group(self, group, checked):
        if not checked:
            return
        block = getattr(self, "_palette_context_block", None)
        if block is None:
            return
        row, col = block
        pal_no = int(group) & 0x03
        attr = self._title_attributes()
        for rr in (row, row + 1):
            for cc in (col, col + 1):
                self._set_title_attr_palette_no(attr, rr, cc, pal_no)
        self._write_title_attributes(attr)
        self._changed = True
        self._group_overlay.setCurrentIndex(pal_no + 1)
        self._palette_panel_sel = pal_no * 4 + 1
        self._refresh()
        self._refresh_title_palette_panel()
        self._preview_status.setText(
            t(
                "title_screen.palette_panel.block_changed",
                "16x16色変更: x={x}, y={y} / パレット {palette}",
            ).format(x=col, y=row, palette=pal_no + 1))

    def _set_title_palette_slot_color(self, nes_idx):
        colors = self._title_palette()
        sel = int(getattr(self, "_palette_panel_sel", 0)) & 0x0F
        colors[sel] = int(nes_idx) & 0x3F
        try:
            self._apply_title_palette_colors(colors)
        except Exception as e:
            QMessageBox.critical(
                self,
                t("title_screen.palette_panel.change_unavailable", "パレット変更不可"),
                t(
                    "title_screen.palette_panel.write_failed",
                    "タイトルパレットを書き換えられませんでした:\n{error}",
                ).format(error=f"{type(e).__name__}: {e}"))
            return
        self._refresh_title_palette_panel()
        self._preview_status.setText(
            t(
                "title_screen.palette_panel.slot_changed",
                "パレット変更: パレット {palette} / slot {slot} = ${value:02X}",
            ).format(palette=sel // 4 + 1, slot=sel % 4, value=colors[sel] & 0x3F))

    def _refresh_picker_grid(self, *_):
        if not hasattr(self, "_picker_scroll"):
            return
        old_v = self._picker_scroll.verticalScrollBar().value()
        items = self._title_picker_items()
        if not items:
            self._picker_scroll.setWidget(
                QLabel(t("title_screen.character_picker.no_frames", "ROMフレームが見つかりません。"))
            )
            return
        zoom = 3
        cell_w = 16 * zoom + 24
        cell_h = 16 * zoom + 20
        gap = 6
        viewport_w = max(1, self._picker_scroll.viewport().width())
        cols = max(3, min(12, (viewport_w - gap) // (cell_w + gap)))
        rows = (len(items) + cols - 1) // cols
        img = QImage(cols * (cell_w + gap) + gap,
                     rows * (cell_h + gap) + gap,
                     QImage.Format_ARGB32)
        img.fill(QColor(28, 28, 28))
        pal = int(self._picker_palette.currentData()) & 0x03
        for i, (g, s, fi, t1, t2, attr) in enumerate(items):
            ox = gap + (i % cols) * (cell_w + gap) + 6
            oy = gap + (i // cols) * (cell_h + gap) + 4
            self._draw_title_picker_frame(img, zoom, ox, oy, t1, t2, attr, pal)
        painter = QPainter(img)
        painter.setPen(QColor(190, 190, 190))
        selected_key = None
        pending = getattr(self, "_pending_title_character", None)
        if pending:
            selected_key = (pending.get("tile1"), pending.get("tile2"), pending.get("attr"))
        for i, (g, s, fi, t1, t2, attr) in enumerate(items):
            x = gap + (i % cols) * (cell_w + gap)
            y = gap + (i // cols) * (cell_h + gap)
            painter.drawText(x + 3, y + cell_h - 4, f"g{g:02X}s{s:02X}f{fi}")
            if selected_key == (t1, t2, attr):
                pen = QPen(QColor(255, 230, 60), 3)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(x, y, cell_w - 1, cell_h - 1)
                painter.setPen(QColor(190, 190, 190))
        painter.end()
        lbl = TitleCharacterGridLabel(len(items), cols, cell_w, cell_h, gap)
        lbl.setPixmap(QPixmap.fromImage(img))
        lbl.frame_clicked.connect(self._pick_title_character_index)
        self._picker_scroll.setWidget(lbl)
        self._picker_scroll.verticalScrollBar().setValue(old_v)

    def _pick_title_character_index(self, index):
        items = self._title_picker_items()
        if not (0 <= int(index) < len(items)):
            return
        g, s, fi, t1, t2, attr = items[int(index)]
        self._pending_title_character = {
            "group": g,
            "state": s,
            "frame": fi,
            "tile1": t1,
            "tile2": t2,
            "attr": attr,
            "palette": int(self._picker_palette.currentData()) & 0x03,
        }
        self._picker_status.setText(
            t(
                "title_screen.character_panel.selection_status",
                "選択: g{group:02X} s{state:02X} f{frame} / "
                "{count_text} / キャンバスをクリックして配置",
            ).format(
                group=g,
                state=s,
                frame=fi,
                count_text=self._title_character_count_text(),
            ))
        self._refresh_picker_grid()

    def _restore_preview_status(self):
        self._preview_status.setText(getattr(self, "_preview_status_text", ""))

    def _on_canvas_zoom_wheel(self, step):
        self._cancel_palette_block_context()
        idx = self._zoom.currentIndex()
        next_idx = max(0, min(self._zoom.count() - 1, idx + int(step)))
        if next_idx != idx:
            self._zoom.setCurrentIndex(next_idx)

    def _on_title_character_drag_start(self, row, col, modifiers=0):
        self._cancel_palette_block_context()
        dx, dy = _ppu_pixel_to_display(int(col) * 8, int(row) * 8)
        slot = self._title_character_at_display(dx, dy)
        if slot is None:
            self._drag_title_character_slot = None
            return
        self._drag_title_character_slot = int(slot)
        self._selected_title_character_slot = int(slot)
        self._preview_status.setText(
            t(
                "title_screen.character.moving_status",
                "キャラスロット {slot} を移動中",
            ).format(slot=int(slot) + 1))
        self._refresh()

    def _on_title_character_drag_move(self, row, col):
        slot = getattr(self, "_drag_title_character_slot", None)
        if slot is None:
            return
        dx, dy = _ppu_pixel_to_display(int(col) * 8, int(row) * 8)
        snap = bytes(self._rom)
        try:
            TS.move_title_character(self._rom, int(slot), dx, dy)
        except Exception as e:
            self._rom[:] = snap
            self._drag_title_character_slot = None
            QMessageBox.critical(
                self, t("title_screen.character.move_failed", "キャラクター移動失敗"),
                f"{type(e).__name__}: {e}")
            return
        self._changed = True
        self._selected_title_character_slot = int(slot)
        self._refresh()

    def _on_title_character_drag_end(self):
        if getattr(self, "_drag_title_character_slot", None) is not None:
            self._preview_status.setText(
                t(
                    "title_screen.character.moved_status",
                    "キャラスロット {slot} を移動しました",
                ).format(slot=int(self._drag_title_character_slot) + 1))
        self._drag_title_character_slot = None

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            self._on_remove_selected_title_character()
            event.accept()
            return
        super().keyPressEvent(event)

    def _on_preview_tile_hovered(self, row, col, stream, bank_tile, file_start, file_end):
        pending = getattr(self, "_pending_stamp", None)
        if pending:
            self._preview_status.setText(
                t(
                    "title_screen.preview.pending_stamp",
                    "貼り付け待ち: {width}x{height}px ({tile_w}x{tile_h} tiles) / "
                    "クリック位置 ({col}, {row})",
                ).format(
                    width=pending["width"],
                    height=pending["height"],
                    tile_w=pending["tile_w"],
                    tile_h=pending["tile_h"],
                    col=col,
                    row=row,
                ))
            return
        dx, dy = _ppu_pixel_to_display(col * 8, row * 8)
        hit = self._title_character_at_display(dx, dy)
        pending_ch = getattr(self, "_pending_title_character", None)
        if pending_ch:
            self._preview_status.setText(
                t(
                    "title_screen.preview.pending_character",
                    "キャラ配置待ち: g{group:02X} s{state:02X} f{frame} / x={x}, y={y}",
                ).format(
                    group=pending_ch["group"],
                    state=pending_ch["state"],
                    frame=pending_ch["frame"],
                    x=dx,
                    y=dy,
                ))
            return
        pending_tile = getattr(self, "_pending_title_tile_stream", None)
        if pending_tile is not None:
            stream = int(pending_tile) & 0xFF
            self._preview_status.setText(
                t(
                    "title_screen.preview.pending_tile",
                    "タイル配置待ち: cell ({col}, {row}) / stream ${stream:02X} / bank内 0x{bank:03X}",
                ).format(col=col, row=row, stream=stream, bank=(_BG_BASE + stream)))
            return
        if hit is not None:
            self._preview_status.setText(
                t(
                    "title_screen.preview.character_hit",
                    "キャラスロット {slot}/{max} / x={x}, y={y}",
                ).format(slot=hit + 1, max=TS.title_character_max(), x=dx, y=dy))
            return
        self._preview_status.setText(
            f"cell ({col}, {row}) / stream 0x{stream:02X} / "
            f"bank 0x{bank_tile:03X} / ROM 0x{file_start:X}-0x{file_end:X}")

    def _on_preview_tile_clicked(self, row, col, modifiers=0):
        self._cancel_palette_block_context()
        dx, dy = _ppu_pixel_to_display(col * 8, row * 8)
        pending_ch = getattr(self, "_pending_title_character", None)
        if pending_ch:
            snap = bytes(self._rom)
            try:
                chg = TS.add_title_character(
                    self._rom, dx, dy, pending_ch["tile1"], pending_ch["tile2"],
                    pending_ch["attr"], pending_ch["palette"])
            except (TS.TitleScreenError, ValueError) as e:
                self._rom[:] = snap
                QMessageBox.critical(
                    self,
                    t("title_screen.character.place_unavailable", "キャラクター配置不可"),
                    str(e),
                )
                return
            except Exception as e:
                self._rom[:] = snap
                QMessageBox.critical(
                    self,
                    t("title_screen.character.place_failed", "キャラクター配置失敗"),
                    f"{type(e).__name__}: {e}")
                return
            self._pending_title_character = None
            self._changed = True
            self._selected_title_character_slot = self._title_character_at_display(dx, dy)
            self._refresh()
            self._preview_status.setText(
                f"{' / '.join(chg)} / {self._title_character_count_text()}")
            return
        pending_tile = getattr(self, "_pending_title_tile_stream", None)
        if pending_tile is not None:
            self._place_title_tile(row, col, int(pending_tile) & 0xFF)
            return
        hit = self._title_character_at_display(dx, dy)
        if hit is not None:
            self._select_title_character_slot(hit)
            return
        pending = getattr(self, "_pending_stamp", None)
        if not pending:
            self._on_edit_title_tile(row, col)
            return
        if row + pending["tile_h"] > (_IMG_H // 8) or \
                col + pending["tile_w"] > _NT_W:
            QMessageBox.warning(
                self,
                t("title_screen.stamp.unavailable", "貼り付け不可"),
                t(
                    "title_screen.stamp.out_of_bounds",
                    "貼り付け先が画面外にはみ出します。\n"
                    "クリック位置: x={x}, y={y}\n"
                    "画像サイズ: {tile_w}x{tile_h} tiles",
                ).format(
                    x=col,
                    y=row,
                    tile_w=pending["tile_w"],
                    tile_h=pending["tile_h"],
                ))
            return
        snap = bytes(self._rom)
        try:
            self._guard_image_16x16_colors(
                pending["image"], start_row=row, start_col=col)
            patterns, tile_w, tile_h = self._tile_patterns_from_image_at(
                pending["image"], row, col)
            chg = TS.apply_title_stamp_cells(
                self._rom, patterns, row, col, tile_w, tile_h)
        except TitlePngColorGuardError as e:
            self._rom[:] = snap
            TitlePngColorGuardDialog(e, self).exec_()
            return
        except (TS.TitleScreenError, ValueError) as e:
            self._rom[:] = snap
            QMessageBox.critical(
                self,
                t("title_screen.stamp.failed", "貼り付け失敗"),
                str(e),
            )
            return
        except Exception as e:
            self._rom[:] = snap
            QMessageBox.critical(
                self,
                t("title_screen.stamp.failed", "貼り付け失敗"),
                f"{type(e).__name__}: {e}")
            return
        self._pending_stamp = None
        self._changed = True
        self._refresh()
        QMessageBox.information(
            self,
            t("title_screen.top_png.paste_complete.title", "Top PNG貼り付け完了"),
            "\n".join(chg),
        )

    def _place_title_tile(self, row, col, stream):
        snap = bytes(self._rom)
        try:
            chg = TS.set_title_tile_cell(self._rom, row, col, stream)
        except (TS.TitleScreenError, ValueError) as e:
            self._rom[:] = snap
            QMessageBox.critical(
                self,
                t("title_screen.tile.place_unavailable", "タイル配置不可"),
                str(e),
            )
            return
        except Exception as e:
            self._rom[:] = snap
            QMessageBox.critical(
                self,
                t("title_screen.tile.place_failed", "タイル配置失敗"),
                f"{type(e).__name__}: {e}")
            return
        self._changed = True
        self._refresh()
        self._pending_title_tile_stream = int(stream) & 0xFF
        self._refresh_title_tile_picker()
        self._preview_status.setText(
            f"{' / '.join(chg)} / cell ({int(col)}, {int(row)})")

    def _title_tile_at_cell(self, row, col):
        d = TS.decode_title_grid(self._rom)
        grid = d["grid"]
        cell = int(row) * _NT_W + int(col)
        if not (0 <= cell < len(grid)):
            raise ValueError("cell is outside title grid")
        stream = int(grid[cell]) & 0xFF
        bank_tile = (_BG_BASE + stream) & 0x1FF
        off = TS.chr_bank3_offset(self._rom)
        pos = off + bank_tile * 0x10
        if pos + 0x10 > len(self._rom):
            raise ValueError("CHR tile is outside ROM")
        return grid, stream, bank_tile, off, pos

    def _title_tile_pixels(self, pos):
        from ..nes.tile import NesTile
        return [list(row) for row in NesTile(bytes(self._rom[pos:pos + 0x10])).pixels]

    def _write_title_tile_pixels(self, pos, pixels):
        enc = _encode_tile_2bpp(pixels)
        if bytes(self._rom[pos:pos + 0x10]) != enc:
            self._rom[pos:pos + 0x10] = enc

    def _title_tile_palette_colors(self, row, col):
        pal = self._title_palette()
        pal_no = self._attr_palette_no(self._title_attributes(), row, col)
        colors = []
        for idx in range(4):
            nes_idx = pal[0] if idx == 0 else pal[pal_no * 4 + idx]
            colors.append(NES_COLORS[nes_idx & 0x3F])
        return colors, pal_no

    @staticmethod
    def _title_tile_ref_count(grid, stream):
        target = int(stream) & 0xFF
        return sum(1 for value in grid if (int(value) & 0xFF) == target)

    def _on_edit_title_tile(self, row, col):
        try:
            grid, stream, bank_tile, chr_off, pos = self._title_tile_at_cell(row, col)
            pixels = self._title_tile_pixels(pos)
            colors, pal_no = self._title_tile_palette_colors(row, col)
        except Exception as e:
            QMessageBox.critical(
                self,
                t("title_screen.tile.edit_unavailable", "8x8編集不可"),
                f"{type(e).__name__}: {e}")
            return
        self._highlight_tile.setValue(bank_tile)
        ref_count = self._title_tile_ref_count(grid, stream)
        del colors
        self._show_title_tile_editor_panel(
            row, col, grid, stream, bank_tile, pos, pixels, pal_no, ref_count)

    def _on_attr_block_clicked(self, row, col):
        if row < 0 or col < 0 or row + 1 >= (_IMG_H // 8) or col + 1 >= _NT_W:
            return
        self._show_title_palette_panel(row, col)
        current = self._attr_palette_no(self._title_attributes(), row, col)
        self._group_overlay.setCurrentIndex(current + 1)
        self._preview_status.setText(
            t(
                "title_screen.palette_panel.block_target",
                "16x16色対象: x={x}, y={y} / パレット {palette}",
            ).format(x=col, y=row, palette=current + 1))

    def _on_replace_attr_group(self):
        self._cancel_palette_block_context()
        src = int(self._group_from.currentData()) & 0x03
        dst = int(self._group_to.currentData()) & 0x03
        if src == dst:
            QMessageBox.information(
                self,
                t("title_screen.palette_group_replace.title", "色グループ置換"),
                t(
                    "title_screen.palette_group_replace.same",
                    "置換元と置換先が同じです。変更はありません。",
                ))
            return
        attr = self._title_attributes()
        changed_blocks = 0
        for by in range(_IMG_H // 16):
            row = by * 2
            for bx in range(_IMG_W // 16):
                col = bx * 2
                if self._attr_palette_no(attr, row, col) != src:
                    continue
                for rr in (row, row + 1):
                    for cc in (col, col + 1):
                        self._set_title_attr_palette_no(attr, rr, cc, dst)
                changed_blocks += 1
        if changed_blocks == 0:
            QMessageBox.information(
                self,
                t("title_screen.palette_group_replace.title", "色グループ置換"),
                t(
                    "title_screen.palette_group_replace.none",
                    "色グループ {group} を使う16x16区画はありません。",
                ).format(group=src))
            return
        self._write_title_attributes(attr)
        self._changed = True
        self._group_overlay.setCurrentIndex(dst + 1)
        self._refresh()
        self._preview_status.setText(
            t(
                "title_screen.palette_group_replace.status",
                "色グループ置換: {src} -> {dst} / {count}区画",
            ).format(src=src, dst=dst, count=changed_blocks))

    # --- 操作 ---
    def _apply_title_palette_colors(self, colors):
        self._set_title_palette(colors)
        self._changed = True
        self._refresh()

    def _on_edit_title_palette(self):
        self._show_title_palette_panel()

    def _on_save_image(self):
        from .file_dialog_compat import get_path
        path = get_path(
            self,
            title=t("title_screen.save_image.dialog_title", "タイトル画面を画像保存"),
            directory="title_screen.png",
            filter="PNG (*.png);;BMP (*.bmp)",
            mode="save",
            app_config=self._app_config,
            config_key="title_screen_image_save",
        )
        if not path:
            return
        img = self._build_image(color=False)
        if not img.save(path):
            QMessageBox.critical(
                self,
                t("title_screen.save.failed.title", "保存失敗"),
                t("title_screen.save_image.failed", "画像を保存できませんでした:\n{path}").format(path=path),
            )
            return
        QMessageBox.information(
            self,
            t("title_screen.save.complete.title", "保存完了"),
            t(
                "title_screen.save_image.complete",
                "タイトル画面 ({width}x{height}, 4階調) を保存:\n{path}",
            ).format(width=_IMG_W, height=_IMG_H, path=path))

    def _on_save_top_image_legacy_unused(self):
        from .file_dialog_compat import get_path
        path = get_path(
            self,
            title=t("title_screen.save_top.dialog_title", "タイトル上部PNGを保存"),
            directory="title_top_256x64.png",
            filter="PNG (*.png);;BMP (*.bmp)",
            mode="save",
            app_config=self._app_config,
            config_key="title_top_png_save",
        )
        if not path:
            return
        img = self._build_image(color=True).copy(0, _TOP_Y, _IMG_W, _TOP_H)
        if not img.save(path):
            QMessageBox.critical(
                self,
                t("title_screen.save.failed.title", "保存失敗"),
                t("title_screen.save_top.failed", "タイトル上部画像を保存できませんでした:\n{path}").format(path=path))
            return
        QMessageBox.information(
            self,
            t("title_screen.save.complete.title", "保存完了"),
            t(
                "title_screen.save_top.complete",
                "タイトル上部画像 ({width}x{height}, 4階調) を保存:\n{path}",
            ).format(width=_IMG_W, height=_TOP_H, path=path))

    def _on_save_top_image(self):
        self._cancel_palette_block_context()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        from .file_dialog_compat import get_path
        path = get_path(
            self,
            title="Save Top PNG",
            directory=f"title_top_256x64_{stamp}.png",
            filter="PNG (*.png);;BMP (*.bmp)",
            mode="save",
            app_config=self._app_config,
            config_key="title_top_png_save",
        )
        if not path:
            return
        path = self._ensure_timestamped_png(path, stamp)

        img = self._build_image(color=True).copy(0, _TOP_Y, _IMG_W, _TOP_H)
        if not img.save(path):
            QMessageBox.critical(
                self, "Save failed",
                f"Could not save top PNG:\n{path}")
            return

        side_path = self._sidecar_path(path)
        try:
            meta = TS.export_title_top_layout(self._rom)
            meta["created_at"] = datetime.now().isoformat(timespec="seconds")
            meta["image_file"] = os.path.basename(path)
            meta["image_mode"] = "color_rgb"
            with open(side_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.warning(
                self, "Sidecar save failed",
                "PNG was saved, but the layout sidecar JSON was not saved:\n"
                f"{type(e).__name__}: {e}")
            return

        QMessageBox.information(
            self, "Saved",
            f"Top PNG saved:\n{path}\n\nLayout sidecar JSON:\n{side_path}")

    @staticmethod
    def _nearest_idx(g):
        best, bd = 0, 1 << 30
        for i, gv in enumerate(_GRAY):
            d = abs(g - gv)
            if d < bd:
                bd, best = d, i
        return best

    def _guard_image_16x16_colors(self, img, start_row=0, start_col=0,
                                  display_top_y=None):
        """Reject imports that would need five or more colors in one attr block."""
        blocks = {}
        rects = {}
        for y in range(img.height()):
            for x in range(img.width()):
                if display_top_y is None:
                    row = start_row + (y // 8)
                    col = start_col + (x // 8)
                    sx = ((col // 2) * 16) - start_col * 8
                    sy = ((row // 2) * 16) - start_row * 8
                else:
                    ppu_x, ppu_y = _display_pixel_to_ppu(x, display_top_y + y)
                    row = ppu_y // 8
                    col = ppu_x // 8
                    dx, dy = _ppu_pixel_to_display((col // 2) * 16, (row // 2) * 16)
                    sx = dx
                    sy = dy - display_top_y
                key = (col // 2, row // 2)
                colors = blocks.setdefault(key, set())
                colors.add(self._pixel_rgb(img, x, y))
                rects.setdefault(key, (sx, sy))
        bad = [
            (bx, by, len(colors), rects[(bx, by)][0], rects[(bx, by)][1])
            for (bx, by), colors in sorted(blocks.items())
            if len(colors) > 4 and
            0 <= rects[(bx, by)][0] <= img.width() - 16 and
            0 <= rects[(bx, by)][1] <= img.height() - 16
        ]
        if not bad:
            return
        lines = [
            "PPU基準の16x16内に5色以上あるため取り込めません。",
            "NES背景attributeは16x16ごとに4色までです。",
            "このまま1色を潰すと絵柄が変わるため中止します。",
            "",
            "問題の16x16ブロック:",
        ]
        for bx, by, n, _sx, _sy in bad[:16]:
            dx, dy = _ppu_pixel_to_display(bx * 16, by * 16)
            lines.append(
                f"- attr ({bx},{by}) / 表示px ({dx},{dy}) / {n}色")
        if len(bad) > 16:
            lines.append(f"...ほか {len(bad) - 16} ブロック")
        raise TitlePngColorGuardError(
            "\n".join(lines), bad_blocks=bad, image=img,
            display_top_y=display_top_y)

    def _on_import_png(self):
        QMessageBox.information(
            self,
            t("title_screen.png_import.title", "PNG取り込み"),
            t(
                "title_screen.png_import.disabled",
                "全体PNG取り込みは現在停止しています。\n"
                "タイトル画像の読み込みは「Top PNG読み込み...」から、"
                "最大256x64の画像を指定してください。",
            ))

    def _cells_from_display_image(self, img):
        img = img.convertToFormat(QImage.Format_RGB32).scaled(
            _IMG_W, _IMG_H, Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation)
        W, H = _IMG_W, _IMG_H
        pal = self._title_palette()
        attr = self._title_attributes()
        attr_color_counts = {}
        for cell in range(_NT_W * (H // 8)):
            row, col = divmod(cell, _NT_W)
            counts = attr_color_counts.setdefault((col // 2, row // 2), Counter())
            ox, oy = col * 8, row * 8
            for y in range(8):
                for x in range(8):
                    sx, sy = _ppu_pixel_to_display(ox + x, oy + y)
                    counts[self._pixel_rgb(img, sx, sy)] += 1
        attr_color_maps = {}
        for (bx, by), counts in attr_color_counts.items():
            pal_no = self._attr_palette_no(attr, by * 2, bx * 2)
            rgb_choices = [
                NES_COLORS[pal[0] & 0x3F],
                NES_COLORS[pal[pal_no * 4 + 1] & 0x3F],
                NES_COLORS[pal[pal_no * 4 + 2] & 0x3F],
                NES_COLORS[pal[pal_no * 4 + 3] & 0x3F],
            ]
            attr_color_maps[(bx, by)] = self._distinct_palette_index_map(
                counts, rgb_choices)
        cells = []
        for cell in range(_NT_W * (H // 8)):
            row, col = divmod(cell, _NT_W)
            color_map = attr_color_maps[(col // 2, row // 2)]
            ox, oy = col * 8, row * 8
            pat = []
            for y in range(8):
                for x in range(8):
                    sx, sy = _ppu_pixel_to_display(ox + x, oy + y)
                    pat.append(color_map[self._pixel_rgb(img, sx, sy)])
            cells.append(pat)
        return cells

    def _tile_patterns_from_image_at(self, img, start_row, start_col):
        tile_w = img.width() // 8
        tile_h = img.height() // 8
        pal = self._title_palette()
        attr = self._title_attributes()
        attr_color_counts = {}
        for ty in range(tile_h):
            for tx in range(tile_w):
                row = start_row + ty
                col = start_col + tx
                counts = attr_color_counts.setdefault((col // 2, row // 2), Counter())
                for y in range(8):
                    for x in range(8):
                        counts[self._pixel_rgb(img, tx * 8 + x, ty * 8 + y)] += 1
        attr_color_maps = {}
        for (bx, by), counts in attr_color_counts.items():
            pal_no = self._attr_palette_no(attr, by * 2, bx * 2)
            rgb_choices = [
                NES_COLORS[pal[0] & 0x3F],
                NES_COLORS[pal[pal_no * 4 + 1] & 0x3F],
                NES_COLORS[pal[pal_no * 4 + 2] & 0x3F],
                NES_COLORS[pal[pal_no * 4 + 3] & 0x3F],
            ]
            attr_color_maps[(bx, by)] = self._distinct_palette_index_map(
                counts, rgb_choices)
        patterns = []
        for ty in range(tile_h):
            for tx in range(tile_w):
                row = start_row + ty
                col = start_col + tx
                color_map = attr_color_maps[(col // 2, row // 2)]
                pat = []
                for y in range(8):
                    for x in range(8):
                        rgb = self._pixel_rgb(img, tx * 8 + x, ty * 8 + y)
                        pat.append(color_map[rgb])
                patterns.append(pat)
        return patterns, tile_w, tile_h

    @staticmethod
    def _pixel_rgb(img, x, y):
        rgb = img.pixel(x, y)
        return ((rgb >> 16) & 0xFF, (rgb >> 8) & 0xFF, rgb & 0xFF)

    @staticmethod
    def _nearest_nes_color(rgb):
        r, g, b = rgb
        best, bd = 0, 1 << 60
        for i, (rr, gg, bb) in enumerate(NES_COLORS):
            d = ((int(r) - rr) * (int(r) - rr) +
                 (int(g) - gg) * (int(g) - gg) +
                 (int(b) - bb) * (int(b) - bb))
            if d < bd:
                best, bd = i, d
        return best & 0x3F

    def _reduce_image_to_four_nes_colors(self, img):
        counts = Counter()
        nearest_cache = {}
        for y in range(img.height()):
            for x in range(img.width()):
                rgb = self._pixel_rgb(img, x, y)
                idx = nearest_cache.get(rgb)
                if idx is None:
                    idx = self._nearest_nes_color(rgb)
                    nearest_cache[rgb] = idx
                counts[idx] += 1
        selected = [idx for idx, _count in counts.most_common(4)]
        if not selected:
            return img.copy()
        selected_rgbs = [NES_COLORS[idx & 0x3F] for idx in selected]
        out = QImage(img.width(), img.height(), QImage.Format_RGB32)
        color_cache = {}
        for y in range(img.height()):
            for x in range(img.width()):
                rgb = self._pixel_rgb(img, x, y)
                mapped = color_cache.get(rgb)
                if mapped is None:
                    mapped = min(
                        selected_rgbs,
                        key=lambda candidate: self._rgb_dist(rgb, candidate),
                    )
                    color_cache[rgb] = mapped
                out.setPixel(x, y, QColor(*mapped).rgb())
        return out

    @staticmethod
    def _load_image_with_pillow(path):
        try:
            from PIL import Image, ImageOps
        except Exception:
            return QImage()
        try:
            with Image.open(path) as pil_img:
                pil_img = ImageOps.exif_transpose(pil_img).convert("RGBA")
                data = pil_img.tobytes("raw", "RGBA")
                img = QImage(
                    data, pil_img.width, pil_img.height,
                    pil_img.width * 4, QImage.Format_RGBA8888,
                )
                return img.copy()
        except Exception:
            return QImage()

    def _top_png_canvas_from_source(self, source, draw_w, draw_h):
        draw_w = max(8, min(_IMG_W, int(draw_w)))
        draw_h = max(8, min(_TOP_H, int(draw_h)))
        draw_w = max(8, (draw_w // 8) * 8)
        draw_h = max(8, (draw_h // 8) * 8)
        pal = self._title_palette()
        bg = NES_COLORS[pal[0] & 0x3F]
        canvas = QImage(_IMG_W, _TOP_H, QImage.Format_RGB32)
        canvas.fill(QColor(*bg))
        scaled = source.scaled(
            draw_w, draw_h, Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation,
        ).convertToFormat(QImage.Format_RGB32)
        ox = ((_IMG_W - draw_w) // 16) * 8
        oy = ((_TOP_H - draw_h) // 16) * 8
        for y in range(draw_h):
            for x in range(draw_w):
                canvas.setPixel(ox + x, oy + y, scaled.pixel(x, y))
        return self._reduce_image_to_four_nes_colors(canvas), draw_w, draw_h

    def _oversized_top_png_candidates(self, source):
        seen = set()
        for tile_w in range(_NT_W, 0, -1):
            tile_h = max(1, min(_TOP_H // 8, round(tile_w * (_TOP_H // 8) / _NT_W)))
            key = (tile_w, tile_h)
            if key in seen:
                continue
            seen.add(key)
            yield self._top_png_canvas_from_source(source, tile_w * 8, tile_h * 8)

    def _set_title_attr_palette_no(self, attr, row, col, pal_no):
        ai = (row // 2) * 16 + (col // 2)
        if not (0 <= ai < len(attr)):
            return
        attr[ai] = pal_no & 0x03

    def _write_title_attributes(self, attr):
        TS.set_title_attribute_expanded(self._rom, attr)

    def _top_png_cells_from_indexed_image(self, top, color_to_index):
        cells = [[0] * 64 for _ in range(_NT_W * (_IMG_H // 8))]
        top_start = 6 * _NT_W
        top_end = 14 * _NT_W
        for ci in range(top_start, top_end):
            row, col = divmod(ci, _NT_W)
            ox, oy = col * 8, row * 8
            pat = []
            for y in range(8):
                for x in range(8):
                    sx, display_y = _ppu_pixel_to_display(ox + x, oy + y)
                    sy = display_y - _TOP_Y
                    if 0 <= sy < _TOP_H:
                        pat.append(color_to_index[self._pixel_rgb(top, sx, sy)])
                    else:
                        pat.append(0)
            cells[ci] = pat
        return cells

    @staticmethod
    def _rgb_dist(a, b):
        return sum((int(x) - int(y)) * (int(x) - int(y))
                   for x, y in zip(a, b))

    @staticmethod
    def _distinct_palette_index_map(color_counts, rgb_choices):
        colors = list(color_counts.keys())
        if len(colors) > 4:
            raise ValueError("internal error: 16x16 color guard was not applied")
        best_map = {}
        best_score = None
        for perm in permutations(range(4), len(colors)):
            score = 0
            for rgb, pi in zip(colors, perm):
                score += color_counts[rgb] * TitleScreenDialog._rgb_dist(
                    rgb, rgb_choices[pi])
            if best_score is None or score < best_score:
                best_score = score
                best_map = {rgb: pi for rgb, pi in zip(colors, perm)}
        return best_map

    def _unused_title_palette_no_outside_top(self, attr):
        counts = [0, 0, 0, 0]
        for row in range(_IMG_H // 8):
            if 6 <= row < 14:
                continue
            for col in range(_NT_W):
                counts[self._attr_palette_no(attr, row, col)] += 1
        unused = [i for i, count in enumerate(counts) if count == 0]
        if not unused:
            raise ValueError(
                "Top PNG用に使える未使用タイトルパレット枠がありません。"
                "既存の下側タイトル色を壊さないため中止します。")
        return min(unused, key=lambda i: 0 if i == 2 else 1)

    def _try_top_png_4color_cells(self, top):
        counts = Counter(
            self._pixel_rgb(top, x, y)
            for y in range(top.height())
            for x in range(top.width())
        )
        if len(counts) > 4:
            return None, []

        pal = self._title_palette()
        attr = self._title_attributes()
        pal_no = self._unused_title_palette_no_outside_top(attr)

        # Keep the universal background color untouched.  Pick the source color
        # closest to the current universal color for pixel index 0, then place
        # the other PNG colors into the selected BG palette's three local slots.
        universal_rgb = NES_COLORS[pal[0] & 0x3F]
        colors = [rgb for rgb, _n in counts.most_common()]
        zero_rgb = min(colors, key=lambda rgb: self._rgb_dist(rgb, universal_rgb))
        rest = [rgb for rgb in colors if rgb != zero_rgb]
        color_to_index = {zero_rgb: 0}
        base = pal_no * 4
        for i, rgb in enumerate(rest[:3], start=1):
            color_to_index[rgb] = i
            pal[base + i] = self._nearest_nes_color(rgb)
        self._set_title_palette(pal)

        for row in range(6, 14):
            for col in range(_NT_W):
                self._set_title_attr_palette_no(attr, row, col, pal_no)
        self._write_title_attributes(attr)

        cells = self._top_png_cells_from_indexed_image(top, color_to_index)
        msg = [
            f"4-color top PNG path: {len(counts)} colors, palette #{pal_no} updated",
            f"source image kept at original size: {top.width()}x{top.height()}",
            "universal background color kept; only top title attributes were retargeted",
        ]
        return cells, msg

    def _on_import_top_png_legacy_unused(self):
        path = self._pick_open(
            "タイトル上部画像を選択 (PNG/BMP, 256x64推奨)", "*.png;*.bmp")
        if not path:
            return
        top = QImage(path)
        if top.isNull():
            QMessageBox.critical(
                self,
                t("title_screen.load.unavailable", "読み込み不可"),
                t("title_screen.load.image_failed", "画像を読み込めません:\n{path}").format(path=path))
            return
        top = top.convertToFormat(QImage.Format_RGB32).scaled(
            _IMG_W, _TOP_H, Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation)
        full = self._build_image(color=False).convertToFormat(QImage.Format_RGB32)
        for y in range(_TOP_H):
            for x in range(_IMG_W):
                full.setPixel(x, _TOP_Y + y, top.pixel(x, y))
        try:
            chg = TS.apply_title_image(self._rom,
                                       self._cells_from_display_image(full))
        except (TS.TitleScreenError, ValueError) as e:
            QMessageBox.critical(
                self,
                t("title_screen.load.unavailable", "読み込み不可"),
                str(e),
            )
            return
        except Exception as e:
            QMessageBox.critical(
                self,
                t("title_screen.load.failed", "読み込み失敗"),
                f"{type(e).__name__}: {e}")
            return
        self._changed = True
        self._refresh()
        QMessageBox.information(
            self,
            t("title_screen.top_png.load_complete.title", "Top PNG読み込み完了"),
            "\n".join(chg)
            + "\n\n"
            + t(
                "title_screen.top_png.load_complete.scope",
                "対象: x=0..255, y=49..112。下半分の山/神殿側は触りません。",
            ))

    def _on_import_top_png(self):
        self._cancel_palette_block_context()
        path = self._pick_open(
            "Open Top Image (PNG/BMP/JPEG)", "*.png;*.bmp;*.jpg;*.jpeg")
        if not path:
            return
        top = QImage(path)
        if top.isNull():
            top = self._load_image_with_pillow(path)
        if top.isNull():
            QMessageBox.critical(
                self,
                t("title_screen.load.image_open_failed.title", "画像読み込み失敗"),
                t("title_screen.load.image_open_failed", "画像を開けません:\n{path}").format(path=path))
            return
        original_size = (top.width(), top.height())
        oversized = top.width() > _IMG_W or top.height() > _TOP_H
        if top.width() <= 0 or top.height() <= 0:
            QMessageBox.critical(
                self,
                t("title_screen.top_png.import_failed.title", "Top PNG取り込み失敗"),
                t(
                    "title_screen.top_png.invalid_size",
                    "画像サイズが不正です: {width}x{height}",
                ).format(width=top.width(), height=top.height()))
            return
        if not oversized and (
                top.width() % 8 != 0 or top.height() % 8 != 0
        ):
            QMessageBox.critical(
                self,
                t("title_screen.top_png.import_failed.title", "Top PNG取り込み失敗"),
                t(
                    "title_screen.top_png.size_not_multiple",
                    "Top PNGとして読み込める画像は、幅と高さが8の倍数である必要があります。\n"
                    "指定画像: {width}x{height}",
                ).format(width=top.width(), height=top.height()))
            return
        source_top = top.convertToFormat(QImage.Format_RGB32)
        top = source_top
        if oversized:
            top, _draw_w, _draw_h = self._top_png_canvas_from_source(
                source_top, _IMG_W, _TOP_H
            )
        if top.width() != _IMG_W or top.height() != _TOP_H:
            self._pending_stamp = {
                "image": top.copy(),
                "width": top.width(),
                "height": top.height(),
                "tile_w": top.width() // 8,
                "tile_h": top.height() // 8,
            }
            self._preview_status.setText(
                t(
                    "title_screen.top_png.pending_stamp_status",
                    "貼り付け待ち: {width}x{height}px ({tile_w}x{tile_h} tiles) / "
                    "プレビュー上の貼り付け開始位置をクリック",
                ).format(
                    width=top.width(),
                    height=top.height(),
                    tile_w=top.width() // 8,
                    tile_h=top.height() // 8,
                ))
            QMessageBox.information(
                self,
                t("title_screen.top_png.pick_paste_position.title", "貼り付け位置を指定"),
                t(
                    "title_screen.top_png.pick_paste_position.body",
                    "読み込んだ画像は256x64より小さいため、まだROMへ適用していません。\n"
                    "タイトルプレビュー上で貼り付け開始位置をクリックしてください。",
                ))
            return
        snap = bytes(self._rom)
        last_error = None
        try:
            candidates = (
                self._oversized_top_png_candidates(source_top)
                if oversized else ((top, top.width(), top.height()),)
            )
            for candidate, draw_w, draw_h in candidates:
                self._rom[:] = snap
                self._guard_image_16x16_colors(candidate, display_top_y=_TOP_Y)
                cells, pre_msgs = self._try_top_png_4color_cells(candidate)
                if cells is None:
                    full = QImage(_IMG_W, _IMG_H, QImage.Format_RGB32)
                    pal = self._title_palette()
                    bg = NES_COLORS[pal[0] & 0x3F]
                    full.fill(QColor(*bg))
                    for y in range(candidate.height()):
                        for x in range(candidate.width()):
                            full.setPixel(x, _TOP_Y + y, candidate.pixel(x, y))
                    cells = self._cells_from_display_image(full)
                    pre_msgs = [
                        "multi-color top PNG path: existing title palette used",
                        f"source image kept at original size: {candidate.width()}x{candidate.height()}",
                    ]
                if oversized:
                    resize_msg = (
                        f"source image resized from "
                        f"{original_size[0]}x{original_size[1]} to "
                        f"{draw_w}x{draw_h} on a 256x64 top canvas and reduced to 4 colors"
                    )
                    pre_msgs = [
                        resize_msg if msg.startswith("source image kept at original size:")
                        else msg
                        for msg in pre_msgs
                    ]
                try:
                    chg = TS.apply_title_top_image_from_png(
                        self._rom, cells)
                    break
                except TS.TitleScreenError as e:
                    last_error = e
                    if oversized and "自由CHR枠の空きが足りません" in str(e):
                        continue
                    raise
            else:
                raise last_error or TS.TitleScreenError("画像を取り込めませんでした。")
        except TitlePngColorGuardError as e:
            self._rom[:] = snap
            TitlePngColorGuardDialog(e, self).exec_()
            return
        except (TS.TitleScreenError, ValueError) as e:
            self._rom[:] = snap
            QMessageBox.critical(
                self,
                t("title_screen.top_png.import_failed.title", "Top PNG取り込み失敗"),
                str(e),
            )
            return
        except Exception as e:
            self._rom[:] = snap
            QMessageBox.critical(
                self,
                t("title_screen.top_png.import_failed.title", "Top PNG取り込み失敗"),
                f"{type(e).__name__}: {e}")
            return
        self._changed = True
        self._refresh()
        QMessageBox.information(
            self,
            t("title_screen.top_png.import_complete.title", "Top PNG取り込み完了"),
            "\n".join(pre_msgs + chg))

    @staticmethod
    def _sidecar_path(path):
        base, _ext = os.path.splitext(path)
        return base + ".json"

    @staticmethod
    def _ensure_timestamped_png(path, stamp):
        d, name = os.path.split(path)
        base, ext = os.path.splitext(name)
        if not ext:
            ext = ".png"
        if _STAMP_RE.search(base):
            return os.path.join(d, base + ext)
        return os.path.join(d, f"{base}_{stamp}{ext}")

    def _try_apply_top_sidecar(self, png_path):
        side = self._sidecar_path(png_path)
        if not os.path.exists(side):
            return []
        with open(side, "r", encoding="utf-8") as f:
            meta = json.load(f)
        if meta.get("format") != _TOP_SIDE_FORMAT:
            raise TS.TitleScreenError(
                f"Top PNG sidecar format mismatch: {side}")
        return TS.apply_title_top_layout(self._rom, meta)

    def _pick_open(self, title, filt):
        from .file_dialog_compat import get_file
        return get_file(
            self,
            title=title,
            filter=filt,
            app_config=self._app_config,
            config_key="title_source_rom_open",
        )

    def _on_pick_title_character(self):
        self._cancel_palette_block_context()
        self._show_title_character_picker_panel()

    def _on_show_title_tile_picker(self):
        self._cancel_palette_block_context()
        self._show_title_tile_picker_panel()

    def _on_clear_title_characters(self):
        self._cancel_palette_block_context()
        if QMessageBox.question(
                self,
                t("title_screen.character.clear_all.title", "キャラ全削除"),
                t(
                    "title_screen.character.clear_all.confirm",
                    "タイトル上に配置した静止キャラを全て消します。",
                )) != QMessageBox.Yes:
            return
        snap = bytes(self._rom)
        try:
            chg = TS.clear_title_characters(self._rom)
        except (TS.TitleScreenError, ValueError) as e:
            self._rom[:] = snap
            QMessageBox.critical(
                self,
                t("title_screen.character.delete_unavailable", "キャラ削除不可"),
                str(e),
            )
            return
        except Exception as e:
            self._rom[:] = snap
            QMessageBox.critical(
                self,
                t("title_screen.character.delete_failed", "キャラ削除失敗"),
                f"{type(e).__name__}: {e}")
            return
        self._pending_title_character = None
        self._selected_title_character_slot = None
        self._changed = True
        self._refresh()
        self._preview_status.setText(
            f"{' / '.join(chg)} / {self._title_character_count_text()}")

    def _on_remove_selected_title_character(self):
        self._cancel_palette_block_context()
        slot = getattr(self, "_selected_title_character_slot", None)
        if slot is None:
            return
        snap = bytes(self._rom)
        try:
            TS.remove_title_character(self._rom, int(slot))
        except (TS.TitleScreenError, ValueError) as e:
            self._rom[:] = snap
            QMessageBox.critical(
                self,
                t("title_screen.character.delete_unavailable", "キャラ削除不可"),
                str(e),
            )
            return
        except Exception as e:
            self._rom[:] = snap
            QMessageBox.critical(
                self,
                t("title_screen.character.delete_failed", "キャラ削除失敗"),
                f"{type(e).__name__}: {e}")
            return
        slots = self._active_title_character_slots()
        self._selected_title_character_slot = slots[0] if slots else None
        self._changed = True
        self._refresh()
        self._preview_status.setText(
            t(
                "title_screen.character.deleted_status",
                "選択キャラを削除しました / {count_text}",
            ).format(count_text=self._title_character_count_text()))

    def _on_edit_title_texts(self):
        self._cancel_palette_block_context()
        keep_geo = self.geometry()

        def restore_editor_geometry():
            if not keep_geo.isNull():
                self.setGeometry(keep_geo)

        try:
            cur_extra = TS.read_title_text_line(self._rom)
        except Exception:
            cur_extra = ""
        try:
            cur_push = TS.read_title_push_start_text(self._rom)
        except (TS.TitleScreenError, ValueError) as e:
            QMessageBox.critical(
                self,
                t("title_screen.text.edit_unavailable", "文字編集不可"),
                str(e),
            )
            return
        except Exception as e:
            QMessageBox.critical(
                self,
                t("title_screen.text.push_read_failed", "PUSH START文字読込失敗"),
                f"{type(e).__name__}: {e}")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(t("title_screen.text.dialog_title", "タイトル文字編集"))
        dlg.setMinimumWidth(660)
        lay = QVBoxLayout(dlg)
        note = QLabel(
            t(
                "title_screen.text.input_note",
                "A-Z / 0-9 / スペース / , . \" が使えます。最大32文字。",
            ))
        note.setStyleSheet("color:#888; font-size:11px;")
        lay.addWidget(note)
        extra_head = QHBoxLayout()
        extra_head.addWidget(QLabel(
            t("title_screen.text.extra_short_label", "追加文字")))
        extra_count = QLabel("")
        extra_count.setStyleSheet("color:#c33;")
        extra_count.setMinimumWidth(56)
        extra_head.addStretch()
        extra_head.addWidget(extra_count)
        lay.addLayout(extra_head)
        extra_edit = QLineEdit(cur_extra[:32])
        extra_edit.setMaxLength(32)
        lay.addWidget(extra_edit)
        push_head = QHBoxLayout()
        push_head.addWidget(QLabel(
            t("title_screen.text.push_short_label", "PUSH START位置の固定文字")))
        push_count = QLabel("")
        push_count.setStyleSheet("color:#c33;")
        push_count.setMinimumWidth(56)
        push_head.addStretch()
        push_head.addWidget(push_count)
        lay.addLayout(push_head)
        push_combo = QComboBox()
        push_combo.setEditable(True)
        for text in _TITLE_PUSH_TEXT_PRESETS:
            push_combo.addItem(text)
        if push_combo.lineEdit() is not None:
            push_combo.lineEdit().setMaxLength(32)
        push_combo.setCurrentText(cur_push[:32])
        lay.addWidget(push_combo)
        status = QLabel("")
        lay.addWidget(status)
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        lay.addWidget(buttons)

        snap = bytes(self._rom)
        preview_changes = []

        def update_counts():
            extra_count.setText(f"{len(extra_edit.text())} / 32")
            push_count.setText(f"{len(push_combo.currentText())} / 32")

        def apply_preview():
            nonlocal preview_changes
            update_counts()
            self._rom[:] = snap
            try:
                changes = []
                changes.extend(TS.add_title_text_line(
                    self._rom, extra_edit.text(), row=14))
                changes.extend(TS.set_title_push_start_text(
                    self._rom, push_combo.currentText()))
            except (TS.TitleScreenError, ValueError) as e:
                self._rom[:] = snap
                status.setText(
                    t("title_screen.input_error", "入力エラー: {error}").format(error=e)
                )
                self._refresh()
                restore_editor_geometry()
                preview_changes = []
                return False
            except Exception as e:
                self._rom[:] = snap
                status.setText(
                    t("title_screen.input_error", "入力エラー: {error}").format(
                        error=f"{type(e).__name__}: {e}"
                    )
                )
                self._refresh()
                restore_editor_geometry()
                preview_changes = []
                return False
            preview_changes = changes
            status.setText(t("title_screen.text.previewing", "プレビュー反映中"))
            self._refresh()
            restore_editor_geometry()
            return True

        update_counts()
        extra_edit.textChanged.connect(lambda *_: apply_preview())
        push_combo.currentTextChanged.connect(lambda *_: apply_preview())

        if dlg.exec_() != QDialog.Accepted:
            self._rom[:] = snap
            self._refresh()
            restore_editor_geometry()
            return

        if not apply_preview():
            self._rom[:] = snap
            QMessageBox.critical(
                self,
                t("title_screen.text.edit_unavailable", "文字編集不可"),
                status.text(),
            )
            restore_editor_geometry()
            return
        self._changed = True
        self._refresh()
        restore_editor_geometry()
        self._preview_status.setText(
            t("title_screen.text.updated", "タイトル文字を更新しました")
        )

    def _on_add_title_text(self):
        self._on_edit_title_texts()

    def _on_edit_push_start_text(self):
        try:
            cur = TS.read_title_push_start_text(self._rom)
        except (TS.TitleScreenError, ValueError) as e:
            QMessageBox.critical(
                self,
                t("title_screen.text.push_unavailable", "PUSH START文字不可"),
                str(e),
            )
            return
        except Exception as e:
            QMessageBox.critical(
                self,
                t("title_screen.text.push_read_failed", "PUSH START文字読込失敗"),
                f"{type(e).__name__}: {e}")
            return
        text, ok = QInputDialog.getText(
            self,
            t("title_screen.text.push_input_title", "PUSH START文字"),
            t(
                "title_screen.text.push_input_label",
                "PUSH START BUTTON位置の固定文字 "
                "(A-Z / 0-9 / スペース / , . \"、最大32文字):",
            ),
            text=cur)
        if not ok:
            return
        snap = bytes(self._rom)
        try:
            chg = TS.set_title_push_start_text(self._rom, text)
        except (TS.TitleScreenError, ValueError) as e:
            self._rom[:] = snap
            QMessageBox.critical(
                self,
                t("title_screen.text.push_unavailable", "PUSH START文字不可"),
                str(e),
            )
            return
        except Exception as e:
            self._rom[:] = snap
            QMessageBox.critical(
                self,
                t("title_screen.text.push_change_failed", "PUSH START文字変更失敗"),
                f"{type(e).__name__}: {e}")
            return
        self._changed = True
        self._refresh()
        self._preview_status.setText(" / ".join(chg))

    def _on_revert(self):
        if bytes(self._rom) == self._snap:
            return
        self._rom[:] = self._snap
        self._changed = False
        self._refresh()
        self._reload_ending_text_edits()
        self._reload_clear_screen_controls()
        QMessageBox.information(
            self,
            t("title_screen.revert.title", "取り消し"),
            t("title_screen.revert.complete", "開いた時点の ROM に戻しました。"),
        )

    def _reload_clear_screen_controls(self):
        combo = getattr(self, "_clear_screen_combo", None)
        if combo is None or not combo.isEnabled():
            self._reload_clear_message_edits()
            return
        try:
            cur = clearscreen_hack.current_preset_id(self._rom)
        except Exception:
            self._reload_clear_message_edits()
            return
        idx = combo.findData(cur)
        if idx >= 0:
            old = combo.blockSignals(True)
            combo.setCurrentIndex(idx)
            combo.blockSignals(old)
        if getattr(self, "_clear_screen_status", None) is not None:
            self._clear_screen_status.setText("")
        self._reload_clear_message_edits()
        self._refresh_clear_preview()

    def _reload_clear_message_edits(self):
        edits = getattr(self, "_clear_message_edits", [])
        if not edits:
            return
        try:
            rows = CM.read_messages(self._rom)
        except CM.ClearMessageError:
            return
        for le, (_name, cur, _count, _orig) in zip(edits, rows):
            old = le.blockSignals(True)
            le.setText(cur.rstrip())
            le.blockSignals(old)
        if getattr(self, "_clear_message_status", None) is not None:
            self._clear_message_status.setText("")

    # --- ボタンボックス ---
    def _on_apply(self):
        # 既に in-place 反映済。確認のみ。
        QMessageBox.information(
            self,
            t("title_screen.apply.title", "適用"),
            t(
                "title_screen.apply.changed",
                "変更は ROM に反映済みです (このまま編集を続けられます)。",
            )
            if self._changed else
            t("title_screen.apply.no_changes", "変更はありません。"))

    def _on_cancel(self):
        # 開いた時点へ復元してから閉じる
        self._rom[:] = self._snap
        self.reject()

    def done(self, r):
        if isinstance(self._app_config, dict):
            try:
                self._app_config["title_screen_dlg_zoom"] = int(self._zoom.currentData())
                save_config(self._app_config)
            except Exception:
                pass
        save_dialog_geometry(self, self._app_config, "title_screen_dlg")
        super().done(r)
