"""Stage wall-color table patch.

The game changes the base wall color every four stages by reading this table:

  CPU $9122 / iNES file offset $1132

Runtime code uses current room number `$0428 >> 2` as the table index, then
writes the selected NES color into all four BG sub-palettes at offsets
$03EA/$03EE/$03F2/$03F6.

Only the first 12 entries are normal stages 1-48.  The trailing two entries are
$80 special-stage markers and are intentionally left untouched.
"""

from __future__ import annotations


class WallColorHackError(ValueError):
    pass


TABLE_OFF = 0x1132
EDIT_COUNT = 12
TABLE_COUNT = 14
ORIGINAL_VALUES = (
    0x07, 0x1C, 0x04, 0x09,
    0x1C, 0x07, 0x04, 0x07,
    0x09, 0x1C, 0x07, 0x04,
)
SPECIAL_VALUES = (0x80, 0x80)


def _check_bounds(rom_data) -> None:
    if TABLE_OFF + TABLE_COUNT > len(rom_data):
        raise WallColorHackError("ROM is too small for the wall-color table.")


def current_values(rom_data) -> tuple[int, ...]:
    _check_bounds(rom_data)
    return tuple(int(v) for v in rom_data[TABLE_OFF:TABLE_OFF + EDIT_COUNT])


def special_values(rom_data) -> tuple[int, int]:
    _check_bounds(rom_data)
    off = TABLE_OFF + EDIT_COUNT
    return int(rom_data[off]), int(rom_data[off + 1])


def stage_range_label(index: int) -> str:
    start = index * 4 + 1
    end = start + 3
    return f"{start}-{end}"


def apply(rom_data, values: tuple[int, ...] | list[int]) -> list[str]:
    _check_bounds(rom_data)
    if len(values) != EDIT_COUNT:
        raise WallColorHackError(
            f"wall-color table requires exactly {EDIT_COUNT} values.")

    normalized = tuple(int(v) & 0x3F for v in values)
    changed: list[str] = []
    for i, value in enumerate(normalized):
        off = TABLE_OFF + i
        if rom_data[off] != value:
            rom_data[off] = value
            changed.append(f"{stage_range_label(i)}=${value:02X}")
    return changed


def restore(rom_data) -> list[str]:
    return apply(rom_data, ORIGINAL_VALUES)
