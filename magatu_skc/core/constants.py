"""定数定義 - C++ Constants_level.h を移植"""

# レベルサイズ
LEVEL_W = 16
LEVEL_H = 12
LEVEL_BLOCK_COUNT = LEVEL_W * LEVEL_H
TILE_BITMASK_BYTE_SIZE = (LEVEL_W * LEVEL_H) // 8  # 24
SIZE_LEVEL_WALL_LAYER = TILE_BITMASK_BYTE_SIZE
SIZE_LEVEL_WALLS = 2 * SIZE_LEVEL_WALL_LAYER  # 48 bytes per level

# タイル描画サイズ
TILE_WIDTH = 16        # メタタイルサイズ（NES 8x8 を 4つ配置）
TILE_SCALE = 2
TILE_GFX_SIZE = TILE_WIDTH * TILE_SCALE

# レベル数
LEVEL_COUNT = 53
ENEMY_COUNT_MAX = 15  # 拡張ROM (m66) の LENGTH_M66_ENEMY_DATA=32 から逆算 (1+15*2+1)

# キーステータス
DEFAULT_KEY_STATUS = 0x00
KEY_STATUS_NORMAL = 0x00
KEY_STATUS_IN_BLOCK = 0x40
KEY_STATUS_HIDDEN = 0x80
KEY_STATUS_WHITE_IN_BLOCK = 0xC0

DEFAULT_SPAWN_ENEMY_LIFETIME = 0x02
DEFAULT_TIME_DECREASE_RATE = 0x01

# Item Data ヘッダのオフセット
ITEM_OFFSET_SPAWN02_SCHEDULE = 0
ITEM_OFFSET_SPAWN01_SCHEDULE = 1
ITEM_OFFSET_SPAWN02_ENEMIES = 2
ITEM_OFFSET_SPAWN01_ENEMIES = 3
ITEM_OFFSET_KEY_STATUS = 4
ITEM_OFFSET_DOOR_POS = 5
ITEM_OFFSET_KEY_POS = 6
ITEM_OFFSET_START_POS = 7
ITEM_OFFSET_SPAWN01 = 8
ITEM_OFFSET_SPAWN02 = 9
ITEM_OFFSET_ITEM_DATA = 10

# アイテムコード境界
ITEM_COPY_INDICATOR_MIN = 0xc0  # 圧縮開始
ITEM_DELIMITER_MIN = 0xe0       # 終端開始
ITEM_CONSTELLATION_MIN = 0xf0   # 星座開始
ITEM_CONSTELLATION_MAX = 0xfb   # 星座終了
ITEM_COMPRESS_MAX_COUNT = ITEM_DELIMITER_MIN - ITEM_COPY_INDICATOR_MIN  # 32
ITEM_FLAG_NORMAL = 0x00
ITEM_FLAG_HIDDEN = 0x40
ITEM_FLAG_IN_BLOCK = 0x80
ITEM_FLAG_WHITE_IN_BLOCK = 0xC0
ITEM_FLAG_VISIBLE_IN_BLOCK = 0x100
ITEM_FLAG_CRACKED_IN_BLOCK = 0x200
ITEM_WHITE_IN_BLOCK_MIN = 0xC0
ITEM_WHITE_IN_BLOCK_MAX = 0xF7
ITEM_WHITE_IN_BLOCK_MAX_BASE = ITEM_WHITE_IN_BLOCK_MAX & 0x3F

ITEM_NO_DEMON_MIRROR = 0x05
MIRROR_ENEMY_SET_DELIMITER = 0x90

# ROM-RAM オフセット差分
ROM_RAM_DIFF = 0x7ff0

# リージョン別 ROM オフセット（skc_config.xml より）
ROM_OFFSETS = {
    "US": {
        "mirror_rate_table": 0x5c10,
        "mirror_enemy_table": 0x5c30,
        "enemy_table": 0x5cfc,
        "block_data": 0x603c,
        "item_table": 0x6a2c,
        "gfx": 0x8010,
        "bonus_pos": 0x19D2,
        "bonus_items": 0x19F2,
    },
    "JP": {
        "mirror_rate_table": 0x5c10,
        "mirror_enemy_table": 0x5c30,
        "enemy_table": 0x5cfc,
        "block_data": 0x603c,
        "item_table": 0x6a2c,
        "gfx": 0x8010,
        "bonus_pos": 0x1955,
        "bonus_items": 0x1975,
    },
}

# データ長
LENGTH_MIRROR_RATE_DATA = 128
LENGTH_MIRROR_ENEMY_DATA = 42
LENGTH_ENEMY_DATA = 726
LENGTH_ITEM_DATA = 1402

MIRROR_RATE_COUNT = 16
MIRROR_ENEMY_COUNT = 17

# CHR-ROM
NES_TILE_W = 8
NES_GFX_TILE_BYTE_SIZE = NES_TILE_W * NES_TILE_W // 4  # 16
NES_TILE_COUNT = 2048

# 星座背景
CONSTELLATION_NAMES = {
    0xf0: ("Aries", 0),
    0xf1: ("Gemini", 0),
    0xf2: ("Virgo", 0),
    0xf3: ("Aquarius", 0),
    0xf4: ("Cancer", 1),
    0xf5: ("Scorpio", 1),
    0xf6: ("Capricorn", 1),
    0xf7: ("Pisces", 1),
    0xf8: ("Taurus", 2),
    0xf9: ("Leo", 2),
    0xfa: ("Libra", 2),
    0xfb: ("Sagittarius", 2),
}

# レベル別パレット指定（skc_config.xml level_palettes より）
LEVEL_PALETTES = [
    0,0,0,0, 1,1,1,1, 2,2,2,2, 3,3,3,3,
    2,2,2,2, 0,0,0,0, 2,2,2,2, 0,0,0,0,
    3,3,3,3, 2,2,2,2, 0,0,0,0, 2,2,2,2,
    4,4,0,4,4
]
