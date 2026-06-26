"""Stage 50 Solomon book color patch.

The visible book color has two storage sites:
- gameplay palette special case at CPU $90CC, iNES file offset 0x10DC
- stage-start screen palette script at CPU $94D4, iNES file offset 0x14E4
This editor exposes one NES color byte and writes the same value to both.
"""

from __future__ import annotations


class Stage50BookColorError(ValueError):
    pass


GAMEPLAY_COLOR_OFF = 0x10DC
INTRO_COLOR_OFF = 0x14E4
COLOR_OFF = GAMEPLAY_COLOR_OFF
ORIGINAL_COLOR = 0x16
GAMEPLAY_CONTEXT = bytes.fromhex("a9 16 8d f3 03 a9 00 a2")
GAMEPLAY_CONTEXT_INDEX = 1
INTRO_CONTEXT = bytes.fromhex("0f 0f 16 30 0f 0f 27 38")
INTRO_CONTEXT_INDEX = 2


def _check_context_at(rom_data, color_off: int, context: bytes, context_index: int) -> int:
    start = color_off - context_index
    end = start + len(context)
    if end > len(rom_data):
        raise Stage50BookColorError("ROM is too small for the Stage 50 book color byte.")
    current = int(rom_data[color_off])
    expected = bytearray(context)
    if current != ORIGINAL_COLOR:
        expected[context_index] = current
    cur = bytes(rom_data[start:end])
    if cur != bytes(expected):
        raise Stage50BookColorError(
            f"Stage 50 book color signature mismatch at 0x{start:04X}: "
            f"got {cur.hex(' ')}"
        )
    return current & 0x3F


def _check_context(rom_data) -> None:
    _check_context_at(
        rom_data, GAMEPLAY_COLOR_OFF, GAMEPLAY_CONTEXT, GAMEPLAY_CONTEXT_INDEX,
    )
    _check_context_at(
        rom_data, INTRO_COLOR_OFF, INTRO_CONTEXT, INTRO_CONTEXT_INDEX,
    )


def current_value(rom_data) -> int:
    _check_context(rom_data)
    return int(rom_data[GAMEPLAY_COLOR_OFF]) & 0x3F


def apply(rom_data, value: int) -> list[str]:
    _check_context(rom_data)
    new_value = int(value) & 0x3F
    changed = []
    for label, off in (
        ("gameplay", GAMEPLAY_COLOR_OFF),
        ("intro", INTRO_COLOR_OFF),
    ):
        current = int(rom_data[off]) & 0x3F
        if current == new_value:
            continue
        rom_data[off] = new_value
        changed.append(f"Stage 50 Solomon book color {label} ${current:02X}->${new_value:02X}")
    return changed
