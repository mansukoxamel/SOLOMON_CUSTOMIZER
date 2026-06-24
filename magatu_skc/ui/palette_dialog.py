"""パレット編集ダイアログ

ROM offset 0xED4 から 32バイト = 8パレット (背景4 + スプライト4) を編集する。
拡張ROMでも変換時に 0..32784 はそのままコピーされるため、同じオフセットが使える。

各パレット = 4バイト [c1, c2, c3, separator(0x0F or 0x00)]
編集対象は c1, c2, c3 の3色のみ。separator は維持。
"""
import os
import json
import random

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QDialogButtonBox, QFrame, QGroupBox, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPixmap, QImage, QPainter, QPen

from .. import __version__
from ..nes.palette import NES_COLORS
from ..core import stage50_book_color, wall_color_hack
from .dialog_geometry import restore_dialog_geometry, save_dialog_geometry


# 編集対象オフセット（パレットテーブル先頭）
PALETTE_OFFSET = 0xED4
# パレット数 (背景4 + スプライト4)
PALETTE_COUNT = 8
# パレットあたりバイト数
BYTES_PER_PALETTE = 4
# 編集可能な色のスロット数（1パレットあたり）
EDITABLE_COLORS = 3

# 各パレットのラベル
PALETTE_LABELS = [
    "BG #0",   "BG #1",   "BG #2",   "BG #3",
    "SPR #0 主人公", "SPR #1 サラマンダー", "SPR #2 ガーゴイル", "SPR #3 ゴブリン",
]

# 背景パレット(0-3)に対応するタイル番号
BG_PREVIEW_TILES = {
    0: 2,   # BG#0 → 白い壁
    1: 1,   # BG#1 → 壊せる壁（茶ブロック）
    2: 12,  # BG#2 → ファイアジャー（青）
    3: 13,  # BG#3 → ファイアジャー（オレンジ）
}

# スプライトパレット(4-7)に対応するキャラクターのタイル番号
# skc_config.xml の tile_definitions から: Dana=3, Dragon=64, Gargoyle=66, Golem=65
SPRITE_PREVIEW_TILES = {
    4: 3,   # SPR#0 → 主人公 (Dana)
    5: 73,  # SPR#1 → サラマンダー (Saramandor right)
    6: 66,  # SPR#2 → ガーゴイル (Gargoyle right)
    7: 65,  # SPR#3 → ゴブリン (Golem right)
}

# 全パレットのプレビュータイル（BGとSPRを統合）
ALL_PREVIEW_TILES = {**BG_PREVIEW_TILES, **SPRITE_PREVIEW_TILES}

PALETTE_DATA_FORMAT = "magatu_skc_palette"
PALETTE_PNG_METADATA_KEY = "SOLOMON_CUSTOMIZER_PALETTE"


def nes_to_qcolor(nes_idx: int) -> QColor:
    nes_idx &= 0x3F
    r, g, b = NES_COLORS[nes_idx]
    return QColor(r, g, b)


class PaletteDialog(QDialog):
    """パレット編集ダイアログ（64色ピッカー統合版）

    ROM の 0xED4 から 32バイトを8パレット × 4バイトとして読み出し、
    各パレットの 3色（4色目のセパレータは維持）を下部の64色グリッドで編集する。
    """

    SWATCH_W = 48
    SWATCH_H = 32

    def __init__(self, rom_data: bytearray, parent=None, tile_renderer=None,
                 app_config=None):
        super().__init__(parent)
        if parent is not None:
            self.setFont(parent.font())
        self.setWindowTitle("パレット編集")
        self.rom_data = rom_data
        self._tile_renderer = tile_renderer
        self._app_config = app_config
        # 作業バッファ（OKまたはApplyで rom_data に反映）
        self._buf = [
            list(rom_data[PALETTE_OFFSET + p * BYTES_PER_PALETTE:
                          PALETTE_OFFSET + (p + 1) * BYTES_PER_PALETTE])
            for p in range(PALETTE_COUNT)
        ]
        # ダイアログ起動時のスナップショット（リセット用）
        self._initial = [list(b) for b in self._buf]
        self._buttons = [[None] * EDITABLE_COLORS for _ in range(PALETTE_COUNT)]
        self._wall_ok = False
        self._wall_buf = []
        self._wall_initial = []
        self._wall_buttons = []
        self._book_color_ok = False
        self._book_color = stage50_book_color.ORIGINAL_COLOR
        self._book_color_initial = self._book_color
        self._book_color_button = None
        try:
            self._wall_buf = list(wall_color_hack.current_values(rom_data))
            wall_color_hack.special_values(rom_data)
            self._wall_initial = list(self._wall_buf)
            self._wall_ok = True
        except wall_color_hack.WallColorHackError:
            self._wall_buf = list(wall_color_hack.ORIGINAL_VALUES)
            self._wall_initial = list(self._wall_buf)
        try:
            self._book_color = stage50_book_color.current_value(rom_data)
            self._book_color_initial = self._book_color
            self._book_color_ok = True
        except stage50_book_color.Stage50BookColorError:
            pass
        self._sprite_icons = {}
        self._changed = False
        # 現在選択中のスウォッチ
        self._sel_palette = None
        self._sel_slot = None
        self._sel_wall = None
        self._sel_book_color = False

        self._build_ui()
        restore_dialog_geometry(self, self._app_config, "palette_dlg")

    def _build_ui(self):
        layout = QVBoxLayout(self)

        info = QLabel(
            "<b>主人公の色は SPR #0〜#3 のどれかにあります</b>。"
            "色ボタンをクリックして選択 → 下の64色パレットで変更。"
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        wall_group = QGroupBox("ステージ壁色 (1-48面)")
        wall_layout = QGridLayout(wall_group)
        for i in range(wall_color_hack.EDIT_COUNT):
            label = QLabel(f"{wall_color_hack.stage_range_label(i)}面")
            btn = QPushButton()
            btn.setFixedSize(self.SWATCH_W, self.SWATCH_H)
            btn.setEnabled(self._wall_ok)
            btn.clicked.connect(lambda _, idx=i: self._on_wall_swatch_click(idx))
            self._wall_buttons.append(btn)
            row = i // 6
            col = (i % 6) * 2
            wall_layout.addWidget(label, row, col)
            wall_layout.addWidget(btn, row, col + 1)
            self._refresh_wall_swatch(i)
        layout.addWidget(wall_group)

        book_group = QGroupBox("Stage 50 ソロモンの書の色")
        book_layout = QHBoxLayout(book_group)
        book_layout.addWidget(QLabel("色"))
        self._book_color_button = QPushButton()
        self._book_color_button.setFixedSize(self.SWATCH_W, self.SWATCH_H)
        self._book_color_button.setEnabled(self._book_color_ok)
        self._book_color_button.clicked.connect(self._on_book_color_swatch_click)
        book_layout.addWidget(self._book_color_button)
        book_layout.addStretch()
        self._refresh_book_color_swatch()
        layout.addWidget(book_group)

        # 背景パレット
        bg_group = QGroupBox("背景パレット")
        bgl = QVBoxLayout(bg_group)
        for p in range(4):
            bgl.addLayout(self._build_palette_row(p))
        layout.addWidget(bg_group)

        # スプライトパレット
        spr_group = QGroupBox("スプライトパレット (主人公・敵・アイテム)")
        sprl = QVBoxLayout(spr_group)
        for p in range(4, 8):
            sprl.addLayout(self._build_palette_row(p))
        layout.addWidget(spr_group)

        # 64色 NES カラーグリッド（統合表示）
        picker_group = QGroupBox("NESカラー選択")
        picker_layout = QVBoxLayout(picker_group)
        self._picker_info = QLabel("↑ 色ボタンをクリックして編集対象を選択")
        picker_layout.addWidget(self._picker_info)

        grid = QGridLayout()
        grid.setSpacing(2)
        self._color_buttons = []
        for i in range(64):
            btn = QPushButton()
            btn.setFixedSize(28, 28)
            qc = nes_to_qcolor(i)
            btn.setStyleSheet(
                f"background-color: {qc.name()}; border: 1px solid #444;"
            )
            btn.setToolTip(f"0x{i:02X}")
            btn.clicked.connect(lambda _, idx=i: self._on_color_pick(idx))
            grid.addWidget(btn, i // 16, i % 16)
            self._color_buttons.append(btn)
        picker_layout.addLayout(grid)
        layout.addWidget(picker_group)

        # 操作ボタン
        btnbar = QHBoxLayout()
        btn_save = QPushButton("設定を画像保存...")
        btn_save.setToolTip("現在のパレット設定をPNG画像とメタデータとして保存")
        btn_save.clicked.connect(self._save_palette_png)
        btnbar.addWidget(btn_save)
        btn_load = QPushButton("画像から読込...")
        btn_load.setToolTip("PNG画像のメタデータからパレット設定を読み込み")
        btn_load.clicked.connect(self._load_palette_file)
        btnbar.addWidget(btn_load)
        btn_reset = QPushButton("編集開始時に戻す")
        btn_reset.setToolTip("このパレット編集を開いた時点の値に戻す")
        btn_reset.clicked.connect(self._reset)
        btnbar.addWidget(btn_reset)
        btn_random3 = QPushButton("ランダム3色")
        btn_random3.setToolTip("選択中のパレット3色をランダムなNES色に変更")
        btn_random3.clicked.connect(self._randomize_selected_palette)
        btnbar.addWidget(btn_random3)
        btn_shift3 = QPushButton("色相ずらし")
        btn_shift3.setToolTip("選択中パレットの色付き3色だけを同じ明度のまま色相方向へずらす")
        btn_shift3.clicked.connect(self._shift_selected_palette)
        btnbar.addWidget(btn_shift3)
        layout.addLayout(btnbar)

        btnbox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply
        )
        btnbox.accepted.connect(self._apply_and_close)
        btnbox.rejected.connect(self.reject)
        btnbox.button(QDialogButtonBox.Apply).clicked.connect(self._apply)
        layout.addWidget(btnbox)

    def _build_palette_row(self, palette_no: int) -> QHBoxLayout:
        row = QHBoxLayout()
        # パレットにプレビューアイコンを表示（BG: 壁/ファイアジャー、SPR: キャラクター）
        if palette_no in ALL_PREVIEW_TILES and self._tile_renderer is not None:
            icon_lbl = QLabel()
            icon_lbl.setFixedSize(48, 48)
            tile_no = ALL_PREVIEW_TILES[palette_no]
            try:
                is_bg = palette_no in BG_PREVIEW_TILES
                qimg = self._tile_renderer.get_tile_image(tile_no, 0, transparent=not is_bg)
                pix = QPixmap.fromImage(qimg).scaled(
                    48, 48, Qt.KeepAspectRatio, Qt.FastTransformation
                )
                icon_lbl.setPixmap(pix)
            except Exception:
                pass
            self._sprite_icons[palette_no] = icon_lbl
            row.addWidget(icon_lbl)
        lbl = QLabel(PALETTE_LABELS[palette_no])
        lbl.setMinimumWidth(140)
        row.addWidget(lbl)
        for slot in range(EDITABLE_COLORS):
            btn = QPushButton()
            btn.setFixedSize(self.SWATCH_W, self.SWATCH_H)
            btn.clicked.connect(
                lambda _, p=palette_no, s=slot: self._on_swatch_click(p, s)
            )
            self._buttons[palette_no][slot] = btn
            self._refresh_swatch(palette_no, slot)
            row.addWidget(btn)
        row.addStretch()
        return row

    def _refresh_swatch(self, palette_no: int, slot: int):
        nes_idx = self._buf[palette_no][slot] & 0x3F
        qc = nes_to_qcolor(nes_idx)
        btn = self._buttons[palette_no][slot]
        # 暗い色の上では文字を白に、明るい色の上では黒に
        r, g, b = NES_COLORS[nes_idx]
        text_color = "#ffffff" if (r + g + b) < 380 else "#000000"
        # 選択中のスウォッチは太い白枠で強調
        is_selected = (palette_no == self._sel_palette and slot == self._sel_slot
                       and self._sel_wall is None)
        border = "3px solid #00ff00" if is_selected else "1px solid #888"
        btn.setStyleSheet(
            f"background-color: {qc.name()}; color: {text_color}; "
            f"border: {border};"
        )
        btn.setText(f"0x{nes_idx:02X}")

    def _on_swatch_click(self, palette_no: int, slot: int):
        """スウォッチをクリック → 64色グリッドの選択対象にする"""
        old_p, old_s = self._sel_palette, self._sel_slot
        old_wall = self._sel_wall
        old_book = self._sel_book_color
        self._sel_palette = palette_no
        self._sel_slot = slot
        self._sel_wall = None
        self._sel_book_color = False
        # 旧選択のボーダーを戻す
        if old_p is not None and old_s is not None:
            self._refresh_swatch(old_p, old_s)
        if old_wall is not None:
            self._refresh_wall_swatch(old_wall)
        if old_book:
            self._refresh_book_color_swatch()
        # 新選択のボーダーを強調
        self._refresh_swatch(palette_no, slot)

        cur_idx = self._buf[palette_no][slot] & 0x3F
        label = PALETTE_LABELS[palette_no]
        self._picker_info.setText(
            f"<b>{label}</b> スロット{slot + 1} を編集中 (現在: 0x{cur_idx:02X})"
        )
        # 64色グリッドの現在色をハイライト
        self._update_color_grid_highlight(cur_idx)

    def _refresh_wall_swatch(self, index: int):
        if not (0 <= index < len(self._wall_buttons)):
            return
        nes_idx = self._wall_buf[index] & 0x3F
        qc = nes_to_qcolor(nes_idx)
        btn = self._wall_buttons[index]
        r, g, b = NES_COLORS[nes_idx]
        text_color = "#ffffff" if (r + g + b) < 380 else "#000000"
        border = "3px solid #00ff00" if index == self._sel_wall else "1px solid #888"
        btn.setStyleSheet(
            f"background-color: {qc.name()}; color: {text_color}; border: {border};"
        )
        btn.setText(f"0x{nes_idx:02X}")

    def _refresh_book_color_swatch(self):
        if self._book_color_button is None:
            return
        nes_idx = self._book_color & 0x3F
        qc = nes_to_qcolor(nes_idx)
        r, g, b = NES_COLORS[nes_idx]
        text_color = "#ffffff" if (r + g + b) < 380 else "#000000"
        border = "3px solid #00ff00" if self._sel_book_color else "1px solid #888"
        self._book_color_button.setStyleSheet(
            f"background-color: {qc.name()}; color: {text_color}; border: {border};"
        )
        self._book_color_button.setText(f"0x{nes_idx:02X}")

    def _on_wall_swatch_click(self, index: int):
        old_p, old_s = self._sel_palette, self._sel_slot
        old_wall = self._sel_wall
        old_book = self._sel_book_color
        self._sel_palette = None
        self._sel_slot = None
        self._sel_wall = index
        self._sel_book_color = False
        if old_p is not None and old_s is not None:
            self._refresh_swatch(old_p, old_s)
        if old_wall is not None:
            self._refresh_wall_swatch(old_wall)
        if old_book:
            self._refresh_book_color_swatch()
        self._refresh_wall_swatch(index)
        cur_idx = self._wall_buf[index] & 0x3F
        self._picker_info.setText(
            f"<b>ステージ壁色 {wall_color_hack.stage_range_label(index)}面</b> を編集中 "
            f"(現在: 0x{cur_idx:02X})"
        )
        self._update_color_grid_highlight(cur_idx)

    def _on_book_color_swatch_click(self):
        old_p, old_s = self._sel_palette, self._sel_slot
        old_wall = self._sel_wall
        self._sel_palette = None
        self._sel_slot = None
        self._sel_wall = None
        self._sel_book_color = True
        if old_p is not None and old_s is not None:
            self._refresh_swatch(old_p, old_s)
        if old_wall is not None:
            self._refresh_wall_swatch(old_wall)
        self._refresh_book_color_swatch()
        cur_idx = self._book_color & 0x3F
        self._picker_info.setText(
            f"<b>Stage 50 ソロモンの書の色</b> を編集中 (現在: 0x{cur_idx:02X})"
        )
        self._update_color_grid_highlight(cur_idx)

    def _update_color_grid_highlight(self, selected_idx: int):
        """64色グリッドで選択中の色を白枠でハイライト"""
        for i, btn in enumerate(self._color_buttons):
            qc = nes_to_qcolor(i)
            if i == selected_idx:
                btn.setStyleSheet(
                    f"background-color: {qc.name()}; border: 3px solid #ffffff;"
                )
            else:
                btn.setStyleSheet(
                    f"background-color: {qc.name()}; border: 1px solid #444;"
                )

    def _on_color_pick(self, nes_idx: int):
        """64色グリッドの色をクリック → 選択中のスウォッチに反映"""
        if self._sel_wall is not None:
            idx = self._sel_wall
            cur = self._wall_buf[idx] & 0x3F
            new_idx = nes_idx & 0x3F
            if new_idx != cur:
                self._wall_buf[idx] = new_idx
                self._refresh_wall_swatch(idx)
                self._changed = True
            self._picker_info.setText(
                f"<b>ステージ壁色 {wall_color_hack.stage_range_label(idx)}面</b> を編集中 "
                f"(現在: 0x{new_idx:02X})"
            )
            self._update_color_grid_highlight(new_idx)
            return
        if self._sel_book_color:
            cur = self._book_color & 0x3F
            new_idx = nes_idx & 0x3F
            if new_idx != cur:
                self._book_color = new_idx
                self._refresh_book_color_swatch()
                self._changed = True
            self._picker_info.setText(
                f"<b>Stage 50 ソロモンの書の色</b> を編集中 (現在: 0x{new_idx:02X})"
            )
            self._update_color_grid_highlight(new_idx)
            return
        if self._sel_palette is None or self._sel_slot is None:
            return
        p, s = self._sel_palette, self._sel_slot
        cur = self._buf[p][s] & 0x3F
        new_idx = nes_idx & 0x3F
        if new_idx != cur:
            self._buf[p][s] = new_idx
            self._refresh_swatch(p, s)
            self._changed = True
            self._refresh_sprite_icons()
        # 情報ラベル更新
        label = PALETTE_LABELS[p]
        self._picker_info.setText(
            f"<b>{label}</b> スロット{s + 1} を編集中 (現在: 0x{new_idx:02X})"
        )
        self._update_color_grid_highlight(new_idx)

    def _refresh_sprite_icons(self):
        """_buf の現在色でスプライトアイコンを再描画"""
        if self._tile_renderer is None:
            return
        from ..nes.palette import get_nes_color
        from ..nes.tile import NES_TILE_W
        config = self._tile_renderer.config
        nes_tiles = self._tile_renderer.nes_tiles

        for pal_no, tile_no in ALL_PREVIEW_TILES.items():
            if pal_no not in self._sprite_icons:
                continue
            tile_def = config.tile_defs.get(tile_no)
            if tile_def is None:
                continue
            # タイルが実際に使うパレット番号（tileset 0 の offset=0 を前提）
            actual_pal_no = tile_def.palette_no
            if actual_pal_no >= PALETTE_COUNT:
                continue
            # _buf からサブパレット構築 [0x0F(透明), c1, c2, c3]
            buf_colors = [0x0F] + [self._buf[actual_pal_no][s] & 0x3F
                                   for s in range(EDITABLE_COLORS)]

            w_t = tile_def.width
            h_t = tile_def.height
            img_w = w_t * NES_TILE_W
            img_h = h_t * NES_TILE_W
            img = QImage(img_w, img_h, QImage.Format_ARGB32)
            is_bg = pal_no in BG_PREVIEW_TILES
            if is_bg:
                # BGタイルは背景色(0x0F=黒)で塗りつぶし
                bg_rgb = get_nes_color(0x0F)
                img.fill(QColor(*bg_rgb))
            else:
                img.fill(QColor(0, 0, 0, 0))

            for idx, (nes_tile_no, flip_v, flip_h) in enumerate(tile_def.nes_tiles):
                tx = (idx % w_t) * NES_TILE_W
                ty = (idx // w_t) * NES_TILE_W
                if nes_tile_no >= len(nes_tiles):
                    continue
                nt = nes_tiles[nes_tile_no]
                for y in range(NES_TILE_W):
                    for x in range(NES_TILE_W):
                        pi = nt.get_palette_index(x, y, flip_v, flip_h)
                        if pi == 0 and not is_bg:
                            continue
                        rgb = get_nes_color(buf_colors[pi])
                        img.setPixel(tx + x, ty + y, QColor(*rgb).rgb())

            pix = QPixmap.fromImage(img).scaled(
                48, 48, Qt.KeepAspectRatio, Qt.FastTransformation
            )
            self._sprite_icons[pal_no].setPixmap(pix)

    def _reset(self):
        for p in range(PALETTE_COUNT):
            for s in range(EDITABLE_COLORS):
                self._buf[p][s] = self._initial[p][s]
                self._refresh_swatch(p, s)
        for i, value in enumerate(self._wall_initial):
            self._wall_buf[i] = value
            self._refresh_wall_swatch(i)
        self._book_color = self._book_color_initial
        self._refresh_book_color_swatch()
        self._changed = False
        self._refresh_sprite_icons()
        if self._sel_wall is not None:
            cur_idx = self._wall_buf[self._sel_wall] & 0x3F
            self._picker_info.setText(
                f"<b>ステージ壁色 {wall_color_hack.stage_range_label(self._sel_wall)}面</b> を編集中 "
                f"(現在: 0x{cur_idx:02X})"
            )
            self._update_color_grid_highlight(cur_idx)
        elif self._sel_book_color:
            cur_idx = self._book_color & 0x3F
            self._picker_info.setText(
                f"<b>Stage 50 ソロモンの書の色</b> を編集中 (現在: 0x{cur_idx:02X})"
            )
            self._update_color_grid_highlight(cur_idx)
        elif self._sel_palette is not None and self._sel_slot is not None:
            cur_idx = self._buf[self._sel_palette][self._sel_slot] & 0x3F
            label = PALETTE_LABELS[self._sel_palette]
            self._picker_info.setText(
                f"<b>{label}</b> スロット{self._sel_slot + 1} を編集中 (現在: 0x{cur_idx:02X})"
            )
            self._update_color_grid_highlight(cur_idx)

    def _selected_palette_no(self):
        if self._sel_wall is not None:
            QMessageBox.information(self, "対象外", "ステージ壁色は1色なので、この操作の対象外です。")
            return None
        if self._sel_book_color:
            QMessageBox.information(self, "対象外", "Stage 50 ソロモンの書の色は1色なので、この操作の対象外です。")
            return None
        if self._sel_palette is None:
            QMessageBox.information(self, "対象未選択", "先に変更したいパレットの色ボタンを選択してください。")
            return None
        return self._sel_palette

    def _refresh_palette_row(self, palette_no: int):
        for slot in range(EDITABLE_COLORS):
            self._refresh_swatch(palette_no, slot)
        self._changed = True
        self._refresh_sprite_icons()
        if self._sel_slot is not None:
            cur_idx = self._buf[palette_no][self._sel_slot] & 0x3F
            self._update_color_grid_highlight(cur_idx)
            label = PALETTE_LABELS[palette_no]
            self._picker_info.setText(
                f"<b>{label}</b> スロット{self._sel_slot + 1} を編集中 (現在: 0x{cur_idx:02X})"
            )

    def _randomize_selected_palette(self):
        palette_no = self._selected_palette_no()
        if palette_no is None:
            return
        for slot, nes_idx in enumerate(random.sample(range(0x40), EDITABLE_COLORS)):
            self._buf[palette_no][slot] = nes_idx
        self._refresh_palette_row(palette_no)

    @staticmethod
    def _shift_nes_hue(nes_idx: int) -> int:
        value = nes_idx & 0x3F
        brightness = value & 0x30
        hue = value & 0x0F
        if 1 <= hue <= 12:
            return brightness | (1 + (hue % 12))
        return value

    def _shift_selected_palette(self):
        palette_no = self._selected_palette_no()
        if palette_no is None:
            return
        for slot in range(EDITABLE_COLORS):
            self._buf[palette_no][slot] = self._shift_nes_hue(self._buf[palette_no][slot])
        self._refresh_palette_row(palette_no)

    def _palette_data(self) -> dict:
        data = {
            "format": PALETTE_DATA_FORMAT,
            "version": 2,
            "app_version": __version__,
            "palettes": [],
            "wall_colors": [],
            "stage50_solomon_book_color": None,
        }
        for p in range(PALETTE_COUNT):
            colors = [self._buf[p][s] & 0x3F for s in range(EDITABLE_COLORS)]
            data["palettes"].append({
                "label": PALETTE_LABELS[p],
                "colors": colors,
            })
        if self._wall_ok:
            for i, value in enumerate(self._wall_buf):
                data["wall_colors"].append({
                    "label": f"{wall_color_hack.stage_range_label(i)}面",
                    "color": value & 0x3F,
                })
        if self._book_color_ok:
            data["stage50_solomon_book_color"] = {
                "label": "Stage 50 ソロモンの書の色",
                "color": self._book_color & 0x3F,
            }
        return data

    def _build_palette_png(self, data: dict) -> QImage:
        wall_colors = data.get("wall_colors", [])
        wall_rows = 2 if wall_colors else 0
        book_color = data.get("stage50_solomon_book_color")
        book_rows = 1 if isinstance(book_color, dict) else 0
        width = 760
        height = 58 + PALETTE_COUNT * 42 + 36 + wall_rows * 44 + book_rows * 44 + 22
        img = QImage(width, height, QImage.Format_ARGB32)
        img.fill(QColor("#101820"))

        painter = QPainter(img)
        try:
            painter.setRenderHint(QPainter.Antialiasing, False)
            painter.setPen(QColor("#E8F1F2"))
            painter.drawText(18, 28, "SOLOMON_CUSTOMIZER palette settings")
            painter.setPen(QColor("#9FB3C8"))
            painter.drawText(18, 48, f"App v{__version__} / NES color indexes are embedded in PNG metadata")

            y = 76
            painter.setPen(QColor("#E8F1F2"))
            painter.drawText(18, y - 12, "Main palettes")
            for p, entry in enumerate(data.get("palettes", [])):
                label = entry.get("label", PALETTE_LABELS[p] if p < PALETTE_COUNT else f"Palette {p}")
                colors = entry.get("colors", [])
                painter.setPen(QColor("#D7E3EA"))
                painter.drawText(18, y + 22, str(label))
                for s, value in enumerate(colors[:EDITABLE_COLORS]):
                    nes_idx = int(value) & 0x3F
                    x = 220 + s * 118
                    painter.fillRect(x, y, 40, 28, nes_to_qcolor(nes_idx))
                    painter.setPen(QPen(QColor("#EEF6F7"), 1))
                    painter.drawRect(x, y, 40, 28)
                    painter.setPen(QColor("#D7E3EA"))
                    painter.drawText(x + 48, y + 20, f"0x{nes_idx:02X}")
                y += 42

            if wall_colors:
                y += 16
                painter.setPen(QColor("#E8F1F2"))
                painter.drawText(18, y - 8, "Stage wall colors")
                for i, entry in enumerate(wall_colors):
                    nes_idx = int(entry.get("color", 0)) & 0x3F
                    col = i % 6
                    row = i // 6
                    x = 18 + col * 122
                    yy = y + row * 44
                    painter.fillRect(x, yy, 36, 24, nes_to_qcolor(nes_idx))
                    painter.setPen(QPen(QColor("#EEF6F7"), 1))
                    painter.drawRect(x, yy, 36, 24)
                    painter.setPen(QColor("#D7E3EA"))
                    painter.drawText(x + 42, yy + 17, f"{entry.get('label', '')} 0x{nes_idx:02X}")
                y += wall_rows * 44 + 16
            if isinstance(book_color, dict):
                nes_idx = int(book_color.get("color", 0)) & 0x3F
                painter.setPen(QColor("#E8F1F2"))
                painter.drawText(18, y - 8, "Stage 50 Solomon book color")
                painter.fillRect(18, y, 36, 24, nes_to_qcolor(nes_idx))
                painter.setPen(QPen(QColor("#EEF6F7"), 1))
                painter.drawRect(18, y, 36, 24)
                painter.setPen(QColor("#D7E3EA"))
                painter.drawText(60, y + 17, f"{book_color.get('label', '')} 0x{nes_idx:02X}")
        finally:
            painter.end()

        meta = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        img.setText(PALETTE_PNG_METADATA_KEY, meta)
        img.setText("Software", f"SOLOMON_CUSTOMIZER {__version__}")
        img.setText("Description", "SOLOMON_CUSTOMIZER palette settings with embedded NES color indexes")
        return img

    def _save_palette_png(self):
        """パレット設定をPNG画像とメタデータに保存"""
        from .file_dialog_compat import get_path
        path = get_path(
            parent=self,
            title="パレット設定を画像保存",
            filter="PNG Images (*.png);;All files (*)",
            mode="save",
        )
        if not path:
            return
        if not path.lower().endswith(".png"):
            path += ".png"
        try:
            img = self._build_palette_png(self._palette_data())
            if not img.save(path, "PNG"):
                raise OSError("PNG保存に失敗しました。")
            QMessageBox.information(self, "保存完了", f"パレット設定画像を保存しました:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "保存失敗", f"{type(e).__name__}: {e}")

    def _read_palette_file(self, path: str) -> dict:
        if path.lower().endswith(".json"):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        img = QImage(path)
        if img.isNull():
            raise ValueError("画像として読み込めません。")
        meta = img.text(PALETTE_PNG_METADATA_KEY)
        if not meta:
            raise ValueError("このPNGにはパレット設定メタデータがありません。")
        return json.loads(meta)

    def _apply_palette_data(self, data: dict) -> bool:
        if data.get("format") != PALETTE_DATA_FORMAT:
            QMessageBox.warning(self, "形式エラー", "このファイルはパレット設定ではありません。")
            return False
        palettes = data.get("palettes", [])
        if len(palettes) != PALETTE_COUNT:
            QMessageBox.warning(self, "形式エラー", f"パレット数が不正です（{len(palettes)}、期待値: {PALETTE_COUNT}）。")
            return False
        for p in range(PALETTE_COUNT):
            colors = palettes[p].get("colors", [])
            if len(colors) != EDITABLE_COLORS:
                QMessageBox.warning(self, "形式エラー", f"パレット {p} の色数が不正です。")
                return False
            for s in range(EDITABLE_COLORS):
                self._buf[p][s] = int(colors[s]) & 0x3F
                self._refresh_swatch(p, s)

        wall_colors = data.get("wall_colors")
        if wall_colors is not None and self._wall_ok:
            if len(wall_colors) != wall_color_hack.EDIT_COUNT:
                QMessageBox.warning(
                    self, "形式エラー",
                    f"壁色数が不正です（{len(wall_colors)}、期待値: {wall_color_hack.EDIT_COUNT}）。"
                )
                return False
            for i, entry in enumerate(wall_colors):
                value = entry.get("color") if isinstance(entry, dict) else entry
                self._wall_buf[i] = int(value) & 0x3F
                self._refresh_wall_swatch(i)
        book_color = data.get("stage50_solomon_book_color")
        if isinstance(book_color, dict) and self._book_color_ok:
            self._book_color = int(book_color.get("color", self._book_color)) & 0x3F
            self._refresh_book_color_swatch()
        self._changed = True
        self._refresh_sprite_icons()
        if self._sel_wall is not None:
            self._update_color_grid_highlight(self._wall_buf[self._sel_wall] & 0x3F)
        elif self._sel_book_color:
            self._update_color_grid_highlight(self._book_color & 0x3F)
        elif self._sel_palette is not None and self._sel_slot is not None:
            self._update_color_grid_highlight(self._buf[self._sel_palette][self._sel_slot] & 0x3F)
        return True

    def _load_palette_file(self):
        """PNGメタデータまたは旧JSONからパレット設定を読み込み"""
        from .file_dialog_compat import get_file
        path = get_file(
            self,
            title="パレット設定を読み込み",
            filter="Palette PNG (*.png);;Legacy JSON (*.json);;All files (*)",
        )
        if not path:
            return
        try:
            data = self._read_palette_file(path)
        except Exception as e:
            QMessageBox.critical(self, "読込失敗", f"{type(e).__name__}: {e}")
            return
        if self._apply_palette_data(data):
            QMessageBox.information(self, "読込完了", f"パレット設定を読み込みました:\n{os.path.basename(path)}")

    def _apply(self) -> bool:
        """編集内容を ROM data に書き戻す。実際に変更があった場合 True。"""
        any_change = False
        for p in range(PALETTE_COUNT):
            for s in range(EDITABLE_COLORS):
                off = PALETTE_OFFSET + p * BYTES_PER_PALETTE + s
                new_val = self._buf[p][s] & 0x3F
                if self.rom_data[off] != new_val:
                    self.rom_data[off] = new_val
                    any_change = True
        if self._wall_ok:
            changed = wall_color_hack.apply(self.rom_data, self._wall_buf)
            any_change = any_change or bool(changed)
        if self._book_color_ok:
            changed = stage50_book_color.apply(self.rom_data, self._book_color)
            any_change = any_change or bool(changed)
        self._changed = False
        # 親ウィンドウに通知
        parent = self.parent()
        if any_change and parent is not None and hasattr(parent, "_on_palette_changed"):
            parent._on_palette_changed()
        return any_change

    def _apply_and_close(self):
        self._apply()
        self.accept()

    def done(self, r):
        save_dialog_geometry(self, self._app_config, "palette_dlg")
        super().done(r)
