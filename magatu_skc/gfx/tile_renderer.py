"""タイル描画 - QImage に NES タイルを描画"""
from PyQt5.QtGui import QImage, QPainter, QColor

from ..core import constants as c
from ..nes.tile import NES_TILE_W
from ..nes import palette as pal
from ..nes.config_loader import SkcConfig, TileDef


class TileRenderer:
    """NESタイルセットからQImageを生成するレンダラー"""

    def __init__(self, config: SkcConfig, nes_tiles: list):
        """
        Args:
            config: skc_config.xml ローダー
            nes_tiles: list[NesTile] - CHR-ROMから読み込んだ全タイル
        """
        self.config = config
        self.nes_tiles = nes_tiles

        # tileset_no × tile_no -> QImage キャッシュ
        # tileset数 × tile_def数 のすべての組合せをキャッシュ
        self._cache = {}

    def get_tile_image(self, tile_no: int, tileset_no: int = 0,
                       transparent: bool = None,
                       bg_main_color: int = None,
                       palette_no_override: int = None,
                       pixel_color_overrides: dict = None) -> QImage:
        """指定のメタタイルをQImageで取得（キャッシュあり）

        Args:
            tile_no: tile_definitions の no
            tileset_no: tilesets のインデックス
            transparent: 透明色を残すか（Noneの場合 tile_def の transparent 属性に従う）
        """
        bg_main_color = None if bg_main_color is None else (int(bg_main_color) & 0x3F)
        palette_no_override = (
            None if palette_no_override is None else int(palette_no_override)
        )
        pixel_color_overrides = {
            int(k) & 0x03: int(v) & 0x3F
            for k, v in (pixel_color_overrides or {}).items()
        }
        overrides_key = tuple(sorted(pixel_color_overrides.items()))
        cache_key = (
            tile_no,
            tileset_no,
            transparent,
            bg_main_color,
            palette_no_override,
            overrides_key,
        )
        if cache_key in self._cache:
            return self._cache[cache_key]

        tile_def = self.config.tile_defs.get(tile_no)
        if tile_def is None:
            # 黒の16x16
            img = QImage(c.TILE_WIDTH, c.TILE_WIDTH, QImage.Format_ARGB32)
            img.fill(QColor(0, 0, 0))
            self._cache[cache_key] = img
            return img

        if transparent is None:
            transparent = tile_def.transparent

        ts = self.config.get_tileset(tileset_no)
        # palette_no は TileDef では「タイル定義側の指定」だが
        # tileset_offset を加算して実際のサブパレットを得る
        base_palette_no = (
            tile_def.palette_no
            if palette_no_override is None
            else palette_no_override
        )
        actual_palette_no = base_palette_no + ts.palette_offset
        actual_tile_offset = ts.tile_offset

        sub_pal = self.config.get_palette(actual_palette_no)
        if bg_main_color is not None and actual_palette_no % 8 < 4:
            colors = list(sub_pal.colors)
            colors[1] = bg_main_color
            sub_pal = pal.SubPalette(colors)

        # メタタイルの幅と高さ（NESタイル単位）
        w_in_tiles = tile_def.width
        h_in_tiles = tile_def.height

        # 出力QImage（ピクセル単位）
        img_w = w_in_tiles * NES_TILE_W
        img_h = h_in_tiles * NES_TILE_W
        img = QImage(img_w, img_h, QImage.Format_ARGB32)
        img.fill(QColor(0, 0, 0, 0 if transparent else 255))

        # 各NESタイルを順に描画
        for idx, (nes_tile_no, flip_v, flip_h) in enumerate(tile_def.nes_tiles):
            tx = (idx % w_in_tiles) * NES_TILE_W
            ty = (idx // w_in_tiles) * NES_TILE_W

            actual_nes_tile_no = nes_tile_no + actual_tile_offset
            if actual_nes_tile_no >= len(self.nes_tiles):
                continue
            nes_tile = self.nes_tiles[actual_nes_tile_no]

            for y in range(NES_TILE_W):
                for x in range(NES_TILE_W):
                    pal_idx = nes_tile.get_palette_index(x, y, flip_v, flip_h)
                    if pal_idx == 0 and transparent:
                        continue  # 透明
                    if pal_idx in pixel_color_overrides:
                        rgb = pal.get_nes_color(pixel_color_overrides[pal_idx])
                    else:
                        rgb = sub_pal.get_rgb(pal_idx)
                    img.setPixel(tx + x, ty + y, QColor(*rgb).rgb())

        self._cache[cache_key] = img
        return img

    def clear_cache(self):
        self._cache = {}
