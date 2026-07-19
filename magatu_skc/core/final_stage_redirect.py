"""Per-stage redirect from a cleared room to the original final room."""
from __future__ import annotations

from . import stage_ext


class FinalStageRedirectError(ValueError):
    pass


def _cf(cpu: int) -> int:
    return 0x10 + (int(cpu) - 0x8000)


OFF_HOOK_CLEAR_RESET = _cf(0xC6F5)
OFF_SIG_AFTER_CLEAR_RESET = _cf(0xC6F8)
OFF_CAVE = 0x6342
CPU_CAVE = 0xE332
FINAL_STAGE_NO = 50
FINAL_STAGE_INDEX = FINAL_STAGE_NO - 1

ORIG_HOOK_CLEAR_RESET = bytes.fromhex("20 0e c7")
HOOK_CLEAR_RESET = bytes((0x20, CPU_CAVE & 0xFF, CPU_CAVE >> 8))
SIG_AFTER_CLEAR_RESET = bytes.fromhex("8d 2a 04 8d 29 04 a9 ee 25 7c 85 7c")

CAVE = bytes.fromhex("ad 7a 07 10 05 a9 31 8d 28 04 4c 0e c7")
RESERVED_SPANS = ((OFF_CAVE, len(CAVE)),)
RAM_FINAL_STAGE_REDIRECT = 0x077A
RAM_RESERVED_SPANS = ((RAM_FINAL_STAGE_REDIRECT, 1),)


def enabled_in_any_level(levels: list) -> bool:
    return any(stage_ext.final_stage_redirect_enabled(lv) for lv in levels or [])


def validate_levels(levels: list) -> None:
    if len(levels or []) > FINAL_STAGE_INDEX and stage_ext.final_stage_redirect_enabled(
        levels[FINAL_STAGE_INDEX]
    ):
        raise FinalStageRedirectError(
            "Stage 50 cannot redirect to itself after clear."
        )


def _verify(rom_data: bytes) -> None:
    required_end = max(
        OFF_HOOK_CLEAR_RESET + len(ORIG_HOOK_CLEAR_RESET),
        OFF_SIG_AFTER_CLEAR_RESET + len(SIG_AFTER_CLEAR_RESET),
        OFF_CAVE + len(CAVE),
    )
    if len(rom_data) < required_end:
        raise FinalStageRedirectError("ROM is too small for final-stage redirect runtime.")
    sig = bytes(rom_data[OFF_SIG_AFTER_CLEAR_RESET:OFF_SIG_AFTER_CLEAR_RESET + len(SIG_AFTER_CLEAR_RESET)])
    if sig != SIG_AFTER_CLEAR_RESET:
        raise FinalStageRedirectError("$C6F8 signature mismatch.")
    hook = bytes(rom_data[OFF_HOOK_CLEAR_RESET:OFF_HOOK_CLEAR_RESET + len(ORIG_HOOK_CLEAR_RESET)])
    if hook not in (ORIG_HOOK_CLEAR_RESET, HOOK_CLEAR_RESET):
        raise FinalStageRedirectError(f"$C6F5 hook bytes are unexpected: {hook.hex(' ')}")
    cur = bytes(rom_data[OFF_CAVE:OFF_CAVE + len(CAVE)])
    if cur != CAVE and any(b not in (0xEA, 0x00) for b in cur):
        raise FinalStageRedirectError(f"$E332 cave is not free: {cur.hex(' ')}")


def apply(rom_data: bytearray, levels: list) -> list[str]:
    validate_levels(levels)
    _verify(rom_data)
    changed: list[str] = []
    if bytes(rom_data[OFF_CAVE:OFF_CAVE + len(CAVE)]) != CAVE:
        rom_data[OFF_CAVE:OFF_CAVE + len(CAVE)] = CAVE
        changed.append("Final-stage redirect cave 注入 ($E332)")
    if bytes(rom_data[OFF_HOOK_CLEAR_RESET:OFF_HOOK_CLEAR_RESET + len(HOOK_CLEAR_RESET)]) != HOOK_CLEAR_RESET:
        rom_data[OFF_HOOK_CLEAR_RESET:OFF_HOOK_CLEAR_RESET + len(HOOK_CLEAR_RESET)] = HOOK_CLEAR_RESET
        changed.append("$C6F5 final-stage redirect hook 有効化")
    return changed
