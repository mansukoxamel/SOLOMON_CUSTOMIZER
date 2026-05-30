"""Levelクラス - C++ SKC_Level の Python移植"""
from typing import Optional
from . import constants as c
from .element import (
    LevelElement, ElementType, Wall, DemonMirror,
    position_from_byte, byte_from_position
)
from .rom import Rom


def bytes_to_bitmask_2d(data: bytes, w: int, h: int, offset: int):
    """バイト列 → 2次元ビットマスク（C++ klib::util::bytes_to_bitmask 移植）"""
    result = []
    bytes_per_row = w // 8
    for j in range(h):
        row = []
        for i in range(bytes_per_row):
            b = data[offset + j * bytes_per_row + i]
            for k in range(7, -1, -1):
                row.append(bool(b & (1 << k)))
        result.append(row)
    return result


def bitmask_to_bytes(bitmask):
    """2次元ビットマスク → バイト列"""
    result = bytearray()
    for row in bitmask:
        for i in range(0, len(row), 8):
            b = 0
            for k in range(8):
                if i + k < len(row) and row[i + k]:
                    b |= 1 << (7 - k)
            result.append(b)
    return bytes(result)


def is_item_constellation(item_no: int) -> bool:
    return c.ITEM_CONSTELLATION_MIN <= item_no <= c.ITEM_CONSTELLATION_MAX


def is_item_delimiter(value: int) -> bool:
    return value == 0x00 or (c.ITEM_DELIMITER_MIN <= value < c.ITEM_CONSTELLATION_MIN)


class Level:
    """1つのレベル分のデータ"""

    def __init__(self):
        self.tiles = [[Wall.NONE for _ in range(c.LEVEL_W)] for _ in range(c.LEVEL_H)]
        self.items: list[LevelElement] = []
        self.enemies: list[LevelElement] = []
        self.constellation: Optional[LevelElement] = None
        self.demon_mirrors = [
            DemonMirror((0, 0), 0, 0),
            DemonMirror((0, 0), 0, 0),
        ]
        self.key_status = c.DEFAULT_KEY_STATUS
        self.spawn_enemy_lifetime = c.DEFAULT_SPAWN_ENEMY_LIFETIME
        self.tileset_no = 0
        self.time_decrease_rate = c.DEFAULT_TIME_DECREASE_RATE
        self.fixed_start_pos = (0, 0)
        self.fixed_key_pos = (0, 0)
        self.fixed_door_pos = (0, 0)
        # Room Flag Table 拡張 (原作ROMに無い新規メタ。bank0 cave へ注入)
        #   bit0=隠し扉 / bit2=B火球(魔法)禁止 / bit3=暗闇 /
        #   bit7=A換石禁止 — magatu_skc.core.room_flags 参照
        #   全0=原作無改変。XML プロジェクトに永続化、ROM保存時に表へ展開
        self.room_flags = 0
        # Cells drawn as white wall but converted to normal breakable stone at runtime.
        # Stored as (x, y) tuples. The visual map tile remains Wall.WHITE.
        self.breakable_white_cells = set()
        # Cells drawn as empty space but converted to normal breakable stone at runtime.
        self.invisible_breakable_cells = set()
        # Cells drawn as white wall but converted to empty space at runtime.
        self.passable_white_cells = set()
        # Cells drawn as empty space but converted to solid white wall at runtime.
        self.invisible_solid_cells = set()
        # Cells drawn as brown wall but converted to empty space at runtime.
        self.passable_brown_cells = set()
        # Cells drawn as brown wall but converted to solid white wall at runtime.
        self.solid_brown_cells = set()
        from . import stage_ext
        stage_ext.init_level_defaults(self)
        from . import panel_monster_stage_variant
        panel_monster_stage_variant.init_level_defaults(self)

    # ======================== ローダー ========================

    def load_block_data(self, rom_data: bytes, offset: int):
        """ブロック配置を読み込み"""
        bblocks = bytes_to_bitmask_2d(rom_data, c.LEVEL_W, c.LEVEL_H, offset)
        wblocks = bytes_to_bitmask_2d(rom_data, c.LEVEL_W, c.LEVEL_H,
                                       offset + c.TILE_BITMASK_BYTE_SIZE)
        self.tiles = []
        for j in range(c.LEVEL_H):
            row = []
            for i in range(c.LEVEL_W):
                row.append(self._walls_to_wall_type(bblocks[j][i], wblocks[j][i]))
            self.tiles.append(row)

    def load_enemy_data(self, rom_data: bytes, offset: int):
        """敵データを読み込み"""
        # spawn lifetime（ビットローテで格納されている）
        l = rom_data[offset]
        self.spawn_enemy_lifetime = ((l & 31) << 3) | (l >> 5)

        i = 1
        self.enemies = []
        while True:
            enemy_no = rom_data[offset + i]
            if enemy_no == 0:
                break
            pos = position_from_byte(rom_data[offset + i + 1])
            self.enemies.append(LevelElement(ElementType.ENEMY, pos, enemy_no))
            i += 2

    def load_item_data(self, rom_data: bytes, offset: int):
        """アイテムデータ + メタデータを読み込み"""
        # メタヘッダ
        self.set_key_status_and_time_dr(rom_data[offset + c.ITEM_OFFSET_KEY_STATUS])
        self.fixed_door_pos = position_from_byte(rom_data[offset + c.ITEM_OFFSET_DOOR_POS])
        self.fixed_key_pos = position_from_byte(rom_data[offset + c.ITEM_OFFSET_KEY_POS])
        self.fixed_start_pos = position_from_byte(rom_data[offset + c.ITEM_OFFSET_START_POS])

        # ミラー2つ（spawn02 が index 0、spawn01 が index 1 - C++と同じ順番）
        self.demon_mirrors = [
            DemonMirror(
                position_from_byte(rom_data[offset + c.ITEM_OFFSET_SPAWN02]),
                rom_data[offset + c.ITEM_OFFSET_SPAWN02_SCHEDULE],
                rom_data[offset + c.ITEM_OFFSET_SPAWN02_ENEMIES],
            ),
            DemonMirror(
                position_from_byte(rom_data[offset + c.ITEM_OFFSET_SPAWN01]),
                rom_data[offset + c.ITEM_OFFSET_SPAWN01_SCHEDULE],
                rom_data[offset + c.ITEM_OFFSET_SPAWN01_ENEMIES],
            ),
        ]

        # アイテムストリーム
        self.items = []
        self.constellation = None
        i = offset + c.ITEM_OFFSET_ITEM_DATA
        while True:
            next_elm = rom_data[i]

            # 終端（0x00 or 0xE0-0xEF）
            if is_item_delimiter(next_elm):
                self.tileset_no = (next_elm >> 2) & 3
                break

            # 星座背景（位置あり、これも終端扱い）
            if is_item_constellation(next_elm):
                pos = position_from_byte(rom_data[i + 1])
                self.constellation = LevelElement(ElementType.ITEM, pos, next_elm)
                self.tileset_no = (next_elm >> 2) & 3
                break

            # 通常アイテム
            if next_elm < c.ITEM_COPY_INDICATOR_MIN:
                pos = position_from_byte(rom_data[i + 1])
                self.items.append(LevelElement(ElementType.ITEM, pos, next_elm))
                i += 2
            else:
                # 0xC0-0xDF: 圧縮（同一アイテム複数）
                repeat_count = next_elm - c.ITEM_COPY_INDICATOR_MIN + 1
                item_no = rom_data[i + 1]
                for j in range(repeat_count):
                    pos = position_from_byte(rom_data[i + 2 + j])
                    self.items.append(LevelElement(ElementType.ITEM, pos, item_no))
                i += 2 + repeat_count

    # ======================== セッター/ゲッター ========================

    def set_key_status_and_time_dr(self, value: int):
        """キーステータスと時間減少率をまとめて設定"""
        if value >= c.KEY_STATUS_HIDDEN:
            self.key_status = c.KEY_STATUS_HIDDEN
        elif value >= c.KEY_STATUS_IN_BLOCK:
            self.key_status = c.KEY_STATUS_IN_BLOCK
        else:
            self.key_status = c.KEY_STATUS_NORMAL
        self.time_decrease_rate = value - self.key_status

    def get_wall_type(self, x: int, y: int) -> Wall:
        return self.tiles[y][x]

    def set_block(self, wall_type: Wall, pos: tuple):
        x, y = pos
        if 0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H:
            self.tiles[y][x] = wall_type
            if wall_type != Wall.WHITE:
                self.breakable_white_cells.discard((x, y))
                self.passable_white_cells.discard((x, y))
            if wall_type != Wall.BROWN:
                self.passable_brown_cells.discard((x, y))
                self.solid_brown_cells.discard((x, y))
            self.invisible_breakable_cells.discard((x, y))
            self.invisible_solid_cells.discard((x, y))

    def has_constellation(self) -> bool:
        return self.constellation is not None

    def get_constellation_no(self) -> int:
        return self.constellation.element_no if self.constellation else 0

    def get_constellation_pos(self) -> tuple:
        return self.constellation.position if self.constellation else (0, 0)

    def is_key_hidden(self) -> bool:
        return self.key_status == c.KEY_STATUS_HIDDEN

    def is_key_in_block(self) -> bool:
        return self.key_status == c.KEY_STATUS_IN_BLOCK

    def is_key_removed(self) -> bool:
        return self.fixed_key_pos[1] < 0

    def is_door_removed(self) -> bool:
        return self.fixed_door_pos[1] < 0

    def add_item(self, item_no: int, pos: tuple):
        self.items.append(LevelElement(ElementType.ITEM, pos, item_no))

    def add_enemy(self, enemy_no: int, pos: tuple) -> bool:
        """敵を追加。上限到達時は False を返す（呼出側で UI フィードバック可能）"""
        if len(self.enemies) >= c.ENEMY_COUNT_MAX:
            return False
        self.enemies.append(LevelElement(ElementType.ENEMY, pos, enemy_no))
        return True

    def delete_item(self, index: int):
        if 0 <= index < len(self.items):
            del self.items[index]

    def delete_enemy(self, index: int):
        if 0 <= index < len(self.enemies):
            del self.enemies[index]

    def get_item_index(self, pos: tuple) -> int:
        for i, item in enumerate(self.items):
            if item.position == pos:
                return i
        return -1

    def get_enemy_index(self, pos: tuple) -> int:
        for i, enemy in enumerate(self.enemies):
            if enemy.position == pos:
                return i
        return -1

    # ======================== シリアライズ（保存用） ========================

    def get_block_bytes(self) -> bytes:
        """ブロックデータをバイト列化（茶+白）"""
        bbm = [[self.tiles[j][i] in (Wall.BROWN, Wall.BROWN_WHITE)
                for i in range(c.LEVEL_W)]
               for j in range(c.LEVEL_H)]
        wbm = [[self.tiles[j][i] in (Wall.WHITE, Wall.BROWN_WHITE)
                for i in range(c.LEVEL_W)]
               for j in range(c.LEVEL_H)]
        return bitmask_to_bytes(bbm) + bitmask_to_bytes(wbm)

    def get_enemy_bytes(self) -> bytes:
        """敵データをバイト列化"""
        # spawn_enemy_lifetime はビットローテして格納
        l = ((self.spawn_enemy_lifetime >> 3) |
             ((self.spawn_enemy_lifetime & 7) << 5)) & 0xff
        result = bytearray([l])
        for e in self.enemies:
            result.append(e.element_no)
            result.append(byte_from_position(e.position))
        result.append(0x00)
        return bytes(result)

    def get_item_bytes(self, ignore_item_elements: list = None) -> bytes:
        """アイテムデータをバイト列化（圧縮あり）"""
        if ignore_item_elements is None:
            ignore_item_elements = []

        result = bytearray()
        # ミラースケジュール・敵セット
        result.append(self.demon_mirrors[0].schedule_no)
        result.append(self.demon_mirrors[1].schedule_no)
        result.append(self.demon_mirrors[0].monster_set_no)
        result.append(self.demon_mirrors[1].monster_set_no)

        # メタデータ
        result.append((self.key_status + self.time_decrease_rate) & 0xff)
        result.append(byte_from_position(self.fixed_door_pos))
        result.append(byte_from_position(self.fixed_key_pos))
        result.append(byte_from_position(self.fixed_start_pos))
        result.append(byte_from_position(self.demon_mirrors[1].position))
        result.append(byte_from_position(self.demon_mirrors[0].position))

        # 無視するアイテムのインデックスを事前に handled に入れる
        handled = set()
        for i, item in enumerate(self.items):
            if item.element_no in ignore_item_elements:
                handled.add(i)

        # 圧縮しながらアイテム書き出し
        for i in range(len(self.items)):
            if i in handled:
                continue
            item_no = self.items[i].element_no
            indexes = self._get_item_indexes(item_no, handled)

            if len(indexes) > 1:
                # 圧縮
                repeat_byte = c.ITEM_COPY_INDICATOR_MIN + len(indexes) - 1
                result.append(repeat_byte)
                result.append(item_no)
                for idx in indexes:
                    result.append(byte_from_position(self.items[idx].position))
            else:
                for idx in indexes:
                    result.append(item_no)
                    result.append(byte_from_position(self.items[idx].position))

        # 終端（星座 or 0xE0+tileset）
        if self.has_constellation():
            result.append(self.constellation.element_no)
            result.append(byte_from_position(self.constellation.position))
        else:
            result.append(c.ITEM_DELIMITER_MIN + 4 * self.tileset_no)

        return bytes(result)

    def _get_item_indexes(self, item_no: int, handled: set) -> list:
        """同じアイテム番号のインデックスを最大32個まで取得（圧縮上限）"""
        result = []
        for i, item in enumerate(self.items):
            if len(result) >= c.ITEM_COMPRESS_MAX_COUNT:
                break
            if i in handled:
                continue
            if item.element_no == item_no:
                result.append(i)
                handled.add(i)
        return result

    @staticmethod
    def _walls_to_wall_type(b: bool, w: bool) -> Wall:
        # BROWN_WHITE (両ビットON) は実機で「壊せない白壁」と同じ挙動のため
        # 廃止扱い。読込時に WHITE へ正規化する (v0.1.99)
        if b and w:
            return Wall.WHITE
        elif b:
            return Wall.BROWN
        elif w:
            return Wall.WHITE
        return Wall.NONE


def load_all_levels(rom: Rom) -> list:
    """ROMから全レベルを読み込み（通常ROM・拡張ROM 両対応）"""
    if rom.is_expanded():
        from . import m66
        return m66.load_all_levels_m66(rom)

    from . import rom_map

    region = rom.base_region()
    levels = []

    for i in range(c.LEVEL_COUNT):
        level = Level()
        level.load_block_data(bytes(rom.data),
                              rom_map.get_block_data_offset(region, i))
        level.load_item_data(bytes(rom.data),
                             rom_map.get_item_data_offset(rom, region, i))
        level.load_enemy_data(bytes(rom.data),
                              rom_map.get_enemy_data_offset(rom, region, i))
        levels.append(level)

    try:
        from . import room_flags
        flags = room_flags.read_table(bytes(rom.data), len(levels))
        for i, fl in enumerate(flags):
            levels[i].room_flags = fl
    except Exception:
        # Room Flag は独自拡張。読めないROMでも原作レベル読込は継続する。
        pass

    try:
        from . import stage_ext
        stage_ext.read_table(bytes(rom.data), levels)
    except Exception:
        pass

    try:
        from . import panel_monster_stage_variant
        panel_monster_stage_variant.read_table(bytes(rom.data), levels)
    except Exception:
        pass

    return levels
