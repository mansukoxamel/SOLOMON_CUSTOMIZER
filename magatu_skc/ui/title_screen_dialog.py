"""タイトルグラフィック移植 (CHR bank3 取り込み) ダイアログ (R196)

タイトルのロゴ/装飾絵は CHR bank3 (8KB) のタイル画像。本ダイアログは
★CHR bank3 をまるごと別 ROM から取り込む (= タイトル画像差し替え)。
  ・別ROMからタイトル画像を取り込む … 所有 ROM の CHR bank3 を複写
  ・画像として保存 … 現 ROM の CHR bank3 を PNG/BMP 出力
IPS でも CRC 一致要求でもない既知ブロックの単純コピー。CHR は両版
同 offset ゆえ US↔JP どちらの向きでも同じ要領。配置/色 (PRG 側
nametable/attribute/palette) は各版のまま = 将来拡張。
Nintendo graphics もツールに埋め込まない (ユーザー所有 ROM のみ)。

キャンセル時は開いた時点の ROM へ復元。
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDialogButtonBox, QMessageBox, QScrollArea, QWidget, QComboBox,
    QFileDialog, QInputDialog, QGridLayout, QGroupBox, QLineEdit,
    QSpinBox,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor, QPen
from ..core import title_screen as TS
from ..core import rom as _rommod
from ..nes.palette import NES_COLORS
from .dialog_geometry import restore_dialog_geometry, save_dialog_geometry
from collections import Counter
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
_TOP_Y = 6 * 8 + 1                  # display-corrected title logo/banner band
_TOP_H = 8 * 8                      # rows 6..13, 256x64
_TOP_SIDE_FORMAT = "solomon_customizer_title_top_sidecar"
_STAMP_RE = re.compile(r"\d{8}_\d{6}")
_TITLE_PALETTE_SCRIPT_OFF = 0x10 + (0x958A - 0x8000)
_TITLE_ATTR_JP_OFF = 0x4D68
_TITLE_ATTR_US_OFF = 0x4CBF
_TITLE_ATTR_EXTRA_JP_OFF = 0x10 + (0xCDF5 - 0x8000)
# bg パターンテーブル = CHR bank3 上位 4KB (tiles 256-511、ロゴ域 R196)
_BG_BASE = 256


class TitlePreviewLabel(QLabel):
    tile_hovered = pyqtSignal(int, int, int, int, int, int)
    tile_left = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._zoom = 1
        self._grid = []
        self._chr_start = 0
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

        # Preview pixels are display-corrected: result(x,y)=rendered((x-8)%W,(y-1)%H).
        src_x = (int(px) - 8) % _IMG_W
        src_y = (int(py) - 1) % _IMG_H
        col = src_x // 8
        row = src_y // 8
        cell = row * _NT_W + col
        if not (0 <= cell < len(self._grid)):
            self.tile_left.emit()
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


class TitlePaletteDialog(QDialog):
    def __init__(self, colors, parent=None, apply_callback=None):
        super().__init__(parent)
        self.setWindowTitle("タイトル色編集")
        self._initial_colors = [c & 0x3F for c in colors]
        self._colors = [c & 0x3F for c in colors]
        self._apply_callback = apply_callback
        self._sel = 0
        self._swatches = []
        self._color_buttons = []

        root = QVBoxLayout(self)
        note = QLabel(
            "タイトル画面のBGパレット16色を編集します。"
            "各値はROMに書かれるNES色番号($00-$3F)です。")
        note.setWordWrap(True)
        root.addWidget(note)

        g = QGroupBox("タイトルパレット $3F00-$3F0F")
        gl = QGridLayout(g)
        labels = [
            "$3F00", "$3F01", "$3F02", "$3F03",
            "$3F04", "$3F05", "$3F06", "$3F07",
            "$3F08", "$3F09", "$3F0A", "$3F0B",
            "$3F0C", "$3F0D", "$3F0E", "$3F0F",
        ]
        for i in range(16):
            gl.addWidget(QLabel(labels[i]), (i // 4) * 2, i % 4)
            b = QPushButton()
            b.setFixedSize(72, 30)
            b.clicked.connect(lambda _, idx=i: self._select_slot(idx))
            self._swatches.append(b)
            gl.addWidget(b, (i // 4) * 2 + 1, i % 4)
        root.addWidget(g)

        picker = QGroupBox("NES 64色")
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

    def _set_selected_color(self, nes_idx):
        self._colors[self._sel] = nes_idx & 0x3F
        self._refresh_all()

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
                    self, "タイトル色変更不可",
                    f"タイトルパレットを書き換えられませんでした:\n{type(e).__name__}: {e}")

    def _on_cancel(self):
        if self._apply_callback is not None:
            try:
                self._apply_callback(list(self._initial_colors))
            except Exception:
                pass
        self.reject()


class TitleScreenDialog(QDialog):
    def __init__(self, rom_data: bytearray, parent=None, app_config=None):
        super().__init__(parent)
        if parent is not None:
            self.setFont(parent.font())
        self.setWindowTitle("タイトル移植 (配置+色区分+絵・US↔JP)")
        self._rom = rom_data
        self._app_config = app_config
        # 開いた時点の ROM 全体を退避 (キャンセル復元用)
        self._snap = bytes(rom_data)
        self._changed = False
        self.resize(620, 760)

        self._region = TS.region_of(rom_data)   # 非対応は例外 (呼び側catch)

        root = QVBoxLayout(self)
        head = QLabel(
            "別 ROM のタイトルを<b>移植</b>します: <b>配置(nametable)"
            "+色区分(attribute)+絵(CHR bank3)</b> をピース単位で"
            "コピー。<b>コードは一切改変しません</b>(各版の描画コードが"
            "自分の位置のデータを読むため US↔JP どちらでも崩れません)。"
            "<br><b>CRC 一致は不要</b>(既知ピースのコピー、IPSではない)。"
            "JP/US 自動判定・双方向。下のプレビューは CHR(絵)を"
            "グレー表示。<br><b>著作権配慮:</b> データはツールに含めず、"
            "ご自分が所有する ROM 同士でのみ移植します。"
            "<br>※色(パレット)は v1 では移植先のまま(配置・絵は移植)。")
        head.setWordWrap(True)
        root.addWidget(head)

        self._info = QLabel()
        root.addWidget(self._info)

        # 倍率
        zr = QHBoxLayout()
        zr.addWidget(QLabel("表示倍率:"))
        self._zoom = QComboBox()
        for z in (1, 2, 3, 4, 6, 8):
            self._zoom.addItem(f"x{z}", z)
        self._zoom.setCurrentIndex(1)   # x2 (デフォルト)
        self._zoom.currentIndexChanged.connect(self._refresh)
        zr.addWidget(self._zoom)
        zr.addSpacing(16)
        zr.addWidget(QLabel("bank内:"))
        self._highlight_tile = HexSpinBox()
        self._highlight_tile.setRange(0x100, 0x1FF)
        self._highlight_tile.setSingleStep(1)
        self._highlight_tile.setValue(0x130)
        self._highlight_tile.setToolTip("指定したCHR bank3内タイルをタイトルプレビュー上でピンク表示")
        self._highlight_tile.valueChanged.connect(self._refresh)
        zr.addWidget(self._highlight_tile)
        zr.addStretch()
        root.addLayout(zr)

        # プレビュー (スクロール)
        self._canvas = TitlePreviewLabel()
        self._canvas.setAlignment(Qt.AlignCenter)
        self._canvas.setStyleSheet("background:#444;")
        self._canvas.tile_hovered.connect(self._on_preview_tile_hovered)
        self._canvas.tile_left.connect(self._restore_preview_status)
        sa = QScrollArea()
        sa.setWidgetResizable(True)
        wrap = QWidget()
        wl = QVBoxLayout(wrap)
        wl.addWidget(self._canvas)
        sa.setWidget(wrap)
        root.addWidget(sa, 1)
        self._preview_status = QLabel("")
        root.addWidget(self._preview_status)

        # 操作ボタン
        br = QHBoxLayout()
        b_save_top = QPushButton("Top PNG保存...")
        b_save_top.setToolTip("タイトル上部ロゴ領域だけを256x64/4階調PNGで保存")
        b_save_top.clicked.connect(self._on_save_top_image)
        br.addWidget(b_save_top)
        b_png_top = QPushButton("Top PNG読込...")
        b_png_top.setToolTip("最大256x64、幅/高さ8の倍数の上部ロゴ領域PNGを読み込み、下半分は触らない")
        b_png_top.clicked.connect(self._on_import_top_png)
        br.addWidget(b_png_top)
        b_imp = QPushButton("別ROMからタイトルを移植...")
        b_imp.setToolTip(
            "所有する別 ROM (.nes/.zip) のタイトルを移植: 配置"
            "(nametable)+色区分(attribute)+絵(CHR bank3) をピース単位"
            "コピー。JP/US 自動判定・CRC不要・US↔JP両方向・コード非改変")
        b_imp.clicked.connect(self._on_transcode_title)
        br.addWidget(b_imp)
        b_text = QPushButton("追加文字...")
        b_text.setToolTip(
            "タイトル中央付近に1行の文字を追加します。"
            "A-Z / 0-9 / スペース / , . \" が使えます。"
            "既存文字ルーチンは変更しません。")
        b_text.clicked.connect(self._on_add_title_text)
        br.addWidget(b_text)
        b_pal = QPushButton("タイトル色...")
        b_pal.setToolTip("タイトル画面のBGパレット16色($3F00-$3F0F)を編集します。")
        b_pal.clicked.connect(self._on_edit_title_palette)
        br.addWidget(b_pal)
        b_revert = QPushButton("変更を取り消す")
        b_revert.setToolTip("このダイアログを開いた時点の ROM に戻す")
        b_revert.clicked.connect(self._on_revert)
        br.addWidget(b_revert)
        root.addLayout(br)

        bb = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
            | QDialogButtonBox.Apply)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self._on_cancel)
        bb.button(QDialogButtonBox.Apply).clicked.connect(self._on_apply)
        root.addWidget(bb)

        self._refresh()
        restore_dialog_geometry(self, self._app_config, "title_screen_dlg")

    # --- 描画 (実タイトル画面を合成) ---
    def _build_image(self, color: bool = True) -> QImage:
        if color:
            try:
                return self._build_color_image()
            except Exception:
                # 色情報が読めない改造ROMでも、従来の4階調表示へ戻す。
                pass
        return self._build_gray_image()

    def _build_gray_image(self) -> QImage:
        """nametable をデコードし CHR bank3 で実タイトルを合成。
        色は未確定ゆえ暗背景4階調 (形状確認用)。"""
        d = TS.decode_title_grid(self._rom)
        self._last_cells = d["cells"]
        tiles = TS.get_chr_bank3_tiles(self._rom)   # 512 NesTile
        grid = d["grid"]
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
        """タイトルattribute 21Bを実PPU側 $2BC9-$2BDD に展開する。"""
        reg = (self._region or "").upper()
        off = _TITLE_ATTR_US_OFF if reg.startswith("US") else _TITLE_ATTR_JP_OFF
        attr = [0xFF] * 64
        if off + 21 <= len(self._rom):
            src = bytes(self._rom[off:off + 21])
            for i in range(21):
                attr[9 + i] = src[20 - i]
        if reg.startswith("JP"):
            attr[42] = 0xCF
            off2 = _TITLE_ATTR_EXTRA_JP_OFF
            if off2 + 7 <= len(self._rom):
                src = bytes(self._rom[off2:off2 + 7])
                for i in range(7):
                    attr[48 + i] = src[6 - i]
            for i in range(8):
                attr[56 + i] = 0xF5
        return attr

    @staticmethod
    def _attr_palette_no(attr, row, col):
        ai = (row // 4) * 8 + (col // 4)
        if not (0 <= ai < len(attr)):
            return 0
        qx = (col % 4) // 2
        qy = (row % 4) // 2
        shift = (qy * 2 + qx) * 2
        return (attr[ai] >> shift) & 0x03

    def _build_color_image(self) -> QImage:
        """タイトルプレビュー用。palette/attributeを反映したRGB画像を作る。"""
        d = TS.decode_title_grid(self._rom)
        self._last_cells = d["cells"]
        tiles = TS.get_chr_bank3_tiles(self._rom)
        grid = d["grid"]
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
        self._draw_preview_grid(pm, z)
        self._canvas.setPixmap(pm)
        self._canvas.setFixedSize(pm.size())
        self._canvas.set_title_context(z, grid, off)
        self._preview_status_text = (
            f"グリッド: 32x30 / CHR bank3開始 0x{off:X} / "
            f"bank内 0x{highlight_tile:03X}: {count}箇所")
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
            # Match the preview's display correction: rendered tile appears at
            # x+8, y+1 with wrap.
            dx = ((col * 8) + 8) % _IMG_W
            dy = ((row * 8) + 1) % _IMG_H
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
            sx = x * zoom
            painter.drawLine(sx, 0, sx, _IMG_H * zoom)
        for y in range(0, _IMG_H + 1, 8):
            sy = y * zoom
            painter.drawLine(0, sy, _IMG_W * zoom, sy)
        painter.end()

    def _restore_preview_status(self):
        self._preview_status.setText(getattr(self, "_preview_status_text", ""))

    def _on_preview_tile_hovered(self, row, col, stream, bank_tile, file_start, file_end):
        self._preview_status.setText(
            f"cell ({col}, {row}) / stream 0x{stream:02X} / "
            f"bank内 0x{bank_tile:03X} / ROM 0x{file_start:X}-0x{file_end:X}")

    # --- 操作 ---
    def _apply_title_palette_colors(self, colors):
        self._set_title_palette(colors)
        self._changed = True
        self._refresh()

    def _on_edit_title_palette(self):
        colors = self._title_palette()
        old_changed = self._changed
        dlg = TitlePaletteDialog(
            colors, self, apply_callback=self._apply_title_palette_colors)
        if dlg.exec_() != QDialog.Accepted:
            try:
                self._set_title_palette(colors)
                self._changed = old_changed
                self._refresh()
            except Exception:
                pass
            return
        try:
            self._apply_title_palette_colors(dlg.colors())
        except Exception as e:
            QMessageBox.critical(
                self, "タイトル色変更不可",
                f"タイトルパレットを書き換えられませんでした:\n{type(e).__name__}: {e}")
            return

    def _on_save_image(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "タイトル画面を画像保存", "title_screen.png",
            "PNG (*.png);;BMP (*.bmp)")
        if not path:
            return
        img = self._build_image(color=False)
        if not img.save(path):
            QMessageBox.critical(self, "保存失敗",
                                 f"画像を保存できませんでした:\n{path}")
            return
        QMessageBox.information(
            self, "保存完了",
            f"タイトル画面 ({_IMG_W}x{_IMG_H}, 4階調) を保存:\n{path}")

    def _on_save_top_image_legacy_unused(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "タイトル上部PNGを保存", "title_top_256x64.png",
            "PNG (*.png);;BMP (*.bmp)")
        if not path:
            return
        img = self._build_image(color=True).copy(0, _TOP_Y, _IMG_W, _TOP_H)
        if not img.save(path):
            QMessageBox.critical(
                self, "保存失敗",
                f"タイトル上部画像を保存できませんでした:\n{path}")
            return
        QMessageBox.information(
            self, "保存完了",
            f"タイトル上部画像 ({_IMG_W}x{_TOP_H}, 4階調) を保存:\n{path}")

    def _on_save_top_image(self):
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Top PNG", f"title_top_256x64_{stamp}.png",
            "PNG (*.png);;BMP (*.bmp)")
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

    def _on_import_png(self):
        QMessageBox.information(
            self, "PNG取り込み",
            "全体PNG取り込みは現在停止しています。\n"
            "タイトル画像の読み込みは「Top PNG読込...」から、"
            "最大256x64の画像を指定してください。")

    def _cells_from_display_image(self, img):
        img = img.convertToFormat(QImage.Format_RGB32).scaled(
            _IMG_W, _IMG_H, Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation)
        W, H = _IMG_W, _IMG_H
        pal = self._title_palette()
        attr = self._title_attributes()
        cells = []
        for cell in range(_NT_W * (H // 8)):
            row, col = divmod(cell, _NT_W)
            pal_no = self._attr_palette_no(attr, row, col)
            nes_choices = [
                pal[0],
                pal[pal_no * 4 + 1],
                pal[pal_no * 4 + 2],
                pal[pal_no * 4 + 3],
            ]
            rgb_choices = [NES_COLORS[c & 0x3F] for c in nes_choices]
            ox, oy = col * 8, row * 8
            pat = []
            for y in range(8):
                sy = (oy + y + 1) % H
                for x in range(8):
                    sx = (ox + x + 8) % W
                    rgb = img.pixel(sx, sy)
                    r = (rgb >> 16) & 0xFF
                    gg = (rgb >> 8) & 0xFF
                    b = rgb & 0xFF
                    best, bd = 0, 1 << 60
                    for pi, (rr, rg, rb) in enumerate(rgb_choices):
                        d = ((int(r) - rr) * (int(r) - rr) +
                             (int(gg) - rg) * (int(gg) - rg) +
                             (int(b) - rb) * (int(b) - rb))
                        if d < bd:
                            best, bd = pi, d
                    pat.append(best)
            cells.append(pat)
        return cells

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

    def _set_title_attr_palette_no(self, attr, row, col, pal_no):
        ai = (row // 4) * 8 + (col // 4)
        if not (0 <= ai < len(attr)):
            return
        qx = (col % 4) // 2
        qy = (row % 4) // 2
        shift = (qy * 2 + qx) * 2
        attr[ai] = (attr[ai] & ~(0x03 << shift)) | \
            ((pal_no & 0x03) << shift)

    def _write_title_attributes(self, attr):
        """Write the 21-byte stock title attribute block from expanded attrs."""
        reg = (self._region or "").upper()
        off = _TITLE_ATTR_US_OFF if reg.startswith("US") else _TITLE_ATTR_JP_OFF
        if off + 21 > len(self._rom):
            raise ValueError("title attribute block is outside ROM")
        for i in range(21):
            self._rom[off + 20 - i] = attr[9 + i] & 0xFF

    def _top_png_cells_from_indexed_image(self, top, color_to_index):
        src_w = top.width()
        src_h = top.height()
        cells = [[0] * 64 for _ in range(_NT_W * (_IMG_H // 8))]
        top_start = 6 * _NT_W
        top_end = 14 * _NT_W
        for ci in range(top_start, top_end):
            row, col = divmod(ci, _NT_W)
            ox, oy = col * 8, row * 8
            src_oy = oy - (_TOP_Y - 1)
            if ox >= src_w or src_oy < 0 or src_oy + 8 > src_h:
                continue
            pat = []
            for y in range(8):
                sy = src_oy + y
                for x in range(8):
                    sx = ox + x
                    pat.append(color_to_index[self._pixel_rgb(top, sx, sy)])
            cells[ci] = pat
        return cells

    @staticmethod
    def _rgb_dist(a, b):
        return sum((int(x) - int(y)) * (int(x) - int(y))
                   for x, y in zip(a, b))

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
                self, "読み込み不可",
                f"画像を読み込めません:\n{path}")
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
            QMessageBox.critical(self, "読み込み不可", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "読み込み失敗",
                                 f"{type(e).__name__}: {e}")
            return
        self._changed = True
        self._refresh()
        QMessageBox.information(
            self, "Top PNG読み込み完了",
            "\n".join(chg) +
            "\n\n対象: x=0..255, y=49..112。下半分の山/神殿側は触りません。")

    def _on_import_top_png(self):
        path = self._pick_open(
            "Open Top PNG (PNG/BMP, max 256x64)", "*.png;*.bmp")
        if not path:
            return
        top = QImage(path)
        if top.isNull():
            QMessageBox.critical(
                self, "Open failed",
                f"Could not open image:\n{path}")
            return
        if top.width() > _IMG_W or top.height() > _TOP_H:
            QMessageBox.critical(
                self, "Import failed",
                "Top PNGとして読み込める画像は最大256x64です。\n"
                f"指定画像: {top.width()}x{top.height()}\n\n"
                "全体PNG取り込みは現在停止しています。")
            return
        if top.width() <= 0 or top.height() <= 0 or \
                top.width() % 8 != 0 or top.height() % 8 != 0:
            QMessageBox.critical(
                self, "Import failed",
                "Top PNGとして読み込める画像は、幅と高さが8の倍数である必要があります。\n"
                f"指定画像: {top.width()}x{top.height()}")
            return
        top = top.convertToFormat(QImage.Format_RGB32)
        snap = bytes(self._rom)
        try:
            cells, pre_msgs = self._try_top_png_4color_cells(top)
            if cells is None:
                full = QImage(_IMG_W, _IMG_H, QImage.Format_RGB32)
                pal = self._title_palette()
                bg = NES_COLORS[pal[0] & 0x3F]
                full.fill(QColor(*bg))
                for y in range(top.height()):
                    for x in range(top.width()):
                        full.setPixel(x, _TOP_Y + y, top.pixel(x, y))
                cells = self._cells_from_display_image(full)
                pre_msgs = [
                    "multi-color top PNG path: existing title palette used",
                    f"source image kept at original size: {top.width()}x{top.height()}",
                ]
            chg = TS.apply_title_top_image_from_png(
                self._rom, cells)
        except (TS.TitleScreenError, ValueError) as e:
            self._rom[:] = snap
            QMessageBox.critical(self, "Import failed", str(e))
            return
        except Exception as e:
            self._rom[:] = snap
            QMessageBox.critical(
                self, "Import failed", f"{type(e).__name__}: {e}")
            return
        self._changed = True
        self._refresh()
        QMessageBox.information(
            self, "Top PNG imported", "\n".join(pre_msgs + chg))

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
        return get_file(self, title=title, filter=filt)

    def _on_transcode_title(self):
        path = self._pick_open(
            "タイトルの移植元 ROM を選択 (所有 .nes/.zip)",
            "*.nes;*.zip")
        if not path:
            return
        try:
            _name, data = _rommod.load_rom_data(path)
            chg = TS.transcode_title(self._rom, bytearray(data))
        except (TS.TitleScreenError, ValueError) as e:
            QMessageBox.critical(self, "移植不可", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "移植失敗",
                                 f"{type(e).__name__}: {e}")
            return
        self._changed = True
        self._refresh()
        QMessageBox.information(
            self, "タイトル移植完了",
            "\n".join(chg) + "\n\n(実機/エミュで要確認)")

    def _on_add_title_text(self):
        try:
            cur = TS.read_title_text_line(self._rom)
        except Exception:
            cur = ""
        dlg = QInputDialog(self)
        dlg.setWindowTitle("タイトル追加文字")
        dlg.setLabelText(
            "タイトル中央付近に出す文字 "
            "(A-Z / 0-9 / スペース / , . \"、最大32文字):")
        dlg.setInputMode(QInputDialog.TextInput)
        dlg.setTextValue(cur[:32])
        line = dlg.findChild(QLineEdit)
        if line is not None:
            line.setMaxLength(32)
        if dlg.exec_() != QDialog.Accepted:
            return
        text = dlg.textValue()
        try:
            chg = TS.add_title_text_line(self._rom, text, row=14)
        except (TS.TitleScreenError, ValueError) as e:
            QMessageBox.critical(self, "追加文字不可", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "追加文字失敗",
                                 f"{type(e).__name__}: {e}")
            return
        self._changed = True
        self._refresh()
        QMessageBox.information(
            self, "追加文字完了",
            "\n".join(chg) + "\n\n既存の文字描画ルーチンは変更していません。")

    def _on_revert(self):
        if bytes(self._rom) == self._snap:
            return
        self._rom[:] = self._snap
        self._changed = False
        self._refresh()
        QMessageBox.information(self, "取り消し",
                                "開いた時点の ROM に戻しました。")

    # --- ボタンボックス ---
    def _on_apply(self):
        # 既に in-place 反映済。確認のみ。
        QMessageBox.information(
            self, "適用",
            "変更は ROM に反映済みです (このまま編集を続けられます)。"
            if self._changed else "変更はありません。")

    def _on_cancel(self):
        # 開いた時点へ復元してから閉じる
        self._rom[:] = self._snap
        self.reject()

    def done(self, r):
        save_dialog_geometry(self, self._app_config, "title_screen_dlg")
        super().done(r)
