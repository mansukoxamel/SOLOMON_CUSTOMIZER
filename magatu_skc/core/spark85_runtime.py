"""Spark Ball enemy ID $85 runtime body for mapper66 saved ROMs."""
from __future__ import annotations

from .element import ElementType


class Spark85RuntimeError(ValueError):
    pass


NEW_ENEMY_ID = 0x85

OFF_BUFFER = 0x69FB
BUFFER_LEN = 24
OFF_RUNTIME = 0x6A13
OFF_AI_DISPATCH = 0x6A13
OFF_INIT_STATUS = 0x6A38

CPU_AI_DISPATCH = 0xEA03
CPU_INIT_STATUS = 0xEA28
CPU_RUNTIME_END = 0xEA46

AI_DISPATCH_RUNTIME = bytes.fromhex(
    "ad 39 04"      # LDA $0439: LIFE hundreds digit
    "f0 03"         # BEQ stop/reverse path
    "4c 29 a9"      # JMP $A929 stock Spark Ball slow AI
    "a0 02"         # LDY #$02
    "b1 2c"         # LDA ($2C),Y: one-shot reverse flag
    "d0 13"         # BNE stop
    "a9 01"         # LDA #$01
    "91 2c"         # STA ($2C),Y
    "a0 06"         # LDY #$06
    "b1 2c"         # LDA ($2C),Y: Spark direction
    "49 01"         # EOR #$01
    "91 2c"         # STA ($2C),Y
    "c8"            # INY
    "b1 2c"         # LDA ($2C),Y: paired phase/direction field
    "49 01"         # EOR #$01
    "91 2c"         # STA ($2C),Y
    "60"            # RTS: stay stopped while LIFE hundreds is zero
)

INIT_STATUS_RUNTIME = bytes.fromhex(
    "a9 c0"         # LDA #$C0
    "85 04"         # STA $04
    "a9 00"         # LDA #$00
    "20 1c 9d"      # JSR $9D1C stock init
    "a5 06"         # LDA $06: current main-slot index
    "20 56 b1"      # JSR $B156: sub-slot pointer in $00/$01
    "a9 00"         # LDA #$00
    "a0 02"         # LDY #$02
    "91 00"         # STA ($00),Y: reverse flag clear
    "a0 06"         # LDY #$06
    "91 00"         # STA ($00),Y: initial direction
    "c8"            # INY
    "a9 02"         # LDA #$02
    "91 00"         # STA ($00),Y
    "60"            # RTS
)

RUNTIME = (
    AI_DISPATCH_RUNTIME
    + bytes((0xEA,)) * (OFF_INIT_STATUS - (OFF_AI_DISPATCH + len(AI_DISPATCH_RUNTIME)))
    + INIT_STATUS_RUNTIME
)

RESERVED_SPANS = (
    (OFF_RUNTIME, len(RUNTIME)),
)

assert OFF_RUNTIME - OFF_BUFFER == BUFFER_LEN
assert len(AI_DISPATCH_RUNTIME) == 34
assert OFF_AI_DISPATCH + len(AI_DISPATCH_RUNTIME) <= OFF_INIT_STATUS
assert OFF_RUNTIME + len(RUNTIME) == 0x6A56
assert CPU_AI_DISPATCH + len(RUNTIME) == CPU_RUNTIME_END


def levels_need_runtime(levels: list) -> bool:
    for lv in levels or []:
        for enemy in getattr(lv, "enemies", []) or []:
            if getattr(enemy, "type", None) == ElementType.ENEMY and int(enemy.element_no) == NEW_ENEMY_ID:
                return True
    return False
