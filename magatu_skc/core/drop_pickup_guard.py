"""Disabled PickupDrop runtime patch.

The previous PickupDrop patches changed live drop behavior and caused regressions
where enemy drops appeared at the bottom floor or stopped in midair. For now the
saver must leave the original ROM behavior untouched.
"""
from __future__ import annotations


class DropPickupGuardError(ValueError):
    pass


def is_applied(rom_data: bytes) -> bool:
    return False


def apply(rom_data: bytearray) -> list[str]:
    return []
