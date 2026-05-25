"""Demonhead behavior tweaks.

Editing support is intentionally limited to the JP / mapper66 JP layout used
by this customizer. US ROMs may be used as title-material sources elsewhere,
but they are not normal edit targets.
"""
from __future__ import annotations

OFF_WAIT = 0x32B7  # CPU $B2A7, Demonhead post-spawn/post-turn CMP immediate
SIG_OFF = 0x3218   # CPU $B208, Demonhead AI entry in JP bank0
SIG = bytes.fromhex("20 84 B3 20 01 B2 20 A9 8E 1F B2 2B B2 30 AE 1C")
ORIGINAL_WAIT = 0x0F
SNAPPY_VALUE = 0x01


class DemonheadHackError(ValueError):
    """Demonhead tweak validation failed."""


def verify(rom_data) -> None:
    if rom_data is None or len(rom_data) < OFF_WAIT + 1:
        raise DemonheadHackError("ROM が短すぎます。")
    actual = bytes(rom_data[SIG_OFF:SIG_OFF + len(SIG)])
    if actual != SIG:
        raise DemonheadHackError(
            "JP版 Demonhead AI の期待バイト列が見つかりません。\n"
            f"  期待: {SIG.hex(' ')}\n"
            f"  実際: {actual.hex(' ')}\n"
            "この設定は日本版 mapper66 拡張ROMを編集対象にしています。"
        )


def current_wait(rom_data) -> int:
    verify(rom_data)
    return int(rom_data[OFF_WAIT])


def is_snappy(rom_data) -> bool:
    return current_wait(rom_data) == SNAPPY_VALUE


def apply(rom_data, snappy: bool) -> list[str]:
    verify(rom_data)
    off = OFF_WAIT
    target = SNAPPY_VALUE if snappy else ORIGINAL_WAIT
    if rom_data[off] == target:
        return []
    rom_data[off] = target
    cpu = 0x8000 + off - 0x10
    if snappy:
        return [f"キビキビ動作ON (反転後待ち ${cpu:04X}→01)"]
    return [f"キビキビ動作OFF (反転後待ち ${cpu:04X}→原作)"]
