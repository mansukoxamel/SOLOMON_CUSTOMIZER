"""Neul enemy ID $88 runtime body for mapper66 saved ROMs."""
from __future__ import annotations

from .element import ElementType


NEW_ENEMY_ID = 0x88

OFF_RUNTIME = 0x6E16
OFF_SETUP_META_LOAD = OFF_RUNTIME
OFF_INIT_STATUS = OFF_RUNTIME + 9
OFF_AI_DISPATCH = OFF_RUNTIME + 19

CPU_RUNTIME = 0xEE06
CPU_SETUP_META_LOAD = CPU_RUNTIME
CPU_INIT_STATUS = CPU_RUNTIME + 9
CPU_AI_DISPATCH = CPU_RUNTIME + 19
CPU_STOCK_NEUL_GHOST_AI = 0xABF7
CPU_STOCK_INIT = 0x9D1C
CPU_RUNTIME_END = CPU_RUNTIME + 22

SETUP_META_RUNTIME = bytes.fromhex(
    "a9 18"         # LDA #$18: stock Neul up setup group
    "85 0e"         # STA $0E
    "a8"            # TAY
    "b9 d3 d9"      # LDA $D9D3,Y
    "60"            # RTS
)

INIT_STATUS_RUNTIME = bytes.fromhex(
    "68"            # PLA: discard saved stock init input
    "a9 c0"         # LDA #$C0: active, no gravity like stock Neul/Ghost
    "85 04"         # STA $04
    "a9 00"         # LDA #$00: stock $30 Neul behavior
    "4c 1c 9d"      # JMP $9D1C stock init writer
)

AI_DISPATCH_RUNTIME = bytes.fromhex(
    "4c f7 ab"      # JMP $ABF7 stock Neul/Ghost AI
)

RUNTIME = SETUP_META_RUNTIME + INIT_STATUS_RUNTIME + AI_DISPATCH_RUNTIME

RESERVED_SPANS = ((OFF_RUNTIME, len(RUNTIME)),)

assert len(SETUP_META_RUNTIME) == CPU_INIT_STATUS - CPU_SETUP_META_LOAD
assert len(INIT_STATUS_RUNTIME) == CPU_AI_DISPATCH - CPU_INIT_STATUS
assert len(AI_DISPATCH_RUNTIME) == CPU_RUNTIME_END - CPU_AI_DISPATCH
assert len(RUNTIME) == 22
assert CPU_RUNTIME + len(RUNTIME) == CPU_RUNTIME_END


def levels_need_runtime(levels: list) -> bool:
    for lv in levels or []:
        for enemy in getattr(lv, "enemies", []) or []:
            if getattr(enemy, "type", None) == ElementType.ENEMY and int(enemy.element_no) == NEW_ENEMY_ID:
                return True
    return False
