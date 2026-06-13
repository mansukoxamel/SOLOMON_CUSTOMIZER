"""Solomon's Seal block-state runtime patch.

The original seal routine always writes $60 to the room grid after the room
data has been loaded.  For mapper66 saves, this helper keeps that original
behavior unless the seal cell already contains a supported block marker.
"""
from __future__ import annotations

import copy

from . import constants as c
from .element import ElementType, LevelElement, Wall, byte_from_position, position_from_byte


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
OFF_PRG1_TRANSPARENT_SEAL_CELL_TABLE = 0x8EEB
OFF_PRG1_TRANSPARENT_SEAL_BIT_TABLE = OFF_PRG1_TRANSPARENT_SEAL_CELL_TABLE + 64
OFF_PRG1_TRANSPARENT_SEAL_MASK_INDEX_TABLE = OFF_PRG1_TRANSPARENT_SEAL_BIT_TABLE + 64
OFF_PRG1_TRANSPARENT_SEAL_CLEAR_MASK_TABLE = OFF_PRG1_TRANSPARENT_SEAL_MASK_INDEX_TABLE + 64
CPU_PRG1_TRANSPARENT_SEAL_SUPPRESS_HELPER = 0x8FDB
OFF_PRG1_TRANSPARENT_SEAL_SUPPRESS_HELPER = CPU_PRG1_TRANSPARENT_SEAL_SUPPRESS_HELPER + 0x10
CPU_PRG1_TRANSPARENT_SEAL_PANEL_TAIL_HELPER = 0x8FFC
OFF_PRG1_TRANSPARENT_SEAL_PANEL_TAIL_HELPER = CPU_PRG1_TRANSPARENT_SEAL_PANEL_TAIL_HELPER + 0x10
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

# PRG1 helper called at the end of the mapper66 room loader.  It handles the
# synthetic transparent-breakable Seal path: when the current Seal bit is
# already present in $7A, restore the live grid cell to $50 and clear the
# visible-in-block mask bit before the PRG0 converter can create another Seal.
TRANSPARENT_SEAL_SUPPRESS_HELPER = bytes((
    0xBD, 0xDB, 0x8E,       # LDA $8EDB,X  ; grid cell index, $FF = none
    0xC9, 0xFF,             # CMP #$FF
    0xF0, 0x19,             # BEQ done
    0xA8,                   # TAY
    0xBD, 0x1B, 0x8F,       # LDA $8F1B,X  ; Seal bit for this room
    0x25, 0x7A,             # AND $7A
    0xF0, 0x11,             # BEQ done
    0xA9, 0x50,             # LDA #$50
    0x99, 0x04, 0x03,       # STA $0304,Y
    0xBC, 0x5B, 0x8F,       # LDY $8F5B,X  ; mask byte index
    0xB9, 0x50, 0x07,       # LDA $0750,Y
    0x3D, 0x9B, 0x8F,       # AND $8F9B,X  ; inverse bit mask
    0x99, 0x50, 0x07,       # STA $0750,Y
    0x60,                   # RTS
))
assert len(TRANSPARENT_SEAL_SUPPRESS_HELPER) == 33

_OLD_TRANSPARENT_SEAL_SUPPRESS_HELPER_BMI = bytes((
    0xBD, 0xDB, 0x8E, 0x30, 0x19, 0xA8, 0xBD, 0x1B, 0x8F, 0x25, 0x7A,
    0xF0, 0x11, 0xA9, 0x50, 0x99, 0x04, 0x03, 0xBC, 0x5B, 0x8F,
    0xB9, 0x50, 0x07, 0x3D, 0x9B, 0x8F, 0x99, 0x50, 0x07, 0x60,
))
assert len(_OLD_TRANSPARENT_SEAL_SUPPRESS_HELPER_BMI) == 31

TRANSPARENT_SEAL_PANEL_TAIL_HELPER = bytes((
    0xA0, 0x0F,             # LDY #$0F
    0xB1, 0x00,             # LDA ($00),Y
    0x99, 0x40, 0x07,       # STA $0740,Y
    0x88,                   # DEY
    0x10, 0xF8,             # BPL loop
    0x4C,
    CPU_PRG1_TRANSPARENT_SEAL_SUPPRESS_HELPER & 0xFF,
    CPU_PRG1_TRANSPARENT_SEAL_SUPPRESS_HELPER >> 8,
))
assert len(TRANSPARENT_SEAL_PANEL_TAIL_HELPER) == 13
_OLD_CPU_PRG1_TRANSPARENT_SEAL_PANEL_TAIL_HELPER = 0x8FFA
_OLD_TRANSPARENT_SEAL_PANEL_TAIL_HELPER = bytes((
    0xA0, 0x0F, 0xB1, 0x00, 0x99, 0x40, 0x07, 0x88, 0x10, 0xF8,
    0x4C, CPU_PRG1_TRANSPARENT_SEAL_SUPPRESS_HELPER & 0xFF,
    CPU_PRG1_TRANSPARENT_SEAL_SUPPRESS_HELPER >> 8,
))

TRANSPARENT_SEAL_TABLE_LEN = 64

RESERVED_SPANS = (
    (OFF_SEAL_HELPER, len(SEAL_HELPER)),
    (OFF_PRG1_SEAL_BLOCK_TABLE, SEAL_BLOCK_TABLE_LEN),
    (OFF_PRG1_TRANSPARENT_SEAL_CELL_TABLE, TRANSPARENT_SEAL_TABLE_LEN),
    (OFF_PRG1_TRANSPARENT_SEAL_BIT_TABLE, TRANSPARENT_SEAL_TABLE_LEN),
    (OFF_PRG1_TRANSPARENT_SEAL_MASK_INDEX_TABLE, TRANSPARENT_SEAL_TABLE_LEN),
    (OFF_PRG1_TRANSPARENT_SEAL_CLEAR_MASK_TABLE, TRANSPARENT_SEAL_TABLE_LEN),
    (OFF_PRG1_TRANSPARENT_SEAL_SUPPRESS_HELPER, len(TRANSPARENT_SEAL_SUPPRESS_HELPER)),
    (OFF_PRG1_TRANSPARENT_SEAL_PANEL_TAIL_HELPER, len(TRANSPARENT_SEAL_PANEL_TAIL_HELPER)),
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


def build_transparent_tables(rom_data: bytes, levels: list) -> tuple[bytes, bytes, bytes, bytes]:
    cells = bytearray([0xFF] * TRANSPARENT_SEAL_TABLE_LEN)
    bits = bytearray([0x00] * TRANSPARENT_SEAL_TABLE_LEN)
    mask_indexes = bytearray([0xFF] * TRANSPARENT_SEAL_TABLE_LEN)
    clear_masks = bytearray([0xFF] * TRANSPARENT_SEAL_TABLE_LEN)
    positions = _seal_positions_by_level(rom_data)
    for level_no, slot_index in SEAL_SLOTS:
        if not (0 <= level_no < len(levels)):
            continue
        seal_pos = positions.get(level_no)
        if seal_pos is None:
            continue
        x, y = seal_pos
        if not (0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H):
            continue
        level = levels[level_no]
        if level.tiles[y][x] != Wall.NONE:
            continue
        if seal_pos not in getattr(level, "invisible_breakable_cells", set()):
            continue
        cell_index = y * c.LEVEL_W + x
        cells[level_no] = byte_from_position(seal_pos) & 0xFF
        bits[level_no] = (1 << slot_index) & 0xFF
        mask_indexes[level_no] = (cell_index >> 3) & 0xFF
        clear_masks[level_no] = (~(1 << (cell_index & 0x07))) & 0xFF
    return bytes(cells), bytes(bits), bytes(mask_indexes), bytes(clear_masks)


def _verify(rom_data: bytearray) -> None:
    need = max(
        OFF_SEAL_HELPER + len(SEAL_HELPER),
        OFF_PRG1_SEAL_BLOCK_TABLE + SEAL_BLOCK_TABLE_LEN,
        OFF_PRG1_TRANSPARENT_SEAL_PANEL_TAIL_HELPER + len(TRANSPARENT_SEAL_PANEL_TAIL_HELPER),
    )
    if rom_data is None or len(rom_data) < need:
        raise SolomonSealBlockError("ROM is too short for Solomon Seal block patch.")
    cur = bytes(rom_data[OFF_SEAL_WRITE:OFF_SEAL_WRITE + len(ORIG_SEAL_WRITE)])
    if cur not in (ORIG_SEAL_WRITE, HOOK_SEAL_WRITE):
        raise SolomonSealBlockError(
            f"$BB90 seal write signature mismatch: got {cur.hex(' ')}"
        )
    cave = bytes(rom_data[OFF_SEAL_HELPER:OFF_SEAL_HELPER + len(SEAL_HELPER)])
    if cave != SEAL_HELPER and any(b not in (0xEA, 0x00) for b in cave):
        raise SolomonSealBlockError(
            f"Solomon Seal block helper cave overlap at file 0x{OFF_SEAL_HELPER:X}: "
            f"got {cave[:16].hex(' ')}..."
        )
    suppress = bytes(
        rom_data[
            OFF_PRG1_TRANSPARENT_SEAL_SUPPRESS_HELPER:
            OFF_PRG1_TRANSPARENT_SEAL_SUPPRESS_HELPER + len(TRANSPARENT_SEAL_SUPPRESS_HELPER)
        ]
    )
    suppress_is_old = suppress[:len(_OLD_TRANSPARENT_SEAL_SUPPRESS_HELPER_BMI)] == _OLD_TRANSPARENT_SEAL_SUPPRESS_HELPER_BMI
    if (
        suppress != TRANSPARENT_SEAL_SUPPRESS_HELPER
        and not suppress_is_old
        and any(b not in (0xEA, 0x00) for b in suppress)
    ):
        raise SolomonSealBlockError(
            f"Transparent Seal suppress helper overlap at file "
            f"0x{OFF_PRG1_TRANSPARENT_SEAL_SUPPRESS_HELPER:X}: got {suppress[:16].hex(' ')}..."
        )
    panel_tail = bytes(
        rom_data[
            OFF_PRG1_TRANSPARENT_SEAL_PANEL_TAIL_HELPER:
            OFF_PRG1_TRANSPARENT_SEAL_PANEL_TAIL_HELPER + len(TRANSPARENT_SEAL_PANEL_TAIL_HELPER)
        ]
    )
    old_tail_overlap = panel_tail[:len(_OLD_TRANSPARENT_SEAL_PANEL_TAIL_HELPER) - 2] == _OLD_TRANSPARENT_SEAL_PANEL_TAIL_HELPER[2:]
    if (
        panel_tail != TRANSPARENT_SEAL_PANEL_TAIL_HELPER
        and not old_tail_overlap
        and any(b not in (0xEA, 0x00) for b in panel_tail)
    ):
        raise SolomonSealBlockError(
            f"Transparent Seal panel-tail helper overlap at file "
            f"0x{OFF_PRG1_TRANSPARENT_SEAL_PANEL_TAIL_HELPER:X}: got {panel_tail[:16].hex(' ')}..."
        )


def apply(rom_data: bytearray, levels: list) -> list[str]:
    _verify(rom_data)
    table = build_table(bytes(rom_data), levels)
    transparent_tables = build_transparent_tables(bytes(rom_data), levels)
    enabled = any(table)
    changed: list[str] = []
    for off, blob, name in (
        (OFF_PRG1_TRANSPARENT_SEAL_CELL_TABLE, transparent_tables[0], "Transparent Seal cell table"),
        (OFF_PRG1_TRANSPARENT_SEAL_BIT_TABLE, transparent_tables[1], "Transparent Seal bit table"),
        (OFF_PRG1_TRANSPARENT_SEAL_MASK_INDEX_TABLE, transparent_tables[2], "Transparent Seal mask-index table"),
        (OFF_PRG1_TRANSPARENT_SEAL_CLEAR_MASK_TABLE, transparent_tables[3], "Transparent Seal clear-mask table"),
        (
            OFF_PRG1_TRANSPARENT_SEAL_SUPPRESS_HELPER,
            TRANSPARENT_SEAL_SUPPRESS_HELPER,
            "Transparent Seal placement suppress helper",
        ),
        (
            OFF_PRG1_TRANSPARENT_SEAL_PANEL_TAIL_HELPER,
            TRANSPARENT_SEAL_PANEL_TAIL_HELPER,
            "Transparent Seal Panel loader tail helper",
        ),
    ):
        if bytes(rom_data[off:off + len(blob)]) != blob:
            rom_data[off:off + len(blob)] = blob
            changed.append(name)
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
