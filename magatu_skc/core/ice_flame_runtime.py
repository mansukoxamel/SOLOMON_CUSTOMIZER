"""Ice Burn ($82) dedicated init/animation runtime for mapper66 saved ROMs."""
from __future__ import annotations

from .element import ElementType


class IceFlameRuntimeError(ValueError):
    pass


NEW_ENEMY_ID = 0x82

OFF_AI_DISPATCH_CALL = 0x21D3  # CPU $A1C3: JSR $A329
OFF_ANIM_UPDATE_CALL = 0x0686  # CPU $8676: JSR $8789
OFF_INIT_WRITE_CALL = 0x2302  # CPU $A2F2: JSR $9D1C
OFF_SETUP_META_LOAD = 0x0ADB  # CPU $8ACB: LDA $D9D3,Y

OFF_RUNTIME = 0x6085

CPU_INIT_STATUS = 0xE075
CPU_ANIM_UPDATE = 0xE092
CPU_RUNTIME_END = 0xE093

ORIG_AI_DISPATCH_CALL = bytes.fromhex("20 29 a3")
HOOK_AI_DISPATCH_CALL = bytes.fromhex("20 c1 e9")

ORIG_ANIM_UPDATE_CALL = bytes.fromhex("20 89 87")
HOOK_ANIM_UPDATE_CALL = bytes((0x20, CPU_ANIM_UPDATE & 0xFF, CPU_ANIM_UPDATE >> 8))

ORIG_INIT_WRITE_CALL = bytes.fromhex("20 1c 9d")
HOOK_INIT_WRITE_CALL = bytes((0x20, CPU_INIT_STATUS & 0xFF, CPU_INIT_STATUS >> 8))

ORIG_SETUP_META_LOAD = bytes.fromhex("b9 d3 d9")
HOOK_SETUP_META_LOAD = bytes.fromhex("20 c4 e9")


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
    INIT_STATUS_RUNTIME
    + ANIM_UPDATE_RUNTIME
)

RESERVED_SPANS = ((OFF_RUNTIME, len(RUNTIME)),)

assert len(INIT_STATUS_RUNTIME) == CPU_ANIM_UPDATE - CPU_INIT_STATUS
assert len(ANIM_UPDATE_RUNTIME) == CPU_RUNTIME_END - CPU_ANIM_UPDATE
assert len(RUNTIME) == 30
assert CPU_INIT_STATUS + len(RUNTIME) == CPU_RUNTIME_END


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
