"""Back Fire enemy ID $8A runtime body for mapper66 saved ROMs."""
from __future__ import annotations

from .element import ElementType


NEW_ENEMY_ID = 0x8A

OFF_RUNTIME = 0x6ED1
OFF_SETUP_META_LOAD = OFF_RUNTIME

CPU_RUNTIME = 0xEEC1
CPU_SETUP_META_LOAD = CPU_RUNTIME
CPU_STOCK_GHOST_AI = 0xABF7
CPU_FIND_FREE_SUB_SLOT = 0xB2EA
CPU_BULLET_SPAWN = 0xAE76
CPU_SUB_SLOT_PTR = 0xB156
CPU_STOCK_INIT = 0x9D1C

COOLDOWN_ARMED = 0x80
COOLDOWN_RELOAD = 0xC0

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
    "a5 06"         # LDA $06: current main-slot index
    "20 56 b1"      # JSR $B156: sub-slot pointer in $00/$01
    "a0 07"         # LDY #$07
    "a9 80"         # LDA #$80: arm Back Fire cooldown flag
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
    # First pass duplicates Bomber/Cannon Ghost instead of sharing it. If the enemy
    # proves useful, issue #68 tracks a later refactor into a common fire path.
    a.b(0xA5, 0x2C, 0x48, 0xA5, 0x2D, 0x48, 0xA5, 0x2E, 0x48, 0xA5, 0x2F, 0x48)
    a.jsr(CPU_STOCK_GHOST_AI)
    a.b(0x68, 0x85, 0x2F, 0x68, 0x85, 0x2E, 0x68, 0x85, 0x2D, 0x68, 0x85, 0x2C)
    a.b(0xA0, 0x03, 0xB1, 0x2E, 0x29, 0x0C)  # stock Ghost wall/break states
    a.branch(0xD0, "rts")
    a.b(0xA0, 0x07, 0xB1, 0x2C)          # parent sub[7] cooldown
    a.branch(0x10, "rts")                 # bit7 clear: not armed
    a.b(0x29, 0x7F)
    a.branch(0xF0, "try_fire")
    a.b(0x38, 0xE9, 0x01, 0x09, COOLDOWN_ARMED, 0x91, 0x2C)
    a.branch(0xD0, "rts")
    a.label("try_fire")
    a.jsr(CPU_FIND_FREE_SUB_SLOT)
    a.branch(0x90, "no_slot")
    a.b(0xA0, 0x00, 0xA9, 0x80, 0x91, 0x04)  # child sub[0] active
    a.b(0xA9, 0x01, 0x11, 0x2C, 0x91, 0x2C)  # parent sub[0] bit0 owns child
    a.b(0x8A, 0xA0, 0x06, 0x91, 0x2C)        # parent sub[6] child index
    a.b(0xA0, 0x08, 0xB1, 0x2E, 0xC9, 0x40, 0xA2, 0x01, 0x90, 0x01, 0xCA)  # X=opposite of current X velocity
    a.jsr(CPU_BULLET_SPAWN)
    a.b(0xA0, 0x07, 0xA9, COOLDOWN_RELOAD, 0x91, 0x2C)
    a.branch(0xD0, "done")
    a.label("no_slot")
    a.label("rts")
    a.label("done")
    a.b(0x60)
    return a.finish()


OFF_AI_DISPATCH = OFF_INIT_STATUS + len(INIT_STATUS_RUNTIME)
CPU_AI_DISPATCH = CPU_INIT_STATUS + len(INIT_STATUS_RUNTIME)

AI_RUNTIME = _build_ai_runtime()

RUNTIME = SETUP_META_RUNTIME + INIT_STATUS_RUNTIME + AI_RUNTIME
CPU_RUNTIME_END = CPU_RUNTIME + len(RUNTIME)

RESERVED_SPANS = ((OFF_RUNTIME, len(RUNTIME)),)

assert len(SETUP_META_RUNTIME) == CPU_INIT_STATUS - CPU_SETUP_META_LOAD
assert len(INIT_STATUS_RUNTIME) == CPU_AI_DISPATCH - CPU_INIT_STATUS
assert len(SETUP_META_RUNTIME) == 9
assert len(INIT_STATUS_RUNTIME) == 22
assert len(AI_RUNTIME) == 99
assert len(RUNTIME) == 130
assert CPU_RUNTIME + len(RUNTIME) == CPU_RUNTIME_END


def levels_need_runtime(levels: list) -> bool:
    for lv in levels or []:
        for enemy in getattr(lv, "enemies", []) or []:
            if getattr(enemy, "type", None) == ElementType.ENEMY and int(enemy.element_no) == NEW_ENEMY_ID:
                return True
    return False
