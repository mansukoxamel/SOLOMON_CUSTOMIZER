"""Solomon's Seal block-state runtime patch.

The original seal routine always writes $60 to the room grid after the room
data has been loaded.  For mapper66 saves, this helper keeps that original
behavior unless the seal cell already contains a supported block marker.
"""
from __future__ import annotations

import copy

from . import constants as c
from .element import ElementType, LevelElement, Wall, position_from_byte


class SolomonSealBlockError(ValueError):
    pass


OFF_SEAL_WRITE = 0x3BA0       # CPU $BB90: LDA #$60 / STA $0304,Y
ORIG_SEAL_WRITE = bytes.fromhex("A9 60 99 04 03")
CPU_SEAL_HELPER = 0xEFF5
OFF_SEAL_HELPER = 0x10 + (CPU_SEAL_HELPER - 0x8000)
# Keep the original LDA #$60, then call the helper instead of the original STA.
HOOK_SEAL_WRITE = bytes((0xA9, 0x60, 0x20, CPU_SEAL_HELPER & 0xFF, CPU_SEAL_HELPER >> 8))

OFF_SEAL_POS_TABLE = 0x3BA6   # CPU $BB96, bit0..bit7 grid coordinates
OFF_PRG1_SEAL_BLOCK_TABLE = 0x8EAB
SEAL_BLOCK_TABLE_LEN = 64
RAM_SEAL_BLOCK_VALUE = 0x077D
ITEM_SOLOMON_SEAL = 0x20
SEAL_SLOTS = (
    (8, 0),   # Stage 9
    (12, 1),  # Stage 13
    (16, 2),  # Stage 17
    (18, 3),  # Stage 19
    (20, 4),  # Stage 21
    (28, 5),  # Stage 29
    (45, 6),  # Stage 46
    (46, 7),  # Stage 47
)

# Helper @ $EFF5:
#   $077D = per-room override value copied by the mapper66 StageExt loader.
#   $00 means no override, so the original $60 seal value is written.
SEAL_HELPER = bytes.fromhex(
    "AD 7D 07 D0 02 A9 60 99 04 03 60"
)
assert len(SEAL_HELPER) == 11

RESERVED_SPANS = (
    (OFF_SEAL_HELPER, len(SEAL_HELPER)),
    (OFF_PRG1_SEAL_BLOCK_TABLE, SEAL_BLOCK_TABLE_LEN),
)


def _seal_positions_by_level(rom_data: bytes) -> dict[int, tuple[int, int]]:
    result: dict[int, tuple[int, int]] = {}
    if rom_data is None or len(rom_data) < OFF_SEAL_POS_TABLE + len(SEAL_SLOTS):
        return result
    for level_no, slot_index in SEAL_SLOTS:
        result[level_no] = position_from_byte(rom_data[OFF_SEAL_POS_TABLE + slot_index])
    return result


def seal_position_for_level(rom_data: bytes, level_no: int) -> tuple[int, int] | None:
    return _seal_positions_by_level(rom_data).get(int(level_no))


def is_seal_position(rom_data: bytes, level_no: int, pos: tuple[int, int]) -> bool:
    seal_pos = seal_position_for_level(rom_data, level_no)
    return seal_pos is not None and tuple(pos) == tuple(seal_pos)


def _level_needs_patch(level, seal_pos: tuple[int, int]) -> bool:
    x, y = seal_pos
    if not (0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H):
        return False
    if level.tiles[y][x] == Wall.BROWN:
        return True
    return (
        level.tiles[y][x] == Wall.WHITE
        and seal_pos in getattr(level, "breakable_white_cells", set())
    )


def is_needed(rom_data: bytes, levels: list) -> bool:
    return any(build_table(rom_data, levels))


def levels_for_save(rom_data: bytes, levels: list) -> list:
    """Add transient transparent-in-block Seal items for ROM saving.

    Brown/white Seal blocks are handled by the PRG0 cell-write override.  A
    transparent breakable block must instead ride the existing visible-in-block
    item runtime path, which requires a normal item byte plus a side-mask entry.
    This function returns shallow-copied Level objects only when such synthetic
    save data is needed; the editor's in-memory level data is left unchanged.
    """
    positions = _seal_positions_by_level(rom_data)
    if not positions:
        return levels
    out = list(levels)
    changed = False
    for level_no, seal_pos in positions.items():
        if not (0 <= level_no < len(out)):
            continue
        level = out[level_no]
        x, y = seal_pos
        if not (0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H):
            continue
        if level.tiles[y][x] != Wall.NONE:
            continue
        if seal_pos not in getattr(level, "invisible_breakable_cells", set()):
            continue
        clone = copy.copy(level)
        clone.items = [
            item for item in (getattr(level, "items", []) or [])
            if item.position != seal_pos
        ]
        clone.items.append(LevelElement(ElementType.ITEM, seal_pos, ITEM_SOLOMON_SEAL))
        clone.visible_in_block_item_cells = set(
            getattr(level, "visible_in_block_item_cells", set()) or []
        )
        clone.visible_in_block_item_cells.add(seal_pos)
        out[level_no] = clone
        changed = True
    return out if changed else levels


def build_table(rom_data: bytes, levels: list) -> bytes:
    table = bytearray(SEAL_BLOCK_TABLE_LEN)
    positions = _seal_positions_by_level(rom_data)
    for level_no, seal_pos in positions.items():
        if not (0 <= level_no < len(levels)):
            continue
        level = levels[level_no]
        x, y = seal_pos
        if not (0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H):
            continue
        if level.tiles[y][x] == Wall.BROWN:
            table[level_no] = 0xA0
        elif (
            level.tiles[y][x] == Wall.WHITE
            and seal_pos in getattr(level, "breakable_white_cells", set())
        ):
            table[level_no] = 0xE0
    return bytes(table)


def _verify(rom_data: bytearray) -> None:
    need = max(
        OFF_SEAL_HELPER + len(SEAL_HELPER),
        OFF_PRG1_SEAL_BLOCK_TABLE + SEAL_BLOCK_TABLE_LEN,
    )
    if rom_data is None or len(rom_data) < need:
        raise SolomonSealBlockError("ROM is too short for Solomon Seal block patch.")
    cur = bytes(rom_data[OFF_SEAL_WRITE:OFF_SEAL_WRITE + len(ORIG_SEAL_WRITE)])
    if cur not in (ORIG_SEAL_WRITE, HOOK_SEAL_WRITE):
        raise SolomonSealBlockError(
            f"$BB90 seal write signature mismatch: got {cur.hex(' ')}"
        )
    cave = bytes(rom_data[OFF_SEAL_HELPER:OFF_SEAL_HELPER + len(SEAL_HELPER)])
    if cave == SEAL_HELPER or all(b in (0xEA, 0x00) for b in cave):
        return
    raise SolomonSealBlockError(
        f"Solomon Seal block helper cave overlap at file 0x{OFF_SEAL_HELPER:X}: "
        f"got {cave[:16].hex(' ')}..."
    )


def apply(rom_data: bytearray, levels: list) -> list[str]:
    _verify(rom_data)
    table = build_table(bytes(rom_data), levels)
    enabled = any(table)
    changed: list[str] = []
    if not enabled:
        if bytes(rom_data[OFF_SEAL_WRITE:OFF_SEAL_WRITE + len(HOOK_SEAL_WRITE)]) == HOOK_SEAL_WRITE:
            rom_data[OFF_SEAL_WRITE:OFF_SEAL_WRITE + len(ORIG_SEAL_WRITE)] = ORIG_SEAL_WRITE
            changed.append("restore original Solomon Seal cell write")
        if any(rom_data[OFF_PRG1_SEAL_BLOCK_TABLE:OFF_PRG1_SEAL_BLOCK_TABLE + SEAL_BLOCK_TABLE_LEN]):
            rom_data[OFF_PRG1_SEAL_BLOCK_TABLE:OFF_PRG1_SEAL_BLOCK_TABLE + SEAL_BLOCK_TABLE_LEN] = bytes(SEAL_BLOCK_TABLE_LEN)
            changed.append("clear Solomon Seal block-state table")
        return changed
    if bytes(rom_data[OFF_SEAL_HELPER:OFF_SEAL_HELPER + len(SEAL_HELPER)]) != SEAL_HELPER:
        rom_data[OFF_SEAL_HELPER:OFF_SEAL_HELPER + len(SEAL_HELPER)] = SEAL_HELPER
        changed.append("Solomon Seal block helper $EFF5")
    if bytes(rom_data[OFF_PRG1_SEAL_BLOCK_TABLE:OFF_PRG1_SEAL_BLOCK_TABLE + SEAL_BLOCK_TABLE_LEN]) != table:
        rom_data[OFF_PRG1_SEAL_BLOCK_TABLE:OFF_PRG1_SEAL_BLOCK_TABLE + SEAL_BLOCK_TABLE_LEN] = table
        changed.append("Solomon Seal block-state table")
    if bytes(rom_data[OFF_SEAL_WRITE:OFF_SEAL_WRITE + len(HOOK_SEAL_WRITE)]) != HOOK_SEAL_WRITE:
        rom_data[OFF_SEAL_WRITE:OFF_SEAL_WRITE + len(HOOK_SEAL_WRITE)] = HOOK_SEAL_WRITE
        changed.append("$BB90 Solomon Seal block-state hook")
    return changed
