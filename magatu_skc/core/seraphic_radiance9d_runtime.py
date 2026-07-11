"""Seraphic Radiance enemy ID $9D runtime for mapper66 saved ROMs."""
from __future__ import annotations

from .element import ElementType


NEW_ENEMY_ID = 0x9D

OFF_RUNTIME = 0x6C7C
CPU_RUNTIME = 0xEC6C
RUNTIME_CAPACITY = 0x11C

OFF_AUX_RUNTIME = 0x3F7C
CPU_AUX_RUNTIME = 0xBF6C
CPU_SOUND_HELPER = CPU_AUX_RUNTIME + 10

CPU_STOCK_INIT = 0x9D1C
CPU_MAIN_TO_SUB_PTR = 0xB156
CPU_MAIN_PTR_LO = 0xB329
CPU_MAIN_PTR_HI = 0xB33E
CPU_SUB_PTR_LO = 0xB306
CPU_SUB_PTR_HI = 0xB317


class _Asm:
    def __init__(self):
        self.data = bytearray()
        self.labels: dict[str, int] = {}
        self.fixups: list[tuple[int, int, str, str]] = []

    def label(self, name: str) -> None:
        self.labels[name] = len(self.data)

    def b(self, *values: int) -> None:
        self.data.extend(v & 0xFF for v in values)

    def jsr(self, addr: int) -> None:
        self.b(0x20, addr & 0xFF, addr >> 8)

    def branch(self, opcode: int, label: str) -> None:
        self.fixups.append((len(self.data), opcode & 0xFF, label, "rel"))
        self.b(opcode, 0x00)

    def finish(self, cpu_base: int) -> bytes:
        for pos, opcode, label, mode in self.fixups:
            if label not in self.labels:
                raise ValueError(f"unknown label: {label}")
            self.data[pos] = opcode
            rel = self.labels[label] - (pos + 2)
            if mode != "rel" or not -128 <= rel <= 127:
                raise ValueError(f"branch out of range: {label}")
            self.data[pos + 1] = rel & 0xFF
        return bytes(self.data)


SETUP_META_RUNTIME = bytes.fromhex(
    "a9 0e"         # LDA #$0E: stock Fairy group supplies safe no-gravity setup
    "85 0e"         # STA $0E
    "a8"            # TAY
    "b9 d3 d9"      # LDA $D9D3,Y
    "60"            # RTS
)

OFF_SETUP_META_LOAD = OFF_RUNTIME
CPU_SETUP_META_LOAD = CPU_RUNTIME
OFF_INIT_STATUS = OFF_SETUP_META_LOAD + len(SETUP_META_RUNTIME)
CPU_INIT_STATUS = CPU_SETUP_META_LOAD + len(SETUP_META_RUNTIME)


def _build_init_runtime() -> bytes:
    a = _Asm()
    a.b(0x68)                              # PLA: discard saved stock-init input
    a.b(0xA9, 0xC0, 0x85, 0x04)          # active, visible, no gravity
    a.b(0xA9, NEW_ENEMY_ID, 0x85, 0x05)  # preserve type $9D
    a.b(0xA9, 0x00)
    a.jsr(CPU_STOCK_INIT)
    a.b(0xA5, 0x06)
    a.jsr(CPU_MAIN_TO_SUB_PTR)
    a.b(0xA0, 0x07, 0xA9, 0x00, 0x91, 0x00)  # sub[7]: right/down direction
    a.b(0x60)
    return a.finish(CPU_INIT_STATUS)


INIT_STATUS_RUNTIME = _build_init_runtime()
OFF_AI_DISPATCH = OFF_INIT_STATUS + len(INIT_STATUS_RUNTIME)
CPU_AI_DISPATCH = CPU_INIT_STATUS + len(INIT_STATUS_RUNTIME)


def _build_ai_runtime() -> bytes:
    a = _Asm()
    # Vertical 1 px/frame movement. sub[7] bit1: 0=down, 1=up.
    a.b(0xA0, 0x07, 0xB1, 0x2C, 0x29, 0x02)
    a.branch(0xD0, "move_up")
    a.b(0xA0, 0x07, 0xB1, 0x2E, 0xC9, 0xD0)
    a.branch(0xB0, "turn_up")
    a.b(0x18, 0x69, 0x01, 0x91, 0x2E)
    a.branch(0xD0, "move_x")
    a.label("turn_up")
    a.b(0xA0, 0x07, 0xB1, 0x2C, 0x09, 0x02, 0x91, 0x2C)
    a.branch(0xD0, "move_x")
    a.label("move_up")
    a.b(0xA0, 0x07, 0xB1, 0x2E, 0xC9, 0x20)
    a.branch(0x90, "turn_down")
    a.branch(0xF0, "turn_down")
    a.b(0x38, 0xE9, 0x01, 0x91, 0x2E)
    a.branch(0xD0, "move_x")
    a.label("turn_down")
    a.b(0xA0, 0x07, 0xB1, 0x2C, 0x29, 0xFD, 0x91, 0x2C)

    # Horizontal 1 px/frame movement. sub[7] bit0: 0=right, 1=left.
    a.label("move_x")
    a.b(0xA0, 0x07, 0xB1, 0x2C, 0x29, 0x01)
    a.branch(0xD0, "move_left")
    a.b(0xA0, 0x0A, 0xB1, 0x2E, 0xC9, 0xE8)
    a.branch(0xB0, "turn_left")
    a.b(0x18, 0x69, 0x01, 0x91, 0x2E)
    a.branch(0xD0, "collide")
    a.label("turn_left")
    a.b(0xA0, 0x07, 0xB1, 0x2C, 0x09, 0x01, 0x91, 0x2C)
    a.branch(0xD0, "collide")
    a.label("move_left")
    a.b(0xA0, 0x0A, 0xB1, 0x2E, 0xC9, 0x08)
    a.branch(0x90, "turn_right")
    a.branch(0xF0, "turn_right")
    a.b(0x38, 0xE9, 0x01, 0x91, 0x2E)
    a.branch(0xD0, "collide")
    a.label("turn_right")
    a.b(0xA0, 0x07, 0xB1, 0x2C, 0x29, 0xFE, 0x91, 0x2C)

    # Scan all 15 main slots. A 16x16 overlap clears main+paired sub slot only;
    # no stock death/drop/score route is called.
    a.label("collide")
    a.b(0xA2, 0x0E)
    a.label("scan")
    a.b(0xBD, CPU_MAIN_PTR_LO & 0xFF, CPU_MAIN_PTR_LO >> 8, 0x85, 0x00)
    a.b(0xBD, CPU_MAIN_PTR_HI & 0xFF, CPU_MAIN_PTR_HI >> 8, 0x85, 0x01)
    a.b(0xA5, 0x00, 0xC5, 0x2E)
    a.branch(0xD0, "active")
    a.b(0xA5, 0x01, 0xC5, 0x2F)
    a.branch(0xF0, "next")
    a.label("active")
    a.b(0xA0, 0x00, 0xB1, 0x00)
    a.branch(0x10, "next")
    a.b(0xC8, 0xB1, 0x00, 0xC9, NEW_ENEMY_ID)
    a.branch(0xF0, "next")
    a.b(0xA0, 0x0A, 0xB1, 0x00, 0x38, 0xF1, 0x2E)
    a.branch(0xB0, "x_abs")
    a.b(0x49, 0xFF, 0x69, 0x01)
    a.label("x_abs")
    a.b(0xC9, 0x10)
    a.branch(0xB0, "next")
    a.b(0xA0, 0x07, 0xB1, 0x00, 0x38, 0xF1, 0x2E)
    a.branch(0xB0, "y_abs")
    a.b(0x49, 0xFF, 0x69, 0x01)
    a.label("y_abs")
    a.b(0xC9, 0x10)
    a.branch(0xB0, "next")
    a.b(0xA9, 0x00, 0xA0, 0x00, 0x91, 0x00)  # clear target main status
    a.b(0x8A, 0x18, 0x69, 0x02, 0xA8)
    a.b(0xB9, CPU_SUB_PTR_LO & 0xFF, CPU_SUB_PTR_LO >> 8, 0x85, 0x00)
    a.b(0xB9, CPU_SUB_PTR_HI & 0xFF, CPU_SUB_PTR_HI >> 8, 0x85, 0x01)
    a.b(0xA0, 0x00, 0xA9, 0x00, 0x91, 0x00)  # clear paired sub status
    a.jsr(CPU_SOUND_HELPER)                     # stock block-removal sound
    a.label("next")
    a.b(0xCA)
    a.branch(0x10, "scan")
    a.b(0x60)
    return a.finish(CPU_AI_DISPATCH)


AI_DISPATCH_RUNTIME = _build_ai_runtime()
OFF_ANIM_UPDATE = OFF_AI_DISPATCH + len(AI_DISPATCH_RUNTIME)
CPU_ANIM_UPDATE = CPU_AI_DISPATCH + len(AI_DISPATCH_RUNTIME)


ANIM_UPDATE_RUNTIME = bytes.fromhex(
    "a5 21"         # LDA $21: global frame counter
    "29 08"         # alternate every 8 frames
    "f0 06"         # BEQ frame031
    "a9 b2"         # frame030 tile 1
    "a2 cf"         # frame030 packed attr
    "d0 04"         # always store
    "a9 b0"         # frame031 tile 1
    "a2 ce"         # frame031 packed attr
    "a0 11"         # main[17] tile 1
    "91 08"
    "c8"            # main[18] tile 2
    "91 08"
    "c8"            # main[19] attr
    "8a"
    "91 08"
    "60"
)

RUNTIME = SETUP_META_RUNTIME + INIT_STATUS_RUNTIME + AI_DISPATCH_RUNTIME + ANIM_UPDATE_RUNTIME
CPU_RUNTIME_END = CPU_RUNTIME + len(RUNTIME)

AI_HALF_SPEED_WRAPPER = bytes(
    (
        0xA5, 0x21,              # LDA $21
        0x29, 0x01,              # AND #$01
        0xF0, 0x01,              # BEQ run_ai
        0x60,                    # RTS on odd frames
        0x4C, CPU_AI_DISPATCH & 0xFF, CPU_AI_DISPATCH >> 8,
    )
)

SOUND_HELPER = bytes.fromhex(
    "a0 08"                     # LDY #$08: stock block-removal sound
    "4c 8d 8e"                  # JMP $8E8D; its RTS returns to AI caller
)

AUX_RUNTIME = AI_HALF_SPEED_WRAPPER + SOUND_HELPER
CPU_AI_ENTRY = CPU_AUX_RUNTIME
RESERVED_SPANS = (
    (OFF_RUNTIME, len(RUNTIME)),
    (OFF_AUX_RUNTIME, len(AUX_RUNTIME)),
)

assert len(RUNTIME) <= RUNTIME_CAPACITY
assert CPU_RUNTIME + len(RUNTIME) == CPU_RUNTIME_END
assert len(RUNTIME) == RUNTIME_CAPACITY
assert len(AI_HALF_SPEED_WRAPPER) == 10
assert len(SOUND_HELPER) == 5
assert len(AUX_RUNTIME) == 15


def levels_need_runtime(levels: list) -> bool:
    for lv in levels or []:
        for enemy in getattr(lv, "enemies", []) or []:
            if getattr(enemy, "type", None) == ElementType.ENEMY and int(enemy.element_no) == NEW_ENEMY_ID:
                return True
    return False
