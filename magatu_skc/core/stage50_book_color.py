"""Stage 50 Solomon book color patch.

The visible book color is controlled by the immediate value at CPU $90CC
(`LDA #$16`), iNES file offset 0x10DC.  This editor exposes only that one
NES color byte; it does not edit a four-color BG palette.
"""

from __future__ import annotations


class Stage50BookColorError(ValueError):
    pass


COLOR_OFF = 0x10DC
ORIGINAL_COLOR = 0x16
CONTEXT = bytes.fromhex("a9 16 8d f3 03 a9 00 a2")
CONTEXT_INDEX = 1


def _check_bounds(rom_data) -> None:
    start = COLOR_OFF - CONTEXT_INDEX
    end = start + len(CONTEXT)
    if end > len(rom_data):
        raise Stage50BookColorError("ROM is too small for the Stage 50 book color byte.")


def _check_context(rom_data) -> None:
    _check_bounds(rom_data)
    start = COLOR_OFF - CONTEXT_INDEX
    end = start + len(CONTEXT)
    current = int(rom_data[COLOR_OFF])
    expected = bytearray(CONTEXT)
    if current != ORIGINAL_COLOR:
        expected[CONTEXT_INDEX] = current
    cur = bytes(rom_data[start:end])
    if cur != bytes(expected):
        raise Stage50BookColorError(
            f"Stage 50 book color signature mismatch at 0x{start:04X}: "
            f"got {cur.hex(' ')}"
        )


def current_value(rom_data) -> int:
    _check_context(rom_data)
    return int(rom_data[COLOR_OFF]) & 0x3F


def apply(rom_data, value: int) -> list[str]:
    _check_context(rom_data)
    new_value = int(value) & 0x3F
    current = int(rom_data[COLOR_OFF])
    if current == new_value:
        return []
    rom_data[COLOR_OFF] = new_value
    return [f"Stage 50 Solomon book color ${current:02X}->${new_value:02X}"]
