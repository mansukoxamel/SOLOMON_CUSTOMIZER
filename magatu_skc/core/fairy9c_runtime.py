"""Dark Fairy enemy ID $9C runtime body for mapper66 saved ROMs."""
from __future__ import annotations

from .element import ElementType


NEW_ENEMY_ID = 0x9C

OFF_RUNTIME = 0x6010
OFF_SETUP_META_LOAD = OFF_RUNTIME

CPU_RUNTIME = 0xE000
CPU_SETUP_META_LOAD = CPU_RUNTIME
CPU_STOCK_FAIRY_AI = 0xA700
CPU_STOCK_INIT_WRITER = 0x9D1C
CPU_TRIGGER_ACTION = 0x8D5F
CPU_DESPAWN = 0xB376
POISON_DELAY_FRAMES = 0x3C

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
    "91 00"         # clear Y velocity left by the $9C stock property read
    "a9 e2"         # LDA #$E2: stock Fairy status
    "85 04"         # STA $04
    "a9 9c"         # LDA #$9C: keep Dark Fairy runtime type
    "85 05"         # STA $05
    "a9 00"         # LDA #$00: stock Fairy behavior
    "20 1c 9d"      # JSR $9D1C stock init writer
    "60"            # RTS
)

OFF_AI_DISPATCH = OFF_INIT_STATUS + len(INIT_STATUS_RUNTIME)
CPU_AI_DISPATCH = CPU_INIT_STATUS + len(INIT_STATUS_RUNTIME)

AI_DISPATCH_RUNTIME = bytes(
    (
        0xA0, 0x07,                               # LDY #$07: poison delay in sub-slot[7]
        0xB1, 0x2C,                               # LDA ($2C),Y
        0xF0, 0x12,                               # BEQ stock_ai
        0x38,                                     # SEC
        0xE9, 0x01,                               # SBC #$01
        0xF0, 0x03,                               # BEQ poison
        0x91, 0x2C,                               # STA ($2C),Y
        0x60,                                     # RTS
        0x91, 0x2C,                               # poison: clear sub-slot[7]
        0xA9, 0x31,                               # LDA #$31: Dana death sequence
        0x20, CPU_TRIGGER_ACTION & 0xFF, CPU_TRIGGER_ACTION >> 8,
        0x4C, CPU_DESPAWN & 0xFF, CPU_DESPAWN >> 8,
        0xAD, 0x53, 0x04,                         # LDA $0453: fairy count before stock AI
        0x48,                                     # PHA
        0xA0, 0x01,                               # LDY #$01
        0xA9, 0x1C,                               # LDA #$1C
        0x91, 0x2E,                               # STA ($2E),Y: temporarily behave as stock Fairy
        0x20, CPU_STOCK_FAIRY_AI & 0xFF, CPU_STOCK_FAIRY_AI >> 8,
        0xA0, 0x01,                               # LDY #$01
        0xA9, NEW_ENEMY_ID,                       # LDA #$9C
        0x91, 0x2E,                               # STA ($2E),Y: restore Dark Fairy type
        0x68,                                     # PLA
        0xCD, 0x53, 0x04,                         # CMP $0453
        0xF0, 0x06,                               # BEQ done
        0xA0, 0x07,                               # LDY #$07
        0xA9, POISON_DELAY_FRAMES,                # LDA #$3C
        0x91, 0x2C,                               # STA ($2C),Y
        0x60,                                     # RTS
    )
)

RUNTIME = SETUP_META_RUNTIME + INIT_STATUS_RUNTIME + AI_DISPATCH_RUNTIME
CPU_RUNTIME_END = CPU_RUNTIME + len(RUNTIME)

RESERVED_SPANS = ((OFF_RUNTIME, len(RUNTIME)),)

assert len(SETUP_META_RUNTIME) == 9
assert len(INIT_STATUS_RUNTIME) == 21
assert len(AI_DISPATCH_RUNTIME) == 56
assert len(RUNTIME) == 86
assert CPU_RUNTIME + len(RUNTIME) == CPU_RUNTIME_END


def levels_need_runtime(levels: list) -> bool:
    for lv in levels or []:
        for enemy in getattr(lv, "enemies", []) or []:
            if getattr(enemy, "type", None) == ElementType.ENEMY and int(enemy.element_no) == NEW_ENEMY_ID:
                return True
    return False
