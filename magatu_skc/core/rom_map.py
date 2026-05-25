"""ROMデータテーブル → オフセット計算

ROMマップドキュメントより:
  RAM Address = Table[i] (low) + Table[i+N] (high) << 8
  ROM Offset  = RAM Address - 0x7ff0
"""
from . import constants as c
from .rom import Rom


def get_offset_from_table(rom: Rom, table_offset: int, index: int, count: int) -> int:
    """データテーブルから指定インデックスのROMオフセットを取得

    Args:
        rom: Romオブジェクト
        table_offset: テーブル開始ROMオフセット
        index: 取得したい要素のインデックス
        count: テーブル全体の要素数（高/低バイト分割の境界）

    Returns:
        ROMオフセット
    """
    low = rom.get_byte(table_offset + index)
    high = rom.get_byte(table_offset + index + count)
    ram_addr = (high << 8) | low
    return ram_addr - c.ROM_RAM_DIFF


def get_block_data_offset(region: str, level_no: int) -> int:
    """ブロックデータのオフセット計算

    ブロックデータは固定サイズ48バイト/レベルなので、テーブル不要
    """
    base = c.ROM_OFFSETS[region]["block_data"]
    return base + level_no * c.SIZE_LEVEL_WALLS


def get_enemy_data_offset(rom: Rom, region: str, level_no: int) -> int:
    """敵データのROMオフセット取得"""
    table = c.ROM_OFFSETS[region]["enemy_table"]
    return get_offset_from_table(rom, table, level_no, c.LEVEL_COUNT)


def get_item_data_offset(rom: Rom, region: str, level_no: int) -> int:
    """アイテムデータのROMオフセット取得"""
    table = c.ROM_OFFSETS[region]["item_table"]
    return get_offset_from_table(rom, table, level_no, c.LEVEL_COUNT)


def get_mirror_rate_offset(rom: Rom, region: str, rate_no: int) -> int:
    """ミラードロップレートのROMオフセット取得"""
    table = c.ROM_OFFSETS[region]["mirror_rate_table"]
    return get_offset_from_table(rom, table, rate_no, c.MIRROR_RATE_COUNT)


def get_mirror_enemy_offset(rom: Rom, region: str, set_no: int) -> int:
    """ミラー敵セットのROMオフセット取得"""
    table = c.ROM_OFFSETS[region]["mirror_enemy_table"]
    return get_offset_from_table(rom, table, set_no, c.MIRROR_ENEMY_COUNT)
