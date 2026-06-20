"""Small original-animation data fixes for enemy orientation glitches."""

from __future__ import annotations


class EnemyOrientationFixError(ValueError):
    pass


def _cf(cpu_addr: int) -> int:
    return cpu_addr - 0x8000 + 0x10


_D94F_VERTICAL_FLIP_ATTRS = (
    (_cf(0xD951), 0xED, 0xCC),
    (_cf(0xD954), 0xED, 0xCC),
)


def apply(rom_data: bytearray) -> list[str]:
    """Patch original D94F enemy animation frames that start vertically flipped."""
    if rom_data is None:
        raise EnemyOrientationFixError("ROM is missing.")
    min_len = max(off for off, _, _ in _D94F_VERTICAL_FLIP_ATTRS) + 1
    if len(rom_data) < min_len:
        raise EnemyOrientationFixError("ROM is too short for enemy orientation fix.")

    changed: list[str] = []
    for off, original, patched in _D94F_VERTICAL_FLIP_ATTRS:
        cur = rom_data[off]
        if cur not in (original, patched):
            cpu = 0x8000 + off - 0x10
            raise EnemyOrientationFixError(
                f"${cpu:04X} enemy animation attr mismatch: got ${cur:02X}"
            )
        if cur != patched:
            rom_data[off] = patched
            changed.append(f"${0x8000 + off - 0x10:04X}: original attr ${original:02X}->${patched:02X}")
    if changed:
        return ["原作由来の敵初期向き補正 " + ", ".join(changed)]
    return changed
