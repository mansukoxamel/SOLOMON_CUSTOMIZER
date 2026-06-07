"""レベル要素（アイテム・敵）の定義 - C++ Level_element 移植"""
from enum import Enum
from . import constants as c


class ElementType(Enum):
    ITEM = "item"
    ENEMY = "enemy"


class Wall(Enum):
    NONE = 0
    BROWN = 1
    WHITE = 2
    BROWN_WHITE = 3


class LevelElement:
    """アイテム or 敵 1個"""

    def __init__(self, elm_type: ElementType, position: tuple, element_no: int):
        self.type = elm_type
        self.position = position  # (x, y)
        self.element_no = element_no  # 0-255

    def get_item_no(self) -> int:
        """ベースアイテム番号取得（hidden/in_block ビットを除外）"""
        if self.is_white_in_block():
            return self.element_no & 0x3f
        if self.element_no >= c.ITEM_COPY_INDICATOR_MIN:
            return self.element_no
        return self.element_no & 0x3f

    def is_hidden(self) -> bool:
        if self.is_white_in_block():
            return False
        return bool(self.element_no & 0x40)

    def is_in_block(self) -> bool:
        return bool(self.element_no & 0x80)

    def is_white_in_block(self) -> bool:
        return c.ITEM_WHITE_IN_BLOCK_MIN <= self.element_no <= c.ITEM_WHITE_IN_BLOCK_MAX

    def set_hidden(self, value: bool):
        if value:
            self.element_no |= 0x40
            self.element_no &= ~0x80 & 0xff  # in_block 解除
        else:
            self.element_no &= ~0x40 & 0xff

    def set_in_block(self, value: bool):
        if value:
            self.element_no |= 0x80
            self.element_no &= ~0x40 & 0xff  # hidden 解除
        else:
            self.element_no &= ~0x80 & 0xff

    def set_white_in_block(self, value: bool):
        base = self.element_no & 0x3f
        if value:
            if base > c.ITEM_WHITE_IN_BLOCK_MAX_BASE:
                raise ValueError(f"Item 0x{base:02X} cannot be stored in a white breakable block")
            self.element_no = base | c.ITEM_FLAG_WHITE_IN_BLOCK
        else:
            self.element_no = base

    def __repr__(self):
        return f"LevelElement(type={self.type.value}, pos={self.position}, no=0x{self.element_no:02x})"


class DemonMirror:
    """デーモンミラー（敵召喚装置）"""

    def __init__(self, position: tuple, schedule_no: int, monster_set_no: int):
        self.position = position
        self.schedule_no = schedule_no
        self.monster_set_no = monster_set_no
        self.enemy_codes = []  # 敵セット実データ（拡張ROM内の実際の敵コードリスト）
        self.schedule_data = []  # ドロップスケジュール実データ（8バイト）

    def __repr__(self):
        return f"DemonMirror(pos={self.position}, sched={self.schedule_no}, set={self.monster_set_no})"


def position_from_byte(b: int) -> tuple:
    """位置バイトを (x, y) に変換

    上位nibble - 1 = y、下位nibble = x
    """
    x = b & 0x0f
    y = (b >> 4) - 1
    return (x, y)


def byte_from_position(pos: tuple) -> int:
    """(x, y) を位置バイトに変換"""
    x, y = pos
    return ((y + 1) & 0x0f) << 4 | (x & 0x0f)
