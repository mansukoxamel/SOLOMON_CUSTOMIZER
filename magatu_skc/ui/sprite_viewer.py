"""スプライト/キャラクタービューア

3モード:
  - ROMフレームデータ: $D0E8 機構由来の16x16スプライトを一覧。
  - キャラクター: skc_config のメタタイル定義で組み立てた実キャラ
    (アイテム/敵/メタ) を名前付きで一覧。tile_renderer 使用。
  - 生CHRタイル: CHR-ROM の 8x8 タイルを素のまま一覧 (上級者向け)。

ROMフレームデータは、ダブルクリックで16x16ピクセル編集へ接続できる。
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSpinBox,
    QScrollArea, QWidget, QGridLayout, QDialogButtonBox, QCheckBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QColor, QPainter

from ..core.i18n import t
from ..nes.tile import NesTile, NES_TILE_W, NES_GFX_TILE_BYTE_SIZE
from ..nes import palette as pal

PALETTE_OFFSET = 0xED4
PALETTE_COUNT = 8
PALETTE_LABELS = [
    "BG #0", "BG #1", "BG #2", "BG #3",
    "SPR #0 主人公", "SPR #1 サラマンダー", "SPR #2 ガーゴイル", "SPR #3 ゴブリン",
]
TILES_PER_BANK = 512
BANK_COLS = 16
RAW_CHR_PINK_RANGES = (
    (0x12C, 0x139),
    (0x13C, 0x14F),
    (0x154, 0x17F),
    (0x180, 0x18F),
    (0x190, 0x197),
    (0x199, 0x19F),
    (0x1A9, 0x1A9),
    (0x1AC, 0x1AF),
    (0x1B8, 0x1BF),
    (0x1E0, 0x1FF),
)


class RomFrameImageLabel(QLabel):
    frame_double_clicked = pyqtSignal(int)

    def __init__(self, item_count, cols, cell_w, cell_h, parent=None):
        super().__init__(parent)
        self._item_count = int(item_count)
        self._cols = int(cols)
        self._cell_w = int(cell_w)
        self._cell_h = int(cell_h)
        self._gap = 4
        self.setMouseTracking(True)

    def mouseDoubleClickEvent(self, event):
        if event.button() != Qt.LeftButton:
            super().mouseDoubleClickEvent(event)
            return
        x = event.pos().x() - self._gap
        y = event.pos().y() - self._gap
        stride_w = self._cell_w + self._gap
        stride_h = self._cell_h + self._gap
        if x < 0 or y < 0 or stride_w <= 0 or stride_h <= 0:
            super().mouseDoubleClickEvent(event)
            return
        col = x // stride_w
        row = y // stride_h
        local_x = x % stride_w
        local_y = y % stride_h
        if col >= self._cols or local_x >= self._cell_w or local_y >= self._cell_h:
            super().mouseDoubleClickEvent(event)
            return
        idx = int(row * self._cols + col)
        if 0 <= idx < self._item_count:
            self.frame_double_clicked.emit(idx)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class RawChrImageLabel(QLabel):
    tile_hovered = pyqtSignal(int)
    tile_left = pyqtSignal()

    def __init__(self, first_tile, tile_count, cols, cell, gap, parent=None):
        super().__init__(parent)
        self._first_tile = int(first_tile)
        self._tile_count = int(tile_count)
        self._cols = int(cols)
        self._cell = int(cell)
        self._gap = int(gap)
        self.setMouseTracking(True)

    def mouseMoveEvent(self, event):
        stride = self._cell + self._gap
        if self._cols <= 0 or self._cell <= 0 or stride <= 0:
            self.tile_left.emit()
            super().mouseMoveEvent(event)
            return
        x = event.pos().x() - self._gap
        y = event.pos().y() - self._gap
        if x < 0 or y < 0:
            self.tile_left.emit()
            super().mouseMoveEvent(event)
            return
        col = x // stride
        row = y // stride
        local_x = x % stride
        local_y = y % stride
        idx = int(row * self._cols + col)
        if (
            col < 0 or col >= self._cols
            or local_x >= self._cell or local_y >= self._cell
            or idx < 0 or idx >= self._tile_count
        ):
            self.tile_left.emit()
            super().mouseMoveEvent(event)
            return
        self.tile_hovered.emit(self._first_tile + idx)
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.tile_left.emit()
        super().leaveEvent(event)


class SpriteViewer(QDialog):
    """スプライト/キャラクタービューア"""

    rom_changed = pyqtSignal()

    @staticmethod
    def _palette_label(index):
        return t(f"sprite_viewer.palette.option.{index}", PALETTE_LABELS[index])

    def __init__(self, rom, tile_renderer=None, config=None, app_config=None, parent=None):
        super().__init__(parent)
        if parent is not None:
            self.setFont(parent.font())
        self.setWindowTitle(t(
            "sprite_viewer.title",
            "スプライト/キャラクタービューア",
        ))
        self.resize(760, 800)
        self.rom = rom
        self.tile_renderer = tile_renderer
        self.config = config
        self._app_config = app_config
        self._editor_dialogs = {}

        data = rom.data
        self.chr_start = 16 + data[4] * 0x4000
        chr_size = data[5] * 0x2000
        if chr_size <= 0 or self.chr_start + chr_size > len(data):
            chr_size = max(0, len(data) - self.chr_start)
        self.total_tiles = chr_size // NES_GFX_TILE_BYTE_SIZE
        self.bank_count = max(1, (self.total_tiles + TILES_PER_BANK - 1) // TILES_PER_BANK)

        layout = QVBoxLayout(self)

        # --- モード切替 ---
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel(t("sprite_viewer.mode.label", "表示モード:")))
        self.mode_combo = QComboBox()
        have_cfg = self.tile_renderer is not None and self.config is not None
        self.mode_combo.addItem(t(
            "sprite_viewer.mode.rom_frames",
            "★ROMフレームデータ (全網羅 16x16)",
        ), "rom")
        if have_cfg:
            self.mode_combo.addItem(t(
                "sprite_viewer.mode.characters",
                "キャラクター (組み立て)",
            ), "char")
        self.mode_combo.addItem(t(
            "sprite_viewer.mode.raw_chr",
            "生CHRタイル (8x8)",
        ), "raw")
        self.mode_combo.currentIndexChanged.connect(self._rebuild_controls)
        mode_row.addWidget(self.mode_combo)
        mode_row.addStretch()
        layout.addLayout(mode_row)

        # --- 動的コントロール行 ---
        self.ctrl_host = QWidget()
        self.ctrl_layout = QHBoxLayout(self.ctrl_host)
        self.ctrl_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ctrl_host)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.canvas = QWidget()
        self.scroll.setWidget(self.canvas)
        layout.addWidget(self.scroll, 1)

        self.hover_label = QLabel("")
        layout.addWidget(self.hover_label)

        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(self.reject)
        bb.accepted.connect(self.accept)
        layout.addWidget(bb)

        self._rebuild_controls()
        self._restore_geometry()

    def _restore_geometry(self):
        cfg = self._app_config
        if not cfg:
            return
        w = int(cfg.get("sprite_viewer_w", -1))
        h = int(cfg.get("sprite_viewer_h", -1))
        x = int(cfg.get("sprite_viewer_x", -1))
        y = int(cfg.get("sprite_viewer_y", -1))
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
            cfg["sprite_viewer_x"] = max(0, self.x())
            cfg["sprite_viewer_y"] = max(0, self.y())
            cfg["sprite_viewer_w"] = self.width()
            cfg["sprite_viewer_h"] = self.height()
            save_config(cfg)
        except Exception:
            pass

    def done(self, r):
        self._save_geometry()
        super().done(r)

    # ---- コントロール構築 (モード依存) ----
    def _rebuild_controls(self):
        while self.ctrl_layout.count():
            w = self.ctrl_layout.takeAt(0).widget()
            if w:
                w.deleteLater()

        mode_code = self.mode_combo.currentData()
        is_char = mode_code == "char"
        is_rom = mode_code == "rom"

        if is_rom:
            self.ctrl_layout.addWidget(QLabel(t("sprite_viewer.chr_bank.label", "CHRバンク:")))
            self.rb_bank = QComboBox()
            for b in range(self.bank_count):
                self.rb_bank.addItem(f"Bank {b}")
            self.rb_bank.setCurrentIndex(min(2, self.bank_count - 1))
            self.rb_bank.currentIndexChanged.connect(self._render_romframes)
            self.ctrl_layout.addWidget(self.rb_bank)

            self.ctrl_layout.addWidget(QLabel(t("sprite_viewer.palette.label", "パレット:")))
            self.rb_pal = QComboBox()
            for i in range(4, 8):
                self.rb_pal.addItem(self._palette_label(i))
            self.rb_pal.addItem(t("sprite_viewer.palette.auto_attr", "attr&3で自動"))
            self.rb_pal.setCurrentIndex(4)
            self.rb_pal.currentIndexChanged.connect(self._render_romframes)
            self.ctrl_layout.addWidget(self.rb_pal)

            self.rb_duplicates = QCheckBox(t(
                "sprite_viewer.duplicates.checkbox",
                "重複参照も表示",
            ))
            self.rb_duplicates.setToolTip(t(
                "sprite_viewer.duplicates.tooltip",
                "同じleft/right/attrを参照するROMフレームも個別に表示",
            ))
            self.rb_duplicates.stateChanged.connect(self._render_romframes)
            self.ctrl_layout.addWidget(self.rb_duplicates)

            self.ctrl_layout.addWidget(QLabel(t("sprite_viewer.zoom.label", "拡大:")))
            self.rb_zoom = QSpinBox()
            self.rb_zoom.setRange(1, 8)
            self.rb_zoom.setValue(3)
            self.rb_zoom.setSuffix(" x")
            self.rb_zoom.valueChanged.connect(self._render_romframes)
            self.ctrl_layout.addWidget(self.rb_zoom)
            self.ctrl_layout.addStretch()
            self._render_romframes()
            return

        if is_char:
            self.ctrl_layout.addWidget(QLabel(t("sprite_viewer.category.label", "カテゴリ:")))
            self.cat_combo = QComboBox()
            self.cat_combo.addItems([
                t("sprite_viewer.category.items", "アイテム"),
                t("sprite_viewer.category.enemies", "敵"),
                t("sprite_viewer.category.meta", "メタ"),
                t("sprite_viewer.category.all_metatiles", "全メタタイル"),
                t("sprite_viewer.category.all_tiledefs", "★全網羅 (全tile_def×全tileset)")])
            self.cat_combo.setCurrentIndex(1)
            self.cat_combo.currentIndexChanged.connect(self._render_chars)
            self.ctrl_layout.addWidget(self.cat_combo)

            self.ctrl_layout.addWidget(QLabel(t("sprite_viewer.tileset.label", "タイルセット:")))
            self.ts_combo = QComboBox()
            for i in range(len(self.config.tilesets)):
                self.ts_combo.addItem(f"tileset {i}")
            self.ts_combo.addItem(t("sprite_viewer.tileset.all", "全部(網羅)"))
            self.ts_combo.currentIndexChanged.connect(self._render_chars)
            self.ctrl_layout.addWidget(self.ts_combo)

            self.opaque_chk = QCheckBox(t("sprite_viewer.opaque.checkbox", "背景不透明"))
            self.opaque_chk.setChecked(True)
            self.opaque_chk.stateChanged.connect(self._render_chars)
            self.ctrl_layout.addWidget(self.opaque_chk)

            self.ctrl_layout.addWidget(QLabel(t("sprite_viewer.zoom.label", "拡大:")))
            self.zoom_spin = QSpinBox()
            self.zoom_spin.setRange(1, 12)
            self.zoom_spin.setValue(4)
            self.zoom_spin.setSuffix(" x")
            self.zoom_spin.valueChanged.connect(self._render_chars)
            self.ctrl_layout.addWidget(self.zoom_spin)
            self.ctrl_layout.addStretch()
            self._render_chars()
        else:
            self.ctrl_layout.addWidget(QLabel(t("sprite_viewer.bank.label", "バンク:")))
            self.bank_combo = QComboBox()
            for b in range(self.bank_count):
                self.bank_combo.addItem(f"Bank {b}")
            self.bank_combo.currentIndexChanged.connect(self._render_raw)
            self.ctrl_layout.addWidget(self.bank_combo)

            self.ctrl_layout.addWidget(QLabel(t("sprite_viewer.palette.label", "パレット:")))
            self.pal_combo = QComboBox()
            for i in range(PALETTE_COUNT):
                self.pal_combo.addItem(self._palette_label(i))
            self.pal_combo.setCurrentIndex(4)
            self.pal_combo.currentIndexChanged.connect(self._render_raw)
            self.ctrl_layout.addWidget(self.pal_combo)

            self.ctrl_layout.addWidget(QLabel(t("sprite_viewer.zoom.label", "拡大:")))
            self.zoom_spin = QSpinBox()
            self.zoom_spin.setRange(1, 16)
            self.zoom_spin.setValue(4)
            self.zoom_spin.setSuffix(" x")
            self.zoom_spin.valueChanged.connect(self._render_raw)
            self.ctrl_layout.addWidget(self.zoom_spin)

            self.grid_chk = QCheckBox(t("sprite_viewer.grid.checkbox", "グリッド線"))
            self.grid_chk.setChecked(True)
            self.grid_chk.stateChanged.connect(self._render_raw)
            self.ctrl_layout.addWidget(self.grid_chk)
            self.ctrl_layout.addStretch()
            self._render_raw()

    # ---- キャラクター（組み立て）モード ----
    def _char_entries(self):
        """(コード, tile_def_no, ラベル) のリストを現カテゴリで返す"""
        cat = self.cat_combo.currentIndex()
        cfg = self.config
        out = []
        if cat == 0:  # アイテム
            for code, td in sorted(cfg.item_map.items()):
                lbl = cfg.item_desc.get(code, f"item 0x{code:02X}")
                out.append((code, td, f"0x{code:02X} {lbl}"))
        elif cat == 1:  # 敵
            for code, td in sorted(cfg.enemy_map.items()):
                lbl = cfg.enemy_desc.get(code, f"enemy 0x{code:02X}")
                out.append((code, td, f"0x{code:02X} {lbl}"))
        elif cat == 2:  # メタ
            for code, td in sorted(cfg.metadata_map.items()):
                lbl = cfg.metadata_desc.get(code, f"meta 0x{code:02X}")
                out.append((code, td, f"0x{code:02X} {lbl}"))
        elif cat == 3:  # 全メタタイル (1 tileset)
            for td in sorted(cfg.tile_defs):
                out.append((td, td, None, f"def#{td}"))
            return out
        else:  # ★全網羅: 全 tile_def × 全 tileset
            for td in sorted(cfg.tile_defs):
                for ts in range(len(cfg.tilesets)):
                    out.append((td, td, ts, f"def#{td} ts{ts}"))
            return out
        # cat 0/1/2 は (code, td, None, label) に正規化
        return [(c, t, None, l) for (c, t, l) in out]

    GROUP_NAMES = {
        0: "system/Dana", 1: "system/Dana", 2: "system/Dana",
        3: "action", 4: "action", 5: "item/効果",
        6: "撃破ボーナス/封印partial", 7: "妖精/封印/星座",
        8: "Bullet", 9: "Panel Monster",
        10: "Spark Ball slow", 11: "Spark Ball fast",
        12: "Neul s0", 13: "Ghost s0", 14: "Neul s1", 15: "Ghost s1",
        16: "Neul s2", 17: "Ghost s2", 18: "Neul s3", 19: "Ghost s3",
        20: "Demonhead s0", 21: "Demonhead s1", 22: "Demonhead s2",
        23: "Saramandor s0", 24: "Saramandor s1", 25: "Saramandor s2",
        26: "Dragon s0", 27: "Dragon s1", 28: "Goblin s0", 29: "Goblin s1",
        30: "Gargoyle s0", 31: "Gargoyle s1",
    }

    def _best_bank(self, t1, t2):
        """4バンクで最も非透明画素が多いバンクを選ぶ (見た目自動補正)"""
        best, best_n = 0, -1
        for bank in range(self.bank_count):
            n = 0
            for byte_idx in (t1, t2):
                half = 256 if (byte_idx & 1) else 0
                for tn in (half + (byte_idx & 0xFE),
                           half + (byte_idx & 0xFE) + 1):
                    tile_no = bank * 512 + tn
                    st = self.chr_start + tile_no * NES_GFX_TILE_BYTE_SIZE
                    tb = self.rom.data[st:st + NES_GFX_TILE_BYTE_SIZE]
                    if len(tb) < NES_GFX_TILE_BYTE_SIZE:
                        continue
                    for b in tb:
                        n += bin(b).count("1")
            if n > best_n:
                best_n, best = n, bank
        return best

    def _render_chars(self):
        sel_ts = self.ts_combo.currentIndex()
        all_ts = (sel_ts >= len(self.config.tilesets))  # "全部(網羅)"
        zoom = self.zoom_spin.value()
        opaque = self.opaque_chk.isChecked()
        entries = self._char_entries()

        old = self.scroll.takeWidget()
        if old:
            old.deleteLater()
        host = QWidget()
        grid = QGridLayout(host)
        grid.setSpacing(6)

        cols = 8
        idx = 0
        n_ts = len(self.config.tilesets)
        for (code, td_no, fixed_ts, label) in entries:
            # このエントリで描画する tileset 群を決定
            if fixed_ts is not None:
                ts_list = [fixed_ts]
            elif all_ts:
                ts_list = list(range(n_ts))
            else:
                ts_list = [sel_ts]

            for ts in ts_list:
                try:
                    img = self.tile_renderer.get_tile_image(
                        td_no, ts, transparent=not opaque)
                except Exception:
                    continue
                if opaque:
                    bg = QImage(img.size(), QImage.Format_ARGB32)
                    bg.fill(QColor(60, 60, 60))
                    from PyQt5.QtGui import QPainter
                    p = QPainter(bg)
                    p.drawImage(0, 0, img)
                    p.end()
                    img = bg
                pm = QPixmap.fromImage(img).scaled(
                    img.width() * zoom, img.height() * zoom,
                    Qt.KeepAspectRatio, Qt.FastTransformation)
                cell = QWidget()
                cl = QVBoxLayout(cell)
                cl.setContentsMargins(2, 2, 2, 2)
                cl.setSpacing(1)
                pic = QLabel()
                pic.setPixmap(pm)
                pic.setAlignment(Qt.AlignCenter)
                lab = label if fixed_ts is not None else f"{label} ts{ts}"
                txt = QLabel(lab)
                txt.setAlignment(Qt.AlignCenter)
                txt.setWordWrap(True)
                txt.setStyleSheet("font-size: 9px;")
                cl.addWidget(pic)
                cl.addWidget(txt)
                grid.addWidget(cell, idx // cols, idx % cols)
                idx += 1

        host.setLayout(grid)
        self.scroll.setWidget(host)
        self.hover_label.setText(t(
            "sprite_viewer.characters.status",
            "{count} 枚表示 / tile_def {tile_defs}種 × tileset {tilesets}種 / フィルタなし全網羅可",
        ).format(count=idx, tile_defs=len(self.config.tile_defs), tilesets=n_ts))

    # ---- 生CHRタイルモード ----
    def _get_subpalette(self):
        idx = self.pal_combo.currentIndex()
        off = PALETTE_OFFSET + idx * 4
        try:
            return pal.load_palette_from_rom(self.rom.data, off)
        except Exception:
            return pal.SubPalette([0x0f, 0x00, 0x10, 0x30])

    def _display_palette_rgb(self, palette_index: int):
        """Return display QRgb colors for the selected ROM palette.

        ROM sprite palettes store three visible colors followed by a separator.
        CHR sprite pixel value 0 is transparent; values 1-3 map to those first
        three ROM bytes.
        """
        off = PALETTE_OFFSET + palette_index * 4
        if palette_index >= 4:
            try:
                colors = [self.rom.data[off + i] & 0x3F for i in range(3)]
            except Exception:
                colors = [0x00, 0x10, 0x30]
            return [None] + [QColor(*pal.get_nes_color(v)).rgb() for v in colors]
        try:
            sub_pal = pal.load_palette_from_rom(self.rom.data, off)
        except Exception:
            sub_pal = pal.SubPalette([0x0f, 0x00, 0x10, 0x30])
        return [QColor(*sub_pal.get_rgb(i)).rgb() for i in range(4)]

    def _sprite_palette_rgb(self, sprite_palette_no: int):
        return self._display_palette_rgb(4 + (int(sprite_palette_no) & 3))

    @staticmethod
    def _is_raw_chr_pink_marked(bank_tile):
        bank_tile = int(bank_tile)
        return any(start <= bank_tile <= end for start, end in RAW_CHR_PINK_RANGES)

    def _render_raw(self):
        bank = self.bank_combo.currentIndex()
        zoom = self.zoom_spin.value()
        show_grid = self.grid_chk.isChecked()
        palette_index = self.pal_combo.currentIndex()

        first = bank * TILES_PER_BANK
        last = min(first + TILES_PER_BANK, self.total_tiles)
        n = last - first
        if n <= 0:
            return
        rows = (n + BANK_COLS - 1) // BANK_COLS
        cell = NES_TILE_W * zoom
        gap = 1 if show_grid else 0
        img_w = BANK_COLS * cell + (BANK_COLS + 1) * gap
        img_h = rows * cell + (rows + 1) * gap

        img = QImage(img_w, img_h, QImage.Format_ARGB32)
        img.fill(QColor(40, 40, 40) if show_grid else QColor(0, 0, 0))
        rgb = self._display_palette_rgb(palette_index)

        for ti in range(n):
            tile_no = first + ti
            start = self.chr_start + tile_no * NES_GFX_TILE_BYTE_SIZE
            tb = bytes(self.rom.data[start:start + NES_GFX_TILE_BYTE_SIZE])
            if len(tb) < NES_GFX_TILE_BYTE_SIZE:
                break
            tile = NesTile(tb)
            ox = gap + (ti % BANK_COLS) * (cell + gap)
            oy = gap + (ti // BANK_COLS) * (cell + gap)
            for y in range(NES_TILE_W):
                for x in range(NES_TILE_W):
                    color = rgb[tile.pixels[y][x]]
                    if color is None:
                        continue
                    px0, py0 = ox + x * zoom, oy + y * zoom
                    for dy in range(zoom):
                        for dx in range(zoom):
                            img.setPixel(px0 + dx, py0 + dy, color)

        painter = QPainter(img)
        painter.setBrush(QColor(255, 0, 180, 70))
        painter.setPen(QColor(255, 70, 210))
        for ti in range(n):
            bank_tile = (first + ti) % TILES_PER_BANK
            if not self._is_raw_chr_pink_marked(bank_tile):
                continue
            ox = gap + (ti % BANK_COLS) * (cell + gap)
            oy = gap + (ti // BANK_COLS) * (cell + gap)
            painter.drawRect(ox, oy, max(0, cell - 1), max(0, cell - 1))
        painter.end()

        lbl = RawChrImageLabel(first, n, BANK_COLS, cell, gap)
        lbl.setPixmap(QPixmap.fromImage(img))
        lbl.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        lbl.tile_hovered.connect(self._on_raw_chr_tile_hovered)
        lbl.tile_left.connect(self._restore_raw_chr_status)
        old = self.scroll.takeWidget()
        if old:
            old.deleteLater()
        self.scroll.setWidget(lbl)
        self._raw_chr_status_text = t(
            "sprite_viewer.raw.status",
            "Bank {bank}: タイル {first}-{last} / CHR開始 0x{chr_start:X}",
        ).format(bank=bank, first=first, last=last - 1, chr_start=self.chr_start)
        self._restore_raw_chr_status()

    def _restore_raw_chr_status(self):
        self.hover_label.setText(getattr(self, "_raw_chr_status_text", ""))

    def _on_raw_chr_tile_hovered(self, tile_no):
        bank = int(tile_no) // TILES_PER_BANK
        bank_tile = int(tile_no) % TILES_PER_BANK
        chr_offset = int(tile_no) * NES_GFX_TILE_BYTE_SIZE
        file_start = self.chr_start + chr_offset
        file_end = file_start + NES_GFX_TILE_BYTE_SIZE - 1
        self.hover_label.setText(t(
            "sprite_viewer.raw.hover",
            "Bank {bank}: タイル {tile_no} (0x{tile_no:03X}) / "
            "bank内 {bank_tile} (0x{bank_tile:03X}) / "
            "CHR+0x{chr_offset:04X} / ROM 0x{file_start:X}-0x{file_end:X}",
        ).format(
            bank=bank,
            tile_no=tile_no,
            bank_tile=bank_tile,
            chr_offset=chr_offset,
            file_start=file_start,
            file_end=file_end,
        ))

    # ---- ★ROMフレームデータモード ($D0E8 機構、16x16 8x16スプライト) ----
    def _cf(self, cpu):
        return 0x10 + (cpu - 0x8000)

    def _romframe_items(self):
        """検証済み $D0E8 機構で全 (group,state,frame,t1,t2,attr) を抽出"""
        rom = self.rom.data
        cf = self._cf
        gptrs = [rom[cf(0xD0E8 + i * 2)] | rom[cf(0xD0E8 + i * 2 + 1)] << 8
                 for i in range(32)]
        uniq = sorted(set(gptrs))
        bound = {}
        for i, p in enumerate(uniq):
            bound[p] = uniq[i + 1] if i + 1 < len(uniq) else 0xD600
        FD_LO, FD_HI = 0xD600, 0xDA00
        items = []
        for g in range(32):
            base = gptrs[g]
            nstates = min(max(0, (bound.get(base, base + 4) - base) // 4), 64)
            for s in range(nstates):
                e = base + s * 4
                phase = rom[cf(e)]
                ri = rom[cf(e + 1)]
                ptr = rom[cf(e + 2)] | rom[cf(e + 3)] << 8
                frames = (phase & 0x0F) + 1
                if ri & 1:  # indirect
                    if not (0xD000 <= ptr <= 0xD600):
                        continue
                    final = rom[cf(ptr)] | rom[cf(ptr + 1)] << 8
                else:
                    final = ptr
                if not (FD_LO <= final < FD_HI):
                    continue
                for fi in range(min(frames, 8)):
                    a = final + fi * 3
                    if not (FD_LO <= a < FD_HI):
                        break
                    items.append((g, s, fi, rom[cf(a)],
                                  rom[cf(a + 1)], rom[cf(a + 2)]))
        return items

    @staticmethod
    def _romframe_edit_key(item):
        return item[3], item[4], item[5]

    def _romframe_ref_counts(self, items):
        counts = {}
        for item in items:
            key = self._romframe_edit_key(item)
            counts[key] = counts.get(key, 0) + 1
        return counts

    def _dedupe_romframe_items(self, items):
        seen = set()
        out = []
        for item in items:
            key = self._romframe_edit_key(item)
            if key in seen:
                continue
            seen.add(key)
            out.append(item)
        return out

    def _draw_8x16(self, img, rgb, ox, oy, byte_idx, bank, zoom,
                   hflip=False, vflip=False):
        """NES 8x16: tile bit0=パターンテーブル($0000/$1000)、
        byte&$FE=上タイル/+1=下。bank は画面のCHRバンク選択を使う。
        attr由来の H/V flip 適用。"""
        half = 256 if (byte_idx & 1) else 0   # bit0=1 → $1000領域
        top = half + (byte_idx & 0xFE)
        for sub, tn in ((0, top), (1, top + 1)):
            tile_no = bank * 512 + tn
            st = self.chr_start + tile_no * NES_GFX_TILE_BYTE_SIZE
            tb = bytes(self.rom.data[st:st + NES_GFX_TILE_BYTE_SIZE])
            if len(tb) < NES_GFX_TILE_BYTE_SIZE:
                continue
            tile = NesTile(tb)
            for y in range(8):
                for x in range(8):
                    pidx = tile.pixels[y][x]
                    if pidx == 0:
                        continue
                    c = rgb[pidx]
                    sx = 7 - x if hflip else x
                    # V-flip: 8x16全体(16px)で反転 → sub も入替
                    if vflip:
                        rsub = 1 - sub
                        ry = 7 - y
                    else:
                        rsub, ry = sub, y
                    bx = ox + sx * zoom
                    by = oy + (rsub * 8 + ry) * zoom
                    for dy in range(zoom):
                        for dx in range(zoom):
                            img.setPixel(bx + dx, by + dy, c)

    def _render_romframes(self):
        bank = self.rb_bank.currentIndex()
        zoom = self.rb_zoom.value()
        pal_sel = self.rb_pal.currentIndex()  # 0-3=固定SPR, 4=attr自動
        all_items = self._romframe_items()
        counts = self._romframe_ref_counts(all_items)
        show_duplicates = getattr(self, "rb_duplicates", None) is not None and self.rb_duplicates.isChecked()
        items = all_items if show_duplicates else self._dedupe_romframe_items(all_items)
        self._romframe_render_items = list(items)
        self._romframe_render_bank = bank

        cols = 16
        cw = 16 * zoom
        ch = 16 * zoom + 12
        rows = (len(items) + cols - 1) // cols
        W = cols * (cw + 4) + 4
        H = rows * (ch + 4) + 4
        img = QImage(W, H, QImage.Format_ARGB32)
        img.fill(QColor(30, 30, 30))
        from PyQt5.QtGui import QPainter
        p = QPainter(img)
        p.setPen(QColor(190, 190, 190))
        for i, (g, s, fi, t1, t2, attr) in enumerate(items):
            ox = 4 + (i % cols) * (cw + 4)
            oy = 4 + (i // cols) * (ch + 4)
            # 確定 attr decode (Codex検証/$85E5・$85F2 ROM一致)
            # sprite1(左tile1): pal=(attr>>6)&3 Hf=(attr>>4)&1 Vf=(attr>>5)&1
            # sprite2(右tile2): pal=(attr>>2)&3 Hf=(attr>>1)&1 Vf=(attr>>0)&1
            if pal_sel == 4:
                p1 = (attr >> 6) & 3
                p2 = (attr >> 2) & 3
            else:
                p1 = p2 = pal_sel
            h1, v1 = (attr >> 4) & 1, (attr >> 5) & 1
            h2, v2 = (attr >> 1) & 1, (attr >> 0) & 1
            r1 = self._sprite_palette_rgb(p1)
            r2 = self._sprite_palette_rgb(p2)
            self._draw_8x16(img, r1, ox, oy, t1, bank, zoom, h1, v1)
            self._draw_8x16(img, r2, ox + 8 * zoom, oy, t2, bank, zoom, h2, v2)
            refs = counts.get(self._romframe_edit_key((g, s, fi, t1, t2, attr)), 1)
            ref_text = f"x{refs}" if refs > 1 and not show_duplicates else ""
            p.drawText(ox, oy + 16 * zoom + 10, f"g{g:02X}s{s:02X}f{fi}{ref_text}")
        p.end()
        lbl = RomFrameImageLabel(len(items), cols, cw, ch)
        lbl.setPixmap(QPixmap.fromImage(img))
        lbl.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        lbl.setToolTip(t(
            "sprite_viewer.romframe.tooltip",
            "ダブルクリックでこのフレームを16x16ピクセル編集で開く",
        ))
        lbl.frame_double_clicked.connect(self._on_romframe_double_clicked)
        old = self.scroll.takeWidget()
        if old:
            old.deleteLater()
        self.scroll.setWidget(lbl)
        if show_duplicates:
            count_text = t(
                "sprite_viewer.romframe.count.references",
                "{count} フレーム参照",
            ).format(count=len(items))
        else:
            count_text = t(
                "sprite_viewer.romframe.count.targets",
                "{targets} 編集対象 / {references} フレーム参照",
            ).format(targets=len(items), references=len(all_items))
        self.hover_label.setText(
            t(
                "sprite_viewer.romframe.status",
                "{count_text} / $D0E8機構由来 / Bank {bank} / "
                "16x16(8x16スプライト) / ROM直読み・configに依存しない",
            ).format(count_text=count_text, bank=bank))

    def _on_romframe_double_clicked(self, index):
        items = getattr(self, "_romframe_render_items", [])
        if not (0 <= int(index) < len(items)):
            return
        item = items[int(index)]
        _, _, _, t1, t2, attr = item
        bank = getattr(self, "_romframe_render_bank", self.rb_bank.currentIndex())
        editor_key = (int(bank), int(t1), int(t2), int(attr))
        old = self._editor_dialogs.get(editor_key)
        if old is not None and old.isVisible():
            old.raise_()
            old.activateWindow()
            return
        from .pixel_editor_dialog import PixelEditorDialog
        dlg = PixelEditorDialog(
            self.rom,
            parent=self,
            initial_key=(t1, t2, attr),
            initial_bank=bank,
            app_config=self._app_config,
        )
        dlg.setAttribute(Qt.WA_DeleteOnClose, True)
        dlg.rom_changed.connect(self._on_editor_rom_changed)
        from weakref import ref as weakref_ref
        owner_ref = weakref_ref(self)

        def clear_editor_dialog(_obj=None, owner_ref=owner_ref, editor_key=editor_key):
            owner = owner_ref()
            if owner is not None:
                owner._editor_dialogs.pop(editor_key, None)

        dlg.destroyed.connect(clear_editor_dialog)
        self._editor_dialogs[editor_key] = dlg
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def _on_editor_rom_changed(self):
        mode_code = self.mode_combo.currentData() if hasattr(self, "mode_combo") else ""
        if mode_code == "rom":
            self._render_romframes()
        self.rom_changed.emit()
