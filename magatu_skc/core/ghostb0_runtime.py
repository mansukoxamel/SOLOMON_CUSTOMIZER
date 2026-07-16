"""Parameterized Ghost A/B runtime for enemy IDs $B0-$B3."""
from __future__ import annotations

from .element import ElementType


FIRST_ID = 0xB0
LAST_ID = 0xB3
NEW_ENEMY_IDS = tuple(range(FIRST_ID, LAST_ID + 1))

OFF_RUNTIME = 0x6268
CPU_RUNTIME = 0xE258
MAX_RUNTIME_SIZE = 218

CPU_STOCK_GHOST_AI = 0xABF7
CPU_FIND_FREE_SUB_SLOT = 0xB2EA
CPU_BULLET_SPAWN = 0xAE76
CPU_SUB_SLOT_PTR = 0xB156

COOLDOWN_ARMED = 0x80

# Preset A ($B0/$B1) and preset B ($B2/$B3). Both initially match $86.
SETUP_GROUP_TABLE = bytes((0x1A, 0x1A))
COOLDOWN_RELOAD_TABLE = bytes((0xC0, 0xC0))
FIRE_DIRECTION_TABLE = bytes((0x03, 0x03))
PARAMETER_TABLES = SETUP_GROUP_TABLE + COOLDOWN_RELOAD_TABLE + FIRE_DIRECTION_TABLE

OFF_SETUP_META_LOAD = OFF_RUNTIME + len(PARAMETER_TABLES)
CPU_SETUP_META_LOAD = CPU_RUNTIME + len(PARAMETER_TABLES)

SETUP_META_RUNTIME = bytes((
    0x29, 0x02,                         # AND #$02: A/B preset bit
    0x4A,                               # LSR A
    0xAA,                               # TAX
    0xBD, CPU_RUNTIME & 0xFF, CPU_RUNTIME >> 8,
    0x85, 0x0E,                         # STA $0E
    0xA8,                               # TAY
    0xB9, 0xD3, 0xD9,                   # LDA $D9D3,Y
    0x60,                               # RTS
))

OFF_INIT_STATUS = OFF_SETUP_META_LOAD + len(SETUP_META_RUNTIME)
CPU_INIT_STATUS = CPU_SETUP_META_LOAD + len(SETUP_META_RUNTIME)

INIT_STATUS_RUNTIME = bytes.fromhex(
    "68"            # PLA: discard saved stock init input
    "a9 c0"         # LDA #$C0: active, no gravity like stock Ghost
    "85 04"         # STA $04
    "a5 05"         # LDA $05: enemy ID
    "29 01"         # AND #$01: even=right, odd=left
    "20 1c 9d"      # JSR $9D1C stock init writer
    "a5 06"         # LDA $06: current main-slot index
    "20 56 b1"      # JSR $B156: sub-slot pointer in $00/$01
    "a0 07"         # LDY #$07
    "a9 80"         # LDA #$80: arm cooldown for the first shot
    "91 00"         # STA ($00),Y
    "60"            # RTS
)


class _Asm:
    def __init__(self):
        self.data = bytearray()
        self.labels: dict[str, int] = {}
        self.fixups: list[tuple[int, int, str]] = []

    def label(self, name: str) -> None:
        self.labels[name] = len(self.data)

    def b(self, *values: int) -> None:
        self.data.extend(v & 0xFF for v in values)

    def jsr(self, addr: int) -> None:
        self.b(0x20, addr & 0xFF, addr >> 8)

    def branch(self, opcode: int, label: str) -> None:
        self.fixups.append((len(self.data), opcode & 0xFF, label))
        self.b(opcode, 0x00)

    def finish(self) -> bytes:
        for pos, opcode, label in self.fixups:
            if label not in self.labels:
                raise ValueError(f"unknown label: {label}")
            rel = self.labels[label] - (pos + 2)
            if not -128 <= rel <= 127:
                raise ValueError(f"branch out of range: {label}")
            self.data[pos] = opcode
            self.data[pos + 1] = rel & 0xFF
        return bytes(self.data)


def _build_ai_runtime() -> bytes:
    a = _Asm()
    a.b(0xA0, 0x01, 0xB1, 0x2E)         # parent main[1] enemy ID
    a.b(0x29, 0x02, 0x4A, 0xAA)         # X=0 preset A, X=1 preset B
    a.b(0xBD, (CPU_RUNTIME + 4) & 0xFF, (CPU_RUNTIME + 4) >> 8)
    a.b(0x48)                             # save Bullet direction
    a.b(0xA5, 0x2C, 0x48, 0xA5, 0x2D, 0x48, 0xA5, 0x2E, 0x48, 0xA5, 0x2F, 0x48)
    a.jsr(CPU_STOCK_GHOST_AI)
    a.b(0x68, 0x85, 0x2F, 0x68, 0x85, 0x2E, 0x68, 0x85, 0x2D, 0x68, 0x85, 0x2C)
    a.b(0xA0, 0x03, 0xB1, 0x2E, 0x29, 0x0C)
    a.branch(0xD0, "rts")
    a.b(0xA0, 0x07, 0xB1, 0x2C)
    a.branch(0x10, "rts")
    a.b(0x29, 0x7F)
    a.branch(0xF0, "try_fire")
    a.b(0x38, 0xE9, 0x01, 0x09, COOLDOWN_ARMED, 0x91, 0x2C)
    a.branch(0xD0, "rts")
    a.label("try_fire")
    a.jsr(CPU_FIND_FREE_SUB_SLOT)
    a.branch(0x90, "no_slot")
    a.b(0xA0, 0x00, 0xA9, 0x80, 0x91, 0x04)
    a.b(0xA9, 0x01, 0x11, 0x2C, 0x91, 0x2C)
    a.b(0x8A, 0xA0, 0x06, 0x91, 0x2C)
    a.b(0x68, 0xAA)
    a.jsr(CPU_BULLET_SPAWN)
    a.b(0xA0, 0x01, 0xB1, 0x2E)
    a.b(0x29, 0x02, 0x4A, 0xAA)
    a.b(0xBD, (CPU_RUNTIME + 2) & 0xFF, (CPU_RUNTIME + 2) >> 8)
    a.b(0xA0, 0x07, 0x91, 0x2C)
    a.branch(0xD0, "done")
    a.label("no_slot")
    a.b(0x68, 0x60)
    a.label("rts")
    a.b(0x68)
    a.label("done")
    a.b(0x60)
    return a.finish()


OFF_AI_DISPATCH = OFF_INIT_STATUS + len(INIT_STATUS_RUNTIME)
CPU_AI_DISPATCH = CPU_INIT_STATUS + len(INIT_STATUS_RUNTIME)
AI_RUNTIME = _build_ai_runtime()

OFF_PROPERTY_META_LOAD = OFF_AI_DISPATCH + len(AI_RUNTIME)
CPU_PROPERTY_META_LOAD = CPU_AI_DISPATCH + len(AI_RUNTIME)

PROPERTY_META_RUNTIME = bytes((
    0xA5, 0x05,                         # LDA $05: spawn enemy ID
    0x29, 0xFC,                         # AND #$FC: normalize $B0-$B3
    0xC9, FIRST_ID,                     # CMP #$B0
    0xD0, 0x03,                         # BNE stock property table
    0xA9, 0x4A,                         # LDA #$4A: same property input as $86
    0x60,                               # RTS
    0xB9, 0x0E, 0xA3,                   # LDA $A30E,Y
    0x60,                               # RTS
))

RUNTIME = (
    PARAMETER_TABLES
    + SETUP_META_RUNTIME
    + INIT_STATUS_RUNTIME
    + AI_RUNTIME
    + PROPERTY_META_RUNTIME
)
CPU_RUNTIME_END = CPU_RUNTIME + len(RUNTIME)
RESERVED_SPANS = ((OFF_RUNTIME, len(RUNTIME)),)

assert len(PARAMETER_TABLES) == 6
assert len(SETUP_META_RUNTIME) == 14
assert len(INIT_STATUS_RUNTIME) == 24
assert len(PROPERTY_META_RUNTIME) == 15
assert len(RUNTIME) <= MAX_RUNTIME_SIZE
assert CPU_RUNTIME + len(RUNTIME) == CPU_RUNTIME_END


def levels_need_runtime(levels: list) -> bool:
    for lv in levels or []:
        for enemy in getattr(lv, "enemies", []) or []:
            if (
                getattr(enemy, "type", None) == ElementType.ENEMY
                and FIRST_ID <= int(enemy.element_no) <= LAST_ID
            ):
                return True
    return False
