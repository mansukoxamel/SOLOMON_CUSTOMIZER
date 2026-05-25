"""スプライト/キャラクタービューア

2モード:
  - キャラクター: skc_config のメタタイル定義で組み立てた実キャラ
    (アイテム/敵/メタ) を名前付きで一覧。tile_renderer 使用。
  - 生CHRタイル: CHR-ROM の 8x8 タイルを素のまま一覧 (上級者向け)。

読込専用（ROM は変更しない）。
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSpinBox,
    QScrollArea, QWidget, QGridLayout, QDialogButtonBox, QCheckBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap, QColor

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


class SpriteViewer(QDialog):
    """スプライト/キャラクタービューア（読込専用）"""

    def __init__(self, rom, tile_renderer=None, config=None, parent=None):
        super().__init__(parent)
        if parent is not None:
            self.setFont(parent.font())
        self.setWindowTitle("スプライト/キャラクタービューア")
        self.resize(760, 800)
        self.rom = rom
        self.tile_renderer = tile_renderer
        self.config = config

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
        mode_row.addWidget(QLabel("表示モード:"))
        self.mode_combo = QComboBox()
        have_cfg = self.tile_renderer is not None and self.config is not None
        self.mode_combo.addItem("★ROMフレームデータ (全網羅 16x16)")
        if have_cfg:
            self.mode_combo.addItem("キャラクター (組み立て)")
        self.mode_combo.addItem("生CHRタイル (8x8素)")
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

    # ---- コントロール構築 (モード依存) ----
    def _rebuild_controls(self):
        while self.ctrl_layout.count():
            w = self.ctrl_layout.takeAt(0).widget()
            if w:
                w.deleteLater()

        mode_txt = self.mode_combo.currentText()
        is_char = mode_txt.startswith("キャラ")
        is_rom = mode_txt.startswith("★ROM")

        if is_rom:
            self.ctrl_layout.addWidget(QLabel("CHRバンク:"))
            self.rb_bank = QComboBox()
            for b in range(self.bank_count):
                self.rb_bank.addItem(f"Bank {b}")
            self.rb_bank.currentIndexChanged.connect(self._render_romframes)
            self.ctrl_layout.addWidget(self.rb_bank)

            self.ctrl_layout.addWidget(QLabel("パレット:"))
            self.rb_pal = QComboBox()
            for i in range(4, 8):
                self.rb_pal.addItem(PALETTE_LABELS[i])
            self.rb_pal.addItem("attr&3で自動")
            self.rb_pal.setCurrentIndex(4)
            self.rb_pal.currentIndexChanged.connect(self._render_romframes)
            self.ctrl_layout.addWidget(self.rb_pal)

            self.ctrl_layout.addWidget(QLabel("拡大:"))
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
            self.ctrl_layout.addWidget(QLabel("カテゴリ:"))
            self.cat_combo = QComboBox()
            self.cat_combo.addItems([
                "アイテム", "敵", "メタ", "全メタタイル",
                "★全網羅 (全tile_def×全tileset)",
                "★ROM由来 全キャラ(組立16x16)"])
            self.cat_combo.setCurrentIndex(5)  # 既定: ROM由来 全キャラ
            self.cat_combo.currentIndexChanged.connect(self._render_chars)
            self.ctrl_layout.addWidget(self.cat_combo)

            self.ctrl_layout.addWidget(QLabel("タイルセット:"))
            self.ts_combo = QComboBox()
            for i in range(len(self.config.tilesets)):
                self.ts_combo.addItem(f"tileset {i}")
            self.ts_combo.addItem("全部(網羅)")
            self.ts_combo.currentIndexChanged.connect(self._render_chars)
            self.ctrl_layout.addWidget(self.ts_combo)

            self.opaque_chk = QCheckBox("背景不透明")
            self.opaque_chk.setChecked(True)
            self.opaque_chk.stateChanged.connect(self._render_chars)
            self.ctrl_layout.addWidget(self.opaque_chk)

            self.ctrl_layout.addWidget(QLabel("拡大:"))
            self.zoom_spin = QSpinBox()
            self.zoom_spin.setRange(1, 12)
            self.zoom_spin.setValue(4)
            self.zoom_spin.setSuffix(" x")
            self.zoom_spin.valueChanged.connect(self._render_chars)
            self.ctrl_layout.addWidget(self.zoom_spin)
            self.ctrl_layout.addStretch()
            self._render_chars()
        else:
            self.ctrl_layout.addWidget(QLabel("バンク:"))
            self.bank_combo = QComboBox()
            for b in range(self.bank_count):
                self.bank_combo.addItem(f"Bank {b}")
            self.bank_combo.currentIndexChanged.connect(self._render_raw)
            self.ctrl_layout.addWidget(self.bank_combo)

            self.ctrl_layout.addWidget(QLabel("パレット:"))
            self.pal_combo = QComboBox()
            for i in range(PALETTE_COUNT):
                self.pal_combo.addItem(PALETTE_LABELS[i])
            self.pal_combo.setCurrentIndex(4)
            self.pal_combo.currentIndexChanged.connect(self._render_raw)
            self.ctrl_layout.addWidget(self.pal_combo)

            self.ctrl_layout.addWidget(QLabel("拡大:"))
            self.zoom_spin = QSpinBox()
            self.zoom_spin.setRange(1, 16)
            self.zoom_spin.setValue(4)
            self.zoom_spin.setSuffix(" x")
            self.zoom_spin.valueChanged.connect(self._render_raw)
            self.ctrl_layout.addWidget(self.zoom_spin)

            self.grid_chk = QCheckBox("グリッド線")
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
        26: "Dragon s0", 27: "Dragon s1", 28: "Golem s0", 29: "Golem s1",
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
        if self.cat_combo.currentText().startswith("★ROM由来"):
            self._render_rom_assembled()
            return
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
        self.hover_label.setText(
            f"{idx} 枚表示 / tile_def {len(self.config.tile_defs)}種 × "
            f"tileset {n_ts}種 / フィルタなし全網羅可")

    # ---- 生CHRタイルモード ----
    def _get_subpalette(self):
        idx = self.pal_combo.currentIndex()
        off = PALETTE_OFFSET + idx * 4
        try:
            return pal.load_palette_from_rom(self.rom.data, off)
        except Exception:
            return pal.SubPalette([0x0f, 0x00, 0x10, 0x30])

    def _render_raw(self):
        bank = self.bank_combo.currentIndex()
        zoom = self.zoom_spin.value()
        show_grid = self.grid_chk.isChecked()
        sub_pal = self._get_subpalette()

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
        rgb = [QColor(*sub_pal.get_rgb(i)).rgb() for i in range(4)]

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
                    px0, py0 = ox + x * zoom, oy + y * zoom
                    for dy in range(zoom):
                        for dx in range(zoom):
                            img.setPixel(px0 + dx, py0 + dy, color)

        lbl = QLabel()
        lbl.setPixmap(QPixmap.fromImage(img))
        lbl.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        old = self.scroll.takeWidget()
        if old:
            old.deleteLater()
        self.scroll.setWidget(lbl)
        self.hover_label.setText(
            f"Bank {bank}: タイル {first}-{last-1} / CHR開始 0x{self.chr_start:X}")

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

    # 確定: CNROM ラッチ $8C79→$8D20=$96 → CHR bank 2 固定
    SPRITE_BANK = 2

    def _draw_8x16(self, img, rgb, ox, oy, byte_idx, bank, zoom,
                   hflip=False, vflip=False):
        """NES 8x16: tile bit0=パターンテーブル($0000/$1000)、
        byte&$FE=上タイル/+1=下。bank は SPRITE_BANK 固定。
        attr由来の H/V flip 適用。"""
        bank = self.SPRITE_BANK
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
        items = self._romframe_items()

        subpals = []
        for pi in range(8):
            try:
                subpals.append(pal.load_palette_from_rom(
                    self.rom.data, PALETTE_OFFSET + pi * 4))
            except Exception:
                subpals.append(pal.SubPalette([0x0f, 0x00, 0x10, 0x30]))

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
            r1 = [QColor(*subpals[4 + p1].get_rgb(k)).rgb() for k in range(4)]
            r2 = [QColor(*subpals[4 + p2].get_rgb(k)).rgb() for k in range(4)]
            self._draw_8x16(img, r1, ox, oy, t1, 2, zoom, h1, v1)
            self._draw_8x16(img, r2, ox + 8 * zoom, oy, t2, 2, zoom, h2, v2)
            p.drawText(ox, oy + 16 * zoom + 10, f"g{g:02X}s{s:02X}f{fi}")
        p.end()
        lbl = QLabel()
        lbl.setPixmap(QPixmap.fromImage(img))
        lbl.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        old = self.scroll.takeWidget()
        if old:
            old.deleteLater()
        self.scroll.setWidget(lbl)
        self.hover_label.setText(
            f"{len(items)} フレーム / $D0E8機構由来 / Bank {bank} / "
            "16x16(8x16スプライト) / ROM直読み・configに依存しない全網羅")

    # ---- ★ROM由来 全キャラ(組立) をキャラクターモードに表示 ----
    def _render_rom_assembled(self):
        zoom = self.zoom_spin.value()
        items = self._romframe_items()
        subpals = []
        for pi in range(8):
            try:
                subpals.append(pal.load_palette_from_rom(
                    self.rom.data, PALETTE_OFFSET + pi * 4))
            except Exception:
                subpals.append(pal.SubPalette([0x0f, 0x00, 0x10, 0x30]))

        old = self.scroll.takeWidget()
        if old:
            old.deleteLater()
        host = QWidget()
        grid = QGridLayout(host)
        grid.setSpacing(6)
        cols = 6
        for i, (g, s, fi, t1, t2, attr) in enumerate(items):
            # 確定 attr decode + CHR bank 2 固定 (Codex検証/ROM一致)
            p1, p2 = (attr >> 6) & 3, (attr >> 2) & 3
            h1, v1 = (attr >> 4) & 1, (attr >> 5) & 1
            h2, v2 = (attr >> 1) & 1, (attr >> 0) & 1
            r1 = [QColor(*subpals[4 + p1].get_rgb(k)).rgb() for k in range(4)]
            r2 = [QColor(*subpals[4 + p2].get_rgb(k)).rgb() for k in range(4)]
            cell_img = QImage(16 * zoom, 16 * zoom, QImage.Format_ARGB32)
            cell_img.fill(QColor(60, 60, 60))
            self._draw_8x16(cell_img, r1, 0, 0, t1, 2, zoom, h1, v1)
            self._draw_8x16(cell_img, r2, 8 * zoom, 0, t2, 2, zoom, h2, v2)
            cell = QWidget()
            cl = QVBoxLayout(cell)
            cl.setContentsMargins(2, 2, 2, 2)
            cl.setSpacing(1)
            pic = QLabel()
            pic.setPixmap(QPixmap.fromImage(cell_img))
            pic.setAlignment(Qt.AlignCenter)
            name = self.GROUP_NAMES.get(g, f"grp{g:02X}")
            txt = QLabel(f"{name}\ng{g:02X}s{s:02X}f{fi}")
            txt.setAlignment(Qt.AlignCenter)
            txt.setWordWrap(True)
            txt.setStyleSheet("font-size: 9px;")
            cl.addWidget(pic)
            cl.addWidget(txt)
            grid.addWidget(cell, i // cols, i % cols)
        host.setLayout(grid)
        self.scroll.setWidget(host)
        self.hover_label.setText(
            f"{len(items)} キャラ(組立16x16) / $D0E8由来 / "
            "CHRバンク自動補正 / configに依存しない全網羅")
