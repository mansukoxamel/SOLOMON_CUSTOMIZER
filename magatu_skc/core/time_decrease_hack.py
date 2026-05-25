"""Global LIFE/TIME decrease-rate table patch.

The level header stores a 0/1/2 selector in byte4 low bits.  During room load,
the game reads CPU $9942 + selector and stores the selected byte into $0436.
This module edits that three-byte table directly:

  $9942: 2D 22 19  ; fast / normal / slow

Larger values decrease the displayed LIFE faster.
"""

from __future__ import annotations


class TimeDecreaseHackError(ValueError):
    pass


TABLE_OFF = 0x1952  # iNES file offset for PRG0 CPU $9942
ORIGINAL_VALUES = (0x2D, 0x22, 0x19)
LABELS = ("速い", "普通", "遅い")
ESTIMATE_BASE_TICKS = 1024 * 256
ESTIMATE_FPS = 60.0


def _check_bounds(rom_data) -> None:
    if TABLE_OFF + 3 > len(rom_data):
        raise TimeDecreaseHackError("ROM is too small for the time-rate table.")


def current_values(rom_data) -> tuple[int, int, int]:
    _check_bounds(rom_data)
    return tuple(int(v) for v in rom_data[TABLE_OFF:TABLE_OFF + 3])


def estimate_total_seconds(value: int) -> float | None:
    """Return approximate seconds until LIFE reaches zero for one table value."""
    value = int(value) & 0xFF
    if value <= 0:
        return None
    return ESTIMATE_BASE_TICKS / (value * ESTIMATE_FPS)


def apply(rom_data, values: tuple[int, int, int] | list[int]) -> list[str]:
    _check_bounds(rom_data)
    if len(values) != 3:
        raise TimeDecreaseHackError("time-rate table requires exactly 3 values.")

    normalized = tuple(int(v) & 0xFF for v in values)
    changed: list[str] = []
    for i, value in enumerate(normalized):
        off = TABLE_OFF + i
        if rom_data[off] != value:
            rom_data[off] = value
            changed.append(f"{LABELS[i]}=${value:02X}")
    return changed


def restore(rom_data) -> list[str]:
    return apply(rom_data, ORIGINAL_VALUES)
