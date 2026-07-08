"""Bullet8C enemy ID $8C base runtime body for mapper66 saved ROMs."""
from __future__ import annotations

from .element import ElementType


NEW_ENEMY_ID = 0x8C

OFF_RUNTIME = 0x6F74
OFF_SETUP_META_LOAD = OFF_RUNTIME

CPU_RUNTIME = 0xEF64
CPU_SETUP_META_LOAD = CPU_RUNTIME
CPU_STOCK_BULLET_STATE0 = 0xAFC7
CPU_STOCK_BULLET_STATE1 = 0xB00A
CPU_STOCK_INIT = 0x9D1C
CPU_STATE_DISPATCH = 0x8EA9
CPU_EXTRACT_STATE = 0xB201
CPU_SUB_SLOT_PTR = 0xB156
RAM_FRAME_COUNTER_LOW = 0x043C

SETUP_META_RUNTIME = bytes.fromhex(
    "a9 10"         # LDA #$10: stock Bullet right group
    "85 0e"         # STA $0E
    "a8"            # TAY
    "b9 d3 d9"      # LDA $D9D3,Y
    "60"            # RTS
)

OFF_INIT_STATUS = OFF_SETUP_META_LOAD + len(SETUP_META_RUNTIME)
CPU_INIT_STATUS = CPU_SETUP_META_LOAD + len(SETUP_META_RUNTIME)

INIT_STATUS_RUNTIME = bytes.fromhex(
    "68"            # PLA: discard saved stock init input
    "a9 c0"         # LDA #$C0: active
    "85 04"         # STA $04
    "a9 00"         # LDA #$00: Bullet right behavior
    "20 1c 9d"      # JSR $9D1C stock init writer
    "a5 06"         # LDA $06: current slot index
    "20 56 b1"      # JSR $B156: sub-slot pointer in $00/$01
    "a0 06"         # LDY #$06
    "a9 ff"         # LDA #$FF: force first sine phase application
    "91 00"         # STA ($00),Y
    "60"            # RTS
)

OFF_AI_DISPATCH = OFF_INIT_STATUS + len(INIT_STATUS_RUNTIME)
CPU_AI_DISPATCH = CPU_INIT_STATUS + len(INIT_STATUS_RUNTIME)

SINE_DELTA_TABLE = bytes((
    0xFD, 0xFD, 0xFC, 0xFC, 0xFC, 0xFC, 0xFB, 0xFB,
    0xFB, 0xFB, 0xFB, 0xFB, 0xFB, 0xFB, 0xFC, 0xFC,
    0xFC, 0xFC, 0xFD, 0xFD, 0xFD, 0xFE, 0xFE, 0xFF,
    0xFF, 0x00, 0x00, 0x01, 0x01, 0x02, 0x02, 0x03,
    0x03, 0x03, 0x04, 0x04, 0x04, 0x04, 0x05, 0x05,
    0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x04, 0x04,
    0x04, 0x04, 0x03, 0x03, 0x03, 0x02, 0x02, 0x01,
    0x01, 0x00, 0x00, 0xFF, 0xFF, 0xFE, 0xFE, 0xFD,
))
CPU_STATE2_WAVY_MOVE = CPU_AI_DISPATCH + 12
CPU_SINE_DELTA_TABLE = CPU_STATE2_WAVY_MOVE + 30

AI_RUNTIME = bytes((
    0x20, CPU_EXTRACT_STATE & 0xFF, CPU_EXTRACT_STATE >> 8,
    0x20, CPU_STATE_DISPATCH & 0xFF, CPU_STATE_DISPATCH >> 8,
    CPU_STOCK_BULLET_STATE0 & 0xFF, CPU_STOCK_BULLET_STATE0 >> 8,
    CPU_STOCK_BULLET_STATE1 & 0xFF, CPU_STOCK_BULLET_STATE1 >> 8,
    CPU_STATE2_WAVY_MOVE & 0xFF, CPU_STATE2_WAVY_MOVE >> 8,
    0x8A,              # TXA: preserve outer enemy-loop X
    0x48,              # PHA
    0xAD, RAM_FRAME_COUNTER_LOW & 0xFF, RAM_FRAME_COUNTER_LOW >> 8,
    0x4A,              # LSR A: advance the sine phase once per 2 frames
    0x29, 0x3F,        # AND #$3F: 64-step sine delta phase
    0xA0, 0x06,        # LDY #$06: last applied sine phase
    0xD1, 0x2C,        # CMP ($2C),Y
    0xF0, 0x0D,        # BEQ restore: do not apply the same phase twice
    0x91, 0x2C,        # STA ($2C),Y
    0xAA,              # TAX: table index = phase
    0xA0, 0x07,        # LDY #$07: main-slot Y pixel
    0xB1, 0x2E,        # LDA ($2E),Y
    0x18,              # CLC
    0x7D, CPU_SINE_DELTA_TABLE & 0xFF, CPU_SINE_DELTA_TABLE >> 8,
    0x91, 0x2E,        # STA ($2E),Y
    0x68,              # PLA
    0xAA,              # TAX
    0x60,              # RTS: skip stock wall collision/despawn.
)) + SINE_DELTA_TABLE

RUNTIME = SETUP_META_RUNTIME + INIT_STATUS_RUNTIME + AI_RUNTIME
CPU_RUNTIME_END = CPU_RUNTIME + len(RUNTIME)

RESERVED_SPANS = ((OFF_RUNTIME, len(RUNTIME)),)

assert len(SETUP_META_RUNTIME) == 9
assert len(INIT_STATUS_RUNTIME) == 22
assert len(SINE_DELTA_TABLE) == 64
assert sum((v if v < 0x80 else v - 0x100) for v in SINE_DELTA_TABLE) == 0
assert CPU_STATE2_WAVY_MOVE == CPU_AI_DISPATCH + 12
assert CPU_SINE_DELTA_TABLE == CPU_STATE2_WAVY_MOVE + 30
assert len(AI_RUNTIME) == 106
assert len(RUNTIME) == 137
assert CPU_RUNTIME + len(RUNTIME) == CPU_RUNTIME_END


def levels_need_runtime(levels: list) -> bool:
    for lv in levels or []:
        for enemy in getattr(lv, "enemies", []) or []:
            if getattr(enemy, "type", None) == ElementType.ENEMY and int(enemy.element_no) == NEW_ENEMY_ID:
                return True
    return False
