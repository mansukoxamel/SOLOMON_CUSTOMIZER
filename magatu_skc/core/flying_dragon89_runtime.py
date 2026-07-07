"""Flying Dragon enemy ID $89 runtime body for mapper66 saved ROMs."""
from __future__ import annotations

from .element import ElementType


NEW_ENEMY_ID = 0x89

OFF_RUNTIME = 0x6EB4
OFF_SETUP_META_LOAD = OFF_RUNTIME
OFF_INIT_STATUS = OFF_RUNTIME + 9
OFF_AI_DISPATCH = OFF_RUNTIME + 29

CPU_RUNTIME = 0xEEA4
CPU_SETUP_META_LOAD = CPU_RUNTIME
CPU_INIT_STATUS = CPU_RUNTIME + 9
CPU_AI_DISPATCH = CPU_RUNTIME + 29
CPU_STOCK_DRAGON_AI = 0xA64A
CPU_STOCK_INIT = 0x9D1C
CPU_RUNTIME_END = CPU_RUNTIME + 32

SETUP_META_RUNTIME = bytes.fromhex(
    "a9 34"         # LDA #$34: stock Dragon right setup group for type $68
    "85 0e"         # STA $0E
    "a8"            # TAY
    "b9 d3 d9"      # LDA $D9D3,Y
    "60"            # RTS
)

INIT_STATUS_RUNTIME = bytes.fromhex(
    "68"            # PLA: discard behavior computed for custom type $89
    "a9 68"         # LDA #$68: convert custom ID to stock Dragon right s0
    "85 05"         # STA $05
    "a9 e0"         # LDA #$E0: stock Dragon status class
    "85 04"         # STA $04
    "a0 05"         # LDY #$05
    "a9 80"         # LDA #$80: stock Dragon initial Y velocity
    "91 00"         # STA ($00),Y
    "a9 18"         # LDA #$18: stock Dragon initial behavior
    "4c 1c 9d"      # JMP $9D1C stock init writer
)

AI_DISPATCH_RUNTIME = bytes.fromhex(
    "4c 4a a6"      # JMP $A64A stock Dragon AI fallback
)

RUNTIME = SETUP_META_RUNTIME + INIT_STATUS_RUNTIME + AI_DISPATCH_RUNTIME

RESERVED_SPANS = ((OFF_RUNTIME, len(RUNTIME)),)

assert len(SETUP_META_RUNTIME) == CPU_INIT_STATUS - CPU_SETUP_META_LOAD
assert len(INIT_STATUS_RUNTIME) == CPU_AI_DISPATCH - CPU_INIT_STATUS
assert len(AI_DISPATCH_RUNTIME) == CPU_RUNTIME_END - CPU_AI_DISPATCH
assert len(RUNTIME) == 32
assert CPU_RUNTIME + len(RUNTIME) == CPU_RUNTIME_END


def levels_need_runtime(levels: list) -> bool:
    for lv in levels or []:
        for enemy in getattr(lv, "enemies", []) or []:
            if getattr(enemy, "type", None) == ElementType.ENEMY and int(enemy.element_no) == NEW_ENEMY_ID:
                return True
    return False
