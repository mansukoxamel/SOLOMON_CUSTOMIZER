"""Ice Flame ($84) dedicated runtime body for mapper66 saved ROMs."""
from __future__ import annotations

from .element import ElementType


class IceFlameRuntimeError(ValueError):
    pass


NEW_ENEMY_ID = 0x84

OFF_AI_DISPATCH_CALL = 0x21D3  # CPU $A1C3: JSR $A329
OFF_ANIM_UPDATE_CALL = 0x0686  # CPU $8676: JSR $8789
OFF_INIT_WRITE_CALL = 0x2302  # CPU $A2F2: JSR $9D1C
OFF_SETUP_META_LOAD = 0x0ADB  # CPU $8ACB: LDA $D9D3,Y

OFF_BUFFER = 0x69B9
BUFFER_LEN = 24
OFF_RUNTIME = 0x69D1

CPU_AI_DISPATCH = 0xE9C1
CPU_SETUP_META_LOAD = 0xE9C4
CPU_INIT_STATUS = 0xE9CD
CPU_ANIM_UPDATE = 0xE9EA
CPU_RUNTIME_END = 0xE9EB

ORIG_AI_DISPATCH_CALL = bytes.fromhex("20 29 a3")
HOOK_AI_DISPATCH_CALL = bytes((0x20, CPU_AI_DISPATCH & 0xFF, CPU_AI_DISPATCH >> 8))

ORIG_ANIM_UPDATE_CALL = bytes.fromhex("20 89 87")
HOOK_ANIM_UPDATE_CALL = bytes((0x20, CPU_ANIM_UPDATE & 0xFF, CPU_ANIM_UPDATE >> 8))

ORIG_INIT_WRITE_CALL = bytes.fromhex("20 1c 9d")
HOOK_INIT_WRITE_CALL = bytes((0x20, CPU_INIT_STATUS & 0xFF, CPU_INIT_STATUS >> 8))

ORIG_SETUP_META_LOAD = bytes.fromhex("b9 d3 d9")
HOOK_SETUP_META_LOAD = bytes((0x20, CPU_SETUP_META_LOAD & 0xFF, CPU_SETUP_META_LOAD >> 8))


AI_DISPATCH_RUNTIME = bytes.fromhex(
    "4c a0 a5"      # JMP $A5A0 Flame-family AI
)

SETUP_META_RUNTIME = bytes.fromhex(
    "a9 40"         # LDA #$40 setup group: Flame/Burn
    "85 0e"         # STA $0E
    "a8"            # TAY
    "b9 d3 d9"      # LDA $D9D3,Y
    "60"            # RTS
)

INIT_STATUS_RUNTIME = bytes.fromhex(
    "a0 00"
    "a9 e0"         # status: active, contact enabled, fireball-killable
    "91 00"
    "a0 03"
    "a9 14"         # behavior/state: White Flame steady state
    "91 00"
    "a0 11"
    "a9 d6"         # fixed frame tile 1
    "91 00"
    "c8"
    "a9 d4"         # fixed frame tile 2
    "91 00"
    "c8"
    "a9 5a"         # fixed frame attr
    "91 00"
    "60"
)

ANIM_UPDATE_RUNTIME = bytes.fromhex(
    "60"            # skip stock animation update for fixed Ice Flame frames
)

RUNTIME = (
    AI_DISPATCH_RUNTIME
    + SETUP_META_RUNTIME
    + INIT_STATUS_RUNTIME
    + ANIM_UPDATE_RUNTIME
)

RESERVED_SPANS = ((OFF_RUNTIME, len(RUNTIME)),)

assert len(AI_DISPATCH_RUNTIME) == CPU_SETUP_META_LOAD - CPU_AI_DISPATCH
assert len(SETUP_META_RUNTIME) == CPU_INIT_STATUS - CPU_SETUP_META_LOAD
assert len(INIT_STATUS_RUNTIME) == CPU_ANIM_UPDATE - CPU_INIT_STATUS
assert len(ANIM_UPDATE_RUNTIME) == CPU_RUNTIME_END - CPU_ANIM_UPDATE
assert len(RUNTIME) == 42
assert CPU_AI_DISPATCH + len(RUNTIME) == CPU_RUNTIME_END


def levels_need_runtime(levels: list) -> bool:
    for lv in levels or []:
        for enemy in getattr(lv, "enemies", []) or []:
            if getattr(enemy, "type", None) == ElementType.ENEMY and int(enemy.element_no) == NEW_ENEMY_ID:
                return True
    return False


def apply(rom_data: bytearray) -> list[str]:
    """Compatibility wrapper; shared dispatch is owned by new_enemy_runtime."""
    from . import new_enemy_runtime
    return new_enemy_runtime.apply(rom_data)
