"""Per-stage redirect from a cleared room to the original final room."""
from __future__ import annotations

from . import stage_ext


class FinalStageRedirectError(ValueError):
    pass


def _cf(cpu: int) -> int:
    return 0x10 + (int(cpu) - 0x8000)


OFF_HOOK_CLEAR_RESET = _cf(0xC6F5)
OFF_SIG_AFTER_CLEAR_RESET = _cf(0xC6F8)
OFF_CAVE = 0x3D28
CPU_CAVE = 0xBD18

ORIG_HOOK_CLEAR_RESET = bytes.fromhex("20 0e c7")
HOOK_CLEAR_RESET = bytes((0x20, CPU_CAVE & 0xFF, CPU_CAVE >> 8))
SIG_AFTER_CLEAR_RESET = bytes.fromhex("8d 2a 04 8d 29 04 a9 ee 25 7c 85 7c")

CAVE = bytes.fromhex("ad 7a 07 10 05 a9 31 8d 28 04 4c 0e c7")
RESERVED_SPANS = ((OFF_CAVE, len(CAVE)),)


def enabled_in_any_level(levels: list) -> bool:
    return any(stage_ext.final_stage_redirect_enabled(lv) for lv in levels or [])


def _verify(rom_data: bytes) -> None:
    if len(rom_data) < OFF_SIG_AFTER_CLEAR_RESET + len(SIG_AFTER_CLEAR_RESET):
        raise FinalStageRedirectError("ROM is too small for final-stage redirect runtime.")
    sig = bytes(rom_data[OFF_SIG_AFTER_CLEAR_RESET:OFF_SIG_AFTER_CLEAR_RESET + len(SIG_AFTER_CLEAR_RESET)])
    if sig != SIG_AFTER_CLEAR_RESET:
        raise FinalStageRedirectError("$C6F8 signature mismatch.")
    hook = bytes(rom_data[OFF_HOOK_CLEAR_RESET:OFF_HOOK_CLEAR_RESET + len(ORIG_HOOK_CLEAR_RESET)])
    if hook not in (ORIG_HOOK_CLEAR_RESET, HOOK_CLEAR_RESET):
        raise FinalStageRedirectError(f"$C6F5 hook bytes are unexpected: {hook.hex(' ')}")
    cur = bytes(rom_data[OFF_CAVE:OFF_CAVE + len(CAVE)])
    if cur != CAVE and any(b not in (0xEA, 0x00) for b in cur):
        raise FinalStageRedirectError(f"$BD18 cave is not free: {cur.hex(' ')}")


def apply(rom_data: bytearray, levels: list) -> list[str]:
    _verify(rom_data)
    changed: list[str] = []
    if bytes(rom_data[OFF_CAVE:OFF_CAVE + len(CAVE)]) != CAVE:
        rom_data[OFF_CAVE:OFF_CAVE + len(CAVE)] = CAVE
        changed.append("Final-stage redirect cave 注入 ($BD18)")
    if bytes(rom_data[OFF_HOOK_CLEAR_RESET:OFF_HOOK_CLEAR_RESET + len(HOOK_CLEAR_RESET)]) != HOOK_CLEAR_RESET:
        rom_data[OFF_HOOK_CLEAR_RESET:OFF_HOOK_CLEAR_RESET + len(HOOK_CLEAR_RESET)] = HOOK_CLEAR_RESET
        changed.append("$C6F5 final-stage redirect hook 有効化")
    return changed
