"""NES CHR-ROM タイル - 8x8 2bpp デコード"""

NES_TILE_W = 8
NES_GFX_TILE_BYTE_SIZE = 16  # 1タイル = 16バイト


class NesTile:
    """NES 8x8 タイル（2bpp = palette index 0-3）

    NES の CHR-ROM 形式:
      最初の 8バイト: 各行の bit 0
      次の 8バイト: 各行の bit 1
      組み合わせて 0-3 のパレットインデックスを得る
    """

    def __init__(self, byte_data: bytes):
        if len(byte_data) < NES_GFX_TILE_BYTE_SIZE:
            raise ValueError(f"Need {NES_GFX_TILE_BYTE_SIZE} bytes, got {len(byte_data)}")

        # 8行 × 8列 のパレットインデックス（0-3）
        self.pixels = []
        for y in range(NES_TILE_W):
            row = []
            a = byte_data[y]
            b = byte_data[y + 8]
            for e in range(7, -1, -1):
                bit_a = (a >> e) & 1
                bit_b = (b >> e) & 1
                pal_index = bit_a + 2 * bit_b
                row.append(pal_index)
            self.pixels.append(row)

    def get_palette_index(self, x: int, y: int,
                          flip_v: bool = False, flip_h: bool = False) -> int:
        """指定座標のパレットインデックス（0-3）取得"""
        # C++ オリジナルの flip 引数の意味に合わせる
        # flip_h: y軸反転（行を反転）
        # flip_v: x軸反転（列を反転）
        ry = NES_TILE_W - 1 - y if flip_h else y
        rx = NES_TILE_W - 1 - x if flip_v else x
        return self.pixels[ry][rx]


def load_chr_tiles(rom_data: bytes, offset: int, count: int) -> list:
    """ROMからCHR-ROMタイルをまとめて読込"""
    tiles = []
    for i in range(count):
        start = offset + i * NES_GFX_TILE_BYTE_SIZE
        tile_data = rom_data[start:start + NES_GFX_TILE_BYTE_SIZE]
        tiles.append(NesTile(tile_data))
    return tiles
