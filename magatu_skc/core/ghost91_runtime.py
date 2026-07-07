"""Ghost91 enemy ID $8B base runtime body for mapper66 saved ROMs."""
from __future__ import annotations

from .element import ElementType


NEW_ENEMY_ID = 0x8B

OFF_RUNTIME = 0x6F53
OFF_SETUP_META_LOAD = OFF_RUNTIME

CPU_RUNTIME = 0xEF43
CPU_SETUP_META_LOAD = CPU_RUNTIME
CPU_STOCK_GHOST_AI = 0xABF7
CPU_STOCK_INIT = 0x9D1C

SETUP_META_RUNTIME = bytes.fromhex(
    "a9 1a"         # LDA #$1A: stock Ghost right speed1 group
    "85 0e"         # STA $0E
    "a8"            # TAY
    "b9 d3 d9"      # LDA $D9D3,Y
    "60"            # RTS
)

OFF_INIT_STATUS = OFF_SETUP_META_LOAD + len(SETUP_META_RUNTIME)
CPU_INIT_STATUS = CPU_SETUP_META_LOAD + len(SETUP_META_RUNTIME)

INIT_STATUS_RUNTIME = bytes.fromhex(
    "68"            # PLA: discard saved stock init input
    "a9 c0"         # LDA #$C0: active, no gravity like stock Ghost
    "85 04"         # STA $04
    "a9 00"         # LDA #$00: Ghost right behavior
    "20 1c 9d"      # JSR $9D1C stock init writer
    "60"            # RTS
)

OFF_AI_DISPATCH = OFF_INIT_STATUS + len(INIT_STATUS_RUNTIME)
CPU_AI_DISPATCH = CPU_INIT_STATUS + len(INIT_STATUS_RUNTIME)

AI_RUNTIME = bytes((0x4C, CPU_STOCK_GHOST_AI & 0xFF, CPU_STOCK_GHOST_AI >> 8))

RUNTIME = SETUP_META_RUNTIME + INIT_STATUS_RUNTIME + AI_RUNTIME
CPU_RUNTIME_END = CPU_RUNTIME + len(RUNTIME)

RESERVED_SPANS = ((OFF_RUNTIME, len(RUNTIME)),)

assert len(SETUP_META_RUNTIME) == 9
assert len(INIT_STATUS_RUNTIME) == 11
assert len(AI_RUNTIME) == 3
assert len(RUNTIME) == 23
assert CPU_RUNTIME + len(RUNTIME) == CPU_RUNTIME_END


def levels_need_runtime(levels: list) -> bool:
    for lv in levels or []:
        for enemy in getattr(lv, "enemies", []) or []:
            if getattr(enemy, "type", None) == ElementType.ENEMY and int(enemy.element_no) == NEW_ENEMY_ID:
                return True
    return False
