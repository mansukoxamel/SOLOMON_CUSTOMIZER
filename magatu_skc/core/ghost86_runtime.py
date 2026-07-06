"""Ghost enemy ID $86 runtime body for mapper66 saved ROMs."""
from __future__ import annotations

from .element import ElementType


NEW_ENEMY_ID = 0x86

OFF_RUNTIME = 0x6D88
OFF_SETUP_GROUP_TABLE = OFF_RUNTIME
OFF_INIT_STATUS = OFF_RUNTIME + 3

CPU_RUNTIME = 0xED78
CPU_SETUP_GROUP_TABLE = CPU_RUNTIME
CPU_INIT_STATUS = CPU_RUNTIME + 3
CPU_AI_DISPATCH = 0xABF7
CPU_RUNTIME_END = CPU_RUNTIME + 14

SETUP_GROUP_TABLE = bytes((
    0x40,  # $84 Ice Flame group
    0x14,  # $85 Spark Ball group
    0x1A,  # $86 Ghost right speed1 group, same visual/velocity class as $34
))

INIT_STATUS_RUNTIME = bytes.fromhex(
    "68"            # PLA: discard saved stock init input
    "a9 c0"         # LDA #$C0: active, no gravity like stock Ghost
    "85 04"         # STA $04
    "a9 00"         # LDA #$00: Ghost right behavior
    "20 1c 9d"      # JSR $9D1C stock init writer
    "60"            # RTS
)

RUNTIME = SETUP_GROUP_TABLE + INIT_STATUS_RUNTIME

RESERVED_SPANS = ((OFF_RUNTIME, len(RUNTIME)),)

assert OFF_INIT_STATUS == OFF_SETUP_GROUP_TABLE + len(SETUP_GROUP_TABLE)
assert len(RUNTIME) == 14
assert CPU_RUNTIME + len(RUNTIME) == CPU_RUNTIME_END


def levels_need_runtime(levels: list) -> bool:
    for lv in levels or []:
        for enemy in getattr(lv, "enemies", []) or []:
            if getattr(enemy, "type", None) == ElementType.ENEMY and int(enemy.element_no) == NEW_ENEMY_ID:
                return True
    return False
