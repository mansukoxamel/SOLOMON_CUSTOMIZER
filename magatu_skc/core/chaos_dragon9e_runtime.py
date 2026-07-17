"""Chaos Dragon enemy ID $9E runtime body for mapper66 saved ROMs."""
from __future__ import annotations

from .element import ElementType


NEW_ENEMY_ID = 0x9E

OFF_RUNTIME = 0x6EB4
OFF_SETUP_META_LOAD = OFF_RUNTIME

CPU_RUNTIME = 0xEEA4
CPU_SETUP_META_LOAD = CPU_RUNTIME
CPU_STOCK_DRAGON_AI = 0xA64A
CPU_STOCK_INIT = 0x9D1C

SETUP_META_RUNTIME = bytes.fromhex(
    "a9 34"         # LDA #$34: stock Dragon right visual/animation group
    "85 0e"         # STA $0E: keep Dragon metadata for $8B03 animation setup
    "a0 00"         # LDY #$00: speed metadata with no vertical write
    "b9 d3 d9"      # LDA $D9D3,Y
    "60"            # RTS
)

OFF_INIT_STATUS = OFF_SETUP_META_LOAD + len(SETUP_META_RUNTIME)
CPU_INIT_STATUS = CPU_SETUP_META_LOAD + len(SETUP_META_RUNTIME)

INIT_STATUS_RUNTIME = bytes.fromhex(
    "68"            # PLA: discard behavior computed for custom type $89
    "a9 c0"         # LDA #$C0: active, no gravity for Chaos Dragon9E
    "85 04"         # STA $04
    "a0 05"         # LDY #$05
    "a9 00"         # LDA #$00: no initial vertical movement
    "91 00"         # STA ($00),Y
    "a9 14"         # LDA #$14: enter Dragon walking state directly
    "4c 1c 9d"      # JMP $9D1C stock init writer
)

OFF_AI_DISPATCH = OFF_INIT_STATUS + len(INIT_STATUS_RUNTIME)
CPU_AI_DISPATCH = CPU_INIT_STATUS + len(INIT_STATUS_RUNTIME)

AI_DISPATCH_RUNTIME = bytes.fromhex(
    "4c 4a a6"      # JMP $A64A stock Dragon AI fallback
)

RUNTIME = SETUP_META_RUNTIME + INIT_STATUS_RUNTIME + AI_DISPATCH_RUNTIME
CPU_RUNTIME_END = CPU_RUNTIME + len(RUNTIME)

RESERVED_SPANS = ((OFF_RUNTIME, len(RUNTIME)),)

assert len(SETUP_META_RUNTIME) == CPU_INIT_STATUS - CPU_SETUP_META_LOAD
assert len(INIT_STATUS_RUNTIME) == CPU_AI_DISPATCH - CPU_INIT_STATUS
assert len(AI_DISPATCH_RUNTIME) == CPU_RUNTIME_END - CPU_AI_DISPATCH
assert len(INIT_STATUS_RUNTIME) == 16
assert CPU_RUNTIME + len(RUNTIME) == CPU_RUNTIME_END


def levels_need_runtime(levels: list) -> bool:
    for lv in levels or []:
        for enemy in getattr(lv, "enemies", []) or []:
            if getattr(enemy, "type", None) == ElementType.ENEMY and int(enemy.element_no) == NEW_ENEMY_ID:
                return True
    return False
