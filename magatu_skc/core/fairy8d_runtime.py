"""Dark Fairy enemy ID $8D base runtime body for mapper66 saved ROMs."""
from __future__ import annotations

from .element import ElementType


NEW_ENEMY_ID = 0x8D

OFF_RUNTIME = 0x6010
OFF_SETUP_META_LOAD = OFF_RUNTIME

CPU_RUNTIME = 0xE000
CPU_SETUP_META_LOAD = CPU_RUNTIME
CPU_STOCK_FAIRY_AI = 0xA700
CPU_STOCK_INIT_WRITER = 0x9D1C

SETUP_META_RUNTIME = bytes.fromhex(
    "a9 0e"         # LDA #$0E: stock Fairy setup/animation group
    "85 0e"         # STA $0E
    "a8"            # TAY
    "b9 d3 d9"      # LDA $D9D3,Y
    "60"            # RTS
)

OFF_INIT_STATUS = OFF_SETUP_META_LOAD + len(SETUP_META_RUNTIME)
CPU_INIT_STATUS = CPU_SETUP_META_LOAD + len(SETUP_META_RUNTIME)

INIT_STATUS_RUNTIME = bytes.fromhex(
    "68"            # PLA: discard saved stock init input
    "a0 05"         # LDY #$05
    "a9 00"         # LDA #$00
    "91 00"         # clear Y velocity left by the $8D stock property read
    "a9 e2"         # LDA #$E2: stock Fairy status
    "85 04"         # STA $04
    "a9 1c"         # LDA #$1C: stock Fairy runtime type
    "85 05"         # STA $05
    "a9 00"         # LDA #$00: stock Fairy behavior
    "20 1c 9d"      # JSR $9D1C stock init writer
    "60"            # RTS
)

OFF_AI_DISPATCH = OFF_INIT_STATUS + len(INIT_STATUS_RUNTIME)
CPU_AI_DISPATCH = CPU_INIT_STATUS + len(INIT_STATUS_RUNTIME)

AI_DISPATCH_RUNTIME = bytes.fromhex(
    "a0 01"         # LDY #$01
    "a9 1c"         # LDA #$1C
    "91 2e"         # convert main-slot type to stock Fairy if $8D reaches AI
    "4c 00 a7"      # JMP $A700 stock Fairy AI
)

RUNTIME = SETUP_META_RUNTIME + INIT_STATUS_RUNTIME + AI_DISPATCH_RUNTIME
CPU_RUNTIME_END = CPU_RUNTIME + len(RUNTIME)

RESERVED_SPANS = ((OFF_RUNTIME, len(RUNTIME)),)

assert len(SETUP_META_RUNTIME) == 9
assert len(INIT_STATUS_RUNTIME) == 21
assert len(AI_DISPATCH_RUNTIME) == 9
assert len(RUNTIME) == 39
assert CPU_RUNTIME + len(RUNTIME) == CPU_RUNTIME_END


def levels_need_runtime(levels: list) -> bool:
    for lv in levels or []:
        for enemy in getattr(lv, "enemies", []) or []:
            if getattr(enemy, "type", None) == ElementType.ENEMY and int(enemy.element_no) == NEW_ENEMY_ID:
                return True
    return False
